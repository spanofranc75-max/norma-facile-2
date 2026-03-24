"""
Report Ispezioni VT/Dimensionali — EN 1090-2:2024.

Rapporto strutturato per ispezioni finali:
  - VT (Visual Testing) secondo ISO 5817 Livello C
  - Dimensionale secondo EN 1090-2 B6/B8 (tolleranze essenziali)

CRUD + PDF + integrazione con Controllo Finale.

GET  /api/report-ispezioni/{commessa_id}           — Stato report con check auto
POST /api/report-ispezioni/{commessa_id}           — Salva risultati ispezioni
POST /api/report-ispezioni/{commessa_id}/approva   — Firma e chiudi report
GET  /api/report-ispezioni/{commessa_id}/pdf       — Download PDF rapporto
"""
import uuid
import io
import html as html_mod
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/report-ispezioni", tags=["report-ispezioni"])
logger = logging.getLogger(__name__)

_e = html_mod.escape

# ── CHECKLIST DEFINIZIONI ──

VT_CHECKS = [
    {"id": "vt_cricche", "label": "Assenza cricche superficiali", "desc": "Nessuna cricca visibile a occhio nudo o con lente 3x", "rif": "ISO 5817 Tab.1 - 1.1"},
    {"id": "vt_porosita", "label": "Porosita entro limiti", "desc": "Porosita singola max 3mm, raggruppata max 12mm/100mm", "rif": "ISO 5817 Tab.1 - 2.1"},
    {"id": "vt_inclusioni", "label": "Inclusioni di scoria accettabili", "desc": "Lunghezza max 25mm, altezza max 2mm per spessore ≤12mm", "rif": "ISO 5817 Tab.1 - 3.1"},
    {"id": "vt_mancanza_fusione", "label": "Fusione completa", "desc": "Nessuna mancanza di fusione visibile su tutti i giunti", "rif": "ISO 5817 Tab.1 - 4.1"},
    {"id": "vt_mancanza_penetrazione", "label": "Penetrazione adeguata", "desc": "Penetrazione conforme a specifica WPS", "rif": "ISO 5817 Tab.1 - 5.1"},
    {"id": "vt_sottosquadro", "label": "Sottosquadro entro limiti", "desc": "Profondita max 0.5mm (continuo) / 1mm (corto, L<25mm)", "rif": "ISO 5817 Tab.1 - 5.7"},
    {"id": "vt_eccesso_sovrametallo", "label": "Sovrametallo entro limiti", "desc": "Eccesso max 1mm+0.25b (con b = larghezza cordone)", "rif": "ISO 5817 Tab.1 - 5.2"},
    {"id": "vt_slivellamento", "label": "Slivellamento bordi accettabile", "desc": "Max 1mm+0.15t per giunti testa-testa (con t = spessore)", "rif": "ISO 5817 Tab.1 - 5.8"},
    {"id": "vt_spruzzi", "label": "Spruzzi rimossi", "desc": "Spruzzi di saldatura rimossi da zone critiche / a vista", "rif": "EN 1090-2 §7.5.18"},
    {"id": "vt_aspetto_generale", "label": "Aspetto generale cordone", "desc": "Cordone regolare, transizione dolce con metallo base", "rif": "ISO 5817 §5"},
]

