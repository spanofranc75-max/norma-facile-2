"""
Template PDF — Richiesta Preventivo Laboratorio Prove.
Genera una bozza professionale per qualifica processo 111 (elettrodo rivestito)
secondo UNI EN ISO 15614-1, EXC2, acciai S275/S355.

GET /api/template-111/preview/{commessa_id}  — Dati preview
GET /api/template-111/pdf/{commessa_id}      — Download PDF
"""
import io
import html as html_mod
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/template-111", tags=["template-111"])
logger = logging.getLogger(__name__)

_e = html_mod.escape


async def _get_company_data(user_id: str) -> dict:
    """Fetch company settings for the template."""
    settings = await db.company_settings.find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    return settings or {}


@router.get("/preview/{commessa_id}")
async def preview_template_111(commessa_id: str, user: dict = Depends(get_current_user)):
    """Preview data for the template."""
    uid = user["user_id"]
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "classe_esecuzione": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    company = await _get_company_data(uid)

    # Auto-detect EXC from riesame
    exc = commessa.get("classe_esecuzione", "")
    if not exc:
        riesame = await db.riesami_tecnici.find_one(
            {"commessa_id": commessa_id}, {"_id": 0, "checks": 1}
        )
        if riesame:
            for ck in (riesame.get("checks") or []):
                if ck.get("id") == "exc_class" and ck.get("valore"):
                    exc = ck["valore"]
                    break
    exc = exc or "EXC2"

    return {
        "commessa_id": commessa_id,
        "numero_commessa": commessa.get("numero", ""),
        "titolo_commessa": commessa.get("title", ""),
        "classe_esecuzione": exc,
        "azienda": {
            "ragione_sociale": company.get("business_name") or company.get("ragione_sociale", ""),
            "indirizzo": company.get("address") or company.get("indirizzo", ""),
            "citta": company.get("city") or company.get("citta", ""),
            "piva": company.get("partita_iva") or company.get("vat_number") or company.get("piva", ""),
            "email": company.get("email", ""),
            "telefono": company.get("phone") or company.get("telefono", ""),
            "cert_en1090": company.get("cert_en1090", ""),
        },
        "specifiche_tecniche": {
            "norma_qualifica": "UNI EN ISO 15614-1",
            "processo": "111 — Saldatura ad arco con elettrodo rivestito (SMAW)",
            "gruppo_materiali": "Gruppo 1.1 e 1.2 (EN ISO/TR 15608)",
            "gradi_acciaio": "S275JR / S355JR",
            "spessori": "da 3 mm a 30 mm",
            "posizioni": "PA, PB, PC, PF (tutte le posizioni richieste dal progetto)",
            "tipo_giunto": "Testa a testa (BW) e a T (FW)",
        },
    }


