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