DIM_CHECKS = [
    {"id": "dim_lunghezze", "label": "Lunghezze componenti (B6)", "desc": "Tolleranza ±2mm per L≤1000mm, ±3mm per 1000<L≤6000mm", "rif": "EN 1090-2 Tab.B.6"},
    {"id": "dim_rettilineita", "label": "Rettilineita (B6)", "desc": "Freccia max L/1000 ma non oltre 5mm per L≤5000mm", "rif": "EN 1090-2 Tab.B.6"},
    {"id": "dim_squadratura", "label": "Squadratura / Ortogonalita (B6)", "desc": "Deviazione max 1mm per 300mm di lunghezza di riferimento", "rif": "EN 1090-2 Tab.B.6"},
    {"id": "dim_interassi_fori", "label": "Interassi fori (B8)", "desc": "Tolleranza ±1mm per distanze ≤500mm, ±2mm per >500mm", "rif": "EN 1090-2 Tab.B.8"},
    {"id": "dim_diametro_fori", "label": "Diametro fori", "desc": "Tolleranza +1/-0 mm rispetto a nominale (fori normali)", "rif": "EN 1090-2 §6.6"},
    {"id": "dim_posizione_piastre", "label": "Posizione piastre di base/ancoraggio", "desc": "Tolleranza ±3mm dalla posizione nominale", "rif": "EN 1090-2 Tab.B.6"},
    {"id": "dim_altezza_complessiva", "label": "Altezza complessiva sezione", "desc": "Tolleranza ±2mm per h≤300mm, ±3mm per h>300mm", "rif": "EN 1090-2 Tab.B.6"},
    {"id": "dim_gola_saldatura", "label": "Dimensione gola saldature (a)", "desc": "Tolleranza: a nominale -0mm / +2mm", "rif": "EN 1090-2 §7.5.15"},
]


class IspezioneResult(BaseModel):
    check_id: str
    esito: Optional[bool] = None
    valore_misurato: Optional[str] = ""
    note: Optional[str] = ""


class ReportSaveData(BaseModel):
    ispezioni_vt: List[IspezioneResult] = Field(default_factory=list)
    ispezioni_dim: List[IspezioneResult] = Field(default_factory=list)
    strumenti_utilizzati: Optional[str] = ""
    condizioni_ambientali: Optional[str] = ""
    ispettore_nome: Optional[str] = ""
    note_generali: Optional[str] = ""


class ReportApprova(BaseModel):
    firma_nome: str
    firma_ruolo: str = "Ispettore VT/Dimensionale"


@router.get("/{commessa_id}")
async def get_report_ispezioni(commessa_id: str, user: dict = Depends(get_current_user)):
    """Stato del report ispezioni con dati salvati."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.report_ispezioni.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    saved_vt = {r["check_id"]: r for r in (saved or {}).get("ispezioni_vt", [])}
    saved_dim = {r["check_id"]: r for r in (saved or {}).get("ispezioni_dim", [])}

    checks_vt = []
    for ck in VT_CHECKS:
        sv = saved_vt.get(ck["id"], {})
        checks_vt.append({
            **ck,
            "esito": sv.get("esito"),
            "valore_misurato": sv.get("valore_misurato", ""),
            "note": sv.get("note", ""),
        })

    checks_dim = []
    for ck in DIM_CHECKS:
        sv = saved_dim.get(ck["id"], {})
        checks_dim.append({
            **ck,
            "esito": sv.get("esito"),
            "valore_misurato": sv.get("valore_misurato", ""),
            "note": sv.get("note", ""),
        })

    n_vt_ok = sum(1 for c in checks_vt if c["esito"] is True)
    n_vt_nok = sum(1 for c in checks_vt if c["esito"] is False)
    n_dim_ok = sum(1 for c in checks_dim if c["esito"] is True)
    n_dim_nok = sum(1 for c in checks_dim if c["esito"] is False)
    n_vt_pending = len(VT_CHECKS) - n_vt_ok - n_vt_nok
    n_dim_pending = len(DIM_CHECKS) - n_dim_ok - n_dim_nok

    completo = n_vt_pending == 0 and n_dim_pending == 0
    superato = completo and n_vt_nok == 0 and n_dim_nok == 0

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "titolo": commessa.get("title", ""),
        "checks_vt": checks_vt,
        "checks_dim": checks_dim,
        "stats": {
            "vt": {"ok": n_vt_ok, "nok": n_vt_nok, "pending": n_vt_pending, "totale": len(VT_CHECKS)},
            "dim": {"ok": n_dim_ok, "nok": n_dim_nok, "pending": n_dim_pending, "totale": len(DIM_CHECKS)},
        },
        "completo": completo,
        "superato": superato,
        "approvato": (saved or {}).get("approvato", False),
        "firma": (saved or {}).get("firma"),
        "strumenti_utilizzati": (saved or {}).get("strumenti_utilizzati", ""),
        "condizioni_ambientali": (saved or {}).get("condizioni_ambientali", ""),
        "ispettore_nome": (saved or {}).get("ispettore_nome", ""),
        "note_generali": (saved or {}).get("note_generali", ""),
        "report_id": (saved or {}).get("report_id"),
    }


@router.post("/{commessa_id}")
async def save_report_ispezioni(commessa_id: str, data: ReportSaveData, user: dict = Depends(get_current_user)):
    """Salva i risultati delle ispezioni."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.report_ispezioni.find_one({"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0})
    if saved and saved.get("approvato"):
        raise HTTPException(409, "Report gia approvato — non modificabile")

    report_id = (saved or {}).get("report_id") or f"rpt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "report_id": report_id,
        "commessa_id": commessa_id,
        "user_id": user["user_id"],
        "ispezioni_vt": [r.dict() for r in data.ispezioni_vt],
        "ispezioni_dim": [r.dict() for r in data.ispezioni_dim],
        "strumenti_utilizzati": data.strumenti_utilizzati or "",
        "condizioni_ambientali": data.condizioni_ambientali or "",
        "ispettore_nome": data.ispettore_nome or "",
        "note_generali": data.note_generali or "",
        "approvato": False,
        "updated_at": now,
    }

    await db.report_ispezioni.update_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"message": "Report ispezioni salvato", "report_id": report_id}


