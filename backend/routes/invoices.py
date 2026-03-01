"""Invoice routes for fatturazione."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List
from io import BytesIO
import uuid
from datetime import datetime, timezone, date
from core.security import get_current_user
from core.database import db
from models.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    InvoiceStatusUpdate, ConvertInvoiceRequest, DocumentType, InvoiceStatus
)
from services.invoice_service import invoice_service
from services.pdf_service import pdf_service
from services.xml_service import xml_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/", response_model=InvoiceListResponse)
async def get_invoices(
    document_type: Optional[DocumentType] = None,
    status: Optional[InvoiceStatus] = None,
    client_id: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get all invoices with filters."""
    query = {"user_id": user["user_id"]}
    
    if document_type:
        query["document_type"] = document_type.value
    if status:
        query["status"] = status.value
    if client_id:
        query["client_id"] = client_id
    if year:
        query["document_number"] = {"$regex": f"-{year}-"}
    
    total = await db.invoices.count_documents(query)
    
    invoices_cursor = db.invoices.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    invoices = await invoices_cursor.to_list(length=limit)
    
    # Populate client names
    for inv in invoices:
        client = await db.clients.find_one(
            {"client_id": inv.get("client_id")},
            {"_id": 0, "business_name": 1}
        )
        inv["client_name"] = client.get("business_name") if client else "N/A"
    
    return InvoiceListResponse(
        invoices=[InvoiceResponse(**inv) for inv in invoices],
        total=total
    )


