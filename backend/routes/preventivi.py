"""Preventivi Commerciali (Smart Quote) routes.

Integrates NormaCore engine for thermal compliance validation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import uuid
from datetime import datetime, timezone, date
from core.security import get_current_user
from core.database import db
from core.engine.thermal import ThermalValidator, ThermalInput
from core.engine.climate_zones import ClimateZone, ZONE_LIMITS
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/preventivi", tags=["preventivi"])


# ── Models ───────────────────────────────────────────────────────

class ThermalData(BaseModel):
    glass_id: Optional[str] = None
    frame_id: Optional[str] = None
    spacer_id: Optional[str] = None
    height_mm: Optional[float] = None
    width_mm: Optional[float] = None
    frame_width_mm: Optional[float] = 80
    zone: Optional[str] = "E"


class QuoteLine(BaseModel):
    line_id: Optional[str] = None
    description: str = ""
    codice_articolo: Optional[str] = None
    dimensions: Optional[str] = None
    quantity: float = 1
    unit: str = "pz"
    unit_price: float = 0
    sconto_1: float = 0  # Discount 1 (%)
    sconto_2: float = 0  # Discount 2 (%)
    vat_rate: str = "22"
    thermal_data: Optional[ThermalData] = None
    notes: Optional[str] = None

    @validator("sconto_1", "sconto_2", "unit_price", "quantity", pre=True)
    def parse_float_fields(cls, v):
        if v is None or v == "":
            return 0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0


class PreventivoCreate(BaseModel):
    client_id: Optional[str] = None
    subject: str = ""
    validity_days: int = 30
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    destinazione_merce: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None
    notes: Optional[str] = None
    note_pagamento: Optional[str] = None
    riferimento: Optional[str] = None
    acconto: float = 0
    sconto_globale: float = 0
    lines: List[QuoteLine] = []
    # Normativa di riferimento per carpenteria metallica
    normativa: Optional[str] = None  # "EN_1090", "EN_13241", "NESSUNA"
    # Disegno tecnico
    numero_disegno: Optional[str] = None
    ingegnere_disegno: Optional[str] = None
    # Classe di esecuzione EN 1090
    classe_esecuzione: Optional[str] = None  # "EXC1", "EXC2", "EXC3", "EXC4"
    # Tempi di consegna
    giorni_consegna: Optional[int] = None  # es. 30 giorni

    @validator("giorni_consegna", pre=True)
    def parse_giorni(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class PreventivoUpdate(BaseModel):
    client_id: Optional[str] = None
    subject: Optional[str] = None
    validity_days: Optional[int] = None
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    destinazione_merce: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None
    notes: Optional[str] = None
    note_pagamento: Optional[str] = None
    riferimento: Optional[str] = None
    acconto: Optional[float] = None
    sconto_globale: Optional[float] = None
    lines: Optional[List[QuoteLine]] = None
    status: Optional[str] = None
    number: Optional[str] = None
    data_preventivo: Optional[str] = None
    normativa: Optional[str] = None  # "EN_1090", "EN_13241", "NESSUNA"
    numero_disegno: Optional[str] = None
    ingegnere_disegno: Optional[str] = None
    classe_esecuzione: Optional[str] = None
    giorni_consegna: Optional[int] = None

    @validator("giorni_consegna", pre=True)
    def parse_giorni(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class ProgressiveInvoiceRequest(BaseModel):
    """Request body for progressive invoicing (acconto / SAL / saldo)."""
    invoice_type: str  # "acconto", "sal", "saldo"
    percentage: Optional[float] = None         # For acconto: e.g. 30
    selected_lines: Optional[List[int]] = None # For SAL: line indices
    custom_amount: Optional[float] = None      # For SAL: fixed amount
    description: Optional[str] = None          # Custom description override


# ── Helpers ──────────────────────────────────────────────────────

def calc_line(line: dict) -> dict:
    qty = float(line.get("quantity", 1))
    price = float(line.get("unit_price", 0))
    s1 = float(line.get("sconto_1", 0))
    s2 = float(line.get("sconto_2", 0))
    # Apply cascading discounts
    net = price * (1 - s1 / 100) * (1 - s2 / 100)
    line["prezzo_netto"] = round(net, 4)
    line["line_total"] = round(qty * net, 2)
    return line


def calc_totals(lines: list, sconto_globale: float = 0, acconto: float = 0) -> dict:
    subtotal = sum(item.get("line_total", 0) for item in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)
    vat_groups = {}
    for item in lines:
        rate = item.get("vat_rate", "22")
        vat_groups.setdefault(rate, 0)
        net_line = item.get("line_total", 0)
        # Proportional global discount
        if subtotal > 0 and sconto_val > 0:
            net_line = net_line * (1 - sconto_globale / 100)
        vat_groups[rate] += net_line
    total_vat = 0
    for rate, base in vat_groups.items():
        try:
            pct = float(rate)
            total_vat += round(base * pct / 100, 2)
        except ValueError:
            pass
    total = round(imponibile + total_vat, 2)
    da_pagare = round(total - float(acconto or 0), 2)
    return {
        "subtotal": round(subtotal, 2),
        "sconto_globale_pct": sconto_globale,
        "sconto_val": sconto_val,
        "imponibile": imponibile,
        "total_vat": round(total_vat, 2),
        "total": total,
        "acconto": round(float(acconto or 0), 2),
        "da_pagare": da_pagare,
        "line_count": len(lines),
    }


def run_compliance(lines: list) -> dict:
    """Run thermal compliance on all lines with thermal_data."""
    results = []
    all_compliant = True
    for item in lines:
        td = item.get("thermal_data")
        if not td or not td.get("glass_id"):
            continue
        # Use 'or' to handle both missing keys AND explicit None values
        inp = ThermalInput(
            height_mm=td.get("height_mm") or 2100,
            width_mm=td.get("width_mm") or 1200,
            frame_width_mm=td.get("frame_width_mm") or 80,
            glass_id=td.get("glass_id") or "doppio_be_argon",
            frame_id=td.get("frame_id") or "acciaio_standard",
            spacer_id=td.get("spacer_id") or "alluminio",
        )
        calc = ThermalValidator.calculate(inp)
        zone = td.get("zone", "E")
        zone_limit = ZONE_LIMITS.get(ClimateZone(zone), 1.3)
        compliant = calc.uw <= zone_limit
        if not compliant:
            all_compliant = False
        results.append({
            "line_id": item.get("line_id"),
            "description": item.get("description"),
            "uw": calc.uw,
            "zone": zone,
            "limit": zone_limit,
            "compliant": compliant,
            "glass_label": calc.glass_label,
            "frame_label": calc.frame_label,
        })
    return {
        "checked_lines": len(results),
        "all_compliant": all_compliant if results else None,
        "results": results,
    }


# ── BRIDGE: Distinta → Preventivo ────────────────────────────────

@router.post("/from-distinta/{distinta_id}")
async def create_preventivo_from_distinta(
    distinta_id: str,
    markup_percent: float = Query(30.0, ge=0, le=200),
    user: dict = Depends(get_current_user),
):
    """Create a Preventivo from a Distinta (BOM). Applies markup to material cost."""
    uid = user["user_id"]
    distinta = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": uid}, {"_id": 0})
    if not distinta:
        raise HTTPException(404, "Distinta non trovata")

    now = datetime.now(timezone.utc)
    prev_id = f"prev_{uuid.uuid4().hex[:12]}"
    year = now.year

    # Counter
    counter = await db.document_counters.find_one_and_update(
        {"counter_id": f"PRV-{uid}-{year}"},
        {"$inc": {"counter": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter.get("counter", 1) if counter else 1
    number = f"PRV-{year}-{seq:04d}"

    # Build lines from distinta items
    items = distinta.get("items", [])
    totals_d = distinta.get("totals", {})
    material_cost = float(totals_d.get("total_cost", 0))
    total_weight = float(totals_d.get("total_weight_kg", 0))

    lines = []
    # Group items into a single summary line or individual lines
    if len(items) <= 8:
        for item in items:
            q = float(item.get("quantity", 1))
            cost_unit = float(item.get("cost_per_unit", 0))
            selling_price = round(cost_unit * (1 + markup_percent / 100), 2)
            line_total = round(selling_price * q, 2)
            lines.append({
                "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                "description": f"{item.get('name', item.get('code', ''))} — {item.get('dimensions', '')} × {float(item.get('length_mm',0))}mm",
                "codice_articolo": item.get("code", ""),
                "quantity": q,
                "unit": item.get("unit", "pz"),
                "unit_price": selling_price,
                "prezzo_netto": selling_price,
                "sconto_1": 0,
                "sconto_2": 0,
                "vat_rate": "22",
                "line_total": line_total,
                "notes": "",
            })
    else:
        # Summarize as single line
        selling_price = round(material_cost * (1 + markup_percent / 100), 2)
        lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "description": f"Realizzazione opera (da Distinta #{distinta.get('name', distinta_id)}) — {len(items)} voci, {round(total_weight, 1)} kg",
            "codice_articolo": "",
            "quantity": 1,
            "unit": "corpo",
            "unit_price": selling_price,
            "prezzo_netto": selling_price,
            "sconto_1": 0,
            "sconto_2": 0,
            "vat_rate": "22",
            "line_total": selling_price,
            "notes": f"Costo materiale: €{material_cost:.2f} + markup {markup_percent:.0f}%",
        })

    # Totals
    subtotal = sum(float(ln.get("line_total", 0)) for ln in lines)
    vat_total = round(subtotal * 0.22, 2)

    prev_doc = {
        "preventivo_id": prev_id,
        "user_id": uid,
        "number": number,
        "client_id": distinta.get("client_id", ""),
        "subject": f"Preventivo da Distinta: {distinta.get('name', '')}",
        "validity_days": 30,
        "lines": lines,
        "sconto_globale": 0,
        "acconto": 0,
        "totals": {
            "subtotal": round(subtotal, 2),
            "sconto_globale_value": 0,
            "imponibile": round(subtotal, 2),
            "iva": vat_total,
            "total": round(subtotal + vat_total, 2),
        },
        "notes": f"Generato da Distinta #{distinta.get('name', distinta_id)}. Markup applicato: {markup_percent:.0f}%.",
        "status": "bozza",
        "linked_distinta_id": distinta_id,
        "converted_to": None,
        "payment_type_id": "",
        "payment_type_label": "",
        "created_at": now,
        "updated_at": now,
    }

    await db.preventivi.insert_one(prev_doc)
    logger.info(f"Preventivo {prev_id} ({number}) created from distinta {distinta_id} with {markup_percent}% markup")
    return {
        "message": f"Preventivo {number} creato da distinta con markup {markup_percent:.0f}%",
        "preventivo_id": prev_id,
        "number": number,
        "material_cost": material_cost,
        "markup_percent": markup_percent,
        "selling_total": round(subtotal, 2),
    }


# ── CRUD ─────────────────────────────────────────────────────────

@router.get("/")
async def list_preventivi(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["user_id"]}
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    total = await db.preventivi.count_documents(query)
    cursor = db.preventivi.find(query, {"_id": 0}).skip(skip).limit(limit).sort("number", -1)
    docs = await cursor.to_list(limit)
    for d in docs:
        if d.get("client_id"):
            c = await db.clients.find_one({"client_id": d["client_id"]}, {"_id": 0, "business_name": 1})
            d["client_name"] = c.get("business_name") if c else d.get("_migrated_client_name")
        elif d.get("_migrated_client_name"):
            d["client_name"] = d["_migrated_client_name"]
        # Compute invoicing progress
        tot = float(d.get("totals", {}).get("total", 0))
        invoiced = float(d.get("total_invoiced", 0))
        d["invoicing_progress"] = round((invoiced / tot * 100), 1) if tot > 0 else 0
        # Lookup linked commessa stato for row coloring
        linked_comm = await db.commesse.find_one(
            {"user_id": user["user_id"], "$or": [
                {"moduli.preventivo_id": d["preventivo_id"]},
                {"linked_preventivo_id": d["preventivo_id"]},
            ]},
            {"_id": 0, "commessa_id": 1, "stato": 1, "numero": 1, "status": 1}
        )
        if linked_comm:
            d["commessa_id"] = linked_comm.get("commessa_id")
            d["commessa_stato"] = linked_comm.get("stato", linked_comm.get("status", ""))
            d["commessa_numero"] = linked_comm.get("numero", "")
    return {"preventivi": docs, "total": total}


@router.get("/{prev_id}")
async def get_preventivo(prev_id: str, user: dict = Depends(get_current_user)):
    doc = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")
    if doc.get("client_id"):
        c = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = c.get("business_name") if c else None
    # Enrich with linked invoice data for workflow timeline
    if doc.get("converted_to"):
        inv = await db.invoices.find_one(
            {"invoice_id": doc["converted_to"]}, {"_id": 0, "invoice_id": 1, "document_number": 1, "status": 1, "updated_at": 1}
        )
        if inv:
            doc["linked_invoice"] = {
                "invoice_id": inv["invoice_id"],
                "document_number": inv["document_number"],
                "status": inv["status"],
            }
    # Compute invoicing progress
    tot = float(doc.get("totals", {}).get("total", 0))
    invoiced = float(doc.get("total_invoiced", 0))
    doc["invoicing_progress"] = round((invoiced / tot * 100), 1) if tot > 0 else 0
    return doc


@router.post("/", status_code=201)
async def create_preventivo(data: PreventivoCreate, user: dict = Depends(get_current_user)):
    prev_id = f"prev_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    year = now.year
    uid = user["user_id"]

    # Atomic counter — find max existing number to seed if needed
    counter_id = f"PRV-{uid}-{year}"
    existing_counter = await db.document_counters.find_one({"counter_id": counter_id})
    if not existing_counter:
        # Seed counter from max existing preventivo number for this year
        max_num = 0
        async for doc in db.preventivi.find(
            {"user_id": uid, "number": {"$regex": f"^PRV-{year}-"}},
            {"number": 1, "_id": 0}
        ):
            try:
                num_str = doc["number"].split("-")[-1]
                num = int(num_str)
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError, KeyError):
                pass
        if max_num > 0:
            await db.document_counters.update_one(
                {"counter_id": counter_id},
                {"$set": {"counter": max_num}},
                upsert=True,
            )

    counter = await db.document_counters.find_one_and_update(
        {"counter_id": counter_id},
        {"$inc": {"counter": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter.get("counter", 1)
    number = f"PRV-{year}-{seq:04d}"

    lines = []
    for line in data.lines:
        d = line.model_dump()
        if not d.get("line_id"):
            d["line_id"] = f"ln_{uuid.uuid4().hex[:8]}"
        lines.append(calc_line(d))

    totals = calc_totals(lines, data.sconto_globale, data.acconto)
    compliance = run_compliance(lines)

    doc = {
        "preventivo_id": prev_id,
        "user_id": user["user_id"],
        "number": number,
        "client_id": data.client_id,
        "subject": data.subject,
        "validity_days": data.validity_days,
        "payment_type_id": data.payment_type_id,
        "payment_type_label": data.payment_type_label,
        "destinazione_merce": data.destinazione_merce,
        "iban": data.iban,
        "banca": data.banca,
        "notes": data.notes,
        "note_pagamento": data.note_pagamento,
        "riferimento": data.riferimento,
        "acconto": data.acconto,
        "sconto_globale": data.sconto_globale,
        "normativa": data.normativa,  # EN_1090, EN_13241, NESSUNA
        "numero_disegno": data.numero_disegno,
        "ingegnere_disegno": data.ingegnere_disegno,
        "classe_esecuzione": data.classe_esecuzione,  # EXC1, EXC2, EXC3, EXC4
        "giorni_consegna": data.giorni_consegna,
        "lines": lines,
        "totals": totals,
        "compliance_status": compliance["all_compliant"],
        "compliance_detail": compliance,
        "status": "bozza",
        "created_at": now,
        "updated_at": now,
    }
    await db.preventivi.insert_one(doc)
    created = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    logger.info(f"Preventivo created: {prev_id} ({number})")
    return created


@router.put("/{prev_id}")
async def update_preventivo(prev_id: str, data: PreventivoUpdate, user: dict = Depends(get_current_user)):
    existing = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Preventivo non trovato")

    upd = {"updated_at": datetime.now(timezone.utc)}
    simple_fields = [
        "client_id", "subject", "validity_days", "notes", "status",
        "payment_type_id", "payment_type_label", "destinazione_merce",
        "iban", "banca", "note_pagamento", "riferimento", "normativa",
        "numero_disegno", "ingegnere_disegno", "classe_esecuzione", "giorni_consegna",
        "number", "data_preventivo",
    ]
    for field in simple_fields:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val

    # Handle numeric fields that can be 0
    if data.acconto is not None:
        upd["acconto"] = data.acconto
    if data.sconto_globale is not None:
        upd["sconto_globale"] = data.sconto_globale

    # Determine lines to use for totals calculation
    lines_for_calc = None
    if data.lines is not None:
        lines = []
        for line in data.lines:
            d = line.model_dump()
            if not d.get("line_id"):
                d["line_id"] = f"ln_{uuid.uuid4().hex[:8]}"
            lines.append(calc_line(d))
        upd["lines"] = lines
        lines_for_calc = lines
        compliance = run_compliance(lines)
        upd["compliance_status"] = compliance["all_compliant"]
        upd["compliance_detail"] = compliance
    else:
        # Use existing lines for recalculation if only sconto_globale or acconto changed
        lines_for_calc = existing.get("lines", [])

    # Recalculate totals if lines, sconto_globale, or acconto changed
    if data.lines is not None or data.sconto_globale is not None or data.acconto is not None:
        sg = data.sconto_globale if data.sconto_globale is not None else existing.get("sconto_globale", 0)
        ac = data.acconto if data.acconto is not None else existing.get("acconto", 0)
        upd["totals"] = calc_totals(lines_for_calc, sg, ac)

    await db.preventivi.update_one({"preventivo_id": prev_id}, {"$set": upd})
    updated = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    return updated


@router.delete("/{prev_id}")
async def delete_preventivo(prev_id: str, user: dict = Depends(get_current_user)):
    result = await db.preventivi.delete_one({"preventivo_id": prev_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Preventivo non trovato")
    return {"message": "Preventivo eliminato"}


# ── Compliance Check ─────────────────────────────────────────────

@router.post("/{prev_id}/check-compliance")
async def check_compliance(prev_id: str, user: dict = Depends(get_current_user)):
    """Run NormaCore thermal compliance on all lines with thermal data."""
    doc = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    compliance = run_compliance(doc.get("lines", []))

    # Update the stored compliance status
    await db.preventivi.update_one(
        {"preventivo_id": prev_id},
        {"$set": {
            "compliance_status": compliance["all_compliant"],
            "compliance_detail": compliance,
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    return compliance



# ── Convert to Invoice ───────────────────────────────────────────

@router.post("/{prev_id}/convert-to-invoice")
async def convert_to_invoice(prev_id: str, user: dict = Depends(get_current_user)):
    """Convert an accepted preventivo into a Fattura (invoice).
    Imports all lines, client, and notes automatically.
    """
    doc = await db.preventivi.find_one(
        {"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    if doc.get("converted_to"):
        raise HTTPException(409, f"Preventivo gia convertito in fattura {doc['converted_to']}")

    # Verify client exists
    client_id = doc.get("client_id")
    if not client_id:
        raise HTTPException(422, "Preventivo senza cliente. Assegnare un cliente prima della conversione.")

    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(422, "Cliente non trovato")

    now = datetime.now(timezone.utc)
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    year = now.year

    # Get next invoice number (atomic counter)
    ft_counter_id = f"FT-{user['user_id']}-{year}"
    ft_existing = await db.document_counters.find_one({"counter_id": ft_counter_id})
    if not ft_existing:
        max_ft = 0
        async for inv_doc in db.invoices.find(
            {"user_id": user["user_id"], "document_number": {"$regex": f"^FT-{year}"}},
            {"document_number": 1, "_id": 0}
        ):
            try:
                num_str = inv_doc["document_number"].split("/")[-1]
                num = int(num_str)
                if num > max_ft:
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
    doc_number = f"FT-{year}/{ft_counter.get('counter', 1):04d}"

    # Map preventivo lines to invoice lines
    invoice_lines = []
    for idx, line in enumerate(doc.get("lines", [])):
        lt = float(line.get("line_total", 0))
        invoice_lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "code": line.get("codice_articolo") or line.get("line_id", ""),
            "description": line.get("description", ""),
            "quantity": float(line.get("quantity", 1)),
            "unit_price": float(line.get("prezzo_netto") or line.get("unit_price", 0)),
            "discount_percent": 0,
            "vat_rate": line.get("vat_rate", "22"),
            "line_total": lt,
            "vat_amount": round(lt * float(line.get("vat_rate", 22)) / 100, 2),
        })

    # Build totals (apply global discount if any)
    sg = float(doc.get("sconto_globale", 0))
    subtotal = sum(row.get("line_total", 0) for row in invoice_lines)
    sconto_val = round(subtotal * sg / 100, 2) if sg else 0
    taxable = subtotal - sconto_val
    total_vat = sum(row.get("vat_amount", 0) for row in invoice_lines)
    if sg:
        total_vat = round(total_vat * (1 - sg / 100), 2)

    # Map payment_type_label to valid enum values
    payment_label = (doc.get("payment_type_label") or "").lower()
    # Determine payment_method from label
    if "riba" in payment_label or payment_label.startswith("rb"):
        payment_method = "riba"
    elif "contanti" in payment_label or "con " in payment_label:
        payment_method = "contanti"
    elif "carta" in payment_label:
        payment_method = "carta"
    elif "assegno" in payment_label:
        payment_method = "assegno"
    else:
        payment_method = "bonifico"  # Default
    
    # Determine payment_terms from label
    if "immediat" in payment_label or "imm " in payment_label:
        payment_terms = "immediato"
    elif "30-60-90" in payment_label or "30/60/90" in payment_label:
        payment_terms = "30-60-90gg"
    elif "30-60" in payment_label or "30/60" in payment_label:
        payment_terms = "30-60gg"
    elif "90" in payment_label:
        payment_terms = "90gg"
    elif "60" in payment_label:
        payment_terms = "60gg"
    elif "fm" in payment_label or "fine mese" in payment_label:
        if "30" in payment_label:
            payment_terms = "fm+30"
        else:
            payment_terms = "fine_mese"
    elif "30" in payment_label:
        payment_terms = "30gg"
    else:
        payment_terms = "30gg"  # Default

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
            "total_due": round(subtotal + total_vat, 2),
        },
        "notes": f"Riferimento preventivo {doc.get('number', prev_id)}. {doc.get('notes', '') or ''}".strip(),
        "internal_notes": None,
        "created_at": now,
        "updated_at": now,
        "converted_from": prev_id,
        "converted_to": None,
    }

    await db.invoices.insert_one(invoice_doc)

    # Update preventivo: mark as accepted and link to invoice
    await db.preventivi.update_one(
        {"preventivo_id": prev_id},
        {"$set": {
            "status": "accettato",
            "converted_to": invoice_id,
            "updated_at": now,
        }}
    )

    logger.info(f"Preventivo {prev_id} converted to invoice {invoice_id} ({doc_number})")
    return {
        "message": f"Preventivo convertito in Fattura {doc_number}",
        "invoice_id": invoice_id,
        "document_number": doc_number,
    }


# ── Progressive Invoicing (Acconto / SAL / Saldo) ─────────────────

@router.get("/{prev_id}/invoicing-status")
async def get_invoicing_status(prev_id: str, user: dict = Depends(get_current_user)):
    """Get the invoicing progress for a preventivo — how much has been billed."""
    uid = user["user_id"]
    doc = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    total_prev = float(doc.get("totals", {}).get("total", doc.get("totals", {}).get("imponibile", 0)))

    # Fetch all invoices linked to this preventivo
    linked = await db.invoices.find(
        {"progressive_from_preventivo": prev_id, "user_id": uid, "status": {"$ne": "annullata"}},
        {"_id": 0, "invoice_id": 1, "document_number": 1, "progressive_type": 1,
         "progressive_amount": 1, "issue_date": 1, "status": 1, "totals": 1}
    ).sort("created_at", 1).to_list(100)

    total_invoiced = sum(float(inv.get("progressive_amount", 0)) for inv in linked)
    remaining = round(total_prev - total_invoiced, 2)
    pct = round((total_invoiced / total_prev * 100), 1) if total_prev > 0 else 0

    return {
        "preventivo_id": prev_id,
        "total_preventivo": round(total_prev, 2),
        "total_invoiced": round(total_invoiced, 2),
        "remaining": max(remaining, 0),
        "percentage_invoiced": min(pct, 100),
        "linked_invoices": linked,
        "is_fully_invoiced": remaining <= 0.01,
    }


@router.post("/{prev_id}/progressive-invoice")
async def create_progressive_invoice(prev_id: str, body: ProgressiveInvoiceRequest, user: dict = Depends(get_current_user)):
    """Create a progressive invoice (acconto, SAL, or saldo) from a preventivo."""
    uid = user["user_id"]
    doc = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    client_id = doc.get("client_id")
    if not client_id:
        raise HTTPException(422, "Preventivo senza cliente. Assegnare un cliente prima della fatturazione.")

    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(422, "Cliente non trovato")

    total_prev = float(doc.get("totals", {}).get("total", doc.get("totals", {}).get("imponibile", 0)))
    prev_number = doc.get("number", prev_id)
    prev_lines = doc.get("lines", [])

    # Fetch existing progressive invoices for this preventivo
    existing_invoices = await db.invoices.find(
        {"progressive_from_preventivo": prev_id, "user_id": uid, "status": {"$ne": "annullata"}},
        {"_id": 0, "invoice_id": 1, "document_number": 1, "progressive_amount": 1,
         "progressive_type": 1, "issue_date": 1}
    ).sort("created_at", 1).to_list(100)

    already_invoiced = sum(float(inv.get("progressive_amount", 0)) for inv in existing_invoices)
    remaining = round(total_prev - already_invoiced, 2)

    if remaining <= 0.01 and body.invoice_type != "saldo":
        raise HTTPException(400, "Preventivo gia' completamente fatturato.")

    # ── Determine invoice amount and lines ──
    invoice_lines = []
    progressive_amount = 0.0
    vat_rate = prev_lines[0].get("vat_rate", "22") if prev_lines else "22"

    if body.invoice_type == "acconto":
        if not body.percentage or body.percentage <= 0 or body.percentage > 100:
            raise HTTPException(400, "Percentuale acconto non valida (1-100)")
        progressive_amount = round(total_prev * body.percentage / 100, 2)
        if progressive_amount > remaining + 0.01:
            raise HTTPException(400, f"Importo acconto ({progressive_amount:.2f}) supera il residuo ({remaining:.2f})")
        desc = body.description or f"Acconto {body.percentage:.0f}% su preventivo {prev_number}"
        invoice_lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "code": "", "description": desc,
            "quantity": 1, "unit_price": progressive_amount, "discount_percent": 0,
            "vat_rate": vat_rate, "line_total": progressive_amount,
            "vat_amount": round(progressive_amount * float(vat_rate) / 100, 2),
        })

    elif body.invoice_type == "sal":
        if body.selected_lines is not None and len(body.selected_lines) > 0:
            # SAL by selected lines
            for idx in body.selected_lines:
                if idx < 0 or idx >= len(prev_lines):
                    raise HTTPException(400, f"Indice riga {idx} non valido")
                ln = prev_lines[idx]
                lt = float(ln.get("line_total", 0))
                progressive_amount += lt
                invoice_lines.append({
                    "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                    "code": ln.get("codice_articolo", ""),
                    "description": ln.get("description", ""),
                    "quantity": float(ln.get("quantity", 1)),
                    "unit_price": float(ln.get("prezzo_netto") or ln.get("unit_price", 0)),
                    "discount_percent": 0,
                    "vat_rate": ln.get("vat_rate", "22"),
                    "line_total": lt,
                    "vat_amount": round(lt * float(ln.get("vat_rate", 22)) / 100, 2),
                })
            progressive_amount = round(progressive_amount, 2)
        elif body.custom_amount and body.custom_amount > 0:
            progressive_amount = round(body.custom_amount, 2)
            if progressive_amount > remaining + 0.01:
                raise HTTPException(400, f"Importo SAL ({progressive_amount:.2f}) supera il residuo ({remaining:.2f})")
            desc = body.description or f"SAL su preventivo {prev_number}"
            invoice_lines.append({
                "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                "code": "", "description": desc,
                "quantity": 1, "unit_price": progressive_amount, "discount_percent": 0,
                "vat_rate": vat_rate, "line_total": progressive_amount,
                "vat_amount": round(progressive_amount * float(vat_rate) / 100, 2),
            })
        else:
            raise HTTPException(400, "Per SAL specificare selected_lines o custom_amount")

        if progressive_amount > remaining + 0.01:
            raise HTTPException(400, f"Importo SAL ({progressive_amount:.2f}) supera il residuo ({remaining:.2f})")

    elif body.invoice_type == "saldo":
        # Full invoice with all lines, minus previous invoices as negative lines
        for ln in prev_lines:
            lt = float(ln.get("line_total", 0))
            invoice_lines.append({
                "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                "code": ln.get("codice_articolo", ""),
                "description": ln.get("description", ""),
                "quantity": float(ln.get("quantity", 1)),
                "unit_price": float(ln.get("prezzo_netto") or ln.get("unit_price", 0)),
                "discount_percent": 0,
                "vat_rate": ln.get("vat_rate", "22"),
                "line_total": lt,
                "vat_amount": round(lt * float(ln.get("vat_rate", 22)) / 100, 2),
            })

        # Add negative lines for each previous invoice
        for prev_inv in existing_invoices:
            amt = float(prev_inv.get("progressive_amount", 0))
            if amt > 0:
                inv_num = prev_inv.get("document_number", "")
                inv_date = str(prev_inv.get("issue_date", ""))[:10]
                invoice_lines.append({
                    "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                    "code": "", "description": f"A detrarre acconto Ft. {inv_num} del {inv_date}",
                    "quantity": 1, "unit_price": -amt, "discount_percent": 0,
                    "vat_rate": vat_rate, "line_total": -amt,
                    "vat_amount": round(-amt * float(vat_rate) / 100, 2),
                })

        progressive_amount = remaining
    else:
        raise HTTPException(400, "Tipo fattura non valido. Usare: acconto, sal, saldo")

    # ── Create the invoice document ──
    now = datetime.now(timezone.utc)
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    year = now.year

    # Use the SAME atomic counter as regular invoices for consistent numbering
    ft_counter_id = f"{uid}_FT_{year}"
    ft_counter = await db.document_counters.find_one_and_update(
        {"counter_id": ft_counter_id},
        {"$inc": {"counter": 1}},
        upsert=True,
        return_document=True,
    )
    doc_number = f"{ft_counter.get('counter', 1)}/{year}"

    # Calculate totals
    subtotal = sum(ln["line_total"] for ln in invoice_lines)
    total_vat = sum(ln["vat_amount"] for ln in invoice_lines)

    # Build VAT breakdown from lines (required by frontend)
    vat_breakdown = {}
    for ln in invoice_lines:
        rate = ln.get("vat_rate", "22")
        if rate not in vat_breakdown:
            vat_breakdown[rate] = {"imponibile": 0.0, "imposta": 0.0}
        vat_breakdown[rate]["imponibile"] += ln["line_total"]
        vat_breakdown[rate]["imposta"] += ln["vat_amount"]
    for rate in vat_breakdown:
        vat_breakdown[rate]["imponibile"] = round(vat_breakdown[rate]["imponibile"], 2)
        vat_breakdown[rate]["imposta"] = round(vat_breakdown[rate]["imposta"], 2)

    total_document = round(subtotal + total_vat, 2)

    # Build label for progressive type
    type_labels = {"acconto": "Acconto", "sal": "SAL", "saldo": "Saldo Finale"}

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
            "vat_breakdown": vat_breakdown,
            "total_vat": round(total_vat, 2),
            "rivalsa_inps": 0.0,
            "cassa": 0.0,
            "ritenuta": 0.0,
            "total_document": total_document,
            "total_to_pay": total_document,
        },
        "notes": f"Rif. Preventivo {prev_number} — {type_labels.get(body.invoice_type, body.invoice_type)}",
        "internal_notes": None,
        "created_at": now,
        "updated_at": now,
        "converted_from": prev_id,
        "converted_to": None,
        # Progressive invoicing tracking fields
        "progressive_from_preventivo": prev_id,
        "progressive_type": body.invoice_type,
        "progressive_amount": round(progressive_amount, 2),
    }

    await db.invoices.insert_one(invoice_doc)

    # Update preventivo: track total invoiced and link
    new_total_invoiced = round(already_invoiced + progressive_amount, 2)
    prev_update = {
        "total_invoiced": new_total_invoiced,
        "updated_at": now,
    }
    # If saldo, mark as fully invoiced
    if body.invoice_type == "saldo" or new_total_invoiced >= total_prev - 0.01:
        prev_update["status"] = "accettato"
        prev_update["converted_to"] = invoice_id  # Last invoice

    await db.preventivi.update_one({"preventivo_id": prev_id}, {
        "$set": prev_update,
        "$push": {"linked_invoices": {
            "invoice_id": invoice_id,
            "document_number": doc_number,
            "type": body.invoice_type,
            "amount": round(progressive_amount, 2),
            "date": now.strftime("%Y-%m-%d"),
        }},
    })

    # Auto-link invoice to commessa if preventivo is linked to one
    commessa = await db.commesse.find_one(
        {"linked_preventivo_id": prev_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1}
    )
    if commessa:
        await db.commesse.update_one(
            {"commessa_id": commessa["commessa_id"]},
            {"$addToSet": {"moduli.fatture_ids": invoice_id}},
        )

    logger.info(f"Progressive invoice {doc_number} ({body.invoice_type}) created from preventivo {prev_id}: {progressive_amount:.2f} EUR")
    return {
        "message": f"Fattura {type_labels.get(body.invoice_type, body.invoice_type)} {doc_number} creata — {fmtEur_py(progressive_amount)}",
        "invoice_id": invoice_id,
        "document_number": doc_number,
        "progressive_type": body.invoice_type,
        "progressive_amount": round(progressive_amount, 2),
        "total_invoiced": new_total_invoiced,
        "remaining": round(total_prev - new_total_invoiced, 2),
    }


def fmtEur_py(v):
    """Format EUR value in Italian style."""
    return f"{v:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


# ── PDF Generation ───────────────────────────────────────────────

@router.get("/{prev_id}/pdf")
async def get_preventivo_pdf(prev_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF quote with commercial offer + technical annex."""
    doc = await db.preventivi.find_one({"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    client = None
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0})

    # Fetch payment type for schedule calculation
    payment_type = None
    if doc.get("payment_type_id"):
        payment_type = await db.payment_types.find_one(
            {"payment_type_id": doc["payment_type_id"], "user_id": user["user_id"]}, {"_id": 0}
        )

    pdf_buffer = generate_preventivo_pdf(doc, company, client, payment_type)
    filename = f"preventivo_{doc.get('number', prev_id).replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Send Preventivo via Email ──