@router.post("/{commessa_id}/approva")
async def approva_report(commessa_id: str, data: ReportApprova, user: dict = Depends(get_current_user)):
    """Firma e approva il report. Immutabile dopo approvazione."""
    saved = await db.report_ispezioni.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not saved:
        raise HTTPException(404, "Nessun report salvato per questa commessa")
    if saved.get("approvato"):
        raise HTTPException(409, "Report gia approvato")

    # Verify all checks are filled
    vt_results = {r["check_id"]: r for r in saved.get("ispezioni_vt", [])}
    dim_results = {r["check_id"]: r for r in saved.get("ispezioni_dim", [])}
    for ck in VT_CHECKS:
        if ck["id"] not in vt_results or vt_results[ck["id"]].get("esito") is None:
            raise HTTPException(400, f"Ispezione VT '{ck['label']}' non compilata")
    for ck in DIM_CHECKS:
        if ck["id"] not in dim_results or dim_results[ck["id"]].get("esito") is None:
            raise HTTPException(400, f"Ispezione DIM '{ck['label']}' non compilata")

    now = datetime.now(timezone.utc).isoformat()
    await db.report_ispezioni.update_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"$set": {
            "approvato": True,
            "data_approvazione": now,
            "firma": {"nome": data.firma_nome, "ruolo": data.firma_ruolo, "timestamp": now},
            "updated_at": now,
        }},
    )
    return {"message": "Report approvato e firmato", "data_approvazione": now}


