"""
Verbale di Posa in Opera — Backend routes.
Genera, salva e produce PDF per la dichiarazione di corretta posa.
"""
import uuid
import os
import io
import base64
from datetime import datetime, timezone, date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/verbale-posa", tags=["verbale-posa"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "verbale_posa")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helper: Load commessa + related data ──

async def _load_commessa_context(commessa_id: str, user_id: str = None) -> dict:
    """Load commessa with related FPC batches, DDT, and company info."""
    query = {"commessa_id": commessa_id}
    if user_id:
        query["user_id"] = user_id
    commessa = await db.commesse.find_one(query, {"_id": 0})

    # Fallback: if commessa_id is actually a project_id, find commessa via FPC project
    if not commessa:
        fpc_p = await db.fpc_projects.find_one({"project_id": commessa_id}, {"_id": 0})
        if fpc_p and fpc_p.get("commessa_id"):
            commessa = await db.commesse.find_one({"commessa_id": fpc_p["commessa_id"]}, {"_id": 0})
            if commessa:
                commessa_id = commessa["commessa_id"]

    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Load related batches (lotti materiale)
    batches = await db.fpc_batches.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(50)

    # Load related DDT
    consegne = commessa.get("consegne", [])
    ddt_ids = [c.get("ddt_id") for c in consegne if c.get("ddt_id")]
    ddts = []
    if ddt_ids:
        ddts = await db.ddt.find(
            {"ddt_id": {"$in": ddt_ids}}, {"_id": 0}
        ).to_list(50)

    # Load client info
    client = None
    if commessa.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": commessa["client_id"]}, {"_id": 0}
        )

    # Load company info from company_settings (filtered by user_id)
    company = await db.company_settings.find_one({"user_id": user_id}, {"_id": 0}) or {} if user_id else {}

    # Load FPC project if exists
    fpc_project = await db.fpc_projects.find_one(
        {"commessa_id": commessa_id}, {"_id": 0}
    )
    # Also check by preventivo
    if not fpc_project and commessa.get("linked_preventivo_id"):
        fpc_project = await db.fpc_projects.find_one(
            {"preventivo_id": commessa["linked_preventivo_id"]}, {"_id": 0}
        )

    return {
        "commessa": commessa,
        "batches": batches,
        "ddts": ddts,
        "client": client,
        "company": company,
        "fpc_project": fpc_project,
    }


# ── GET context data for the form ──