@router.get("/{prev_id}/preview-email")
async def preview_preventivo_email(prev_id: str, user: dict = Depends(get_current_user)):
    """Preview email that would be sent for a preventivo."""
    doc = await db.preventivi.find_one(
        {"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    client = None
    to_email = ""
    client_name = ""
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0})
        if client:
            client_name = client.get("business_name", "")
            to_email = client.get("pec") or client.get("email") or ""
            if not to_email:
                for contact in client.get("contacts", []):
                    if contact.get("email"):
                        to_email = contact["email"]
                        break

    from services.email_preview import build_invoice_email
    prev_number = doc.get("number", prev_id)
    totals = doc.get("totals", {})
    total = totals.get("total_document") or totals.get("total", 0)

    preview = build_invoice_email(
        client_name=client_name,
        document_number=prev_number,
        document_type="PRV",
        total=total,
    )
    return {
        "to_email": to_email,
        "to_name": client_name,
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"Preventivo_{prev_number}.pdf",
    }



@router.post("/{prev_id}/send-email")
async def send_preventivo_email(prev_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
    """Generate PDF and send preventivo via email to client."""
    payload = payload or {}
    doc = await db.preventivi.find_one(
        {"preventivo_id": prev_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Preventivo non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    client = None
    to_email = None
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0})
        if client:
            to_email = client.get("pec") or client.get("email")
            if not to_email:
                for contact in client.get("contacts", []):
                    if contact.get("email") and contact.get("doc_preferences", {}).get("preventivi"):
                        to_email = contact["email"]
                        break

    if not to_email:
        raise HTTPException(400, "Nessun indirizzo email trovato per il cliente.")

    # Fetch payment type for schedule calculation
    payment_type = None
    if doc.get("payment_type_id"):
        payment_type = await db.payment_types.find_one(
            {"payment_type_id": doc["payment_type_id"], "user_id": user["user_id"]}, {"_id": 0}
        )

    pdf_buffer = generate_preventivo_pdf(doc, company, client, payment_type)
    pdf_bytes = pdf_buffer.getvalue()
    prev_number = doc.get("number", prev_id)
    filename = f"preventivo_{prev_number.replace(' ', '_').replace('/', '_')}.pdf"

    from services.email_service import send_invoice_email as _send, send_email_with_attachment
    totals = doc.get("totals", {})
    total = totals.get("total_document") or totals.get("total", 0)

    if payload.get("custom_subject") or payload.get("custom_body"):
        custom_subject = payload.get("custom_subject") or f"Preventivo n. {prev_number}"
        custom_body = payload.get("custom_body") or ""
        success = await send_email_with_attachment(
            to_email=to_email, subject=custom_subject, body=custom_body,
            pdf_bytes=pdf_bytes, filename=filename,
        )
    else:
        success = await _send(
            to_email=to_email,
            client_name=client.get("business_name", "") if client else "",
            document_number=prev_number,
            document_type="PRV",
            total=total,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )

    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la configurazione Resend.")

    await db.preventivi.update_one(
        {"preventivo_id": prev_id},
        {"$set": {
            "email_sent": True,
            "email_sent_to": to_email,
            "email_sent_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    return {"message": f"Preventivo inviato via email a {to_email}", "to": to_email}



# ── PDF Builder (WeasyPrint — shared template) ──────────────────

def generate_preventivo_pdf(prev: dict, company: dict, client: dict, payment_type: dict = None):
    """Generate Preventivo PDF using the unified template."""
    from services.pdf_template import (
        fmt_it, safe, build_header_html, compute_iva_groups,
        build_totals_html, build_conditions_html, render_pdf, format_date,
    )

    co = company or {}
    cl = client or {}

    header = build_header_html(co, cl)

    # ── Document data ──
    doc_number = prev.get("number", "")
    display_num = doc_number.replace("PRV-", "").replace("/", "-") if doc_number else ""
    doc_date = format_date(prev.get("created_at", ""))
    payment_label = safe(prev.get("payment_type_label"))
    validity = prev.get("validity_days", 30) or 30
    riferimento = safe(prev.get("riferimento"))
    subject = safe(prev.get("subject"))
    notes_text = prev.get("notes", "") or ""

    # ── Build line items HTML ──
    lines = prev.get("lines", [])
    lines_html = ""
    for ln in lines:
        codice = safe(ln.get("codice_articolo") or "")
        desc = safe(ln.get("description") or "").replace("\n", "<br>")
        um = safe(ln.get("unit", "pz"))
        qty = fmt_it(ln.get("quantity", 1))
        price = fmt_it(ln.get("unit_price", 0))
        s1 = float(ln.get("sconto_1") or 0)
        s2 = float(ln.get("sconto_2") or 0)
        sc = ""
        if s1 > 0 and s2 > 0:
            sc = f"{fmt_it(s1)}%+{fmt_it(s2)}%"
        elif s1 > 0:
            sc = f"{fmt_it(s1)}%"
        elif s2 > 0:
            sc = f"{fmt_it(s2)}%"
        importo = fmt_it(ln.get("line_total", 0))
        iva = safe(str(ln.get("vat_rate", "22")))

        lines_html += f"""<tr>
            <td class="tc">{codice}</td>
            <td class="desc-cell">{desc}</td>
            <td class="tc">{um}</td>
            <td class="tr">{qty}</td>
            <td class="tr">{price}</td>
            <td class="tc">{sc}</td>
            <td class="tr">{importo}</td>
            <td class="tc">{iva}%</td>
        </tr>"""

    # ── IVA / Totals ──
    sconto_globale = float(prev.get("sconto_globale") or 0)
    iva_data = compute_iva_groups(lines, sconto_globale)
    totals_html = build_totals_html(iva_data, sconto_globale)

    # ── Notes ──
    ref_note_html = ""
    if riferimento:
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {riferimento}</p>'
    elif subject:
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {subject}</p>'

    tech_notes_html = ""
    if notes_text.strip():
        tech_notes_html = f'<div class="info-box"><strong>Note:</strong> {safe(notes_text).replace(chr(10), "<br>")}</div>'

    # ── Bank details ──
    bank_name = safe(prev.get("banca") or "")
    bank_iban = safe(prev.get("iban") or "")
    # Fallback to old bank_details if preventivo doesn't have specific bank
    if not bank_name and not bank_iban:
        bank = co.get("bank_details", {}) or {}
        bank_name = safe(bank.get("bank_name") or "")
        bank_iban = safe(bank.get("iban") or "")
    bank_html = ""
    if bank_name or bank_iban:
        bank_html = '<div class="bank-info">'
        if bank_name:
            bank_html += f"<p><strong>Banca:</strong> {bank_name}</p>"
        if bank_iban:
            bank_html += f"<p><strong>IBAN:</strong> {bank_iban}</p>"
        bank_html += "</div>"

    # ── Conditions page ──
    condizioni_html = build_conditions_html(co, doc_number)

    # ── Assemble ──
    body = f"""
    {header}
    <div class="doc-title">
        <h1>PREVENTIVO</h1>
        <div class="doc-num">{safe(display_num)}</div>
    </div>
    <table class="meta-table">
        <tr><td class="meta-label">DATA:</td><td>{doc_date}</td></tr>
        <tr><td class="meta-label">Pagamento:</td><td>{payment_label}</td></tr>
        <tr><td class="meta-label">Validit&agrave;:</td><td>{validity} giorni</td></tr>
    </table>

    {ref_note_html}

    <table class="items-table">
        <colgroup>
            <col style="width:8%"><col style="width:38%"><col style="width:6%">
            <col style="width:8%"><col style="width:12%"><col style="width:8%">
            <col style="width:12%"><col style="width:8%">
        </colgroup>
        <thead><tr>
            <th>Codice</th><th>Descrizione</th><th>u.m.</th>
            <th>Quantit&agrave;</th><th>Prezzo</th><th>Sconti</th>
            <th>Importo</th><th>Iva</th>
        </tr></thead>
        <tbody>{lines_html}</tbody>
    </table>

    {tech_notes_html}
    {totals_html}
    {bank_html}
    {condizioni_html}
    """

    return render_pdf(body)