@router.get("/{commessa_id}/pdf")
async def download_report_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Genera PDF del rapporto ispezioni."""
    uid = user["user_id"]
    report = await get_report_ispezioni(commessa_id, user)
    company = await db.company_settings.find_one({"user_id": uid}, {"_id": 0}) or {}
    biz = _e(company.get("business_name") or company.get("ragione_sociale", ""))
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    logo_html = ""
    logo_b64 = company.get("logo_url", "")
    if logo_b64 and logo_b64.startswith("data:"):
        logo_html = f'<img src="{logo_b64}" style="max-height:50px;">'

    def _build_rows(checks, area_label):
        rows = ""
        for c in checks:
            esito = c.get("esito")
            esito_txt = "Conforme" if esito is True else "Non Conforme" if esito is False else "—"
            esito_cls = "ok" if esito is True else "nok" if esito is False else ""
            rows += f"""<tr>
                <td>{_e(c['label'])}</td>
                <td style="font-size:7pt;color:#718096;">{_e(c['rif'])}</td>
                <td class="{esito_cls}">{esito_txt}</td>
                <td style="font-size:8pt;">{_e(c.get('valore_misurato',''))}</td>
                <td style="font-size:8pt;">{_e(c.get('note',''))}</td>
            </tr>"""
        return rows

    vt_rows = _build_rows(report["checks_vt"], "VT")
    dim_rows = _build_rows(report["checks_dim"], "DIM")

    firma_html = ""
    firma = report.get("firma")
    if firma:
        firma_html = f"""<div class="firma-box">
            <strong>Approvato da:</strong> {_e(firma['nome'])} — {_e(firma['ruolo'])}<br>
            <strong>Data:</strong> {_e(firma['timestamp'][:10])}<br>
            <em>Rapporto firmato digitalmente — non modificabile</em>
        </div>"""

    stats = report["stats"]
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 15mm; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 9pt; color: #1a202c; }}
    .header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #1a365d; padding-bottom: 8px; margin-bottom: 12px; }}
    h1 {{ font-size: 14pt; color: #1a365d; margin: 0 0 4px 0; }}
    h2 {{ font-size: 11pt; color: #2d3748; margin: 14px 0 6px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 6px 0 12px 0; }}
    th, td {{ border: 1px solid #cbd5e0; padding: 4px 6px; font-size: 8pt; text-align: left; }}
    th {{ background: #edf2f7; font-weight: 600; }}
    .ok {{ color: #276749; font-weight: 700; background: #f0fff4; }}
    .nok {{ color: #c53030; font-weight: 700; background: #fff5f5; }}
    .meta {{ font-size: 8pt; color: #718096; }}
    .stats {{ display: flex; gap: 12px; margin: 8px 0; }}
    .stat {{ padding: 6px 12px; border-radius: 4px; text-align: center; }}
    .stat-ok {{ background: #f0fff4; border: 1px solid #c6f6d5; }}
    .stat-nok {{ background: #fff5f5; border: 1px solid #fed7d7; }}
    .firma-box {{ margin-top: 20px; padding: 10px; background: #ebf8ff; border: 1px solid #90cdf4; border-radius: 4px; }}
</style></head><body>

<div class="header">
    <div>{logo_html if logo_html else f'<div style="font-size:14pt;font-weight:700;color:#1a365d;">{biz}</div>'}</div>
    <div style="text-align:right;" class="meta">
        {biz}<br>Data: {today}<br>Commessa: {_e(report['numero'])}
    </div>
</div>

<h1>Rapporto Ispezioni VT / Dimensionale</h1>
<p class="meta">Commessa: {_e(report['numero'])} — {_e(report['titolo'])}<br>
Ispettore: {_e(report.get('ispettore_nome',''))}<br>
Strumenti: {_e(report.get('strumenti_utilizzati',''))}<br>
Condizioni: {_e(report.get('condizioni_ambientali',''))}</p>

<div class="stats">
    <div class="stat stat-ok">VT OK: <strong>{stats['vt']['ok']}/{stats['vt']['totale']}</strong></div>
    <div class="stat stat-nok">VT NOK: <strong>{stats['vt']['nok']}</strong></div>
    <div class="stat stat-ok">DIM OK: <strong>{stats['dim']['ok']}/{stats['dim']['totale']}</strong></div>
    <div class="stat stat-nok">DIM NOK: <strong>{stats['dim']['nok']}</strong></div>
</div>

<h2>1. Controllo Visivo (VT) — ISO 5817 Livello C</h2>
<table>
    <tr><th style="width:25%;">Verifica</th><th style="width:20%;">Rif. Normativo</th><th style="width:12%;">Esito</th><th style="width:18%;">Misura</th><th>Note</th></tr>
    {vt_rows}
</table>

<h2>2. Controllo Dimensionale — EN 1090-2 B6/B8</h2>
<table>
    <tr><th style="width:25%;">Verifica</th><th style="width:20%;">Rif. Normativo</th><th style="width:12%;">Esito</th><th style="width:18%;">Misura</th><th>Note</th></tr>
    {dim_rows}
</table>

<h2>3. Note Generali</h2>
<p>{_e(report.get('note_generali','') or 'Nessuna nota')}</p>

{firma_html}

</body></html>"""

    from weasyprint import HTML
    buf = io.BytesIO()
    HTML(string=html).write_pdf(buf)
    fname = f"Report_Ispezioni_{report['numero'].replace('/','-')}_{today.replace('/','-')}.pdf"
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
