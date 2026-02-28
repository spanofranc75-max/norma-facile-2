"""Preventivi Commerciali (Smart Quote) routes.

Integrates NormaCore engine for thermal compliance validation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
    number = f"PRV-{year}/{seq:04d}"

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
    cursor = db.preventivi.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    docs = await cursor.to_list(limit)
    for d in docs:
        if d.get("client_id"):
            c = await db.clients.find_one({"client_id": d["client_id"]}, {"_id": 0, "business_name": 1})
            d["client_name"] = c.get("business_name") if c else None
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
    return doc


@router.post("/", status_code=201)
async def create_preventivo(data: PreventivoCreate, user: dict = Depends(get_current_user)):
    prev_id = f"prev_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # Generate number
    count = await db.preventivi.count_documents({"user_id": user["user_id"]})
    number = f"PRV-{now.year}-{count + 1:04d}"

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
        "iban", "banca", "note_pagamento", "riferimento",
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

    # Get next invoice number
    count = await db.invoices.count_documents(
        {"user_id": user["user_id"], "document_type": "fattura"}
    )
    doc_number = f"FT-{year}/{count + 1:04d}"

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

    pdf_buffer = generate_preventivo_pdf(doc, company, client)
    filename = f"preventivo_{doc.get('number', prev_id).replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Send Preventivo via Email ──

@router.post("/{prev_id}/send-email")
async def send_preventivo_email(prev_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF and send preventivo via email to client."""
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

    pdf_buffer = generate_preventivo_pdf(doc, company, client)
    pdf_bytes = pdf_buffer.getvalue()
    prev_number = doc.get("number", prev_id)
    filename = f"preventivo_{prev_number.replace(' ', '_').replace('/', '_')}.pdf"

    from services.email_service import send_invoice_email as _send
    total = doc.get("totals", {}).get("total_document", 0)

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



# ── PDF Builder (WeasyPrint HTML/CSS) ────────────────────────────