@router.get("/quick-fill/sources")
async def get_quick_fill_sources(
    q: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List preventivi and DDT available for quick fill into an invoice."""
    uid = user["user_id"]
    sources = []

    # Fetch Preventivi (exclude already converted or cancelled)
    if not doc_type or doc_type == "preventivo":
        prev_q = {"user_id": uid, "status": {"$nin": ["annullato"]}}
        if q:
            prev_q["$or"] = [
                {"number": {"$regex": q, "$options": "i"}},
                {"subject": {"$regex": q, "$options": "i"}},
                {"client_name": {"$regex": q, "$options": "i"}},
            ]
        prev_cursor = db.preventivi.find(prev_q, {"_id": 0}).sort("created_at", -1).limit(50)
        prevs = await prev_cursor.to_list(50)
        for p in prevs:
            if p.get("client_id"):
                c = await db.clients.find_one({"client_id": p["client_id"]}, {"_id": 0, "business_name": 1})
                p["client_name"] = c.get("business_name") if c else ""
            sources.append({
                "source_type": "preventivo",
                "source_id": p.get("preventivo_id"),
                "number": p.get("number", ""),
                "client_name": p.get("client_name", ""),
                "client_id": p.get("client_id", ""),
                "subject": p.get("subject", ""),
                "total": p.get("totals", {}).get("total", 0),
                "date": str(p.get("created_at", ""))[:10],
                "status": p.get("status", ""),
                "converted_to": p.get("converted_to"),
                "lines": p.get("lines", []),
                "sconto_globale": p.get("sconto_globale", 0),
                "acconto": p.get("acconto", 0),
                "payment_type_id": p.get("payment_type_id"),
                "payment_type_label": p.get("payment_type_label"),
            })

    # Fetch DDT (non fatturato)
    if not doc_type or doc_type == "ddt":
        ddt_q = {"user_id": uid}
        if q:
            ddt_q["$or"] = [
                {"number": {"$regex": q, "$options": "i"}},
                {"subject": {"$regex": q, "$options": "i"}},
                {"client_name": {"$regex": q, "$options": "i"}},
            ]
        ddt_cursor = db.ddt_documents.find(ddt_q, {"_id": 0}).sort("created_at", -1).limit(50)
        ddts = await ddt_cursor.to_list(50)
        for d in ddts:
            sources.append({
                "source_type": "ddt",
                "source_id": d.get("ddt_id"),
                "number": d.get("number", ""),
                "client_name": d.get("client_name", ""),
                "client_id": d.get("client_id", ""),
                "subject": d.get("subject", ""),
                "total": d.get("totals", {}).get("total", 0),
                "date": str(d.get("created_at", ""))[:10],
                "status": d.get("status", ""),
                "converted_to": d.get("converted_to"),
                "lines": d.get("lines", []),
                "sconto_globale": d.get("sconto_globale", 0),
                "acconto": d.get("acconto", 0),
                "ddt_type": d.get("ddt_type", ""),
            })

    return {"sources": sources, "total": len(sources)}


@router.post("/from-preventivo/{preventivo_id}")
async def create_invoice_from_preventivo(
    preventivo_id: str,
    user: dict = Depends(get_current_user),
):
    """Create an Invoice (bozza) from an existing Preventivo. Copies lines, client, notes."""
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    if prev.get("converted_to"):
        raise HTTPException(409, f"Preventivo già convertito in fattura {prev['converted_to']}")

    client_id = prev.get("client_id")
    if not client_id:
        raise HTTPException(422, "Preventivo senza cliente. Assegnare un cliente prima della conversione.")

    now = datetime.now(timezone.utc)
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    year = now.year

    count = await db.invoices.count_documents({"user_id": uid, "document_type": {"$in": ["fattura", "FT"]}})
    doc_number = f"FT-{year}/{count + 1:04d}"

    # Map lines
    invoice_lines = []
    for line in prev.get("lines", []):
        lt = float(line.get("line_total", 0))
        vat_r = line.get("vat_rate", "22")
        invoice_lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "code": line.get("codice_articolo", ""),
            "description": line.get("description", ""),
            "quantity": float(line.get("quantity", 1)),
            "unit_price": float(line.get("prezzo_netto") or line.get("unit_price", 0)),
            "discount_percent": 0,
            "vat_rate": vat_r,
            "line_total": lt,
            "vat_amount": round(lt * float(vat_r) / 100, 2),
        })

    sg = float(prev.get("sconto_globale", 0))
    subtotal = sum(r["line_total"] for r in invoice_lines)
    sconto_val = round(subtotal * sg / 100, 2) if sg else 0
    taxable = subtotal - sconto_val
    total_vat = sum(r["vat_amount"] for r in invoice_lines)
    if sg:
        total_vat = round(total_vat * (1 - sg / 100), 2)

    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": uid,
        "document_type": "FT",
        "document_number": doc_number,
        "client_id": client_id,
        "issue_date": now.strftime("%Y-%m-%d"),
        "due_date": None,
        "status": "bozza",
        "payment_method": "bonifico",
        "payment_terms": "30gg",
        "tax_settings": {
            "apply_rivalsa_inps": False, "rivalsa_inps_rate": 4.0,
            "apply_cassa": False, "cassa_type": None, "cassa_rate": 4.0,
            "apply_ritenuta": False, "ritenuta_rate": 20.0, "ritenuta_base": "imponibile",
        },
        "lines": invoice_lines,
        "totals": {
            "subtotal": round(subtotal, 2),
            "taxable_amount": round(taxable, 2),
            "total_vat": round(total_vat, 2),
            "total_document": round(taxable + total_vat, 2),
            "total_due": round(subtotal + total_vat, 2),
        },
        "notes": f"Rif. Preventivo {prev.get('number', preventivo_id)}. {prev.get('notes', '') or ''}".strip(),
        "internal_notes": None,
        "created_at": now,
        "updated_at": now,
        "converted_from": preventivo_id,
        "converted_to": None,
    }

    await db.invoices.insert_one(invoice_doc)
    await db.preventivi.update_one(
        {"preventivo_id": preventivo_id},
        {"$set": {"status": "accettato", "converted_to": invoice_id, "updated_at": now}},
    )

    return {
        "message": f"Fattura {doc_number} creata da Preventivo {prev.get('number', '')}",
        "invoice_id": invoice_id,
        "document_number": doc_number,
    }


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific invoice by ID."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": invoice.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    invoice["client_name"] = client.get("business_name") if client else "N/A"
    
    return InvoiceResponse(**invoice)


@router.post("/", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    invoice_data: InvoiceCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new invoice/document."""
    # Verify client exists
    client = await db.clients.find_one(
        {"client_id": invoice_data.client_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    year = invoice_data.issue_date.year
    
    # Get next document number
    document_number = await invoice_service.get_next_number(
        user["user_id"],
        invoice_data.document_type,
        year
    )
    
    # Calculate lines
    calculated_lines = [
        invoice_service.calculate_line(line)
        for line in invoice_data.lines
    ]
    
    # Calculate totals
    totals = invoice_service.calculate_totals(
        calculated_lines,
        invoice_data.tax_settings
    )
    
    # Calculate due date if not provided
    due_date = invoice_data.due_date
    if not due_date and invoice_data.document_type == DocumentType.FATTURA:
        due_date = invoice_service.calculate_due_date(
            invoice_data.issue_date,
            invoice_data.payment_terms.value
        )
    
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"],
        "document_type": invoice_data.document_type.value,
        "document_number": document_number,
        "client_id": invoice_data.client_id,
        "issue_date": invoice_data.issue_date.isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "status": InvoiceStatus.BOZZA.value,
        "payment_method": invoice_data.payment_method.value,
        "payment_terms": invoice_data.payment_terms.value,
        "tax_settings": invoice_data.tax_settings.model_dump(),
        "lines": calculated_lines,
        "totals": totals.model_dump(),
        "notes": invoice_data.notes,
        "internal_notes": invoice_data.internal_notes,
        "created_at": now,
        "updated_at": now,
        "converted_from": None,
        "converted_to": None
    }
    
    await db.invoices.insert_one(invoice_doc)
    
    # Retrieve without _id
    created = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    created["client_name"] = client.get("business_name")
    
    logger.info(f"Invoice created: {document_number} by user {user['user_id']}")
    return InvoiceResponse(**created)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing invoice."""
    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Can only edit drafts
    if existing.get("status") not in [InvoiceStatus.BOZZA.value, "bozza"]:
        raise HTTPException(
            status_code=400,
            detail="Solo i documenti in bozza possono essere modificati"
        )
    
    update_dict = {}
    
    # Update client if changed
    if invoice_data.client_id:
        client = await db.clients.find_one(
            {"client_id": invoice_data.client_id, "user_id": user["user_id"]}
        )
        if not client:
            raise HTTPException(status_code=400, detail="Cliente non trovato")
        update_dict["client_id"] = invoice_data.client_id
    
    # Update other fields
    if invoice_data.issue_date:
        update_dict["issue_date"] = invoice_data.issue_date.isoformat()
    if invoice_data.due_date:
        update_dict["due_date"] = invoice_data.due_date.isoformat()
    if invoice_data.payment_method:
        update_dict["payment_method"] = invoice_data.payment_method.value
    if invoice_data.payment_terms:
        update_dict["payment_terms"] = invoice_data.payment_terms.value
    if invoice_data.notes is not None:
        update_dict["notes"] = invoice_data.notes
    if invoice_data.internal_notes is not None:
        update_dict["internal_notes"] = invoice_data.internal_notes
    
    # Recalculate if lines or tax settings changed
    if invoice_data.lines is not None or invoice_data.tax_settings is not None:
        lines = invoice_data.lines if invoice_data.lines else []
        tax_settings = invoice_data.tax_settings or existing.get("tax_settings", {})
        
        if invoice_data.lines:
            calculated_lines = [
                invoice_service.calculate_line(line)
                for line in invoice_data.lines
            ]
            update_dict["lines"] = calculated_lines
        else:
            calculated_lines = existing.get("lines", [])
        
        if invoice_data.tax_settings:
            update_dict["tax_settings"] = invoice_data.tax_settings.model_dump()
            from models.invoice import TaxSettings
            tax_obj = invoice_data.tax_settings
        else:
            from models.invoice import TaxSettings
            tax_obj = TaxSettings(**existing.get("tax_settings", {}))
        
        totals = invoice_service.calculate_totals(calculated_lines, tax_obj)
        update_dict["totals"] = totals.model_dump()
    
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": update_dict}
    )
    
    updated = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Invoice updated: {invoice_id}")
    return InvoiceResponse(**updated)


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    status_update: InvoiceStatusUpdate,
    user: dict = Depends(get_current_user)
):
    """Update invoice status."""
    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Validate status transitions
    current_status = existing.get("status")
    new_status = status_update.status.value
    
    # Define valid transitions
    valid_transitions = {
        "bozza": ["emessa", "annullata"],
        "emessa": ["inviata_sdi", "pagata", "annullata"],
        "inviata_sdi": ["accettata", "rifiutata"],
        "accettata": ["pagata", "scaduta"],
        "rifiutata": ["bozza"],
        "pagata": [],
        "scaduta": ["pagata"],
        "annullata": []
    }
    
    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Transizione non valida: {current_status} -> {new_status}"
        )
    
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    updated = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Invoice status updated: {invoice_id} -> {new_status}")
    return InvoiceResponse(**updated)


@router.post("/convert", response_model=InvoiceResponse)
async def convert_document(
    convert_request: ConvertInvoiceRequest,
    user: dict = Depends(get_current_user)
):
    """Convert document(s) (e.g., Preventivo -> Fattura, DDT -> Fattura)."""
    if not convert_request.source_ids:
        raise HTTPException(status_code=400, detail="Nessun documento sorgente specificato")
    
    # Get source documents
    sources = []
    for source_id in convert_request.source_ids:
        doc = await db.invoices.find_one(
            {"invoice_id": source_id, "user_id": user["user_id"]},
            {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail=f"Documento {source_id} non trovato")
        sources.append(doc)
    
    # Validate conversion (all must have same client for merge)
    client_ids = set(s.get("client_id") for s in sources)
    if len(client_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail="Per unire documenti, devono avere lo stesso cliente"
        )
    
    # Use first source as base
    base = sources[0]
    client_id = base.get("client_id")
    
    # Merge lines from all sources
    all_lines = []
    for source in sources:
        all_lines.extend(source.get("lines", []))
    
    # Create new invoice
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    year = datetime.now().year
    
    document_number = await invoice_service.get_next_number(
        user["user_id"],
        convert_request.target_type,
        year
    )
    
    # Recalculate totals
    from models.invoice import TaxSettings
    tax_settings = TaxSettings(**base.get("tax_settings", {}))
    totals = invoice_service.calculate_totals(all_lines, tax_settings)
    
    # Calculate due date for fattura
    due_date = None
    if convert_request.target_type == DocumentType.FATTURA:
        due_date = invoice_service.calculate_due_date(
            date.today(),
            base.get("payment_terms", "30gg")
        )
    
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"],
        "document_type": convert_request.target_type.value,
        "document_number": document_number,
        "client_id": client_id,
        "issue_date": date.today().isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "status": InvoiceStatus.BOZZA.value,
        "payment_method": base.get("payment_method", "bonifico"),
        "payment_terms": base.get("payment_terms", "30gg"),
        "tax_settings": base.get("tax_settings", {}),
        "lines": all_lines,
        "totals": totals.model_dump(),
        "notes": base.get("notes"),
        "internal_notes": f"Convertito da: {', '.join(s.get('document_number', '') for s in sources)}",
        "created_at": now,
        "updated_at": now,
        "converted_from": convert_request.source_ids[0] if len(sources) == 1 else None,
        "converted_to": None
    }
    
    await db.invoices.insert_one(invoice_doc)
    
    # Update source documents with conversion reference
    for source in sources:
        converted_to = source.get("converted_to") or []
        converted_to.append(invoice_id)
        await db.invoices.update_one(
            {"invoice_id": source.get("invoice_id")},
            {"$set": {"converted_to": converted_to}}
        )
    
    created = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "business_name": 1})
    created["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Document converted: {convert_request.source_ids} -> {document_number}")
    return InvoiceResponse(**created)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Generate and download invoice PDF."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    client = await db.clients.find_one(
        {"client_id": invoice.get("client_id")},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    # Get company settings
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    if not company:
        company = {
            "business_name": user.get("name", ""),
            "email": user.get("email", "")
        }
    
    # Generate PDF
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice, client, company)
    
    # Create filename
    filename = f"{invoice.get('document_number', 'documento')}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{invoice_id}/xml")
async def get_invoice_xml(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Generate and download FatturaPA XML for SDI."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Only fatture can be exported as XML
    if invoice.get("document_type") not in ["FT", "NC"]:
        raise HTTPException(
            status_code=400,
            detail="Solo fatture e note di credito possono essere esportate in XML"
        )
    
    client = await db.clients.find_one(
        {"client_id": invoice.get("client_id")},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    if not company or not company.get("partita_iva"):
        raise HTTPException(
            status_code=400,
            detail="Configura i dati aziendali prima di esportare XML"
        )
    
    # Generate XML
    xml_content = xml_service.generate_fattura_xml(invoice, client, company)
    
    # Create filename following SDI naming convention
    # IT + P.IVA cedente + _ + progressivo univoco + .xml
    piva = company.get("partita_iva", "").replace(" ", "")
    doc_num = invoice.get("document_number", "").replace("-", "_")
    filename = f"IT{piva}_{doc_num}.xml"
    
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ── Send Invoice via Email ──

@router.get("/{invoice_id}/preview-email")
async def preview_invoice_email(invoice_id: str, user: dict = Depends(get_current_user)):
    """Preview email that would be sent for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    client = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0})
    to_email = ""
    client_name = ""
    if client:
        client_name = client.get("business_name", "")
        to_email = client.get("pec") or client.get("email") or ""
        if not to_email:
            for contact in client.get("contacts", []):
                if contact.get("email"):
                    to_email = contact["email"]
                    break

    from services.email_preview import build_invoice_email
    doc_num = invoice.get("document_number", "")
    doc_type = invoice.get("document_type", "FT")
    total = invoice.get("totals", {}).get("total_document", 0)

    preview = build_invoice_email(
        client_name=client_name,
        document_number=doc_num,
        document_type=doc_type,
        total=total,
    )
    return {
        "to_email": to_email,
        "to_name": client_name,
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"{doc_num}.pdf",
    }