@router.get("/pdf/{commessa_id}")
async def download_template_111_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate and download the PDF template."""
    uid = user["user_id"]
    data = await preview_template_111(commessa_id, user)
    company = await _get_company_data(uid)

    az = data["azienda"]
    spec = data["specifiche_tecniche"]
    exc = data["classe_esecuzione"]
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    # Logo
    logo_html = ""
    logo_b64 = company.get("logo_url", "")
    if logo_b64 and logo_b64.startswith("data:"):
        logo_html = f'<img src="{logo_b64}" style="max-height:60px;max-width:200px;">'
    else:
        logo_html = f'<div style="font-size:18px;font-weight:700;color:#1a365d;">{_e(az["ragione_sociale"])}</div>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 20mm 18mm; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; color: #1a202c; line-height: 1.5; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #1a365d; padding-bottom: 12px; margin-bottom: 20px; }}
    .header-right {{ text-align: right; font-size: 8pt; color: #718096; }}
    h1 {{ font-size: 16pt; color: #1a365d; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 1px; }}
    h2 {{ font-size: 12pt; color: #2d3748; margin: 18px 0 8px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
    h3 {{ font-size: 10pt; color: #4a5568; margin: 12px 0 6px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0 16px 0; }}
    th, td {{ border: 1px solid #cbd5e0; padding: 6px 10px; font-size: 9pt; text-align: left; }}
    th {{ background: #edf2f7; font-weight: 600; color: #2d3748; }}
    .highlight {{ background: #ebf8ff; border: 1px solid #90cdf4; padding: 10px; border-radius: 4px; margin: 12px 0; }}
    .highlight strong {{ color: #2b6cb0; }}
    .footer {{ position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 7pt; color: #a0aec0; border-top: 1px solid #e2e8f0; padding-top: 6px; }}
    .firma {{ margin-top: 40px; }}
    .firma-line {{ border-bottom: 1px solid #2d3748; width: 250px; display: inline-block; margin-top: 50px; }}
</style></head><body>

<div class="header">
    <div>{logo_html}</div>
    <div class="header-right">
        {_e(az["ragione_sociale"])}<br>
        {_e(az["indirizzo"])} {_e(az["citta"])}<br>
        P.IVA: {_e(az["piva"])}<br>
        Data: {today}
    </div>
</div>

<h1>Richiesta Preventivo per Qualifica Processo di Saldatura</h1>
<p style="color:#718096;margin-top:0;">Rif. Commessa: {_e(data.get("numero_commessa",""))} — {_e(data.get("titolo_commessa",""))}</p>

<h2>1. Oggetto della Richiesta</h2>
<p>La scrivente {_e(az["ragione_sociale"])} (P.IVA {_e(az["piva"])}), operante nel settore delle costruzioni metalliche
in conformita alla norma <strong>EN 1090-1</strong> in classe <strong>{_e(exc)}</strong>,
richiede preventivo per la <strong>qualifica del processo di saldatura n. 111</strong>
(saldatura ad arco con elettrodo rivestito — SMAW) in accordo alla norma:</p>

<div class="highlight">
    <strong>UNI EN ISO 15614-1</strong> — Specificazione e qualificazione delle procedure di saldatura per materiali metallici.
    Prove di qualificazione della procedura di saldatura. Parte 1: Saldatura ad arco e saldatura a gas degli acciai.
</div>

<h2>2. Specifiche Tecniche</h2>
<table>
    <tr><th style="width:40%;">Parametro</th><th>Valore Richiesto</th></tr>
    <tr><td>Norma di Qualifica</td><td><strong>{_e(spec["norma_qualifica"])}</strong></td></tr>
    <tr><td>Processo di Saldatura</td><td>{_e(spec["processo"])}</td></tr>
    <tr><td>Classe di Esecuzione</td><td><strong>{_e(exc)}</strong></td></tr>
    <tr><td>Gruppo Materiali Base</td><td>{_e(spec["gruppo_materiali"])}</td></tr>
    <tr><td>Gradi di Acciaio</td><td>{_e(spec["gradi_acciaio"])}</td></tr>
    <tr><td>Gamma Spessori</td><td>{_e(spec["spessori"])}</td></tr>
    <tr><td>Posizioni di Saldatura</td><td>{_e(spec["posizioni"])}</td></tr>
    <tr><td>Tipo di Giunto</td><td>{_e(spec["tipo_giunto"])}</td></tr>
</table>

<h2>3. Prove Richieste</h2>
<table>
    <tr><th>Prova</th><th>Norma di Riferimento</th><th>Note</th></tr>
    <tr><td>Esame visivo (VT)</td><td>EN ISO 17637</td><td>100% — Livello di accettabilita ISO 5817-C</td></tr>
    <tr><td>Radiografia (RT) o Ultrasuoni (UT)</td><td>EN ISO 17636 / EN ISO 17640</td><td>Per giunti testa a testa (BW)</td></tr>
    <tr><td>Prova di piega</td><td>EN ISO 5173</td><td>Al dritto e al rovescio</td></tr>
    <tr><td>Prova di trazione trasversale</td><td>EN ISO 4136</td><td>Proprieta meccaniche del giunto</td></tr>
    <tr><td>Prova di resilienza (Charpy)</td><td>EN ISO 9016</td><td>Se richiesto dal progetto / EXC3+</td></tr>
    <tr><td>Esame macro/micrografia</td><td>EN ISO 17639</td><td>Sezione trasversale del giunto</td></tr>
    <tr><td>Prova di durezza</td><td>EN ISO 9015</td><td>ZTA e metallo fuso</td></tr>
</table>

<h2>4. Informazioni Aggiuntive</h2>
<h3>4.1 Materiale di Apporto</h3>
<p>Elettrodi rivestiti basici conformi a EN ISO 2560 (da concordare con il laboratorio in base
agli spessori e al tipo di giunto).</p>

<h3>4.2 Certificazione Richiesta</h3>
<p>Al termine delle prove, si richiede il rilascio del <strong>WPQR (Welding Procedure Qualification Record)</strong>
conforme a UNI EN ISO 15614-1, utilizzabile per la redazione delle WPS aziendali.</p>

<h3>4.3 Tempistiche</h3>
<p>Si prega di indicare nel preventivo:
<br>— Tempi di esecuzione delle prove
<br>— Tempi di rilascio del WPQR
<br>— Disponibilita per la preparazione dei campioni (se a carico del laboratorio)</p>

<h2>5. Richiesta di Preventivo</h2>
<p>Si prega di voler fornire preventivo dettagliato comprensivo di:</p>
<table>
    <tr><th>Voce</th><th>Note</th></tr>
    <tr><td>Preparazione provini e saldatura campioni</td><td>Se a carico del laboratorio</td></tr>
    <tr><td>Prove non distruttive (VT + RT/UT)</td><td></td></tr>
    <tr><td>Prove distruttive (trazione, piega, resilienza, durezza, macro)</td><td></td></tr>
    <tr><td>Redazione e rilascio WPQR</td><td>Completo di riferimenti normativi</td></tr>
    <tr><td>TOTALE (IVA esclusa)</td><td></td></tr>
</table>

<div class="firma">
    <p>In attesa di cortese riscontro, porgiamo distinti saluti.</p>
    <p style="margin-top:30px;">
        Per {_e(az["ragione_sociale"])}<br>
        <span class="firma-line"></span><br>
        <span style="font-size:8pt;color:#718096;">Timbro e Firma</span>
    </p>
</div>

<div class="footer">
    {_e(az["ragione_sociale"])} — {_e(az["indirizzo"])} {_e(az["citta"])} — P.IVA {_e(az["piva"])}
    {(' — Tel. ' + _e(az["telefono"])) if az.get("telefono") else ''}
    {(' — ' + _e(az["email"])) if az.get("email") else ''}
</div>
</body></html>"""

    from weasyprint import HTML
    buf = io.BytesIO()
    HTML(string=html).write_pdf(buf)
    pdf_bytes = buf.getvalue()

    fname = f"Richiesta_Qualifica_Processo_111_{data.get('numero_commessa','').replace('/','-')}_{today.replace('/','-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
