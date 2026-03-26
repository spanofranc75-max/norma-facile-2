"""Invoice routes for fatturazione."""
import os
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional
from io import BytesIO
import uuid
import calendar
from datetime import datetime, timezone, date, timedelta
from core.security import get_current_user, tenant_match
from core.rbac import require_role
from core.database import db
from models.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceStatusUpdate, ConvertInvoiceRequest, DocumentType, InvoiceStatus
)
from services.invoice_service import invoice_service
from services.pdf_service import pdf_service
from services.xml_service import xml_service
from services.audit_trail import log_activity
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])


async def generate_scadenze_pagamento(invoice_doc: dict, uid: str):
    """Calculate and store payment deadlines from client's payment type."""
    client_id = invoice_doc.get("client_id")
    if not client_id:
        return

    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "payment_type_id": 1})
    pt_id = client.get("payment_type_id") if client else None
    if not pt_id:
        return

    pt = await db.payment_types.find_one({"payment_type_id": pt_id}, {"_id": 0})
    if not pt:
        return

    # Derive quote from legacy flags if needed
    quote_list = pt.get("quote", [])
    if not quote_list:
        flag_map = {"immediato": 0, "gg_30": 30, "gg_60": 60, "gg_90": 90, "gg_120": 120, "gg_150": 150, "gg_180": 180}
        days = sorted(d for flag, d in flag_map.items() if pt.get(flag))
        if days:
            share = round(100.0 / len(days), 2)
            quote_list = [{"giorni": d, "quota": share} for d in days]

    if not quote_list:
        return

    issue_str = invoice_doc.get("issue_date", "")
    try:
        invoice_date = date.fromisoformat(issue_str)
    except (ValueError, TypeError):
        invoice_date = date.today()

    total_due = invoice_doc.get("totals", {}).get("total_document", 0) or 0
    fine_mese = pt.get("fine_mese", False)
    richiedi_gs = pt.get("richiedi_giorno_scadenza", False)
    giorno_sc = pt.get("giorno_scadenza")

    scadenze = []
    for i, q in enumerate(quote_list):
        giorni = q.get("giorni", 0)
        quota_pct = q.get("quota", 100)
        target = invoice_date + timedelta(days=giorni)

        if fine_mese:
            last_day = calendar.monthrange(target.year, target.month)[1]
            target = target.replace(day=last_day)

        if richiedi_gs and giorno_sc:
            try:
                last_day = calendar.monthrange(target.year, target.month)[1]
                target = target.replace(day=min(giorno_sc, last_day))
            except ValueError:
                pass

        importo = round(total_due * quota_pct / 100, 2)
        scadenze.append({
            "rata": i + 1,
            "data_scadenza": target.isoformat(),
            "quota_pct": quota_pct,
            "importo": importo,
            "pagata": False,
            "data_pagamento": None,
        })

    await db.invoices.update_one(
        {"invoice_id": invoice_doc["invoice_id"]},
        {"$set": {"scadenze_pagamento": scadenze, "payment_type_id": pt_id}}
    )
    logger.info(f"Generated {len(scadenze)} scadenze for invoice {invoice_doc['invoice_id']}")


@router.get("/")
async def get_invoices(
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Get all invoices with filters."""
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    
    if document_type:
        query["document_type"] = document_type
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    if year:
        # Match both formats: "FT-2026-0001" and "1/2026"
        query["$or"] = [
            {"document_number": {"$regex": f"/{year}"}},
            {"document_number": {"$regex": f"-{year}[-/]"}},
            {"issue_date": {"$regex": f"^{year}-"}},
        ]
    
    total = await db.invoices.count_documents(query)
    
    invoices_cursor = db.invoices.find(query, {"_id": 0}).skip(skip).limit(limit).sort("issue_date", -1)
    invoices = await invoices_cursor.to_list(length=limit)
    
    # Populate client names — prefer snapshot, fallback to live lookup
    for inv in invoices:
        snapshot = inv.get("client_snapshot")
        if snapshot and snapshot.get("business_name"):
            inv["client_name"] = snapshot["business_name"]
        else:
            client = await db.clients.find_one(
                {"client_id": inv.get("client_id")},
                {"_id": 0, "business_name": 1}
            )
            inv["client_name"] = client.get("business_name") if client else inv.get("client_business_name", "N/A")
    
    return {"invoices": invoices, "total": total}


@router.get("/quick-fill/sources")
async def get_quick_fill_sources(
    q: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    user: dict = Depends(require_role("admin", "amministrazione")),
):
    """List preventivi and DDT available for quick fill into an invoice."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    sources = []

    # Fetch Preventivi (exclude already converted or cancelled)
    if not doc_type or doc_type == "preventivo":
        prev_q = {"user_id": uid, "tenant_id": tenant_match(user), "status": {"$nin": ["annullato"]}}
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
                "cup": p.get("cup", ""),
                "cig": p.get("cig", ""),
                "cuc": p.get("cuc", ""),
            })

    # Fetch DDT (non fatturato)
    if not doc_type or doc_type == "ddt":
        ddt_q = {"user_id": uid, "tenant_id": tenant_match(user)}
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
    user: dict = Depends(require_role("admin", "amministrazione")),
):
    """Create an Invoice (bozza) from an existing Preventivo. Copies lines, client, notes."""
    from services.client_snapshot import build_snapshot
    uid = user["user_id"]
    tid = user["tenant_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0})
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

    # Atomic counter for invoice numbering
    ft_counter_id = f"{uid}_FT_{year}"
    ft_existing = await db.document_counters.find_one({"counter_id": ft_counter_id})
    if not ft_existing:
        max_ft = 0
        async for inv_doc in db.invoices.find(
            {"user_id": uid, "tenant_id": tenant_match(user)},
            {"document_number": 1, "_id": 0}
        ):
            dn = inv_doc.get("document_number", "")
            try:
                if "/" in dn:
                    parts = dn.split("/")
                    num = int(parts[0])
                    inv_year = int(parts[1]) if len(parts) > 1 else 0
                    if inv_year == year and num > max_ft:
                        max_ft = num
                elif dn.startswith("FT-"):
                    num = int(dn.split("-")[-1])
                    if str(year) in dn and num > max_ft:
                        max_ft = num
            except (ValueError, IndexError, KeyError):
                pass
        if max_ft > 0:
            await db.document_counters.update_one(
                {"counter_id": ft_counter_id}, {"$set": {"counter": max_ft}}, upsert=True
            )
    ft_counter = await db.document_counters.find_one_and_update(
        {"counter_id": ft_counter_id}, {"$inc": {"counter": 1}}, upsert=True, return_document=True
    )
    doc_number = f"{ft_counter.get('counter', 1)}/{year}"

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

    # Build VAT breakdown from lines (required by frontend)
    vat_breakdown = {}
    for ln in invoice_lines:
        rate = ln.get("vat_rate", "22")
        if rate not in vat_breakdown:
            vat_breakdown[rate] = {"imponibile": 0.0, "imposta": 0.0}
        vat_breakdown[rate]["imponibile"] += ln["line_total"]
        vat_breakdown[rate]["imposta"] += ln["vat_amount"]
    for rate in vat_breakdown:
        if sg:
            vat_breakdown[rate]["imponibile"] = round(vat_breakdown[rate]["imponibile"] * (1 - sg / 100), 2)
            vat_breakdown[rate]["imposta"] = round(vat_breakdown[rate]["imposta"] * (1 - sg / 100), 2)
        else:
            vat_breakdown[rate]["imponibile"] = round(vat_breakdown[rate]["imponibile"], 2)
            vat_breakdown[rate]["imposta"] = round(vat_breakdown[rate]["imposta"], 2)

    total_document = round(taxable + total_vat, 2)

    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": uid, "tenant_id": tenant_match(user),
        "document_type": "FT",
        "document_number": doc_number,
        "client_id": client_id,
        "client_snapshot": await build_snapshot(client_id),
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
            "subtotal": round(taxable, 2),
            "vat_breakdown": vat_breakdown,
            "total_vat": round(total_vat, 2),
            "rivalsa_inps": 0.0,
            "cassa": 0.0,
            "ritenuta": 0.0,
            "total_document": total_document,
            "total_to_pay": total_document,
        },
        "notes": f"Rif. Preventivo {prev.get('number', preventivo_id)}. {prev.get('notes', '') or ''}".strip(),
        "internal_notes": None,
        "cup": prev.get("cup", ""),
        "cig": prev.get("cig", ""),
        "cuc": prev.get("cuc", ""),
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


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Get a specific invoice by ID."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Populate client name — prefer snapshot, fallback to live lookup
    snapshot = invoice.get("client_snapshot")
    if snapshot and snapshot.get("business_name"):
        invoice["client_name"] = snapshot["business_name"]
    else:
        client = await db.clients.find_one(
            {"client_id": invoice.get("client_id")},
            {"_id": 0, "business_name": 1}
        )
        invoice["client_name"] = client.get("business_name") if client else invoice.get("client_business_name", "N/A")
    
    return invoice


