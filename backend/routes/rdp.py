"""
RdP — Richiesta di Preventivo a Fornitore (dal Preventivo Cliente)

Flusso:
1. L'utente seleziona righe del preventivo → sceglie fornitore → genera RdP
2. Il fornitore risponde con un prezzo
3. L'utente inserisce il prezzo e applica ricarico → aggiorna il preventivo cliente
4. Quando il preventivo diventa commessa → converte RdP in OdA
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user, tenant_match
from core.rbac import require_role
from core.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/preventivi", tags=["RdP - Richieste Preventivo Fornitore"])

COLL = "rdp_requests"
PREV_COLL = "preventivi"


# ── Models ──

class RdpLineItem(BaseModel):
    line_index: int  # index in preventivo.lines[]
    description: str
    quantity: float = 1
    unit: str = "kg"
    note: Optional[str] = ""

class CreateRdpRequest(BaseModel):
    supplier_id: Optional[str] = ""
    supplier_name: str
    items: List[RdpLineItem]
    note: Optional[str] = ""

class RdpResponseInput(BaseModel):
    """When the supplier responds with prices."""
    prices: List[dict]  # [{line_index, unit_price}]
    total_offered: Optional[float] = None
    note: Optional[str] = ""

class UpdatePreventivoPricesInput(BaseModel):
    """Apply supplier prices to preventivo with markup."""
    markup_rules: List[dict]  # [{line_index, supplier_price, markup_pct}]


# ── Endpoints ──

@router.get("/{prev_id}/rdp")
async def list_rdp(prev_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """List all RdP for a preventivo."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    prev = await db[PREV_COLL].find_one({"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    rdps = []
    async for r in db[COLL].find(
        {"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)},
        {"_id": 0}
    ).sort("created_at", -1):
        rdps.append(r)
    return {"rdp_list": rdps}


@router.post("/{prev_id}/rdp")
async def create_rdp(prev_id: str, data: CreateRdpRequest, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Create a new RdP (supplier quote request) from preventivo lines."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    prev = await db[PREV_COLL].find_one({"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    now = datetime.now(timezone.utc)
    rdp_id = f"rdp_{uuid.uuid4().hex[:10]}"

    # Build items with descriptions from preventivo lines
    prev_lines = prev.get("lines", [])
    items = []
    for item in data.items:
        idx = item.line_index
        prev_desc = ""
        if 0 <= idx < len(prev_lines):
            prev_desc = prev_lines[idx].get("description", "")
        items.append({
            "line_index": idx,
            "description": item.description or prev_desc,
            "quantity": item.quantity,
            "unit": item.unit,
            "note": item.note or "",
            "supplier_price": None,  # filled when response arrives
        })

    rdp_doc = {
        "rdp_id": rdp_id,
        "preventivo_id": prev_id,
        "preventivo_number": prev.get("number", ""),
        "user_id": uid, "tenant_id": tenant_match(user),
        "supplier_id": data.supplier_id or "",
        "supplier_name": data.supplier_name,
        "items": items,
        "note": data.note or "",
        "status": "inviata",
        "total_offered": None,
        "response_note": "",
        "converted_to_oda": False,
        "oda_id": None,
        "commessa_id": None,
        "created_at": now,
        "updated_at": now,
    }

    await db[COLL].insert_one(rdp_doc)
    rdp_doc.pop("_id", None)
    return {"message": f"RdP creata per {data.supplier_name}", "rdp": rdp_doc}


@router.put("/{prev_id}/rdp/{rdp_id}/response")
async def record_rdp_response(prev_id: str, rdp_id: str, data: RdpResponseInput, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Record supplier's price response."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    rdp = await db[COLL].find_one({"rdp_id": rdp_id, "preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not rdp:
        raise HTTPException(404, "RdP non trovata")

    now = datetime.now(timezone.utc)
    items = rdp.get("items", [])

    # Update individual item prices
    for price_entry in data.prices:
        idx = price_entry.get("line_index")
        unit_price = price_entry.get("unit_price", 0)
        for item in items:
            if item["line_index"] == idx:
                item["supplier_price"] = float(unit_price)
                break

    # Calculate total if not provided
    total = data.total_offered
    if total is None:
        total = sum(
            (it.get("supplier_price") or 0) * it.get("quantity", 1)
            for it in items
        )

    await db[COLL].update_one(
        {"rdp_id": rdp_id},
        {"$set": {
            "items": items,
            "total_offered": round(total, 2),
            "response_note": data.note or "",
            "status": "risposta_ricevuta",
            "updated_at": now,
        }}
    )

    updated = await db[COLL].find_one({"rdp_id": rdp_id}, {"_id": 0})
    return {"message": "Prezzi fornitore registrati", "rdp": updated}


@router.post("/{prev_id}/rdp/{rdp_id}/apply-prices")
async def apply_rdp_prices_to_preventivo(prev_id: str, rdp_id: str, data: UpdatePreventivoPricesInput, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Apply supplier prices + markup to the preventivo lines."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    prev = await db[PREV_COLL].find_one({"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    rdp = await db[COLL].find_one({"rdp_id": rdp_id, "preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not rdp:
        raise HTTPException(404, "RdP non trovata")

    lines = prev.get("lines", [])
    updated_lines = []

    for rule in data.markup_rules:
        idx = rule.get("line_index")
        supplier_price = float(rule.get("supplier_price", 0))
        markup_pct = float(rule.get("markup_pct", 30))

        if 0 <= idx < len(lines):
            client_price = round(supplier_price * (1 + markup_pct / 100), 2)
            lines[idx]["unit_price"] = client_price
            lines[idx]["costo_fornitore"] = supplier_price
            lines[idx]["ricarico_pct"] = markup_pct

            # Recalculate line_total
            qty = float(lines[idx].get("quantity", 1) or 1)
            sc1 = float(lines[idx].get("sconto_1", 0) or 0)
            sc2 = float(lines[idx].get("sconto_2", 0) or 0)
            total = client_price * qty * (1 - sc1/100) * (1 - sc2/100)
            lines[idx]["line_total"] = round(total, 2)

            updated_lines.append({
                "line_index": idx,
                "description": lines[idx].get("description", ""),
                "supplier_price": supplier_price,
                "markup_pct": markup_pct,
                "client_price": client_price,
            })

    # Recalculate preventivo totals
    imponibile = sum(float(l.get("line_total", 0) or 0) for l in lines)
    total_vat = 0
    for l in lines:
        vat_rate = float(l.get("vat_rate", 22) or 22)
        line_tot = float(l.get("line_total", 0) or 0)
        total_vat += line_tot * vat_rate / 100

    now = datetime.now(timezone.utc)
    await db[PREV_COLL].update_one(
        {"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)},
        {"$set": {
            "lines": lines,
            "totals.imponibile": round(imponibile, 2),
            "totals.total_vat": round(total_vat, 2),
            "totals.total": round(imponibile + total_vat, 2),
            "updated_at": now,
        }}
    )

    # Mark RdP as applied
    await db[COLL].update_one(
        {"rdp_id": rdp_id},
        {"$set": {"status": "applicata", "updated_at": now}}
    )

    return {
        "message": f"Prezzi aggiornati su {len(updated_lines)} righe del preventivo",
        "updated_lines": updated_lines,
        "new_totals": {
            "imponibile": round(imponibile, 2),
            "total_vat": round(total_vat, 2),
            "total": round(imponibile + total_vat, 2),
        }
    }


@router.post("/{prev_id}/rdp/{rdp_id}/convert-oda")
async def convert_rdp_to_oda(prev_id: str, rdp_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Convert an RdP to an OdA (Ordine di Acquisto) in the linked commessa."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    rdp = await db[COLL].find_one({"rdp_id": rdp_id, "preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not rdp:
        raise HTTPException(404, "RdP non trovata")

    if rdp.get("converted_to_oda"):
        raise HTTPException(400, f"RdP gia' convertita in OdA: {rdp.get('oda_id')}")

    # Find the linked commessa
    commessa = await db.commesse.find_one(
        {"user_id": uid, "tenant_id": tenant_match(user), "$or": [
            {"moduli.preventivo_id": prev_id},
            {"linked_preventivo_id": prev_id},
        ]},
        {"_id": 0, "commessa_id": 1, "numero": 1}
    )
    if not commessa:
        raise HTTPException(400, "Nessuna commessa collegata a questo preventivo. Accettare prima il preventivo.")

    cid = commessa["commessa_id"]
    now = datetime.now(timezone.utc)
    oda_id = f"oda_{uuid.uuid4().hex[:10]}"

    # Build OdA righe from RdP items
    righe = []
    for item in rdp.get("items", []):
        righe.append({
            "descrizione": item.get("description", ""),
            "quantita": item.get("quantity", 1),
            "unita_misura": item.get("unit", "kg"),
            "prezzo_unitario": item.get("supplier_price") or 0,
            "richiede_cert_31": False,
            "note": item.get("note", ""),
        })

    oda = {
        "ordine_id": oda_id,
        "fornitore_nome": rdp.get("supplier_name", ""),
        "fornitore_id": rdp.get("supplier_id", ""),
        "righe": righe,
        "importo_totale": rdp.get("total_offered") or sum(
            (r.get("prezzo_unitario", 0) * r.get("quantita", 1)) for r in righe
        ),
        "note": f"Convertito da RdP {rdp_id} — Preventivo {rdp.get('preventivo_number', '')}",
        "riferimento_rdp_id": rdp_id,
        "stato": "emesso",
        "data_ordine": now.isoformat(),
    }

    # Ensure approvvigionamento structure exists
    await db.commesse.update_one(
        {"commessa_id": cid, "approvvigionamento": {"$exists": False}},
        {"$set": {"approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []}}}
    )

    # Push OdA to commessa
    await db.commesse.update_one(
        {"commessa_id": cid},
        {"$push": {"approvvigionamento.ordini": oda}}
    )

    # Update RdP status
    await db[COLL].update_one(
        {"rdp_id": rdp_id},
        {"$set": {
            "converted_to_oda": True,
            "oda_id": oda_id,
            "commessa_id": cid,
            "status": "convertita_oda",
            "updated_at": now,
        }}
    )

    return {
        "message": f"OdA {oda_id} creato nella commessa {commessa.get('numero', cid)}",
        "oda_id": oda_id,
        "commessa_id": cid,
    }


@router.delete("/{prev_id}/rdp/{rdp_id}")
async def delete_rdp(prev_id: str, rdp_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Delete an RdP."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    result = await db[COLL].delete_one({"rdp_id": rdp_id, "preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "RdP non trovata")
    return {"message": "RdP eliminata"}


# ── PDF Generation ──

@router.get("/{prev_id}/rdp/{rdp_id}/pdf")
async def download_rdp_pdf(prev_id: str, rdp_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Generate a professional PDF for the RdP to send to the supplier."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    uid = user["user_id"]
    tid = user["tenant_id"]
    rdp = await db[COLL].find_one({"rdp_id": rdp_id, "preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not rdp:
        raise HTTPException(404, "RdP non trovata")

    company = await db.company_settings.find_one({"user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0}) or {}
    prev = await db[PREV_COLL].find_one({"preventivo_id": prev_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0})

    pdf_bytes = _generate_rdp_pdf(rdp, company, prev)

    filename = f"RdP_{rdp.get('supplier_name', 'Fornitore').replace(' ', '_')}_{rdp_id[-6:]}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_rdp_pdf(rdp: dict, company: dict, preventivo: dict) -> bytes:
    """Generate professional RdP PDF."""
    from weasyprint import HTML
    import html as html_mod

    esc = html_mod.escape
    co = company or {}

    def _s(v): return esc(str(v or ""))
    def _fmt(n):
        try:
            val = float(n or 0)
            s = f"{val:,.2f}"
            return s.replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    # Company info
    biz = _s(co.get("business_name"))
    addr = _s(co.get("address"))
    cap_city = f"{_s(co.get('cap'))} {_s(co.get('city'))}"
    piva = _s(co.get("partita_iva"))
    phone = _s(co.get("phone") or co.get("tel"))
    email = _s(co.get("email") or co.get("contact_email"))

    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" style="max-width:160px;max-height:50px;" />'

    # Date
    from datetime import datetime
    created = rdp.get("created_at")
    if isinstance(created, datetime):
        date_str = created.strftime("%d/%m/%Y")
    else:
        date_str = datetime.now().strftime("%d/%m/%Y")

    # Items table
    rows = ""
    for i, item in enumerate(rdp.get("items", []), 1):
        rows += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_s(item.get('description',''))}</td>
            <td style="text-align:right;">{_fmt(item.get('quantity',0))}</td>
            <td style="text-align:center;">{_s(item.get('unit',''))}</td>
            <td style="text-align:center;">{_s(item.get('note',''))}</td>
        </tr>"""

    note = _s(rdp.get("note", "")).replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<style>
@page {{ size: A4; margin: 16mm; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: Helvetica, "Liberation Sans", Arial, sans-serif; font-size:9pt; color:#1a1a2e; line-height:1.4; }}
.header {{ display:table; width:100%; margin-bottom:5mm; }}
.header-left {{ display:table-cell; width:50%; vertical-align:top; }}
.header-right {{ display:table-cell; width:50%; vertical-align:top; text-align:right; }}
.company {{ font-size:8pt; color:#64748b; line-height:1.6; }}
.company-name {{ font-size:13pt; font-weight:800; color:#1a1a2e; }}
.divider {{ height:3px; background:#1a3a6b; margin:3mm 0 4mm; border-radius:1px; }}
.title {{ font-size:18pt; font-weight:800; color:#1a3a6b; margin-bottom:2mm; }}
.subtitle {{ font-size:10pt; color:#64748b; margin-bottom:4mm; }}
.meta {{ display:table; width:100%; margin-bottom:5mm; }}
.meta-left {{ display:table-cell; width:50%; vertical-align:top; }}
.meta-right {{ display:table-cell; width:50%; vertical-align:top; }}
.meta-box {{ padding:3mm; border:1px solid #e2e8f0; border-radius:4px; background:#f8fafc; }}
.meta-label {{ font-size:7.5pt; font-weight:600; color:#94a3b8; letter-spacing:1px; text-transform:uppercase; margin-bottom:1px; }}
.meta-name {{ font-size:11pt; font-weight:700; color:#1a1a2e; margin-bottom:1px; }}
.meta-details {{ font-size:8.5pt; color:#475569; line-height:1.5; }}
table.items {{ width:100%; border-collapse:collapse; margin:3mm 0; }}
table.items thead th {{ background:#f1f5f9; border-bottom:2px solid #cbd5e1; padding:8px; font-size:7.5pt; font-weight:700; text-transform:uppercase; color:#475569; letter-spacing:0.5px; }}
table.items tbody td {{ padding:9px 8px; border-bottom:1px solid #e2e8f0; }}
.note-box {{ margin-top:4mm; padding:3mm; background:#fffbeb; border:1px solid #fde68a; border-radius:4px; font-size:8.5pt; color:#92400e; }}
.response-area {{ margin-top:6mm; padding:4mm; border:2px dashed #cbd5e1; border-radius:6px; background:#f8fafc; }}
.response-title {{ font-size:10pt; font-weight:700; color:#1a3a6b; margin-bottom:3mm; }}
.response-table {{ width:100%; border-collapse:collapse; }}
.response-table td {{ padding:6px 8px; border-bottom:1px solid #e2e8f0; }}
.response-table .label {{ font-size:8pt; color:#64748b; }}
.footer {{ position:fixed; bottom:12mm; left:16mm; right:16mm; text-align:center; font-size:7pt; color:#a0aec0; border-top:1px solid #e2e8f0; padding-top:2mm; }}
</style></head><body>

<!-- HEADER -->
<div class="header">
    <div class="header-left">{logo_html}<div class="company-name">{biz}</div><div class="company">{addr}<br>{cap_city}<br>P.IVA {piva}{"<br>Tel " + phone if phone else ""}{"<br>" + email if email else ""}</div></div>
    <div class="header-right"><div style="font-size:8pt;color:#64748b;">Data</div><div style="font-size:12pt;font-weight:700;">{date_str}</div></div>
</div>

<div class="divider"></div>

<!-- TITLE -->
<div class="title">RICHIESTA DI OFFERTA</div>
<div class="subtitle">Rif. Preventivo {_s(rdp.get('preventivo_number',''))}</div>

<!-- DESTINATARIO -->
<div class="meta">
    <div class="meta-left">
        <div class="meta-box">
            <div class="meta-label">Destinatario</div>
            <div class="meta-name">Spett.le {_s(rdp.get('supplier_name',''))}</div>
        </div>
    </div>
    <div class="meta-right">
        <div class="meta-box" style="text-align:left;">
            <div class="meta-label">Riferimento Interno</div>
            <div class="meta-details">RdP ID: {rdp.get('rdp_id','')}<br>Prev.: {_s(rdp.get('preventivo_number',''))}</div>
        </div>
    </div>
</div>

<p style="margin-bottom:4mm;font-size:9pt;">Con la presente Vi chiediamo cortesemente di volerci quotare i seguenti materiali/lavorazioni:</p>

<!-- ITEMS TABLE -->
<table class="items">
    <thead><tr>
        <th style="width:6%;text-align:center;">N.</th>
        <th style="width:50%;text-align:left;">Descrizione</th>
        <th style="width:14%;text-align:right;">Quantita'</th>
        <th style="width:10%;text-align:center;">U.M.</th>
        <th style="width:20%;text-align:center;">Note</th>
    </tr></thead>
    <tbody>{rows}</tbody>
</table>

{"<div class='note-box'><strong>Note:</strong> " + note + "</div>" if note else ""}

<!-- RESPONSE AREA -->
<div class="response-area">
    <div class="response-title">Spazio riservato alla Vs. offerta</div>
    <table class="response-table">
        <tr><td class="label" style="width:40%;">Prezzo totale offerto:</td><td style="border-bottom:1px solid #333; width:60%;"></td></tr>
        <tr><td class="label">Tempi di consegna:</td><td style="border-bottom:1px solid #333;"></td></tr>
        <tr><td class="label">Validita' offerta:</td><td style="border-bottom:1px solid #333;"></td></tr>
        <tr><td class="label">Note:</td><td style="border-bottom:1px solid #333;height:20mm;"></td></tr>
    </table>
    <div style="margin-top:5mm;display:table;width:100%;">
        <div style="display:table-cell;width:50%;"><div style="font-size:8pt;color:#64748b;">Data</div><div style="border-bottom:1px solid #333;width:80%;height:12mm;"></div></div>
        <div style="display:table-cell;width:50%;"><div style="font-size:8pt;color:#64748b;">Timbro e Firma</div><div style="border-bottom:1px solid #333;width:80%;height:12mm;"></div></div>
    </div>
</div>

<div class="footer">{biz} — P.IVA {piva} — Documento generato da 1090 Norma Facile</div>
</body></html>"""

    from io import BytesIO
    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    return buf.getvalue()