def _fmt_it(n):
    """Format number Italian style: 1.234,56"""
    import locale
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    # Manual Italian formatting
    s = f"{val:,.2f}"  # e.g. "1,234.56"
    # Swap . and , for Italian
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def generate_preventivo_pdf(prev: dict, company: dict, client: dict):
    """Generate PDF matching the Steel Project Design layout using WeasyPrint."""
    from io import BytesIO
    from weasyprint import HTML
    import html as html_mod

    co = company or {}
    cl = client or {}
    esc = html_mod.escape

    # ── Company info ──
    company_name = esc(co.get("business_name", ""))
    company_addr = esc(co.get("address", ""))
    company_cap = esc(co.get("cap", ""))
    company_city = esc(co.get("city", ""))
    company_prov = esc(co.get("province", ""))
    company_full_addr = company_addr
    if company_cap or company_city:
        parts = [p for p in [company_cap, company_city, f"({company_prov})" if company_prov else ""] if p]
        company_full_addr += f"<br>{' '.join(parts)}" if company_addr else ' '.join(parts)
    company_piva = esc(co.get("partita_iva", ""))
    company_cf = esc(co.get("codice_fiscale", ""))
    company_phone = esc(co.get("phone", co.get("tel", "")))
    company_email = esc(co.get("email", co.get("contact_email", "")))

    # Logo
    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="logo" />'

    # ── Client info ──
    cl_name = esc(cl.get("business_name", ""))
    cl_addr = esc(cl.get("address", ""))
    cl_cap = esc(cl.get("cap", ""))
    cl_city = esc(cl.get("city", ""))
    cl_prov = esc(cl.get("province", ""))
    cl_full_addr = cl_addr
    if cl_cap or cl_city:
        parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
        cl_full_addr += f"<br>{' '.join(parts)}" if cl_addr else ' '.join(parts)
    cl_cf = esc(cl.get("codice_fiscale", ""))
    cl_piva = esc(cl.get("partita_iva", ""))
    cl_sdi = esc(cl.get("codice_sdi", ""))
    cl_pec = esc(cl.get("pec", ""))
    cl_email = esc(cl.get("email", ""))

    # ── Document data ──
    doc_number = prev.get("number", "")
    # Extract display number (remove PRV- prefix)
    display_num = doc_number.replace("PRV-", "").replace("/", "-") if doc_number else ""
    created = prev.get("created_at")
    if isinstance(created, datetime):
        doc_date = created.strftime("%d-%m-%Y")
    elif isinstance(created, str):
        try:
            doc_date = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%d-%m-%Y")
        except Exception:
            doc_date = datetime.now().strftime("%d-%m-%Y")
    else:
        doc_date = datetime.now().strftime("%d-%m-%Y")

    payment_label = esc(prev.get("payment_type_label", ""))
    validity = prev.get("validity_days", 30)
    subject = esc(prev.get("subject", ""))
    riferimento = esc(prev.get("riferimento", ""))
    notes_text = prev.get("notes", "") or ""

    # ── Build line items HTML ──
    lines = prev.get("lines", [])
    lines_html = ""
    for ln in lines:
        codice = esc(str(ln.get("codice_articolo", "") or ""))
        desc = esc(str(ln.get("description", ""))).replace("\n", "<br>")
        um = esc(str(ln.get("unit", "pz")))
        qty = _fmt_it(ln.get("quantity", 1))
        price = _fmt_it(ln.get("unit_price", 0))
        s1 = float(ln.get("sconto_1", 0))
        s2 = float(ln.get("sconto_2", 0))
        sconto_display = ""
        if s1 > 0 and s2 > 0:
            sconto_display = f"{_fmt_it(s1)}%+{_fmt_it(s2)}%"
        elif s1 > 0:
            sconto_display = f"{_fmt_it(s1)}%"
        elif s2 > 0:
            sconto_display = f"{_fmt_it(s2)}%"
        importo = _fmt_it(ln.get("line_total", 0))
        iva = esc(str(ln.get("vat_rate", "22")))

        lines_html += f"""<tr>
            <td class="tc">{codice}</td>
            <td class="desc-cell">{desc}</td>
            <td class="tc">{um}</td>
            <td class="tr">{qty}</td>
            <td class="tr">{price}</td>
            <td class="tc">{sconto_display}</td>
            <td class="tr">{importo}</td>
            <td class="tc">{iva}%</td>
        </tr>"""

    # ── Compute IVA breakdown ──
    sconto_globale = float(prev.get("sconto_globale", 0))
    acconto = float(prev.get("acconto", 0))
    subtotal = sum(float(ln.get("line_total", 0)) for ln in lines)
    sconto_val = round(subtotal * sconto_globale / 100, 2) if sconto_globale else 0
    imponibile = round(subtotal - sconto_val, 2)

    vat_groups = {}
    for ln in lines:
        rate_str = str(ln.get("vat_rate", "22"))
        base = float(ln.get("line_total", 0))
        if sconto_globale and subtotal > 0:
            base = base * (1 - sconto_globale / 100)
        vat_groups.setdefault(rate_str, {"base": 0.0, "tax": 0.0})
        vat_groups[rate_str]["base"] += base

    total_vat = 0.0
    iva_rows_html = ""
    for rate_str, grp in sorted(vat_groups.items()):
        try:
            pct = float(rate_str)
            tax = round(grp["base"] * pct / 100, 2)
        except ValueError:
            pct = 0
            tax = 0
        grp["tax"] = tax
        total_vat += tax
        iva_rows_html += f"""<tr>
            <td>IVA {rate_str}%</td>
            <td class="tr">{_fmt_it(grp['base'])}</td>
            <td class="tc">{rate_str}%</td>
            <td class="tr">{_fmt_it(tax)}</td>
        </tr>"""

    total = round(imponibile + total_vat, 2)

    # ── Notes before/after table ──
    ref_note_html = ""
    if riferimento:
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {esc(riferimento)}</p>'
    elif subject:
        ref_note_html = f'<p class="ref-note"><strong>Note:</strong> {esc(subject)}</p>'

    tech_notes_html = ""
    if notes_text.strip():
        tech_notes_html = f'<div class="tech-notes"><strong>Note:</strong> {esc(notes_text).replace(chr(10), "<br>")}</div>'

    # ── Global discount row ──
    sconto_row_html = ""
    if sconto_globale > 0:
        sconto_row_html = f"""
        <tr class="summary-row">
            <td>Sconto globale ({_fmt_it(sconto_globale)}%):</td>
            <td class="tr">-{_fmt_it(sconto_val)}</td>
        </tr>"""

    # ── Condizioni di vendita ──
    condizioni = co.get("condizioni_vendita", "")
    condizioni_html = ""
    if condizioni and condizioni.strip():
        condizioni_escaped = esc(condizioni).replace("\n", "<br>")
        condizioni_html = f"""
        <div class="page-break"></div>
        <h2 class="conditions-title">CONDIZIONI GENERALI DI VENDITA</h2>
        <div class="conditions-text">{condizioni_escaped}</div>
        <div class="acceptance-section">
            <div class="sig-block">
                <p>Firma e timbro per accettazione</p>
                <div class="sig-line"></div>
                <p class="sig-label">Data di accettazione</p>
                <p class="sig-label">(legale rappresentante)</p>
            </div>
            <div class="legal-notice">
                <p>Ai sensi e per gli effetti dell'Art. 1341 e segg. Del Codice Civile,
                il sottoscritto Acquirente dichiara di aver preso specifica, precisa e
                dettagliata visione di tutte le disposizioni del contratto e di approvarle
                integralmente senza alcuna riserva.</p>
            </div>
            <div class="sig-block" style="margin-top: 20px;">
                <p>li _______________</p>
                <div class="sig-line"></div>
                <p class="sig-label">Firma e timbro (il legale rappresentante)</p>
            </div>
        </div>
        <div class="doc-footer">
            <p>{esc(company_name)}</p>
            <p>Documento {esc(doc_number)}</p>
        </div>"""

    # ── Bank details ──
    bank = co.get("bank_details", {}) or {}
    bank_name = esc(bank.get("bank_name", "") or prev.get("banca", "") or "")
    bank_iban = esc(bank.get("iban", "") or prev.get("iban", "") or "")
    bank_html = ""
    if bank_name or bank_iban:
        bank_html = '<div class="bank-info">'
        if bank_name:
            bank_html += f"<p><strong>Banca:</strong> {bank_name}</p>"
        if bank_iban:
            bank_html += f"<p><strong>IBAN:</strong> {bank_iban}</p>"
        bank_html += "</div>"

    # ── Full HTML (table-based layout for WeasyPrint) ──
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: A4;
        margin: 15mm 18mm 18mm 18mm;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 9pt;
        color: #222;
        line-height: 1.35;
    }}
    .page-break {{ page-break-before: always; }}

    /* ── HEADER TABLE ── */
    .header-table {{
        width: 100%;
        border: none;
        border-collapse: collapse;
        margin-bottom: 10px;
    }}
    .header-table td {{
        vertical-align: top;
        border: none;
        padding: 0;
    }}
    .company-cell {{
        width: 55%;
        padding-right: 15px;
    }}
    .client-cell {{
        width: 45%;
        border: 1px solid #999 !important;
        padding: 8px 10px !important;
        font-size: 8.5pt;
    }}
    .logo {{
        max-width: 140px;
        max-height: 55px;
        margin-bottom: 6px;
    }}
    .company-name {{
        font-size: 13pt;
        font-weight: bold;
        color: #222;
        margin-bottom: 3px;
    }}
    .company-details {{
        font-size: 8pt;
        color: #333;
        line-height: 1.55;
    }}
    .cl-label {{
        font-size: 8pt;
        color: #555;
        font-weight: bold;
    }}
    .cl-name {{
        font-weight: bold;
        font-size: 10pt;
        margin: 2px 0;
    }}
    .cl-details {{
        font-size: 8pt;
        color: #333;
        line-height: 1.55;
    }}

    /* ── TITLE ── */
    .doc-title {{
        text-align: center;
        margin: 14px 0 6px 0;
    }}
    .doc-title h1 {{
        font-size: 18pt;
        font-weight: bold;
        color: #222;
        letter-spacing: 2px;
        margin: 0 0 2px 0;
    }}
    .doc-num {{
        font-size: 14pt;
        font-weight: bold;
        color: #333;
    }}

    /* ── QUOTE META ── */
    .meta-table {{
        margin: 8px 0;
        font-size: 9pt;
        border: none;
        border-collapse: collapse;
    }}
    .meta-table td {{
        border: none;
        padding: 1px 6px 1px 0;
        vertical-align: top;
    }}
    .meta-label {{
        font-weight: bold;
        white-space: nowrap;
        width: 80px;
    }}
    .ref-note {{
        margin: 8px 0;
        padding: 5px 8px;
        background: #f5f5f5;
        border-left: 3px solid #888;
        font-size: 8.5pt;
    }}

    /* ── ITEMS TABLE ── */
    .items-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0 6px 0;
        font-size: 8pt;
    }}
    .items-table th {{
        background: #eee;
        border: 1px solid #999;
        padding: 5px 4px;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 7.5pt;
        text-align: center;
    }}
    .items-table td {{
        border: 1px solid #bbb;
        padding: 4px 4px;
        vertical-align: top;
    }}
    .items-table .desc-cell {{
        text-align: left;
        line-height: 1.4;
    }}
    .items-table .tc {{ text-align: center; }}
    .items-table .tr {{ text-align: right; }}
    .items-table col.c-codice {{ width: 8%; }}
    .items-table col.c-desc {{ width: 38%; }}
    .items-table col.c-um {{ width: 6%; }}
    .items-table col.c-qty {{ width: 8%; }}
    .items-table col.c-price {{ width: 12%; }}
    .items-table col.c-sconto {{ width: 8%; }}
    .items-table col.c-importo {{ width: 12%; }}
    .items-table col.c-iva {{ width: 8%; }}

    /* ── TECH NOTES ── */
    .tech-notes {{
        margin: 8px 0;
        padding: 6px 8px;
        background: #fafafa;
        border: 1px solid #ddd;
        font-size: 8pt;
        line-height: 1.4;
    }}

    /* ── TOTALS (right-aligned via table) ── */
    .totals-outer {{
        width: 100%;
        border: none;
        border-collapse: collapse;
        margin-top: 10px;
    }}
    .totals-outer td {{
        border: none;
        padding: 0;
        vertical-align: top;
    }}
    .totals-spacer {{ width: 45%; }}
    .totals-content {{ width: 55%; }}
    .iva-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 8.5pt;
        margin-bottom: 6px;
    }}
    .iva-table th {{
        background: #eee;
        border: 1px solid #999;
        padding: 4px 5px;
        font-size: 7.5pt;
        text-transform: uppercase;
        text-align: center;
    }}
    .iva-table td {{
        border: 1px solid #bbb;
        padding: 3px 5px;
    }}
    .summary-table {{
        width: 100%;
        font-size: 9pt;
        margin-top: 4px;
        border: none;
        border-collapse: collapse;
    }}
    .summary-table td {{
        padding: 2px 5px;
        border: none;
    }}
    .summary-row td {{ font-size: 9pt; }}
    .total-final td {{
        font-size: 13pt;
        font-weight: bold;
        border-top: 2px solid #333;
        padding-top: 6px;
    }}

    /* ── BANK INFO ── */
    .bank-info {{
        margin-top: 12px;
        padding: 6px 8px;
        border: 1px solid #ccc;
        font-size: 8pt;
        background: #fafafa;
    }}

    /* ── CONDITIONS (PAGE 2) ── */
    .conditions-title {{
        font-size: 11pt;
        font-weight: bold;
        text-align: center;
        margin-bottom: 12px;
        text-transform: uppercase;
    }}
    .conditions-text {{
        font-size: 7.5pt;
        line-height: 1.45;
        text-align: justify;
    }}
    .acceptance-section {{
        margin-top: 30px;
    }}
    .sig-block {{
        margin: 15px 0;
    }}
    .sig-line {{
        border-bottom: 1px solid #333;
        width: 250px;
        height: 30px;
        margin: 4px 0;
    }}
    .sig-label {{
        font-size: 7.5pt;
        color: #666;
    }}
    .legal-notice {{
        margin-top: 20px;
        font-size: 7pt;
        line-height: 1.4;
        border: 1px solid #ccc;
        padding: 6px 8px;
        background: #fafafa;
    }}
    .doc-footer {{
        margin-top: 40px;
        text-align: right;
        font-size: 8pt;
        color: #555;
    }}