@router.post("/{invoice_id}/send-email")
async def send_invoice_email(invoice_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
    """Generate PDF and send invoice via email to client."""
    payload = payload or {}
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    client = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0})
    if not client:
        raise HTTPException(400, "Cliente non trovato")

    # Find email recipient
    to_email = client.get("pec") or client.get("email")
    if not to_email:
        # Check contacts for email preferences
        for contact in client.get("contacts", []):
            if contact.get("email") and contact.get("doc_preferences", {}).get("fatture"):
                to_email = contact["email"]
                break
    if not to_email:
        raise HTTPException(400, "Nessun indirizzo email trovato per il cliente. Aggiungi un'email o PEC nella scheda cliente.")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Generate PDF
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice, client, company)
    doc_num = invoice.get("document_number", "documento")
    filename = f"{doc_num}.pdf"

    # Send email
    from services.email_service import send_invoice_email as _send, send_email_with_attachment
    doc_type = invoice.get("document_type", "FT")
    total = invoice.get("totals", {}).get("total_document", 0)

    if payload.get("custom_subject") or payload.get("custom_body"):
        custom_subject = payload.get("custom_subject") or f"Documento {doc_num}"
        custom_body = payload.get("custom_body") or ""
        success = await send_email_with_attachment(
            to_email=to_email, subject=custom_subject, body=custom_body,
            pdf_bytes=pdf_bytes, filename=filename,
        )
    else:
        success = await _send(
            to_email=to_email,
            client_name=client.get("business_name", ""),
            document_number=doc_num,
            document_type=doc_type,
            total=total,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )

    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la configurazione Resend in Impostazioni.")

    # Track email sent
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "email_sent": True,
            "email_sent_to": to_email,
            "email_sent_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    logger.info(f"Invoice {doc_num} sent via email to {to_email}")
    return {"message": f"Email inviata con successo a {to_email}", "to": to_email}


