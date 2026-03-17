"""
Personale Routes â Dipendenti, Presenze, Documenti, Report.
Prefix: /api/personale (registered via main.py include_router)
"""
import io
import logging
from datetime import datetime, timezone
from uuid import uuid4
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional

from core.database import db
from core.security import get_current_user
from models.dipendente import DipendenteModel, PresenzaModel, DocumentoPersonaleModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/personale", tags=["personale"])

MESI_IT = {
    "01": "Gennaio", "02": "Febbraio", "03": "Marzo", "04": "Aprile",
    "05": "Maggio", "06": "Giugno", "07": "Luglio", "08": "Agosto",
    "09": "Settembre", "10": "Ottobre", "11": "Novembre", "12": "Dicembre",
}

# âââ DIPENDENTI ââââââââââââââââââââââââââââââââââââââââââââââââââ

@router.get("/dipendenti")
async def list_dipendenti(user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    docs = await db.dipendenti.find(
        {"user_id": uid, "attivo": True}, {"_id": 0}
    ).sort("cognome", 1).to_list(200)
    return {"dipendenti": docs, "total": len(docs)}


@router.post("/dipendenti")
async def create_dipendente(body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    dip = DipendenteModel(user_id=uid, **body)
    doc = dip.model_dump()
    await db.dipendenti.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/dipendenti/{dipendente_id}")
async def update_dipendente(dipendente_id: str, body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    body.pop("_id", None)
    body.pop("dipendente_id", None)
    body.pop("user_id", None)
    result = await db.dipendenti.update_one(
        {"dipendente_id": dipendente_id, "user_id": uid},
        {"$set": body}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Dipendente non trovato")
    updated = await db.dipendenti.find_one(
        {"dipendente_id": dipendente_id, "user_id": uid}, {"_id": 0}
    )
    return updated


@router.delete("/dipendenti/{dipendente_id}")
async def delete_dipendente(dipendente_id: str, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    result = await db.dipendenti.update_one(
        {"dipendente_id": dipendente_id, "user_id": uid},
        {"$set": {"attivo": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Dipendente non trovato")
    return {"ok": True}


# âââ PRESENZE ââââââââââââââââââââââââââââââââââââââââââââââââââââ

@router.get("/presenze")
async def list_presenze(
    mese: str = Query("", description="yyyy-mm"),
    dipendente_id: str = Query(""),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    filt = {"user_id": uid}
    if mese:
        filt["data"] = {"$regex": f"^{mese}"}
    if dipendente_id:
        filt["dipendente_id"] = dipendente_id
    docs = await db.presenze.find(filt, {"_id": 0}).sort("data", 1).to_list(1000)
    return {"presenze": docs, "total": len(docs)}


@router.post("/presenze")
async def create_presenza(body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    # Check if already exists for this date+dipendente
    existing = await db.presenze.find_one({
        "user_id": uid,
        "dipendente_id": body.get("dipendente_id"),
        "data": body.get("data"),
    })
    if existing:
        # Update existing
        await db.presenze.update_one(
            {"presenza_id": existing["presenza_id"]},
            {"$set": {
                "tipo": body.get("tipo", "presente"),
                "ore_lavorate": body.get("ore_lavorate", 0),
                "ore_straordinario": body.get("ore_straordinario", 0),
                "note": body.get("note", ""),
            }}
        )
        updated = await db.presenze.find_one(
            {"presenza_id": existing["presenza_id"]}, {"_id": 0}
        )
        return updated

    pres = PresenzaModel(user_id=uid, **body)
    doc = pres.model_dump()
    await db.presenze.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/presenze/bulk")
async def bulk_presenze(body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    dip_id = body.get("dipendente_id")
    giorni = body.get("giorni", [])
    if not dip_id or not giorni:
        raise HTTPException(400, "dipendente_id e giorni richiesti")

    results = []
    for g in giorni:
        data = g.get("data")
        if not data:
            continue
        existing = await db.presenze.find_one({
            "user_id": uid, "dipendente_id": dip_id, "data": data
        })
        if existing:
            await db.presenze.update_one(
                {"presenza_id": existing["presenza_id"]},
                {"$set": {
                    "tipo": g.get("tipo", "presente"),
                    "ore_lavorate": g.get("ore_lavorate", 0),
                    "ore_straordinario": g.get("ore_straordinario", 0),
                    "note": g.get("note", ""),
                }}
            )
        else:
            pres = PresenzaModel(
                user_id=uid, dipendente_id=dip_id,
                data=data,
                tipo=g.get("tipo", "presente"),
                ore_lavorate=g.get("ore_lavorate", 0),
                ore_straordinario=g.get("ore_straordinario", 0),
                note=g.get("note", ""),
            )
            doc = pres.model_dump()
            await db.presenze.insert_one(doc)
            doc.pop("_id", None)
        results.append(data)
    return {"ok": True, "inserted": len(results)}


@router.put("/presenze/{presenza_id}")
async def update_presenza(presenza_id: str, body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    body.pop("_id", None)
    body.pop("presenza_id", None)
    body.pop("user_id", None)
    result = await db.presenze.update_one(
        {"presenza_id": presenza_id, "user_id": uid},
        {"$set": body}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Presenza non trovata")
    updated = await db.presenze.find_one(
        {"presenza_id": presenza_id, "user_id": uid}, {"_id": 0}
    )
    return updated


@router.delete("/presenze/{presenza_id}")
async def delete_presenza(presenza_id: str, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    result = await db.presenze.delete_one({"presenza_id": presenza_id, "user_id": uid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Presenza non trovata")
    return {"ok": True}


# âââ DOCUMENTI âââââââââââââââââââââââââââââââââââââââââââââââââââ

@router.get("/documenti")
async def list_documenti(
    dipendente_id: str = Query(""),
    tipo: str = Query(""),
    mese: str = Query(""),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    filt = {"user_id": uid}
    if dipendente_id:
        filt["dipendente_id"] = dipendente_id
    if tipo:
        filt["tipo"] = tipo
    if mese:
        filt["mese"] = mese
    docs = await db.documenti_personale.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"documenti": docs, "total": len(docs)}


@router.post("/documenti/upload")
async def upload_documento(
    file: UploadFile = File(...),
    dipendente_id: str = Form(...),
    tipo: str = Form("altro"),
    mese: str = Form(""),
    descrizione: str = Form(""),
    importo: float = Form(0.0),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    file_data = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf"
    storage_path = f"norma-facile/personale/{uid}/{uuid4()}.{ext}"

    from services.object_storage import put_object
    result = put_object(storage_path, file_data, file.content_type or "application/pdf")

    doc_model = DocumentoPersonaleModel(
        user_id=uid,
        dipendente_id=dipendente_id,
        tipo=tipo,
        mese=mese,
        descrizione=descrizione or file.filename,
        importo=importo,
        file_url=result["path"],
    )
    doc = doc_model.model_dump()
    await db.documenti_personale.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/documenti/{documento_id}")
async def delete_documento(documento_id: str, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    doc = await db.documenti_personale.find_one(
        {"documento_id": documento_id, "user_id": uid}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    result = await db.documenti_personale.delete_one(
        {"documento_id": documento_id, "user_id": uid}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Documento non trovato")
    return {"ok": True}


@router.get("/documenti/{documento_id}/download")
async def download_documento(documento_id: str, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    doc = await db.documenti_personale.find_one(
        {"documento_id": documento_id, "user_id": uid}, {"_id": 0}
    )
    if not doc or not doc.get("file_url"):
        raise HTTPException(404, "Documento non trovato")
    from services.object_storage import get_object
    data, ct = get_object(doc["file_url"])
    filename = doc.get("descrizione", "documento") + ".pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# âââ REPORT ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

@router.get("/report/mensile")
async def report_mensile(
    mese: str = Query(..., description="yyyy-mm"),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    dipendenti = await db.dipendenti.find(
        {"user_id": uid, "attivo": True}, {"_id": 0}
    ).to_list(200)

    presenze = await db.presenze.find(
        {"user_id": uid, "data": {"$regex": f"^{mese}"}}, {"_id": 0}
    ).to_list(5000)

    documenti = await db.documenti_personale.find(
        {"user_id": uid, "mese": mese}, {"_id": 0}
    ).to_list(500)

    # Check if already sent
    sent = await db.report_inviati.find_one(
        {"user_id": uid, "mese": mese}, {"_id": 0}
    )

    # Aggregate per dipendente
    report = []
    for dip in dipendenti:
        did = dip["dipendente_id"]
        pres_dip = [p for p in presenze if p["dipendente_id"] == did]
        docs_dip = [d for d in documenti if d["dipendente_id"] == did]

        conteggi = {"presente": 0, "assente": 0, "ferie": 0, "permesso": 0, "malattia": 0, "straordinario": 0}
        ore_totali = 0.0
        ore_straordinario = 0.0
        for p in pres_dip:
            t = p.get("tipo", "presente")
            if t in conteggi:
                conteggi[t] += 1
            ore_totali += float(p.get("ore_lavorate", 0) or 0)
            ore_straordinario += float(p.get("ore_straordinario", 0) or 0)

        rimborsi = sum(float(d.get("importo", 0) or 0) for d in docs_dip if d.get("tipo") == "rimborso_spese")
        buste_paga = [d for d in docs_dip if d.get("tipo") == "busta_paga"]

        report.append({
            "dipendente_id": did,
            "nome": dip.get("nome", ""),
            "cognome": dip.get("cognome", ""),
            "ruolo": dip.get("ruolo", ""),
            "tipo_contratto": dip.get("tipo_contratto", ""),
            "conteggi": conteggi,
            "ore_totali": round(ore_totali, 1),
            "ore_straordinario": round(ore_straordinario, 1),
            "rimborsi_spese": round(rimborsi, 2),
            "buste_paga": len(buste_paga),
            "presenze_dettaglio": pres_dip,
        })

    return {
        "mese": mese,
        "report": report,
        "totale_dipendenti": len(report),
        "inviato": sent is not None,
        "inviato_il": sent.get("sent_at") if sent else None,
        "email_destinatario": sent.get("email_destinatario") if sent else None,
    }


def _generate_report_pdf(mese: str, report: list, company_name: str, logo_url: str = "") -> bytes:
    """Generate PDF report for presenze using WeasyPrint."""
    from services.pdf_template import render_pdf

    mm, yy = mese.split("-")[1], mese.split("-")[0]
    mese_label = f"{MESI_IT.get(mm, mm)} {yy}"

    rows_html = ""
    for dip in report:
        nome = f"{dip['cognome']} {dip['nome']}"
        c = dip["conteggi"]
        rows_html += f"""
        <tr>
            <td style="font-weight:600">{nome}</td>
            <td style="text-align:center">{c['presente']}</td>
            <td style="text-align:center">{c['assente']}</td>
            <td style="text-align:center">{c['ferie']}</td>
            <td style="text-align:center">{c['permesso']}</td>
            <td style="text-align:center">{c['malattia']}</td>
            <td style="text-align:center">{dip['ore_totali']}</td>
            <td style="text-align:center">{dip['ore_straordinario']}</td>
            <td style="text-align:right">{dip['rimborsi_spese']:.2f} &euro;</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4 landscape; margin: 15mm; }}
    body {{ font-family: 'Helvetica Neue', sans-serif; font-size: 10pt; color: #1e293b; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0055FF; padding-bottom: 10px; margin-bottom: 20px; }}
    .header h1 {{ font-size: 18pt; color: #0055FF; margin: 0; }}
    .header .company {{ font-size: 10pt; color: #64748b; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th {{ background: #0055FF; color: white; padding: 8px 6px; text-align: center; font-size: 9pt; }}
    th:first-child {{ text-align: left; }}
    td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 9pt; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .footer {{ margin-top: 30px; font-size: 8pt; color: #94a3b8; text-align: center; }}
</style></head><body>
    <div class="header">
        <div>
            <h1>Registro Presenze &mdash; {mese_label}</h1>
            <div class="company">{company_name}</div>
        </div>
    </div>
    <table>
        <thead>
            <tr>
                <th style="text-align:left">Dipendente</th>
                <th>Presenze</th>
                <th>Assenze</th>
                <th>Ferie</th>
                <th>Permessi</th>
                <th>Malattia</th>
                <th>Ore Lav.</th>
                <th>Ore Straord.</th>
                <th style="text-align:right">Rimborsi</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    <div class="footer">
        Generato automaticamente da Norma Facile 2.0 &mdash; {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}
    </div>
</body></html>"""

    buf = io.BytesIO()
    HTML(string=html).write_pdf(buf)
    return buf.getvalue()


@router.post("/report/invia-email")
async def invia_report_email(
    mese: str = Query(..., description="yyyy-mm"),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]

    # Get consulente email from settings
    company = await db.company_settings.find_one({"user_id": uid}, {"_id": 0})
    email_consulente = (company or {}).get("report_presenze_email_consulente", "")
    if not email_consulente:
        raise HTTPException(400, "Email consulente non configurata. Vai in Report > Impostazioni.")

    company_name = (company or {}).get("business_name", "Azienda")

    # Generate report data
    report_data = await report_mensile(mese=mese, user=user)
    report = report_data["report"]

    # Generate PDF
    pdf_bytes = _generate_report_pdf(mese, report, company_name)

    mm, yy = mese.split("-")[1], mese.split("-")[0]
    mese_label = f"{MESI_IT.get(mm, mm)} {yy}"

    # Send via Resend
    from core.config import settings as app_settings
    try:
        import resend
        resend.api_key = app_settings.resend_api_key
        import base64
        resend.Emails.send({
            "from": f"{company_name} <{app_settings.sender_email}>",
            "to": [email_consulente],
            "subject": f"Registro Presenze - {mese_label}",
            "html": f"""
                <div style="font-family:sans-serif;padding:20px;">
                    <h2 style="color:#0055FF;">Registro Presenze &mdash; {mese_label}</h2>
                    <p>In allegato il registro presenze mensile con {len(report)} dipendenti.</p>
                    <p style="color:#64748b;font-size:12px;">Inviato automaticamente da Norma Facile 2.0</p>
                </div>
            """,
            "attachments": [{
                "filename": f"presenze_{mese}.pdf",
                "content": base64.b64encode(pdf_bytes).decode(),
                "type": "application/pdf",
            }],
        })
    except Exception as e:
        logger.error(f"[PERSONALE] Errore invio email report: {e}")
        raise HTTPException(500, f"Errore invio email: {str(e)}")

    # Record send
    await db.report_inviati.insert_one({
        "user_id": uid,
        "mese": mese,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "email_destinatario": email_consulente,
    })

    return {"ok": True, "email": email_consulente, "mese": mese_label}


@router.get("/report/pdf")
async def download_report_pdf(
    mese: str = Query(..., description="yyyy-mm"),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    company = await db.company_settings.find_one({"user_id": uid}, {"_id": 0})
    company_name = (company or {}).get("business_name", "Azienda")
    report_data = await report_mensile(mese=mese, user=user)
    pdf_bytes = _generate_report_pdf(mese, report_data["report"], company_name)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="presenze_{mese}.pdf"'}
    )


@router.post("/report/schedula")
async def schedula_report(body: dict, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    giorno = body.get("report_presenze_giorno_invio", 5)
    email = body.get("report_presenze_email_consulente", "")
    if not email:
        raise HTTPException(400, "Email consulente richiesta")
    if not (1 <= giorno <= 28):
        raise HTTPException(400, "Giorno invio deve essere tra 1 e 28")

    await db.company_settings.update_one(
        {"user_id": uid},
        {"$set": {
            "report_presenze_giorno_invio": giorno,
            "report_presenze_email_consulente": email,
        }},
        upsert=True,
    )
    return {"ok": True, "giorno": giorno, "email": email}


@router.get("/report/impostazioni")
async def get_report_settings(user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    company = await db.company_settings.find_one({"user_id": uid}, {"_id": 0})
    return {
        "report_presenze_giorno_invio": (company or {}).get("report_presenze_giorno_invio", 5),
        "report_presenze_email_consulente": (company or {}).get("report_presenze_email_consulente", ""),
    }