</style>
</head>
<body>
    <!-- HEADER (table layout for WeasyPrint) -->
    <table class="header-table">
        <tr>
            <td class="company-cell">
                {logo_html}
                <div class="company-name">{company_name}</div>
                <div class="company-details">
                    {company_full_addr}
                    {"<br>P.IVA: " + company_piva if company_piva else ""}
                    {"<br>Cod. Fisc.: " + company_cf if company_cf else ""}
                    {"<br>Tel: " + company_phone if company_phone else ""}
                    {"<br>Email: " + company_email if company_email else ""}
                </div>
            </td>
            <td class="client-cell">
                <div class="cl-label">Spett.le</div>
                <div class="cl-name">{cl_name}</div>
                <div class="cl-details">
                    {cl_full_addr}
                    {"<br>P.IVA: " + cl_piva if cl_piva else ""}
                    {"<br>Cod. Fisc.: " + cl_cf if cl_cf else ""}
                    {"<br>Cod. SDI: " + cl_sdi if cl_sdi else ""}
                    {"<br>PEC: " + cl_pec if cl_pec else ""}
                    {"<br>Email: " + cl_email if cl_email and not cl_pec else ""}
                </div>
            </td>
        </tr>
    </table>

    <!-- TITLE -->
    <div class="doc-title">
        <h1>PREVENTIVO</h1>
        <div class="doc-num">{esc(display_num)}</div>
    </div>

    <!-- META (table for alignment) -->
    <table class="meta-table">
        <tr><td class="meta-label">DATA:</td><td>{doc_date}</td></tr>
        <tr><td class="meta-label">Pagamento:</td><td>{payment_label}</td></tr>
        <tr><td class="meta-label">Validit&agrave;:</td><td>{validity} giorni</td></tr>
    </table>

    {ref_note_html}

    <!-- ITEMS TABLE -->
    <table class="items-table">
        <colgroup>
            <col class="c-codice">
            <col class="c-desc">
            <col class="c-um">
            <col class="c-qty">
            <col class="c-price">
            <col class="c-sconto">
            <col class="c-importo">
            <col class="c-iva">
        </colgroup>
        <thead>
            <tr>
                <th>Codice</th>
                <th>Descrizione</th>
                <th>u.m.</th>
                <th>Quantit&agrave;</th>
                <th>Prezzo</th>
                <th>Sconti</th>
                <th>Importo</th>
                <th>Iva</th>
            </tr>
        </thead>
        <tbody>
            {lines_html}
        </tbody>
    </table>

    {tech_notes_html}

    <!-- TOTALS (right-aligned via table) -->
    <table class="totals-outer">
        <tr>
            <td class="totals-spacer"></td>
            <td class="totals-content">
                <table class="iva-table">
                    <thead>
                        <tr>
                            <th>Dettaglio IVA</th>
                            <th>Imponibile</th>
                            <th>% IVA</th>
                            <th>Imposta</th>
                        </tr>
                    </thead>
                    <tbody>
                        {iva_rows_html}
                    </tbody>
                </table>
                <table class="summary-table">
                    {sconto_row_html}
                    <tr class="summary-row">
                        <td><strong>TOTALE IMPONIBILE:</strong></td>
                        <td class="tr">{_fmt_it(imponibile)}</td>
                    </tr>
                    <tr class="summary-row">
                        <td><strong>Totale IVA:</strong></td>
                        <td class="tr">{_fmt_it(total_vat)}</td>
                    </tr>
                    <tr class="total-final">
                        <td><strong>Totale:</strong></td>
                        <td class="tr"><strong>{_fmt_it(total)} &euro;</strong></td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    {bank_html}

    {condizioni_html}

</body>
</html>"""

    buffer = BytesIO()
    HTML(string=html_content).write_pdf(buffer)
    buffer.seek(0)
    return buffer