# ── Send Invoice to SDI ──

@router.post("/{invoice_id}/send-sdi")
async def send_invoice_to_sdi(invoice_id: str, user: dict = Depends(get_current_user)):
    """Generate FatturaPA XML and send to SDI via Aruba."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    if invoice.get("document_type") not in ["FT", "NC"]:
        raise HTTPException(400, "Solo fatture e note di credito possono essere inviate al SDI")

    if invoice.get("status") == "bozza":
        raise HTTPException(400, "Non puoi inviare una bozza al SDI. Prima emetti il documento.")

    client = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0})
    if not client:
        raise HTTPException(400, "Cliente non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not company or not company.get("partita_iva"):
        raise HTTPException(400, "Configura i dati aziendali (P.IVA obbligatoria) prima di inviare al SDI")

    # Generate XML
    xml_content = xml_service.generate_fattura_xml(invoice, client, company)
    piva = company.get("partita_iva", "").replace(" ", "")
    doc_num = invoice.get("document_number", "").replace("-", "_").replace("/", "_")
    filename = f"IT{piva}_{doc_num}.xml"

    # Send to SDI via Aruba
    from services.aruba_sdi import aruba_sdi
    if not aruba_sdi.is_configured:
        raise HTTPException(400, "SDI non configurato. Inserisci SDI_API_KEY e SDI_API_SECRET nel file .env")

    result = await aruba_sdi.send_invoice(xml_content, filename)

    if not result.get("success"):
        raise HTTPException(500, f"Invio SDI fallito: {result.get('error', 'Errore sconosciuto')}")

    # Update invoice status
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "status": "inviata_sdi",
            "sdi_id": result.get("sdi_id"),
            "sdi_sent_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    logger.info(f"Invoice {doc_num} sent to SDI: {result.get('sdi_id')}")
    return {"message": "Fattura inviata al SDI con successo", "sdi_id": result.get("sdi_id")}



@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete an invoice (only drafts)."""
    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    if existing.get("status") != InvoiceStatus.BOZZA.value:
        raise HTTPException(
            status_code=400,
            detail="Solo i documenti in bozza possono essere eliminati"
        )
    
    await db.invoices.delete_one({"invoice_id": invoice_id})
    
    logger.info(f"Invoice deleted: {invoice_id}")
    return {"message": "Documento eliminato con successo"}


