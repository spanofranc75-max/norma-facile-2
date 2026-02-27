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
    line["line_total"] = round(qty * price, 2)
    return line


def calc_totals(lines: list) -> dict:
    subtotal = sum(item.get("line_total", 0) for item in lines)
    vat_groups = {}
    for item in lines:
        rate = item.get("vat_rate", "22")
        vat_groups.setdefault(rate, 0)
        vat_groups[rate] += item.get("line_total", 0)
    total_vat = 0
    for rate, base in vat_groups.items():
        try:
            pct = float(rate)
            total_vat += round(base * pct / 100, 2)
        except ValueError:
            pass
    return {
        "subtotal": round(subtotal, 2),
        "total_vat": round(total_vat, 2),
        "total": round(subtotal + total_vat, 2),
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

    totals = calc_totals(lines)
    compliance = run_compliance(lines)

    doc = {
        "preventivo_id": prev_id,
        "user_id": user["user_id"],
        "number": number,
        "client_id": data.client_id,
        "subject": data.subject,
        "validity_days": data.validity_days,
        "payment_terms": data.payment_terms,
        "notes": data.notes,
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
    for field in ["client_id", "subject", "validity_days", "payment_terms", "notes", "status"]:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val

    if data.lines is not None:
        lines = []
        for line in data.lines:
            d = line.model_dump()
            if not d.get("line_id"):
                d["line_id"] = f"ln_{uuid.uuid4().hex[:8]}"
            lines.append(calc_line(d))
        upd["lines"] = lines
        upd["totals"] = calc_totals(lines)
        compliance = run_compliance(lines)
        upd["compliance_status"] = compliance["all_compliant"]
        upd["compliance_detail"] = compliance

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
        invoice_lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "code": line.get("line_id", ""),
            "description": line.get("description", ""),
            "quantity": float(line.get("quantity", 1)),
            "unit_price": float(line.get("unit_price", 0)),
            "discount_percent": 0,
            "vat_rate": line.get("vat_rate", "22"),
            "line_total": float(line.get("line_total", 0)),
            "vat_amount": round(float(line.get("line_total", 0)) * float(line.get("vat_rate", 22)) / 100, 2),
        })

    # Build totals
    subtotal = sum(row.get("line_total", 0) for row in invoice_lines)
    total_vat = sum(row.get("vat_amount", 0) for row in invoice_lines)

    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"],
        "document_type": "FT",  # Must use enum value, not string literal
        "document_number": doc_number,
        "client_id": client_id,
        "issue_date": now.strftime("%Y-%m-%d"),
        "due_date": None,
        "status": "bozza",
        "payment_method": "bonifico",
        "payment_terms": doc.get("payment_terms", "30gg"),
        "tax_settings": {
            "apply_rivalsa_inps": False, "rivalsa_inps_rate": 4.0,
            "apply_cassa": False, "cassa_type": None, "cassa_rate": 4.0,
            "apply_ritenuta": False, "ritenuta_rate": 20.0, "ritenuta_base": "imponibile",
        },
        "lines": invoice_lines,
        "totals": {
            "subtotal": round(subtotal, 2),
            "taxable_amount": round(subtotal, 2),
            "total_vat": round(total_vat, 2),
            "total_document": round(subtotal + total_vat, 2),
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


# ── PDF Builder ──────────────────────────────────────────────────

def generate_preventivo_pdf(prev: dict, company: dict, client: dict):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    BLUE = colors.HexColor("#0055FF")
    DARK = colors.HexColor("#1E293B")

    buffer = BytesIO()
    doc_pdf = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, textColor=BLUE, spaceAfter=2 * mm)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=12, textColor=DARK, spaceAfter=2 * mm)
    normal = styles["Normal"]


    # Header
    co = company or {}
    elements.append(Paragraph(co.get("company_name", "Norma Facile"), title_style))
    if co.get("address"):
        elements.append(Paragraph(co["address"], normal))
    if co.get("vat_number"):
        elements.append(Paragraph(f"P.IVA: {co['vat_number']}", normal))
    elements.append(Spacer(1, 6 * mm))

    # Preventivo info
    elements.append(Paragraph(f"PREVENTIVO N. {prev.get('number', '-')}", ParagraphStyle("Num", parent=styles["Heading1"], fontSize=16, textColor=DARK)))
    elements.append(Spacer(1, 3 * mm))

    info = [["Data", datetime.now().strftime("%d/%m/%Y")], ["Validita", f"{prev.get('validity_days', 30)} giorni"], ["Pagamento", prev.get("payment_terms", "30gg")]]
    if prev.get("subject"):
        info.append(["Oggetto", prev["subject"]])

    # Client
    if client:
        info.append(["Cliente", client.get("business_name", "-")])
        if client.get("address"):
            info.append(["Indirizzo", client["address"]])
        if client.get("vat_number"):
            info.append(["P.IVA", client["vat_number"]])

    t = Table(info, colWidths=[40 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))

    # Lines table
    lines = prev.get("lines", [])
    if lines:
        elements.append(Paragraph("DETTAGLIO OFFERTA", subtitle_style))
        header = ["#", "Descrizione", "Dim.", "Q.ta", "Prezzo Unit.", "IVA", "Totale"]
        data = [header]
        for i, row in enumerate(lines):
            data.append([
                str(i + 1),
                row.get("description", "-"),
                row.get("dimensions", "-") or "-",
                str(row.get("quantity", 1)),
                f"{row.get('unit_price', 0):.2f}",
                f"{row.get('vat_rate', '22')}%",
                f"{row.get('line_total', 0):.2f}",
            ])

        lt = Table(data, colWidths=[8 * mm, 55 * mm, 25 * mm, 15 * mm, 25 * mm, 15 * mm, 25 * mm])
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
        ]))
        elements.append(lt)
        elements.append(Spacer(1, 4 * mm))

        # Totals
        totals = prev.get("totals", {})
        tot_data = [
            ["Imponibile", f"EUR {totals.get('subtotal', 0):.2f}"],
            ["IVA", f"EUR {totals.get('total_vat', 0):.2f}"],
            ["TOTALE", f"EUR {totals.get('total', 0):.2f}"],
        ]
        tt = Table(tot_data, colWidths=[130 * mm, 38 * mm])
        tt.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTSIZE", (0, 2), (-1, 2), 12),
            ("TEXTCOLOR", (1, 2), (1, 2), BLUE),
            ("LINEABOVE", (0, 2), (-1, 2), 1, DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(tt)

    # Technical Annex — Thermal Compliance
    compliance = prev.get("compliance_detail", {})
    comp_results = compliance.get("results", [])
    if comp_results:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("ALLEGATO TECNICO - PRESTAZIONI TERMICHE", subtitle_style))
        elements.append(Paragraph("Calcolo trasmittanza termica secondo EN ISO 10077-1", normal))
        elements.append(Spacer(1, 3 * mm))

        th_header = ["Voce", "Vetro", "Telaio", "Uw (W/m2K)", "Zona", "Limite", "Esito"]
        th_data = [th_header]
        for r in comp_results:
            esito = "CONFORME" if r["compliant"] else "NON CONFORME"
            th_data.append([
                r.get("description", "-")[:30],
                r.get("glass_label", "-")[:25],
                r.get("frame_label", "-")[:25],
                f"{r['uw']:.2f}",
                r["zone"],
                f"{r['limit']:.2f}",
                esito,
            ])

        tht = Table(th_data, colWidths=[30 * mm, 30 * mm, 30 * mm, 20 * mm, 12 * mm, 15 * mm, 28 * mm])
        tht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        # Color compliance cells
        for i, r in enumerate(comp_results, 1):
            color = colors.HexColor("#059669") if r["compliant"] else colors.HexColor("#DC2626")
            tht.setStyle(TableStyle([
                ("TEXTCOLOR", (6, i), (6, i), color),
                ("FONTNAME", (6, i), (6, i), "Helvetica-Bold"),
            ]))
        elements.append(tht)

        # Global verdict
        elements.append(Spacer(1, 3 * mm))
        is_ok = compliance.get("all_compliant", False)
        verdict_color = colors.HexColor("#059669") if is_ok else colors.HexColor("#DC2626")
        verdict_text = "TUTTE LE VOCI CONFORMI - Ecobonus 2026 OK" if is_ok else "ATTENZIONE: Alcune voci NON conformi ai limiti Ecobonus"
        verdict_style = ParagraphStyle("Verdict", parent=normal, fontSize=11, textColor=verdict_color, fontName="Helvetica-Bold")
        elements.append(Paragraph(verdict_text, verdict_style))

    # Notes
    if prev.get("notes"):
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph("NOTE", subtitle_style))
        elements.append(Paragraph(prev["notes"], normal))

    doc_pdf.build(elements)
    buffer.seek(0)
    return buffer