@router.get("/context/{commessa_id}")
async def get_verbale_context(commessa_id: str, user: dict = Depends(get_current_user)):
    """Load all data needed to populate the verbale form."""
    ctx = await _load_commessa_context(commessa_id, user["user_id"])
    cm = ctx["commessa"]
    client = ctx["client"] or {}
    company = ctx["company"] or {}
    fpc = ctx["fpc_project"] or {}

    # Format batches for frontend
    lotti = []
    for b in ctx["batches"]:
        lotti.append({
            "batch_id": b.get("batch_id"),
            "material_type": b.get("material_type", "acciaio"),
            "description": b.get("description", b.get("dimensions", "")),
            "heat_number": b.get("heat_number", ""),
            "acciaieria": b.get("acciaieria", ""),
            "cert_31": b.get("cert_31_number", b.get("cert_31", "")),
            "quantity": b.get("quantity", ""),
            "dimensions": b.get("dimensions", ""),
        })

    # Format DDTs
    ddt_list = []
    for d in ctx["ddts"]:
        ddt_list.append({
            "ddt_id": d.get("ddt_id"),
            "number": d.get("number", ""),
            "date": str(d.get("date", d.get("created_at", ""))),
            "destination": d.get("destination", ""),
        })

    # Materials from commessa lines or FPC project lines
    materiali = []
    lines = fpc.get("lines", [])
    if not lines:
        # Try to get from preventivo
        prev_id = cm.get("linked_preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
            if prev:
                lines = prev.get("lines", prev.get("righe", []))

    for line in lines:
        materiali.append({
            "description": line.get("description", line.get("descrizione", "")),
            "quantity": line.get("quantity", line.get("quantita", "")),
            "unit": line.get("unit", line.get("unita", "")),
        })

    return {
        "commessa_id": commessa_id,
        "commessa_number": cm.get("numero", cm.get("number", "")),
        "commessa_title": cm.get("title", cm.get("oggetto", "")),
        "cantiere": cm.get("cantiere", cm.get("title", "")),
        "client_name": cm.get("client_name", client.get("business_name", "")),
        "client_address": client.get("address", ""),
        "client_email": client.get("email", ""),
        "company_name": company.get("business_name") or company.get("ragione_sociale", ""),
        "company_address": company.get("address") or company.get("indirizzo", ""),
        "company_piva": company.get("partita_iva", ""),
        "company_cf": company.get("codice_fiscale", ""),
        "execution_class": fpc.get("fpc_data", {}).get("execution_class", ""),
        "materiali": materiali,
        "lotti": lotti,
        "ddts": ddt_list,
    }


# ── GET existing verbale ──

@router.get("/{commessa_id}")
async def get_verbale(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get existing verbale for a commessa, if any."""
    doc = await db.verbali_posa.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if not doc:
        return {"exists": False}
    # Don't send photo blobs — just metadata
    photos = doc.get("photos", [])
    photo_meta = [{"index": i, "filename": p.get("filename", f"foto_{i+1}.jpg")} for i, p in enumerate(photos)]
    doc["photos"] = photo_meta
    doc["exists"] = True
    return doc


# ── SAVE verbale ──

@router.post("/{commessa_id}")
async def save_verbale(
    commessa_id: str,
    user: dict = Depends(get_current_user),
    data_posa: str = Form(""),
    luogo_posa: str = Form(""),
    responsabile: str = Form(""),
    note_cantiere: str = Form(""),
    check_regola_arte: str = Form("true"),
    check_conformita: str = Form("true"),
    check_materiali: str = Form("true"),
    check_sicurezza: str = Form("true"),
    signature_data: str = Form(""),
    photos: List[UploadFile] = File(default=[]),
):
    """Save or update the verbale di posa."""
    # Verify commessa exists
    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "commessa_id": 1, "numero": 1})
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Process photos — save to disk, store references
    photo_entries = []
    for i, photo in enumerate(photos[:3]):  # Max 3 photos
        content = await photo.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB max per photo
            continue
        ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
        safe_name = f"{commessa_id}_foto_{i}_{uuid.uuid4().hex[:8]}{ext}"
        fpath = os.path.join(UPLOAD_DIR, safe_name)
        with open(fpath, "wb") as f:
            f.write(content)
        photo_entries.append({
            "filename": photo.filename or f"foto_{i+1}.jpg",
            "safe_filename": safe_name,
            "size_kb": round(len(content) / 1024),
        })

    verbale_id = f"vp_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc = {
        "verbale_id": verbale_id,
        "commessa_id": commessa_id,
        "commessa_number": commessa.get("numero", ""),
        "user_id": user.get("user_id"),
        "data_posa": data_posa,
        "luogo_posa": luogo_posa,
        "responsabile": responsabile,
        "note_cantiere": note_cantiere,
        "checklist": {
            "regola_arte": check_regola_arte == "true",
            "conformita_normative": check_conformita == "true",
            "materiali_conformi": check_materiali == "true",
            "sicurezza_rispettata": check_sicurezza == "true",
        },
        "signature_data": signature_data,
        "status": "salvato",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # If new photos uploaded, replace; otherwise keep existing
    existing = await db.verbali_posa.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if photo_entries:
        doc["photos"] = photo_entries
    elif existing and existing.get("photos"):
        doc["photos"] = existing["photos"]
    else:
        doc["photos"] = []

    await db.verbali_posa.update_one(
        {"commessa_id": commessa_id},
        {"$set": doc},
        upsert=True,
    )

    return {"verbale_id": verbale_id, "message": "Verbale salvato"}


# ── GENERATE PDF ──

@router.get("/{commessa_id}/pdf")
async def generate_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate the Verbale di Posa PDF."""
    ctx = await _load_commessa_context(commessa_id, user["user_id"])
    verbale = await db.verbali_posa.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if not verbale:
        raise HTTPException(404, "Verbale non ancora salvato")

    cm = ctx["commessa"]
    client = ctx["client"] or {}
    company = ctx["company"] or {}
    fpc = ctx["fpc_project"] or {}

    today_str = date.today().strftime("%d/%m/%Y")
    commessa_num = cm.get("numero", cm.get("number", commessa_id))

    # Build photo HTML
    photos_html = ""
    for p in verbale.get("photos", []):
        sf = p.get("safe_filename", "")
        fpath = os.path.join(UPLOAD_DIR, sf)
        if sf and os.path.exists(fpath):
            with open(fpath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = sf.rsplit(".", 1)[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            photos_html += f'<div class="photo-item"><img src="data:{mime};base64,{b64}" /><p>{p.get("filename","")}</p></div>'

    # Build signature HTML
    sig_html = ""
    sig_data = verbale.get("signature_data", "")
    if sig_data and sig_data.startswith("data:"):
        sig_html = f'<div class="signature-box"><p class="sig-label">Firma del Committente / Responsabile</p><img src="{sig_data}" class="sig-img" /></div>'
    else:
        sig_html = '<div class="signature-box"><p class="sig-label">Firma del Committente / Responsabile</p><div class="sig-line"></div></div>'

    # Build materials table
    materials = []
    lines = fpc.get("lines", [])
    if not lines:
        prev_id = cm.get("linked_preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
            if prev:
                lines = prev.get("lines", prev.get("righe", []))
    for line in lines:
        desc = line.get("description", line.get("descrizione", ""))
        qty = line.get("quantity", line.get("quantita", ""))
        unit = line.get("unit", line.get("unita", ""))
        materials.append(f'<tr><td>{desc[:120]}</td><td style="text-align:center">{qty}</td><td style="text-align:center">{unit}</td></tr>')

    # Build lotti appendix
    lotti_rows = ""
    for b in ctx["batches"]:
        lotti_rows += f"""<tr>
            <td>{b.get("heat_number","")}</td>
            <td>{b.get("dimensions","")}</td>
            <td>{b.get("acciaieria","")}</td>
            <td>{b.get("cert_31_number", b.get("cert_31",""))}</td>
        </tr>"""

    # Build DDT appendix
    ddt_rows = ""
    for d in ctx["ddts"]:
        ddt_rows += f"""<tr>
            <td>{d.get("number","")}</td>
            <td>{str(d.get("date", d.get("created_at","")))[:10]}</td>
            <td>{d.get("destination","")}</td>
        </tr>"""

    checklist = verbale.get("checklist", {})

    exec_class = fpc.get("fpc_data", {}).get("execution_class", "N/A") if fpc else "N/A"
    company_name = company.get("business_name") or company.get("ragione_sociale", "") if company else ""
    company_addr = company.get("address") or company.get("indirizzo", "") if company else ""
    company_piva = company.get("partita_iva", "") if company else ""

    # Logo aziendale — from company_settings filtered by user_id
    logo_url = company.get("logo_url", "") if company else ""
    if not logo_url:
        cs = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0, "logo_url": 1})
        logo_url = cs.get("logo_url", "") if cs else ""
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" style="max-height:50px;max-width:180px;object-fit:contain;" />'
    else:
        logo_html = f'<h1 style="font-size:18pt;color:#0055FF;margin:0;letter-spacing:1px;">{company_name.upper()}</h1>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.5; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #0055FF; padding-bottom: 12px; margin-bottom: 20px; }}
    .logo-area {{ }}
    .logo-area h1 {{ font-size: 18pt; color: #0055FF; margin: 0; letter-spacing: 1px; }}
    .logo-area p {{ font-size: 8pt; color: #666; margin: 2px 0 0 0; }}
    .doc-info {{ text-align: right; }}
    .doc-info h2 {{ font-size: 12pt; color: #333; margin: 0 0 4px 0; text-transform: uppercase; letter-spacing: 0.5px; }}
    .doc-info p {{ font-size: 8pt; color: #666; margin: 1px 0; }}
    .section {{ margin: 16px 0; }}
    .section-title {{ font-size: 11pt; font-weight: bold; color: #0055FF; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
    th {{ background: #0055FF; color: white; padding: 6px 8px; text-align: left; font-size: 8pt; text-transform: uppercase; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #e5e5e5; font-size: 9pt; }}
    tr:nth-child(even) td {{ background: #f8f9fa; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .info-item {{ }}
    .info-label {{ font-size: 7pt; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
    .info-value {{ font-size: 10pt; font-weight: 500; }}
    .check-item {{ margin: 4px 0; font-size: 10pt; }}
    .check-ok {{ color: #16a34a; font-weight: bold; }}
    .check-no {{ color: #dc2626; }}
    .notes-box {{ background: #f8f9fa; border: 1px solid #e5e5e5; border-radius: 4px; padding: 10px; min-height: 40px; font-size: 9pt; white-space: pre-wrap; }}
    .photos-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 8px 0; }}
    .photo-item {{ text-align: center; }}
    .photo-item img {{ max-width: 100%; max-height: 160px; border: 1px solid #ddd; border-radius: 4px; }}
    .photo-item p {{ font-size: 7pt; color: #888; margin: 2px 0 0 0; }}
    .signature-box {{ margin-top: 30px; text-align: center; }}
    .sig-label {{ font-size: 8pt; color: #888; margin-bottom: 4px; }}
    .sig-img {{ max-height: 80px; }}
    .sig-line {{ border-bottom: 1px solid #333; width: 250px; margin: 40px auto 4px auto; }}
    .appendix {{ page-break-before: always; }}
    .appendix-title {{ font-size: 13pt; font-weight: bold; color: #0055FF; margin-bottom: 12px; }}
    .footer {{ margin-top: 30px; text-align: center; font-size: 7pt; color: #aaa; border-top: 1px solid #e5e5e5; padding-top: 8px; }}
</style></head><body>

<!-- HEADER -->
<div class="header">
    <div class="logo-area">
        {logo_html}
        <p>{company_addr} | P.IVA {company_piva}</p>
    </div>
    <div class="doc-info">
        <h2>Dichiarazione di Corretta Posa in Opera</h2>
        <p>Commessa: <strong>{commessa_num}</strong></p>
        <p>Data: <strong>{verbale.get("data_posa", today_str)}</strong></p>
    </div>
</div>

<!-- DATI CANTIERE -->
<div class="section">
    <div class="section-title">Dati del Cantiere</div>
    <div class="info-grid">
        <div class="info-item"><div class="info-label">Committente</div><div class="info-value">{cm.get("client_name", "")}</div></div>
        <div class="info-item"><div class="info-label">Cantiere / Luogo</div><div class="info-value">{verbale.get("luogo_posa", cm.get("cantiere", cm.get("title","")))}</div></div>
        <div class="info-item"><div class="info-label">Oggetto Lavori</div><div class="info-value">{cm.get("title", cm.get("oggetto",""))}</div></div>
        <div class="info-item"><div class="info-label">Responsabile Montaggio</div><div class="info-value">{verbale.get("responsabile","")}</div></div>
        <div class="info-item"><div class="info-label">Classe di Esecuzione</div><div class="info-value">{exec_class}</div></div>
        <div class="info-item"><div class="info-label">Impresa Esecutrice</div><div class="info-value">{company_name}</div></div>
    </div>
</div>

<!-- MATERIALI -->
<div class="section">
    <div class="section-title">Materiali Posati</div>
    <table>
        <thead><tr><th>Descrizione</th><th style="width:80px;text-align:center">Quantita</th><th style="width:60px;text-align:center">U.M.</th></tr></thead>
        <tbody>{''.join(materials) if materials else '<tr><td colspan="3" style="text-align:center;color:#999">Nessun materiale</td></tr>'}</tbody>
    </table>
</div>

<!-- CHECKLIST -->
<div class="section">
    <div class="section-title">Dichiarazioni</div>
    <div class="check-item">{'<span class="check-ok">[X]</span>' if checklist.get("regola_arte") else '<span class="check-no">[ ]</span>'} Il montaggio e stato eseguito <strong>a regola d'arte</strong></div>
    <div class="check-item">{'<span class="check-ok">[X]</span>' if checklist.get("conformita_normative") else '<span class="check-no">[ ]</span>'} Conformita alle <strong>normative vigenti</strong> (D.M. 17/01/2018 - NTC, EN 1090)</div>
    <div class="check-item">{'<span class="check-ok">[X]</span>' if checklist.get("materiali_conformi") else '<span class="check-no">[ ]</span>'} I materiali utilizzati sono <strong>conformi ai certificati 3.1</strong></div>
    <div class="check-item">{'<span class="check-ok">[X]</span>' if checklist.get("sicurezza_rispettata") else '<span class="check-no">[ ]</span>'} Le <strong>prescrizioni di sicurezza</strong> (D.Lgs 81/08) sono state rispettate</div>
</div>

<!-- NOTE -->
<div class="section">
    <div class="section-title">Note di Cantiere</div>
    <div class="notes-box">{verbale.get("note_cantiere","") or "Nessuna nota."}</div>
</div>

<!-- FOTO -->
{f'<div class="section"><div class="section-title">Documentazione Fotografica</div><div class="photos-grid">{photos_html}</div></div>' if photos_html else ''}

<!-- FIRMA -->
{sig_html}

<div class="footer">
    Documento generato da NormaFacile 2.0 — {company_name} — {today_str}
</div>

<!-- APPENDICE: LOTTI -->
{f'''<div class="appendix">
    <div class="appendix-title">Appendice A — Lotti di Materiale (EN 1090)</div>
    <table>
        <thead><tr><th>N. Colata</th><th>Dimensioni</th><th>Acciaieria</th><th>Cert. 3.1</th></tr></thead>
        <tbody>{lotti_rows if lotti_rows else '<tr><td colspan="4" style="text-align:center;color:#999">Nessun lotto registrato</td></tr>'}</tbody>
    </table>
</div>''' if lotti_rows or True else ''}

<!-- APPENDICE: DDT -->
{f'''<div class="section" style="margin-top:20px">
    <div class="section-title">Appendice B — Documenti di Trasporto (DDT)</div>
    <table>
        <thead><tr><th>Numero DDT</th><th>Data</th><th>Destinazione</th></tr></thead>
        <tbody>{ddt_rows if ddt_rows else '<tr><td colspan="3" style="text-align:center;color:#999">Nessun DDT registrato</td></tr>'}</tbody>
    </table>
</div>'''}

</body></html>"""

    # Generate PDF with WeasyPrint
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html).write_pdf()
    except Exception as e:
        raise HTTPException(500, f"Errore generazione PDF: {str(e)}")

    # File name
    code = commessa_num.replace("/", "-").replace(" ", "_") or commessa_id
    date_str = date.today().strftime("%Y%m%d")
    filename = f"Verbale_Posa_{code}_{date_str}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