# ── Scadenze / Payment Tracking ─────────────────────────────────

from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField


class ScadenzaPayment(PydanticBaseModel):
    """Record a payment against an invoice."""
    importo: float = PydanticField(..., gt=0)
    data_pagamento: str  # ISO date
    metodo: Optional[str] = None
    note: Optional[str] = None


@router.get("/{invoice_id}/scadenze")
async def get_scadenze(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Get payment schedule and history for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    totals = invoice.get("totals", {})
    total_doc = totals.get("total_document", 0) or totals.get("total_to_pay", 0)
    pagamenti = invoice.get("pagamenti", [])
    pagato = sum(p.get("importo", 0) for p in pagamenti)
    residuo = round(total_doc - pagato, 2)

    # Payment status
    if pagato <= 0:
        payment_status = "non_pagata"
    elif residuo <= 0.01:
        payment_status = "pagata"
    else:
        payment_status = "parzialmente_pagata"

    return {
        "invoice_id": invoice_id,
        "document_number": invoice.get("document_number"),
        "total_document": total_doc,
        "pagamenti": pagamenti,
        "totale_pagato": round(pagato, 2),
        "residuo": max(residuo, 0),
        "payment_status": payment_status,
        "due_date": invoice.get("due_date"),
    }


@router.post("/{invoice_id}/scadenze/pagamento")
async def record_payment(
    invoice_id: str,
    payment: ScadenzaPayment,
    user: dict = Depends(get_current_user)
):
    """Record a payment for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    totals = invoice.get("totals", {})
    total_doc = totals.get("total_document", 0) or totals.get("total_to_pay", 0)
    existing_payments = invoice.get("pagamenti", [])
    already_paid = sum(p.get("importo", 0) for p in existing_payments)

    if payment.importo > (total_doc - already_paid + 0.01):
        raise HTTPException(400, "Importo supera il residuo da pagare")

    new_payment = {
        "payment_id": f"pay_{uuid.uuid4().hex[:8]}",
        "importo": payment.importo,
        "data_pagamento": payment.data_pagamento,
        "metodo": payment.metodo,
        "note": payment.note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    new_paid = already_paid + payment.importo
    residuo = round(total_doc - new_paid, 2)

    # Determine new status
    if residuo <= 0.01:
        new_status = "pagata"
    else:
        new_status = invoice.get("status")
        # Don't revert to bozza, keep current status

    update = {
        "$push": {"pagamenti": new_payment},
        "$set": {
            "totale_pagato": round(new_paid, 2),
            "residuo": max(residuo, 0),
            "payment_status": "pagata" if residuo <= 0.01 else "parzialmente_pagata",
            "updated_at": datetime.now(timezone.utc),
        }
    }
    if residuo <= 0.01:
        update["$set"]["status"] = "pagata"

    await db.invoices.update_one({"invoice_id": invoice_id}, update)

    logger.info(f"Payment recorded for {invoice_id}: {payment.importo} EUR")
    return {
        "message": "Pagamento registrato",
        "totale_pagato": round(new_paid, 2),
        "residuo": max(residuo, 0),
        "payment_status": "pagata" if residuo <= 0.01 else "parzialmente_pagata",
    }


@router.delete("/{invoice_id}/scadenze/pagamento/{payment_id}")
async def delete_payment(
    invoice_id: str,
    payment_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a recorded payment."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    pagamenti = invoice.get("pagamenti", [])
    new_pagamenti = [p for p in pagamenti if p.get("payment_id") != payment_id]

    if len(new_pagamenti) == len(pagamenti):
        raise HTTPException(404, "Pagamento non trovato")

    new_paid = sum(p.get("importo", 0) for p in new_pagamenti)
    totals = invoice.get("totals", {})
    total_doc = totals.get("total_document", 0) or totals.get("total_to_pay", 0)
    residuo = round(total_doc - new_paid, 2)

    if new_paid <= 0:
        ps = "non_pagata"
    elif residuo <= 0.01:
        ps = "pagata"
    else:
        ps = "parzialmente_pagata"

    # Update status back if needed
    update_set = {
        "pagamenti": new_pagamenti,
        "totale_pagato": round(new_paid, 2),
        "residuo": max(residuo, 0),
        "payment_status": ps,
        "updated_at": datetime.now(timezone.utc),
    }
    # If was pagata but now partially or unpaid, revert to emessa
    if invoice.get("status") == "pagata" and ps != "pagata":
        update_set["status"] = "emessa"

    await db.invoices.update_one({"invoice_id": invoice_id}, {"$set": update_set})
    return {"message": "Pagamento eliminato", "payment_status": ps}


@router.post("/{invoice_id}/duplicate", response_model=InvoiceResponse)
async def duplicate_invoice(
    invoice_id: str,
    user: dict = Depends(get_current_user)
):
    """Duplicate an existing invoice as a new draft."""
    original = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not original:
        raise HTTPException(404, "Documento non trovato")

    new_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    year = datetime.now().year

    doc_type_str = original.get("document_type", "FT")
    # Convert string to DocumentType enum for get_next_number
    doc_type_enum = DocumentType(doc_type_str)
    document_number = await invoice_service.get_next_number(user["user_id"], doc_type_enum, year)

    new_doc = {
        **original,
        "invoice_id": new_id,
        "document_number": document_number,
        "status": "bozza",
        "issue_date": date.today().isoformat(),
        "created_at": now,
        "updated_at": now,
        "converted_from": None,
        "converted_to": None,
        "pagamenti": [],
        "totale_pagato": 0,
        "residuo": 0,
        "payment_status": "non_pagata",
    }
    # Remove _id if present
    new_doc.pop("_id", None)

    await db.invoices.insert_one(new_doc)

    created = await db.invoices.find_one({"invoice_id": new_id}, {"_id": 0})
    client = await db.clients.find_one(
        {"client_id": created.get("client_id")}, {"_id": 0, "business_name": 1}
    )
    created["client_name"] = client.get("business_name") if client else "N/A"

    logger.info(f"Invoice duplicated: {invoice_id} -> {new_id}")
    return InvoiceResponse(**created)
