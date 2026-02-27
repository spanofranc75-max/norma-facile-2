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
    pdf_buffer = generate_ddt_pdf(doc)
    filename = f"ddt_{doc.get('number', ddt_id).replace('/', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