@router.post("/", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    invoice_data: InvoiceCreate,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Create a new invoice/document."""
    from services.client_snapshot import build_snapshot
    
    # Verify client exists
    client = await db.clients.find_one(
        {"client_id": invoice_data.client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    # Build immutable client snapshot
    client_snapshot = await build_snapshot(invoice_data.client_id)
    
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    year = invoice_data.issue_date.year
    
    # Get next document number (or use manual one)
    if invoice_data.document_number:
        document_number = invoice_data.document_number
    else:
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
            invoice_data.payment_terms
        )
    
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "document_type": invoice_data.document_type.value,
        "document_number": document_number,
        "client_id": invoice_data.client_id,
        "client_snapshot": client_snapshot,
        "issue_date": invoice_data.issue_date.isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "status": InvoiceStatus.BOZZA.value,
        "payment_method": invoice_data.payment_method.value,
        "payment_terms": invoice_data.payment_terms,
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
    await log_activity(user, "create", "fattura", invoice_id, label=document_number)
    return InvoiceResponse(**created)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Update an existing invoice."""
    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    is_draft = existing.get("status") in [InvoiceStatus.BOZZA.value, "bozza"]
    is_nc = existing.get("document_type") == "NC"
    
    # Non-draft FT: block structural changes (lines, tax, number, client, issue_date)
    # NC (Note di Credito) are always editable for lines and tax_settings
    if not is_draft and not is_nc:
        has_structural = (
            invoice_data.lines is not None
            or invoice_data.tax_settings is not None
            or invoice_data.document_number is not None
            or invoice_data.client_id is not None
            or invoice_data.issue_date is not None
        )
        if has_structural:
            raise HTTPException(
                status_code=400,
                detail="Solo i documenti in bozza possono essere modificati nelle righe, impostazioni fiscali, numero, cliente o data emissione."
            )
    
    update_dict = {}
    
    # Update document number if provided (draft only — checked above)
    if invoice_data.document_number is not None:
        update_dict["document_number"] = invoice_data.document_number
    
    # Update client if changed (draft only — checked above)
    if invoice_data.client_id:
        client = await db.clients.find_one(
            {"client_id": invoice_data.client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
        )
        if not client:
            raise HTTPException(status_code=400, detail="Cliente non trovato")
        update_dict["client_id"] = invoice_data.client_id
    
    # Update other fields (allowed on all statuses)
    if invoice_data.issue_date:
        update_dict["issue_date"] = invoice_data.issue_date.isoformat()
    if invoice_data.due_date:
        update_dict["due_date"] = invoice_data.due_date.isoformat()
    elif 'due_date' in (invoice_data.model_fields_set or set()):
        update_dict["due_date"] = None
    if invoice_data.payment_method:
        update_dict["payment_method"] = invoice_data.payment_method.value
    if invoice_data.payment_terms:
        update_dict["payment_terms"] = invoice_data.payment_terms
    if invoice_data.notes is not None:
        update_dict["notes"] = invoice_data.notes
    if invoice_data.internal_notes is not None:
        update_dict["internal_notes"] = invoice_data.internal_notes
    
    # Recalculate if lines or tax settings changed (draft only — checked above)
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



@router.patch("/{invoice_id}/renumber")
async def renumber_invoice(
    invoice_id: str,
    data: dict,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Change document number on any invoice regardless of status. For fixing numbering errors."""
    new_number = data.get("document_number", "").strip()
    if not new_number:
        raise HTTPException(400, "Numero documento obbligatorio")

    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Documento non trovato")

    old_number = existing.get("document_number", "")
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "document_number": new_number,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    logger.info(f"Invoice renumbered: {old_number} -> {new_number} by user {user['user_id']}")
    updated = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    # Return raw dict to avoid strict model validation for older invoices
    return updated


@router.post("/{invoice_id}/create-nota-credito")
async def create_nota_credito(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Create a Credit Note (Nota di Credito) from an existing invoice."""
    from services.client_snapshot import build_snapshot
    
    original = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not original:
        raise HTTPException(404, "Fattura originale non trovata")

    if original.get("document_type") not in ["FT", "NC"]:
        raise HTTPException(400, "La nota di credito può essere creata solo da una fattura o nota di credito")

    # Get next NC number
    year = datetime.now().year
    nc_number = await invoice_service.get_next_number(user["user_id"], "NC", year)

    now = datetime.now(timezone.utc).isoformat()
    nc_id = f"inv_{uuid.uuid4().hex[:16]}"

    # Copy lines from original
    nc_lines = []
    for line in original.get("lines", []):
        # Normalizza i campi per garantire
        # che la NC abbia tutti i valori corretti
        qty = float(line.get("quantity") or 1)
        price = float(
            line.get("unit_price")
            or line.get("prezzo_netto")
            or 0
        )
        discount = float(line.get("discount_percent") or 0)
        vat = line.get("vat_rate", "22")

        # Ricalcola line_total normalizzato
        net = price * (1 - discount / 100)
        lt = round(qty * net, 2)
        vat_rate_num = 0
        try:
            vat_rate_num = float(vat)
        except (ValueError, TypeError):
            vat_rate_num = 0
        vat_amt = round(lt * vat_rate_num / 100, 2)

        nc_line = {
            **line,  # Mantieni tutti i campi originali
            "line_id": f"line_{uuid.uuid4().hex[:8]}",
            # Sovrascrivi con valori normalizzati
            "quantity": qty,
            "unit_price": price,
            "discount_percent": discount,
            "vat_rate": vat,
            "line_total": lt,
            "vat_amount": vat_amt,
        }
        nc_lines.append(nc_line)

    nc_doc = {
        "invoice_id": nc_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "document_type": "NC",
        "document_number": nc_number,
        "issue_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "due_date": None,
        "status": "bozza",
        "client_id": original.get("client_id"),
        "client_snapshot": original.get("client_snapshot") or await build_snapshot(original.get("client_id")),
        "client_name": original.get("client_name"),
        "payment_method": original.get("payment_method") or "bonifico",
        "payment_terms": original.get("payment_terms") or "30gg",
        "tax_settings": original.get("tax_settings", {}),
        "lines": nc_lines,
        "totals": original.get("totals", {}),
        "notes": f"Nota di credito per storno fattura n. {original.get('document_number', '')}",
        "internal_notes": None,
        "created_at": now,
        "updated_at": now,
        "related_invoice_id": invoice_id,
        "related_invoice_number": original.get("document_number", ""),
    }

    await db.invoices.insert_one(nc_doc)

    # Se la NC è collegata a una fattura progressiva,
    # aggiorna il tracking sul preventivo
    original_prev_id = original.get("progressive_from_preventivo")
    original_prog_amount = float(original.get("progressive_amount", 0))

    if original_prev_id and original_prog_amount > 0:
        # La NC eredita il collegamento al preventivo
        # con progressive_amount per segnalare lo storno
        await db.invoices.update_one(
            {"invoice_id": nc_id},
            {"$set": {
                "progressive_from_preventivo": original_prev_id,
                "progressive_amount": original_prog_amount,
                "progressive_type": "storno",
                "document_type": "NC",
            }}
        )
        logger.info(
            f"NC {nc_id} collegata al preventivo "
            f"{original_prev_id} come storno di "
            f"{original_prog_amount}"
        )

    logger.info(f"Credit note {nc_number} created from invoice {original.get('document_number')} by user {user['user_id']}")

    # ── Audit log NC ──
    await db.outbound_audit_log.insert_one({
        "log_id": f"audit_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "action_type": "nota_credito_creata",
        "status": "success",
        "details": {
            "nc_id": nc_id,
            "nc_number": nc_number,
            "original_invoice_id": invoice_id,
            "original_invoice_number": original.get("document_number", ""),
            "client_id": original.get("client_id"),
            "client_name": original.get("client_name", ""),
            "totals": nc_doc.get("totals", {}),
        },
        "timestamp": now,
    })

    return {
        "message": f"Nota di Credito {nc_number} creata da fattura {original.get('document_number', '')}",
        "invoice_id": nc_id,
        "document_number": nc_number,
    }



@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    status_update: InvoiceStatusUpdate,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Update invoice status."""
    # PUNTO 1 — Verifica body
    if not status_update or not status_update.status:
        raise HTTPException(422, "Campo 'status' mancante nel body")

    existing = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
        "emessa": ["bozza", "inviata_sdi", "pagata", "annullata"],
        "inviata_sdi": ["accettata", "rifiutata", "pagata"],
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
    
    update_fields = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc)
    }
    
    # When marking as paid, also update payment_status
    if new_status == "pagata":
        total_doc = existing.get("totals", {}).get("total_document", 0)
        update_fields["payment_status"] = "pagata"
        update_fields["totale_pagato"] = total_doc
        update_fields["residuo"] = 0
    
    # PUNTO 2 — Wrappa update MongoDB
    try:
        await db.invoices.update_one(
            {"invoice_id": invoice_id},
            {"$set": update_fields}
        )
    except Exception as e:
        logger.error(f"Status update failed for {invoice_id}: {e}")
        raise HTTPException(500, f"Errore aggiornamento stato: {e}")

    # Auto-generate payment deadlines when invoice is emitted
    if new_status == "emessa":
        await generate_scadenze_pagamento(existing, user["user_id"])
    
    # PUNTO 3 — _id escluso in tutte le projection
    updated = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Invoice status updated: {invoice_id} -> {new_status}")
    return InvoiceResponse(**updated)



@router.get("/{invoice_id}/scadenze")
async def get_invoice_scadenze(invoice_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Get payment deadlines for an invoice."""
    doc = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "scadenze_pagamento": 1, "invoice_id": 1}
    )
    if not doc:
        raise HTTPException(404, "Fattura non trovata")
    return {"scadenze": doc.get("scadenze_pagamento", []), "invoice_id": invoice_id}


@router.post("/{invoice_id}/scadenze/pagamento")
async def add_scadenza_pagamento(invoice_id: str, body: dict, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Register a payment against an invoice."""
    inv = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not inv:
        raise HTTPException(404, "Fattura non trovata")

    payment = {
        "payment_id": str(uuid.uuid4()),
        "data_pagamento": body.get("data_pagamento", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "importo": float(body.get("importo", 0)),
        "metodo": body.get("metodo", ""),
        "note": body.get("note", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    scadenze = inv.get("scadenze_pagamento", [])
    scadenze.append(payment)
    totale_pagato = sum(s.get("importo", 0) for s in scadenze if s.get("importo"))

    update = {
        "scadenze_pagamento": scadenze,
        "totale_pagato": totale_pagato,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    total_doc = inv.get("total_document") or inv.get("total", 0)
    if totale_pagato >= total_doc and total_doc > 0:
        update["status"] = "pagata"
        update["payment_status"] = "pagata"

    await db.invoices.update_one({"invoice_id": invoice_id}, {"$set": update})
    return {"scadenze": scadenze, "totale_pagato": totale_pagato, "message": "Pagamento registrato"}


@router.delete("/{invoice_id}/scadenze/pagamento/{payment_id}")
async def delete_scadenza_pagamento(invoice_id: str, payment_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Remove a payment from an invoice."""
    inv = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not inv:
        raise HTTPException(404, "Fattura non trovata")

    scadenze = inv.get("scadenze_pagamento", [])
    scadenze = [s for s in scadenze if s.get("payment_id") != payment_id]
    totale_pagato = sum(s.get("importo", 0) for s in scadenze if s.get("importo"))

    update = {
        "scadenze_pagamento": scadenze,
        "totale_pagato": totale_pagato,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    total_doc = inv.get("total_document") or inv.get("total", 0)
    old_status = inv.get("status", "")
    if totale_pagato < total_doc and old_status == "pagata":
        update["status"] = "accettata" if inv.get("sdi_sent_at") else "inviata_sdi" if inv.get("fic_document_id") else "emessa"
        update["payment_status"] = "parziale" if totale_pagato > 0 else "non_pagata"

    await db.invoices.update_one({"invoice_id": invoice_id}, {"$set": update})
    return {"scadenze": scadenze, "totale_pagato": totale_pagato, "message": "Pagamento rimosso"}


@router.post("/{invoice_id}/scadenze/genera")
async def regenerate_invoice_scadenze(invoice_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """(Re)generate payment deadlines for an invoice based on client's payment type."""
    doc = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Fattura non trovata")
    await generate_scadenze_pagamento(doc, user["user_id"])
    updated = await db.invoices.find_one({"invoice_id": invoice_id}, {"_id": 0, "scadenze_pagamento": 1})
    return {"scadenze": updated.get("scadenze_pagamento", []), "message": "Scadenze generate"}


@router.post("/sync-scadenze")
async def sync_all_scadenze(user: dict = Depends(require_role("admin", "amministrazione"))):
    """Generate scadenze_pagamento for all invoices that don't have them.
    Uses client payment type if available, otherwise creates single scadenza from due_date."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    invoices = await db.invoices.find(
        {"user_id": uid, "tenant_id": tenant_match(user),
         "status": {"$in": ["emessa", "inviata_sdi", "accettata"]},
         "payment_status": {"$ne": "pagata"},
         "$or": [
             {"scadenze_pagamento": {"$exists": False}},
             {"scadenze_pagamento": []},
             {"scadenze_pagamento": None},
         ]},
        {"_id": 0, "invoice_id": 1, "client_id": 1, "due_date": 1,
         "issue_date": 1, "totals": 1}
    ).to_list(500)

    synced = 0
    for inv in invoices:
        # Try generating from payment type first
        await generate_scadenze_pagamento(inv, uid)
        # Check if it worked
        check = await db.invoices.find_one(
            {"invoice_id": inv["invoice_id"]},
            {"_id": 0, "scadenze_pagamento": 1}
        )
        if check and check.get("scadenze_pagamento"):
            synced += 1
            continue

        # Fallback: create single scadenza from due_date
        due = inv.get("due_date") or inv.get("issue_date")
        total = inv.get("totals", {}).get("total_document", 0) or 0
        if due and total:
            scadenza = [{
                "rata": 1,
                "data_scadenza": due,
                "quota_pct": 100,
                "importo": round(total, 2),
                "pagata": False,
                "data_pagamento": None,
            }]
            await db.invoices.update_one(
                {"invoice_id": inv["invoice_id"]},
                {"$set": {"scadenze_pagamento": scadenza}}
            )
            synced += 1

    return {"message": f"Sincronizzazione completata: {synced} fatture aggiornate su {len(invoices)} trovate", "synced": synced, "total": len(invoices)}



@router.patch("/{invoice_id}/scadenze/{rata}/paga")
async def mark_scadenza_pagata(invoice_id: str, rata: int, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Mark a specific installment as paid."""
    doc = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Fattura non trovata")
    scadenze = doc.get("scadenze_pagamento", [])
    updated_scadenze = []
    found = False
    for s in scadenze:
        if s.get("rata") == rata:
            s["pagata"] = not s.get("pagata", False)
            s["data_pagamento"] = date.today().isoformat() if s["pagata"] else None
            found = True
        updated_scadenze.append(s)
    if not found:
        raise HTTPException(404, f"Rata {rata} non trovata")
    # If all scadenze are paid, auto-update invoice status
    all_paid = all(s.get("pagata") for s in updated_scadenze)
    update_set = {"scadenze_pagamento": updated_scadenze, "updated_at": datetime.now(timezone.utc)}
    if all_paid:
        update_set["status"] = "pagata"
    await db.invoices.update_one({"invoice_id": invoice_id}, {"$set": update_set})
    return {"scadenze": updated_scadenze, "all_paid": all_paid}


@router.post("/convert", response_model=InvoiceResponse)
async def convert_document(
    convert_request: ConvertInvoiceRequest,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Convert document(s) (e.g., Preventivo -> Fattura, DDT -> Fattura)."""
    if not convert_request.source_ids:
        raise HTTPException(status_code=400, detail="Nessun documento sorgente specificato")
    
    # Get source documents
    sources = []
    for source_id in convert_request.source_ids:
        doc = await db.invoices.find_one(
            {"invoice_id": source_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
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



@router.post("/preview-pdf")
async def preview_invoice_pdf(
    data: dict,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Generate a live PDF preview from unsaved form data."""
    client_id = data.get("client_id")
    client = {}
    if client_id:
        client = await db.clients.find_one({"client_id": client_id}, {"_id": 0}) or {}

    company = await db.company_settings.find_one(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ) or {"business_name": user.get("name", ""), "email": user.get("email", "")}

    # Build a temporary invoice dict from form data
    lines = data.get("lines", [])
    for ln in lines:
        qty = float(ln.get("quantity") or 0)
        price = float(ln.get("unit_price") or 0)
        disc = float(ln.get("discount_percent") or 0)
        net = qty * price * (1 - disc / 100)
        ln["line_total"] = round(net, 2)
        vat_rate = ln.get("vat_rate", "22")
        vr = 0 if vat_rate in ("N3", "N4") else float(vat_rate or 0)
        ln["vat_amount"] = round(net * vr / 100, 2)

    invoice_data = {
        "document_type": data.get("document_type", "FT"),
        "document_number": data.get("document_number") or "ANTEPRIMA",
        "issue_date": data.get("issue_date", ""),
        "due_date": data.get("due_date", ""),
        "payment_method": data.get("payment_method", "bonifico"),
        "payment_terms": data.get("payment_terms", ""),
        "payment_type_label": data.get("payment_type_label", ""),
        "notes": data.get("notes", ""),
        "lines": lines,
        "totals": data.get("totals", {}),
    }

    pdf_bytes = pdf_service.generate_invoice_pdf(invoice_data, client, company)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=anteprima.pdf"}
    )



@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Generate and download invoice PDF."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


@router.get("/{invoice_id}/xml")
async def get_invoice_xml(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Generate and download FatturaPA XML for SDI."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
async def preview_invoice_email(invoice_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Preview email that would be sent for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    client = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0})
    to_email = ""
    client_name = ""
    all_recipients = []
    if client:
        client_name = client.get("business_name", "")
        # Default: email normale (NOT PEC)
        to_email = client.get("email") or ""
        # Collect ALL available emails
        if client.get("email"):
            all_recipients.append({"email": client["email"], "label": f"{client_name} (Email)", "type": "email", "default": True})
        if client.get("pec"):
            all_recipients.append({"email": client["pec"], "label": f"{client_name} (PEC)", "type": "pec", "default": False})
        for contact in client.get("contacts", []):
            c_email = contact.get("email")
            if c_email and not any(r["email"] == c_email for r in all_recipients):
                c_name = contact.get("name") or contact.get("role") or c_email
                all_recipients.append({"email": c_email, "label": c_name, "type": "contact", "default": False})
        # If no regular email, fallback to PEC
        if not to_email:
            to_email = client.get("pec") or ""
            for r in all_recipients:
                if r["email"] == to_email:
                    r["default"] = True
        if not to_email and all_recipients:
            to_email = all_recipients[0]["email"]
            all_recipients[0]["default"] = True

    from services.email_preview import build_invoice_email, check_company_warnings
    doc_num = invoice.get("document_number", "")
    doc_type = invoice.get("document_type", "FT")
    total = invoice.get("totals", {}).get("total_document", 0)

    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}) or {}
    company_name = company.get("business_name") or company.get("name") or ""
    company_warnings = check_company_warnings(company)

    preview = build_invoice_email(
        client_name=client_name,
        document_number=doc_num,
        document_type=doc_type,
        total=total,
        company_name=company_name,
    )

    # Collect suggested CC contacts
    suggested_contacts = []
    if client:
        for field, label in [("pec", "PEC"), ("email", "Email")]:
            val = client.get(field)
            if val and val != to_email:
                suggested_contacts.append({"email": val, "name": f"{client_name} ({label})"})
        for contact in client.get("contacts", []):
            c_email = contact.get("email")
            if c_email and c_email != to_email and not any(s["email"] == c_email for s in suggested_contacts):
                c_name = contact.get("name") or contact.get("role") or c_email
                suggested_contacts.append({"email": c_email, "name": c_name})

    return {
        "to_email": to_email,
        "to_name": client_name,
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"{doc_num}.pdf",
        "all_recipients": all_recipients,
        "suggested_contacts": suggested_contacts,
        "company_warnings": company_warnings,
    }



@router.post("/{invoice_id}/send-email")
async def send_invoice_email(invoice_id: str, payload: dict = None, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Generate PDF and send invoice via email to client."""
    payload = payload or {}
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    client = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0})
    if not client:
        raise HTTPException(400, "Cliente non trovato")

    # Find email recipients — use payload override or default to regular email
    to_emails = payload.get("to_emails", [])
    if to_emails:
        to_email = to_emails[0]
        cc_list = to_emails[1:] + payload.get("cc", [])
    else:
        # Default: regular email first, then PEC
        to_email = payload.get("to_email") or client.get("email") or client.get("pec") or ""
        if not to_email:
            for contact in client.get("contacts", []):
                if contact.get("email"):
                    to_email = contact["email"]
                    break
        cc_list = payload.get("cc", [])
    if not to_email:
        raise HTTPException(400, "Nessun indirizzo email trovato per il cliente. Aggiungi un'email o PEC nella scheda cliente.")

    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}) or {}

    # Generate PDF
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice, client, company)
    doc_num = invoice.get("document_number", "documento")
    filename = f"{doc_num}.pdf"

    # Send email
    from services.email_service import send_invoice_email as _send, send_email_with_attachment, check_email_service
    check_email_service()
    doc_type = invoice.get("document_type", "FT")
    total = invoice.get("totals", {}).get("total_document", 0)

    if payload.get("custom_subject") or payload.get("custom_body"):
        custom_subject = payload.get("custom_subject") or f"Documento {doc_num}"
        custom_body = payload.get("custom_body") or ""
        success = await send_email_with_attachment(
            to_email=to_email, subject=custom_subject, body=custom_body,
            pdf_bytes=pdf_bytes, filename=filename, user_id=user["user_id"],
            cc=cc_list if cc_list else None,
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
            user_id=user["user_id"],
            cc=cc_list if cc_list else None,
        )

    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la configurazione Resend in Impostazioni.")

    # Track email sent
    all_recipients = [to_email] + (cc_list or [])
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "email_sent": True,
            "email_sent_to": ", ".join(all_recipients),
            "email_sent_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    logger.info(f"Invoice {doc_num} sent via email to {', '.join(all_recipients)}")

    # Audit log
    from services.outbound_audit import log_outbound
    await log_outbound(
        user_id=user["user_id"],
        action_type=f"email_{doc_type.lower()}",
        recipient=", ".join(all_recipients),
        details={"document_number": doc_num, "document_type": doc_type, "filename": filename},
        status="sent",
    )

    return {"message": f"Email inviata con successo a {', '.join(all_recipients)}", "to": to_email, "cc": cc_list}


# ── Send Invoice to SDI ──

@router.post("/{invoice_id}/send-sdi")
async def send_invoice_to_sdi(invoice_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Sync invoice to Fatture in Cloud and send to SDI."""
    from core.demo_guard import is_demo_user
    if is_demo_user(user):
        return {"message": "Invio SDI simulato in modalita demo", "simulated": True, "invoice_id": invoice_id}
    return await _send_sdi_impl(invoice_id, user)


async def _send_sdi_impl(invoice_id: str, user: dict):
    """Actual send-sdi implementation.
    
    Flow:
    1. Validate ALL required fields BEFORE calling FIC
    2. Map to FIC format + log payload
    3. Create/update on FIC (handle 409 duplicates)
    4. Send to SDI
    5. Update local status
    """
    import httpx
    from services.fattureincloud_api import (
        get_fic_client, map_fattura_to_fic,
        validate_invoice_for_sdi, extract_fic_error_message,
    )

    # ── Fetch data ──
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    if invoice.get("document_type") not in ["FT", "NC"]:
        raise HTTPException(400, "Solo fatture e note di credito possono essere inviate al SDI")

    if invoice.get("status") == "bozza":
        raise HTTPException(400, "Non puoi inviare una bozza al SDI. Prima emetti il documento.")

    client_doc = await db.clients.find_one({"client_id": invoice.get("client_id")}, {"_id": 0}) or {}
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}) or {}

    # ── STEP 1: Validazione pre-invio ──
    validation_errors = validate_invoice_for_sdi(invoice, client_doc, company)
    if validation_errors:
        error_msg = "Validazione SDI fallita:\n" + "\n".join(f"- {e}" for e in validation_errors)
        logger.warning(f"SDI validation failed for {invoice.get('document_number')}: {validation_errors}")
        raise HTTPException(422, error_msg)

    # ── Check FIC credentials ──
    fic_token = company.get("fic_access_token") or os.environ.get("FIC_ACCESS_TOKEN")
    fic_company_id = company.get("fic_company_id") or os.environ.get("FIC_COMPANY_ID")
    if not fic_token or not fic_company_id:
        raise HTTPException(400, "Configura le credenziali Fatture in Cloud in Impostazioni -> Integrazioni")

    fic = get_fic_client(access_token=fic_token, company_id=int(fic_company_id))

    # ── STEP 2: Map to FIC format (includes payload logging) ──
    try:
        fic_data = map_fattura_to_fic(invoice, client_doc)
    except Exception as e:
        logger.error(f"map_fattura_to_fic failed for {invoice_id}: {e}")
        raise HTTPException(422, f"Errore nella mappatura dati per FIC: {e}")

    # ── STEP 3: Create or update on FIC ──
    fic_doc_id = invoice.get("fic_document_id")

    # If already sent to SDI, check status instead of re-sending
    if fic_doc_id and invoice.get("status") == "inviata_sdi":
        return {"message": f"Fattura {invoice.get('document_number')} gia' inviata al SDI (FIC id={fic_doc_id})", "fic_document_id": fic_doc_id}

    if not fic_doc_id:
        try:
            result = await fic.create_issued_invoice(fic_data)
            fic_doc_id = result.get("data", {}).get("id")
            logger.info(f"Created FIC document id={fic_doc_id}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Document already exists — find and update
                fic_doc_id = await _handle_fic_409(fic, invoice, fic_data)
            else:
                detail = extract_fic_error_message(e)
                fic_status = e.response.status_code
                body_text = ""
                try:
                    body_text = e.response.text[:500]
                except Exception:
                    pass
                logger.error(f"FIC create failed ({fic_status}): {detail} | Body: {body_text}")
                # Map FIC errors to appropriate HTTP status (never return 401/403 for FIC errors)
                if fic_status == 401:
                    raise HTTPException(502, f"Token FattureInCloud scaduto o non valido. Genera un nuovo token dal tuo account FattureInCloud (Impostazioni > Connessioni API). Dettaglio: {detail}")
                elif fic_status == 403:
                    raise HTTPException(502, f"Permessi insufficienti sul token FattureInCloud. Verifica che il token abbia i permessi necessari. Dettaglio: {detail}")
                elif fic_status in (500, 502, 503, 504):
                    raise HTTPException(502, f"FattureInCloud temporaneamente non disponibile (HTTP {fic_status}). Riprova tra qualche minuto. Dettaglio: {detail}")
                else:
                    raise HTTPException(422, f"Errore Fatture in Cloud ({fic_status}): {detail}")
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise HTTPException(503, str(e))

    if not fic_doc_id:
        raise HTTPException(500, "Fatture in Cloud non ha restituito un ID documento")

    # ── STEP 4: Send to SDI ──
    try:
        sdi_result = await fic.send_to_sdi(fic_doc_id)
        logger.info(f"SDI send result for doc {fic_doc_id}: {sdi_result}")
    except httpx.HTTPStatusError as e:
        detail = extract_fic_error_message(e)
        logger.error(f"SDI send failed ({e.response.status_code}): {detail}")

        # AUTO-RECOVERY: se la fattura è già stata inviata/è in corso, allinea lo stato locale
        detail_lower = detail.lower()
        already_sent = any(kw in detail_lower for kw in [
            "già in corso", "gia in corso", "già presente", "gia presente",
            "duplicat", "already", "in corso un tentativo",
        ])
        if already_sent:
            logger.info(f"Auto-recovery: document {fic_doc_id} already sent to SDI, syncing local status")
            await db.invoices.update_one(
                {"invoice_id": invoice_id},
                {"$set": {
                    "status": "inviata_sdi",
                    "fic_document_id": fic_doc_id,
                    "sdi_sent_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            doc_num = invoice.get("document_number", "")
            return {
                "message": f"Fattura {doc_num} gia' presente su SDI. Stato locale allineato.",
                "fic_document_id": fic_doc_id,
                "recovered": True,
            }

        # Save fic_doc_id even if SDI fails, so we don't recreate
        await db.invoices.update_one(
            {"invoice_id": invoice_id},
            {"$set": {"fic_document_id": fic_doc_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        fic_status = e.response.status_code
        if fic_status in (401, 403):
            raise HTTPException(502, f"Token FattureInCloud scaduto o non valido. Genera un nuovo token dal tuo account FIC. Dettaglio: {detail}")
        elif fic_status in (500, 502, 503, 504):
            raise HTTPException(502, f"FattureInCloud/SDI temporaneamente non disponibile (HTTP {fic_status}). Documento creato su FIC (id={fic_doc_id}), riprova tra qualche minuto.")
        else:
            raise HTTPException(422, f"Invio SDI fallito ({fic_status}): {detail}. Documento creato su FIC (id={fic_doc_id}).")
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        await db.invoices.update_one(
            {"invoice_id": invoice_id},
            {"$set": {
                "fic_document_id": fic_doc_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        raise HTTPException(503, str(e))

    # ── STEP 5: Update local status ──
    await db.invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {
            "status": "inviata_sdi",
            "fic_document_id": fic_doc_id,
            "sdi_sent_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    doc_num = invoice.get("document_number", "")
    logger.info(f"Invoice {doc_num} synced to FIC (id={fic_doc_id}) and sent to SDI")

    # Audit log
    from services.outbound_audit import log_outbound
    await log_outbound(
        user_id=user["user_id"],
        action_type="sdi_send",
        recipient=client_doc.get("business_name", ""),
        details={"document_number": doc_num, "fic_document_id": fic_doc_id},
        status="sent",
        external_id=str(fic_doc_id),
    )

    return {"message": f"Fattura {doc_num} inviata al SDI con successo", "fic_document_id": fic_doc_id}


async def _handle_fic_409(fic, invoice: dict, fic_data: dict) -> int:
    """Handle 409 Conflict: document number exists on FIC. Find and update it.
    
    If document is locked or already sent to SDI, return the ID anyway
    so the caller can proceed with the SDI send (which will trigger auto-recovery).
    """
    doc_num_raw = invoice.get("document_number", "")
    doc_type = invoice.get("document_type", "FT")
    fic_type = "credit_note" if doc_type == "NC" else "invoice"

    # Extract numeric part: "NC-2/2026" → 2, "16/2026" → 16
    try:
        num_part = str(doc_num_raw).split("/")[0]
        num_part = num_part.split("-")[-1] if "-" in num_part else num_part
        num_int = int(num_part)
    except (ValueError, IndexError):
        raise HTTPException(409, f"Numero documento '{doc_num_raw}' non valido per la ricerca su FIC")

    logger.info(f"Document {doc_num_raw} already exists on FIC (type={fic_type}), searching for number={num_int}...")
    try:
        search_result = await fic._request("GET", "/issued_documents", params={
            "type": fic_type, "q": f"number = {num_int}", "per_page": 10,
            "fields": "id,number,date,ei_status",
        })
        docs = search_result.get("data", [])
    except Exception as se:
        logger.error(f"FIC search failed: {se}")
        raise HTTPException(409, f"Documento n.{num_int} ({fic_type}) esiste gia' su FIC. Ricerca fallita: {str(se)[:100]}")

    existing_id = None
    for doc in docs:
        if doc.get("number") == num_int:
            existing_id = doc.get("id")
            ei_status = doc.get("ei_status")
            if ei_status:
                logger.info(f"FIC doc {existing_id} already has ei_status={ei_status}, skipping update")
                return existing_id
            break

    if not existing_id:
        raise HTTPException(409, f"Documento n.{num_int} esiste gia' su FIC ma non trovato nella ricerca. Verifica manualmente.")

    logger.info(f"Updating existing FIC document id={existing_id}")
    try:
        from services.fattureincloud_api import extract_fic_error_message
        import httpx as httpx_lib
        update_result = await fic.update_issued_invoice(existing_id, fic_data)
        return update_result.get("data", {}).get("id") or existing_id
    except httpx_lib.HTTPStatusError as ue:
        detail = extract_fic_error_message(ue)
        detail_lower = detail.lower()
        # If document is locked (already in SDI pipeline), return ID anyway — let SDI send handle it
        if "locked" in detail_lower or "bloccato" in detail_lower:
            logger.info(f"FIC doc {existing_id} is locked, returning ID for SDI send attempt")
            return existing_id
        raise HTTPException(ue.response.status_code, f"Documento n.{num_int} su FIC (id={existing_id}): aggiornamento fallito. {detail}")
    except Exception as ue:
        raise HTTPException(409, f"Aggiornamento documento n.{num_int} fallito: {str(ue)[:150]}")


@router.get("/{invoice_id}/stato-sdi")
async def check_invoice_sdi_status(invoice_id: str, user: dict = Depends(require_role("admin", "amministrazione"))):
    """Check SDI status for a sent invoice via Fatture in Cloud."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(404, "Documento non trovato")

    fic_doc_id = invoice.get("fic_document_id")
    if not fic_doc_id:
        raise HTTPException(400, "Documento non ancora sincronizzato con Fatture in Cloud")

    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    fic_token = company.get("fic_access_token") if company else None
    fic_company_id = company.get("fic_company_id") if company else None
    if not fic_token or not fic_company_id:
        raise HTTPException(400, "Credenziali Fatture in Cloud non configurate")

    try:
        from services.fattureincloud_api import get_fic_client
        fic = get_fic_client(access_token=fic_token, company_id=int(fic_company_id))
        result = await fic.get_sdi_status(int(fic_doc_id))
        return {"fic_document_id": fic_doc_id, "status_data": result}
    except Exception as e:
        logger.error(f"FIC status check error: {e}")
        raise HTTPException(500, f"Errore verifica stato: {str(e)}")



@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """
    Elimina una fattura SOLO se in stato bozza.
    Le fatture emesse non possono essere eliminate —
    devono essere annullate per preservare la
    numerazione progressiva (obbligo fiscale IT).
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    inv = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": uid, "tenant_id": tenant_match(user)},
        {"_id": 0, "status": 1, "document_number": 1, "document_type": 1, "sdi_id": 1, "protocollo_sdi": 1}
    )
    if not inv:
        raise HTTPException(404, "Fattura non trovata")

    status = inv.get("status", "bozza")

    # Fatture emesse o pagate non si eliminano mai
    if status in ("emessa", "pagata"):
        raise HTTPException(
            409,
            f"Impossibile eliminare una fattura {status}. "
            f"Usa 'Annulla' per invalidare il documento "
            f"preservando la numerazione progressiva."
        )

    # Fatture già annullate: eliminazione fisica consentita
    # solo se non sono state inviate a SDI (nessun protocollo fiscale)
    if status == "annullata":
        sdi = inv.get("sdi_id") or inv.get("protocollo_sdi")
        if sdi:
            raise HTTPException(
                409,
                "Fattura annullata ma già inviata a SDI. Non eliminabile."
            )
        await db.invoices.delete_one(
            {"invoice_id": invoice_id, "user_id": uid, "tenant_id": tenant_match(user)}
        )
        logger.info(f"Deleted annullata invoice {inv.get('document_number')} (no SDI)")
        await log_activity(user, "delete", "fattura", invoice_id, label=inv.get("document_number", ""))
        return {"message": f"Fattura annullata {inv.get('document_number')} eliminata fisicamente."}

    # Solo bozze si possono eliminare
    await db.invoices.delete_one(
        {"invoice_id": invoice_id, "user_id": uid, "tenant_id": tenant_match(user)}
    )
    logger.info(
        f"Fattura bozza {invoice_id} eliminata da {uid}"
    )
    await log_activity(user, "delete", "fattura", invoice_id, label=inv.get("document_number", ""))
    return {"message": "Fattura eliminata"}


@router.patch("/{invoice_id}/annulla")
async def annulla_invoice(
    invoice_id: str,
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """
    Annulla una fattura emessa.
    Non la elimina — cambia stato in 'annullata'.
    Il numero progressivo rimane visibile nella lista.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    inv = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": uid, "tenant_id": tenant_match(user)},
        {"_id": 0, "status": 1, "document_number": 1}
    )
    if not inv:
        raise HTTPException(404, "Fattura non trovata")

    status = inv.get("status", "bozza")

    if status == "annullata":
        raise HTTPException(409, "Fattura già annullata")

    await db.invoices.update_one(
        {"invoice_id": invoice_id, "user_id": uid, "tenant_id": tenant_match(user)},
        {"$set": {
            "status": "annullata",
            "annullata_at": datetime.now(timezone.utc).isoformat(),
            "annullata_note": "Annullata manualmente",
        }}
    )
    logger.info(
        f"Fattura {invoice_id} annullata da {uid}"
    )
    return {
        "message": f"Fattura {inv.get('document_number')} annullata",
        "status": "annullata",
    }


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
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Get payment schedule and history for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Record a payment for an invoice."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Delete a recorded payment."""
    invoice = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
    user: dict = Depends(require_role("admin", "amministrazione"))
):
    """Duplicate an existing invoice as a new draft."""
    original = await db.invoices.find_one(
        {"invoice_id": invoice_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
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



# ══════════════════════════════════════════════════════════════════
#  One-shot admin cleanup: remove bogus invoice 9908/2026
#  CALL ONCE then remove this endpoint
# ══════════════════════════════════════════════════════════════════
@router.delete("/admin/cleanup-9908")
async def cleanup_bogus_invoice(user: dict = Depends(require_role("admin", "amministrazione"))):
    """
    Removes the bogus invoice 9908/2026 (status annullata, never sent to SDI).
    This is a one-time cleanup endpoint. Remove after use.
    """
    # Step 1: Find the invoice
    inv = await db.invoices.find_one(
        {"document_number": "9908/2026", "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "invoice_id": 1, "status": 1, "document_number": 1, "client_id": 1}
    )
    if not inv:
        # Try alternative field names
        inv = await db.invoices.find_one(
            {"invoice_number": "9908/2026", "user_id": user["user_id"], "tenant_id": tenant_match(user)},
            {"_id": 0, "invoice_id": 1, "status": 1, "invoice_number": 1, "client_id": 1}
        )
    if not inv:
        return {"message": "Fattura 9908/2026 non trovata. Probabilmente già eliminata.", "deleted": False}

    if inv.get("status") != "annullata":
        raise HTTPException(400, f"La fattura 9908/2026 ha status '{inv.get('status')}', non 'annullata'. Annullala prima.")

    # Step 2: Delete physically
    result = await db.invoices.delete_one(
        {"document_number": "9908/2026", "user_id": user["user_id"], "tenant_id": tenant_match(user), "status": "annullata"}
    )
    if result.deleted_count == 0:
        result = await db.invoices.delete_one(
            {"invoice_number": "9908/2026", "user_id": user["user_id"], "tenant_id": tenant_match(user), "status": "annullata"}
        )

    # Step 3: Verify counter is NOT touched
    counter_id = f"{user['user_id']}_FT_2026"
    counter = await db.document_counters.find_one({"counter_id": counter_id}, {"_id": 0})

    logger.info(f"[CLEANUP] Deleted bogus invoice 9908/2026 for user {user['user_id']}. Counter untouched: {counter}")
    return {
        "message": f"Fattura 9908/2026 eliminata fisicamente. Contatore FT 2026 invariato: {counter.get('counter', '?') if counter else 'N/A'}",
        "deleted": True,
        "counter_current": counter.get("counter") if counter else None,
        "remaining_invoices": await db.invoices.count_documents({"user_id": user["user_id"], "tenant_id": tenant_match(user)}),
    }
