"""DDT (Documento di Trasporto) routes — Full CRUD + PDF + Convert."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.ddt import DDTCreate, DDTUpdate, DDTLine
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ddt", tags=["ddt"])

COLLECTION = "ddt_documents"

# ── Stats / Registro ──

@router.get("/stats/registro")
async def ddt_stats(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    user: dict = Depends(get_current_user),
):
    """KPI cards and monthly shipping report for DDT register."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    target_year = year or now.year
    target_month = month or now.month

    # Date range for month filter
    from calendar import monthrange
    last_day = monthrange(target_year, target_month)[1]
    start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    end = datetime(target_year, target_month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    base_q = {"user_id": uid}
    month_q = {**base_q, "created_at": {"$gte": start, "$lte": end}}

    # Total counts
    total_all = await db[COLLECTION].count_documents(base_q)
    total_month = await db[COLLECTION].count_documents(month_q)

    # Per-type breakdown this month
    per_type = {}
    for t in ["vendita", "conto_lavoro", "rientro_conto_lavoro"]:
        per_type[t] = await db[COLLECTION].count_documents({**month_q, "ddt_type": t})

    # Per-status this month
    per_status = {}
    for s in ["non_fatturato", "parzialmente_fatturato", "fatturato"]:
        per_status[s] = await db[COLLECTION].count_documents({**month_q, "status": s})

    # Volume totale mese
    pipeline = [
        {"$match": month_q},
        {"$group": {"_id": None, "volume": {"$sum": "$totals.total"}}},
    ]
    agg = await db[COLLECTION].aggregate(pipeline).to_list(1)
    volume_month = round(agg[0]["volume"], 2) if agg else 0

    # Top 5 clienti del mese
    client_pipeline = [
        {"$match": month_q},
        {"$group": {"_id": "$client_name", "count": {"$sum": 1}, "volume": {"$sum": "$totals.total"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_clients = await db[COLLECTION].aggregate(client_pipeline).to_list(5)

    return {
        "year": target_year,
        "month": target_month,
        "total_all": total_all,
        "total_month": total_month,
        "per_type": per_type,
        "per_status": per_status,
        "volume_month": volume_month,
        "top_clients": [
            {"name": c["_id"] or "Senza cliente", "count": c["count"], "volume": round(c["volume"], 2)}
            for c in top_clients
        ],
    }


DDT_TYPE_LABELS = {
    "vendita": "DDT di Vendita",
    "conto_lavoro": "DDT Conto Lavoro",
    "rientro_conto_lavoro": "DDT Rientro Conto Lavoro",
}

CAUSALI_DEFAULT = [
    "Vendita", "Conto Lavoro", "Reso Conto Lavoro",
    "Conto Visione", "Riparazione", "Omaggio", "Trasferimento",
]


def calc_line(line: dict) -> dict:
    qty = float(line.get("quantity", 0))
    price = float(line.get("unit_price", 0))
    s1 = float(line.get("sconto_1", 0))
    s2 = float(line.get("sconto_2", 0))
    net = price * (1 - s1 / 100) * (1 - s2 / 100)
    line["prezzo_netto"] = round(net, 4)
    line["line_total"] = round(qty * net, 2)
    return line


def calc_totals(lines: list, sconto_globale: float = 0, acconto: float = 0) -> dict:
    subtotal = sum(item.get("line_total", 0) for item in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)
    total_vat = 0
    for item in lines:
        rate_str = item.get("vat_rate", "22")
        base = item.get("line_total", 0)
        if sconto_globale:
            base = base * (1 - sconto_globale / 100)
        try:
            total_vat += round(base * float(rate_str) / 100, 2)
        except ValueError:
            pass
    total = round(imponibile + total_vat, 2)
    da_pagare = round(total - float(acconto or 0), 2)
    return {
        "subtotal": round(subtotal, 2),
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "total_vat": round(total_vat, 2),
        "total": total,
        "acconto": round(float(acconto or 0), 2),
        "da_pagare": da_pagare,
        "line_count": len(lines),
    }


async def next_ddt_number(user_id: str, ddt_type: str) -> str:
    prefix = {"vendita": "DDT", "conto_lavoro": "CL", "rientro_conto_lavoro": "RCL"}.get(ddt_type, "DDT")
    year = datetime.now(timezone.utc).strftime("%Y")
    count = await db[COLLECTION].count_documents({"user_id": user_id, "ddt_type": ddt_type})
    return f"{prefix}-{year}-{count + 1:04d}"


# ── List ──

@router.get("/")
async def list_ddt(
    ddt_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if ddt_type:
        q["ddt_type"] = ddt_type
    if status:
        q["status"] = status
    if search:
        q["$or"] = [
            {"number": {"$regex": search, "$options": "i"}},
            {"subject": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
        ]
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        if date_to:
            date_filter["$lte"] = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        q["created_at"] = date_filter
    total = await db[COLLECTION].count_documents(q)
    items = await db[COLLECTION].find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items, "total": total}


# ── Get One ──

@router.get("/causali")
async def get_causali():
    return {"causali": CAUSALI_DEFAULT}


@router.get("/{ddt_id}")
async def get_ddt(ddt_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"ddt_id": ddt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "DDT non trovato")
    return doc


# ── Create ──

@router.post("/", status_code=201)
async def create_ddt(data: DDTCreate, user: dict = Depends(get_current_user)):
    ddt_id = f"ddt_{uuid.uuid4().hex[:12]}"
    number = await next_ddt_number(user["user_id"], data.ddt_type)
    now = datetime.now(timezone.utc)

    # Resolve client name
    client_name = ""
    if data.client_id:
        client = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0, "business_name": 1})
        if client:
            client_name = client["business_name"]

    lines = []
    for line in data.lines:
        d = line.model_dump()
        if not d.get("line_id"):
            d["line_id"] = f"ln_{uuid.uuid4().hex[:8]}"
        lines.append(calc_line(d))

    totals = calc_totals(lines, data.sconto_globale, data.acconto)

    # Auto-set causale based on type (if not explicitly provided or if default "Vendita" for non-vendita types)
    causale = data.causale_trasporto
    causale_defaults = {"vendita": "Vendita", "conto_lavoro": "Conto Lavoro", "rientro_conto_lavoro": "Reso Conto Lavoro"}
    if not causale or (causale == "Vendita" and data.ddt_type != "vendita"):
        causale = causale_defaults.get(data.ddt_type, "Vendita")

    doc = {
        "ddt_id": ddt_id,
        "user_id": user["user_id"],
        "number": number,
        "ddt_type": data.ddt_type,
        "ddt_type_label": DDT_TYPE_LABELS.get(data.ddt_type, "DDT"),
        "client_id": data.client_id,
        "client_name": client_name,
        "subject": data.subject,
        "destinazione": data.destinazione.model_dump() if data.destinazione else {},
        "causale_trasporto": causale,
        "aspetto_beni": data.aspetto_beni,
        "vettore": data.vettore,
        "mezzo_trasporto": data.mezzo_trasporto,
        "porto": data.porto,
        "data_ora_trasporto": data.data_ora_trasporto or now.strftime("%d/%m/%Y %H:%M"),
        "num_colli": data.num_colli,
        "peso_lordo_kg": data.peso_lordo_kg,
        "peso_netto_kg": data.peso_netto_kg,
        "payment_type_id": data.payment_type_id,
        "payment_type_label": data.payment_type_label,
        "stampa_prezzi": data.stampa_prezzi,
        "riferimento": data.riferimento,
        "acconto": data.acconto,
        "sconto_globale": data.sconto_globale,
        "notes": data.notes,
        "lines": lines,
        "totals": totals,
        "status": "non_fatturato",
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"ddt_id": ddt_id}, {"_id": 0})
    logger.info(f"DDT created: {ddt_id} ({number})")
    return created


# ── Update ──

@router.put("/{ddt_id}")
async def update_ddt(ddt_id: str, data: DDTUpdate, user: dict = Depends(get_current_user)):
    existing = await db[COLLECTION].find_one(
        {"ddt_id": ddt_id, "user_id": user["user_id"]}
    )
    if not existing:
        raise HTTPException(404, "DDT non trovato")

    upd = {"updated_at": datetime.now(timezone.utc)}

    simple = [
        "ddt_type", "client_id", "subject", "causale_trasporto", "aspetto_beni",
        "vettore", "mezzo_trasporto", "porto", "data_ora_trasporto",
        "payment_type_id", "payment_type_label", "stampa_prezzi", "riferimento", "notes", "status",
    ]
    for field in simple:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val

    if data.destinazione is not None:
        upd["destinazione"] = data.destinazione.model_dump()
    if data.num_colli is not None:
        upd["num_colli"] = data.num_colli
    if data.peso_lordo_kg is not None:
        upd["peso_lordo_kg"] = data.peso_lordo_kg
    if data.peso_netto_kg is not None:
        upd["peso_netto_kg"] = data.peso_netto_kg
    if data.acconto is not None:
        upd["acconto"] = data.acconto
    if data.sconto_globale is not None:
        upd["sconto_globale"] = data.sconto_globale

    # Resolve client name
    cid = data.client_id if data.client_id is not None else existing.get("client_id")
    if cid:
        client = await db.clients.find_one({"client_id": cid}, {"_id": 0, "business_name": 1})
        if client:
            upd["client_name"] = client["business_name"]

    # Update ddt_type_label
    if data.ddt_type:
        upd["ddt_type_label"] = DDT_TYPE_LABELS.get(data.ddt_type, "DDT")

    if data.lines is not None:
        lines = []
        for line in data.lines:
            d = line.model_dump()
            if not d.get("line_id"):
                d["line_id"] = f"ln_{uuid.uuid4().hex[:8]}"
            lines.append(calc_line(d))
        upd["lines"] = lines
        sg = data.sconto_globale if data.sconto_globale is not None else existing.get("sconto_globale", 0)
        ac = data.acconto if data.acconto is not None else existing.get("acconto", 0)
        upd["totals"] = calc_totals(lines, sg, ac)
    elif data.sconto_globale is not None or data.acconto is not None:
        # Recalculate with existing lines
        ex_lines = existing.get("lines", [])
        sg = data.sconto_globale if data.sconto_globale is not None else existing.get("sconto_globale", 0)
        ac = data.acconto if data.acconto is not None else existing.get("acconto", 0)
        upd["totals"] = calc_totals(ex_lines, sg, ac)

    await db[COLLECTION].update_one({"ddt_id": ddt_id}, {"$set": upd})
    updated = await db[COLLECTION].find_one({"ddt_id": ddt_id}, {"_id": 0})
    return updated


# ── Delete ──

@router.delete("/{ddt_id}")
async def delete_ddt(ddt_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one(
        {"ddt_id": ddt_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "DDT non trovato")
    return {"message": "DDT eliminato"}


# ── PDF ──

@router.get("/{ddt_id}/pdf")
async def get_ddt_pdf(ddt_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"ddt_id": ddt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "DDT non trovato")

    from services.ddt_pdf_service import generate_ddt_pdf
    # Fetch company settings for logo/condizioni
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    pdf_buffer = generate_ddt_pdf(doc, company)
    filename = f"ddt_{doc.get('number', ddt_id).replace('/', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Convert DDT to Invoice ──

@router.post("/{ddt_id}/convert-to-invoice")
async def convert_ddt_to_invoice(ddt_id: str, user: dict = Depends(get_current_user)):
    """Convert a DDT into a Fattura (invoice). Maps lines, client, and totals."""
    doc = await db[COLLECTION].find_one(
        {"ddt_id": ddt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "DDT non trovato")

    if doc.get("converted_to"):
        raise HTTPException(409, f"DDT già convertito in fattura {doc['converted_to']}")

    client_id = doc.get("client_id")
    if not client_id:
        raise HTTPException(422, "DDT senza cliente. Assegnare un cliente prima della conversione.")

    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(422, "Cliente non trovato")

    now = datetime.now(timezone.utc)
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    year = now.year

    # Next invoice number
    count = await db.invoices.count_documents(
        {"user_id": user["user_id"], "document_type": "FT"}
    )
    doc_number = f"FT-{year}/{count + 1:04d}"

    # Map DDT lines to invoice lines
    invoice_lines = []
    for line in doc.get("lines", []):
        lt = float(line.get("line_total", 0))
        invoice_lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "code": line.get("codice_articolo", ""),
            "description": line.get("description", ""),
            "quantity": float(line.get("quantity", 0)),
            "unit_price": float(line.get("prezzo_netto") or line.get("unit_price", 0)),
            "discount_percent": 0,
            "vat_rate": line.get("vat_rate", "22"),
            "line_total": lt,
            "vat_amount": round(lt * float(line.get("vat_rate", 22)) / 100, 2),
        })

    # Build totals
    sg = float(doc.get("sconto_globale", 0))
    subtotal = sum(row.get("line_total", 0) for row in invoice_lines)
    sconto_val = round(subtotal * sg / 100, 2) if sg else 0
    taxable = subtotal - sconto_val
    total_vat = sum(row.get("vat_amount", 0) for row in invoice_lines)
    if sg:
        total_vat = round(total_vat * (1 - sg / 100), 2)

    # Map payment from DDT
    payment_label = (doc.get("payment_type_label") or "").lower()
    if "riba" in payment_label:
        payment_method = "riba"
    elif "contanti" in payment_label:
        payment_method = "contanti"
    elif "carta" in payment_label:
        payment_method = "carta"
    elif "assegno" in payment_label:
        payment_method = "assegno"
    else:
        payment_method = "bonifico"

    if "immediat" in payment_label:
        payment_terms = "immediato"
    elif "90" in payment_label:
        payment_terms = "90gg"
    elif "60" in payment_label:
        payment_terms = "60gg"
    elif "fm" in payment_label or "fine mese" in payment_label:
        payment_terms = "fm+30" if "30" in payment_label else "fine_mese"
    else:
        payment_terms = "30gg"

    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"],
        "document_type": "FT",
        "document_number": doc_number,
        "client_id": client_id,
        "issue_date": now.strftime("%Y-%m-%d"),
        "due_date": None,
        "status": "bozza",
        "payment_method": payment_method,
        "payment_terms": payment_terms,
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
            "total_due": round(taxable + total_vat, 2),
        },
        "notes": f"Rif. DDT {doc.get('number', ddt_id)}. {doc.get('notes', '') or ''}".strip(),
        "internal_notes": None,
        "created_at": now,
        "updated_at": now,
        "converted_from": ddt_id,
        "converted_to": None,
    }

    await db.invoices.insert_one(invoice_doc)

    # Update DDT: mark as fatturato and link to invoice
    await db[COLLECTION].update_one(
        {"ddt_id": ddt_id},
        {"$set": {
            "status": "fatturato",
            "converted_to": invoice_id,
            "updated_at": now,
        }}
    )

    logger.info(f"DDT {ddt_id} converted to invoice {invoice_id} ({doc_number})")
    return {
        "message": f"DDT convertito in Fattura {doc_number}",
        "invoice_id": invoice_id,
        "document_number": doc_number,
    }
