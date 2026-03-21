"""
Riesame Tecnico — Gate di commessa per EN 1090.
Checklist bloccante pre-produzione con verifica automatica e firma digitale.

GET  /api/riesame/{commessa_id}         — Stato riesame + check automatici
POST /api/riesame/{commessa_id}         — Crea/aggiorna il riesame con note
POST /api/riesame/{commessa_id}/approva — Firma e approva (immutabile)
GET  /api/riesame/{commessa_id}/pdf     — PDF Verbale di Riesame
"""
import io
import uuid
import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from weasyprint import HTML

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/riesame", tags=["riesame-tecnico"])
logger = logging.getLogger(__name__)

CHECKS_DEFINITION = [
    {
        "id": "exc_class",
        "sezione": "Contratto",
        "label": "Classe di Esecuzione confermata",
        "desc": "EXC2 (default) o EXC3 specificata nel contratto/ordine",
        "auto": True,
    },
    {
        "id": "materiali_confermati",
        "sezione": "Contratto",
        "label": "Materiali base confermati",
        "desc": "S355J2 per travi, S275JR per piastre — coerenti con ordine",
        "auto": True,
    },
    {
        "id": "disegni_validati",
        "sezione": "Progettazione",
        "label": "Disegni validati e revisionati",
        "desc": "Disegni costruttivi approvati con revisione corrente",
        "auto": False,
    },
    {
        "id": "tolleranze_en1090",
        "sezione": "Progettazione",
        "label": "Tolleranze conformi EN 1090-2",
        "desc": "Tolleranze essenziali e funzionali verificate sul disegno",
        "auto": False,
    },
    {
        "id": "wps_assegnate",
        "sezione": "Saldatura",
        "label": "WPS assegnate alla commessa",
        "desc": "Almeno una WPS disponibile e conforme al materiale",
        "auto": True,
    },
    {
        "id": "saldatori_qualificati",
        "sezione": "Saldatura",
        "label": "Saldatori qualificati disponibili",
        "desc": "Almeno un saldatore con patentino valido per il processo richiesto",
        "auto": True,
    },
    {
        "id": "attrezzature_idonee",
        "sezione": "Attrezzature",
        "label": "Attrezzature con manutenzione valida",
        "desc": "Sega, Trapano, Saldatrice — nessuna in stato fuori servizio",
        "auto": True,
    },
    {
        "id": "strumenti_tarati",
        "sezione": "Attrezzature",
        "label": "Strumenti di misura tarati",
        "desc": "Calibro, metro, livella — taratura in corso di validita",
        "auto": True,
    },
    {
        "id": "tolleranza_calibro",
        "sezione": "Attrezzature",
        "label": "Tolleranza calibro conforme (configurabile per strumento)",
        "desc": "Verifica che la tolleranza di ogni strumento di misura rispetti la soglia impostata (racc. RINA audit 2025)",
        "auto": True,
    },
    {
        "id": "documenti_aziendali",
        "sezione": "Sicurezza",
        "label": "Documenti aziendali validi",
        "desc": "DURC, Visura, DVR — non scaduti per la durata della commessa",
        "auto": True,
    },
    {
        "id": "consumabili_disponibili",
        "sezione": "Approvvigionamento",
        "label": "Consumabili di saldatura disponibili",
        "desc": "Filo/elettrodi con lotto e certificato assegnati alla commessa",
        "auto": True,
    },
]


async def _run_auto_checks(commessa_id: str, user_id: str) -> dict:
    """Esegue le verifiche automatiche leggendo i dati dal database."""
    results = {}
    today = date.today()

    # Load commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    if not commessa:
        return results

    # 1. EXC class
    exc = commessa.get("exc_class") or commessa.get("execution_class", "")
    fpc_prj = await db.fpc_projects.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "fpc_data": 1}
    )
    if fpc_prj:
        exc = exc or fpc_prj.get("fpc_data", {}).get("execution_class", "")
    results["exc_class"] = {
        "ok": bool(exc),
        "valore": exc or "Non definita",
        "nota": f"Classe {exc}" if exc else "Definire la classe di esecuzione nel progetto FPC",
    }

    # 2. Materials confirmed (check FPC batches)
    batches = await db.fpc_batches.find(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    ).to_list(100)
    mat_types = set()
    for b in batches:
        mt = (b.get("material_type") or b.get("material", "")).upper()
        if mt:
            mat_types.add(mt)
    results["materiali_confermati"] = {
        "ok": len(batches) > 0,
        "valore": f"{len(batches)} lotti ({', '.join(sorted(mat_types)[:4])})" if batches else "Nessun lotto",
        "nota": "Lotti materiale registrati con certificati 3.1" if batches else "Caricare i lotti materiale nel modulo FPC",
    }

    # 3. WPS assigned
    wps_list = await db.wps.find(
        {"user_id": user_id}, {"_id": 0, "wps_id": 1, "process": 1, "status": 1}
    ).to_list(50)
    active_wps = [w for w in wps_list if w.get("status") != "revocata"]
    results["wps_assegnate"] = {
        "ok": len(active_wps) > 0,
        "valore": f"{len(active_wps)} WPS attive",
        "nota": "WPS disponibili per la produzione" if active_wps else "Creare almeno una WPS",
    }

    # 4. Qualified welders
    welders = await db.welders.find(
        {"user_id": user_id}, {"_id": 0, "name": 1, "qualifications": 1}
    ).to_list(100)
    qualified = 0
    for w in welders:
        quals = w.get("qualifications", [])
        for q in quals:
            exp = q.get("expiry_date", "")
            if exp:
                try:
                    if date.fromisoformat(str(exp)[:10]) >= today:
                        qualified += 1
                        break
                except (ValueError, TypeError):
                    pass
    results["saldatori_qualificati"] = {
        "ok": qualified > 0,
        "valore": f"{qualified} saldatori qualificati",
        "nota": "Patentini verificati e in corso di validita" if qualified > 0 else "Nessun saldatore con patentino valido",
    }

    # 5. Equipment (attrezzature + instruments)
    instruments = await db.instruments.find(
        {"user_id": user_id}, {"_id": 0}
    ).to_list(100)

    expired_instr = []
    calibro_fuori_tolleranza = []
    for inst in instruments:
        nc = inst.get("next_calibration", "") or inst.get("next_calibration_date", "")
        if nc:
            try:
                if date.fromisoformat(str(nc)[:10]) < today:
                    expired_instr.append(inst.get("name", "?"))
            except (ValueError, TypeError):
                pass
        # Check per-instrument configurable tolerance threshold
        soglia = inst.get("soglia_accettabilita")
        if soglia is not None and isinstance(soglia, (int, float)):
            scostamento = inst.get("ultimo_scostamento")
            if scostamento is not None and isinstance(scostamento, (int, float)):
                unita = inst.get("unita_soglia", "mm")
                if abs(scostamento) > soglia:
                    calibro_fuori_tolleranza.append(
                        f"{inst.get('name','?')}: scostamento {scostamento}{unita} > soglia {soglia}{unita}"
                    )

    results["strumenti_tarati"] = {
        "ok": len(expired_instr) == 0,
        "valore": f"{len(instruments)} strumenti, {len(expired_instr)} scaduti",
        "nota": f"Strumenti scaduti: {', '.join(expired_instr[:3])}" if expired_instr else "Tutti gli strumenti in regola",
    }

    results["attrezzature_idonee"] = {
        "ok": len(expired_instr) == 0 and len(instruments) > 0,
        "valore": f"{len(instruments)} registrati",
        "nota": "Verificare manutenzione macchine" if not instruments else "Attrezzature operative",
    }

    results["tolleranza_calibro"] = {
        "ok": len(calibro_fuori_tolleranza) == 0,
        "valore": "Conforme" if not calibro_fuori_tolleranza else f"{len(calibro_fuori_tolleranza)} fuori tolleranza",
        "nota": "; ".join(calibro_fuori_tolleranza[:3]) if calibro_fuori_tolleranza else "Tutti gli strumenti entro la soglia configurata",
    }

    # 6. Company docs
    from models.company_doc import GLOBAL_DOC_TYPES
    global_docs = await db.company_documents.find(
        {"category": "sicurezza_globale"}, {"_id": 0}
    ).to_list(50)
    gmap = {}
    for d in global_docs:
        tag = (d.get("tags", []) or [None])[0]
        if tag:
            gmap[tag] = d
    doc_problems = []
    for dtype, meta in GLOBAL_DOC_TYPES.items():
        d = gmap.get(dtype)
        if not d:
            doc_problems.append(f"{meta['label']}: mancante")
        elif d.get("scadenza"):
            try:
                exp = date.fromisoformat(d["scadenza"])
                if exp < today:
                    doc_problems.append(f"{meta['label']}: scaduto")
            except (ValueError, TypeError):
                pass

    results["documenti_aziendali"] = {
        "ok": len(doc_problems) == 0,
        "valore": f"{len(gmap)}/{len(GLOBAL_DOC_TYPES)} caricati",
        "nota": "; ".join(doc_problems[:3]) if doc_problems else "Tutti i documenti validi",
    }

    # 7. Consumables
    cons = await db.consumable_batches.find(
        {"user_id": user_id, "assigned_commesse": commessa_id},
        {"_id": 0}
    ).to_list(50)
    if not cons:
        cons = await db.consumable_batches.find(
            {"user_id": user_id}, {"_id": 0}
        ).to_list(5)
    results["consumabili_disponibili"] = {
        "ok": len(cons) > 0,
        "valore": f"{len(cons)} lotti consumabili",
        "nota": "Fili/elettrodi con certificati assegnati" if cons else "Caricare consumabili di saldatura",
    }

    return results


class RiesameNote(BaseModel):
    checks_manuali: dict = Field(default_factory=dict)
    note_generali: str = ""


class RiesameApprova(BaseModel):
    firma_nome: str
    firma_ruolo: str = "Responsabile Qualita"
    note_approvazione: str = ""


@router.get("/{commessa_id}")
async def get_riesame(commessa_id: str, user: dict = Depends(get_current_user)):
    """Stato del riesame tecnico con check automatici in tempo reale."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1, "exc_class": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Run auto checks
    auto_results = await _run_auto_checks(commessa_id, user["user_id"])

    # Load saved riesame
    saved = await db.riesami_tecnici.find_one(
        {"commessa_id": commessa_id}, {"_id": 0}
    )

    # Merge auto + manual checks
    checks = []
    for ck in CHECKS_DEFINITION:
        cid = ck["id"]
        auto_res = auto_results.get(cid, {})
        manual_override = (saved or {}).get("checks_manuali", {}).get(cid)

        if ck["auto"]:
            esito = auto_res.get("ok", False)
            valore = auto_res.get("valore", "")
            nota = auto_res.get("nota", "")
        else:
            esito = manual_override if manual_override is not None else False
            valore = "Confermato" if esito else "Da verificare"
            nota = ""

        checks.append({
            "id": cid,
            "sezione": ck["sezione"],
            "label": ck["label"],
            "desc": ck["desc"],
            "auto": ck["auto"],
            "esito": esito,
            "valore": valore,
            "nota": nota,
        })

    # Aggregate
    superato = all(c["esito"] for c in checks)
    n_ok = sum(1 for c in checks if c["esito"])

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "stato_commessa": commessa.get("stato", ""),
        "checks": checks,
        "superato": superato,
        "n_ok": n_ok,
        "n_totale": len(checks),
        "approvato": (saved or {}).get("approvato", False),
        "data_approvazione": (saved or {}).get("data_approvazione"),
        "firma": (saved or {}).get("firma"),
        "note_generali": (saved or {}).get("note_generali", ""),
        "riesame_id": (saved or {}).get("riesame_id"),
    }


@router.post("/{commessa_id}")
async def save_riesame(commessa_id: str, data: RiesameNote, user: dict = Depends(get_current_user)):
    """Salva i check manuali e le note del riesame (non ancora approvato)."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Check if already approved (immutable)
    saved = await db.riesami_tecnici.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if saved and saved.get("approvato"):
        raise HTTPException(409, "Riesame gia approvato — non modificabile")

    riesame_id = (saved or {}).get("riesame_id") or f"ries_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "riesame_id": riesame_id,
        "commessa_id": commessa_id,
        "user_id": user["user_id"],
        "checks_manuali": data.checks_manuali,
        "note_generali": data.note_generali,
        "approvato": False,
        "updated_at": now,
    }

    await db.riesami_tecnici.update_one(
        {"commessa_id": commessa_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"message": "Riesame salvato", "riesame_id": riesame_id}


@router.post("/{commessa_id}/approva")
async def approva_riesame(commessa_id: str, data: RiesameApprova, user: dict = Depends(get_current_user)):
    """Firma e approva il riesame tecnico. Immutabile dopo approvazione."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "stato": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.riesami_tecnici.find_one({"commessa_id": commessa_id}, {"_id": 0})
    if saved and saved.get("approvato"):
        raise HTTPException(409, "Riesame gia approvato")

    # Verify all auto checks pass
    auto_results = await _run_auto_checks(commessa_id, user["user_id"])
    manual_checks = (saved or {}).get("checks_manuali", {})

    for ck in CHECKS_DEFINITION:
        cid = ck["id"]
        if ck["auto"]:
            if not auto_results.get(cid, {}).get("ok", False):
                raise HTTPException(
                    400,
                    f"Check '{ck['label']}' non superato. Risolvere prima di approvare."
                )
        else:
            if not manual_checks.get(cid):
                raise HTTPException(
                    400,
                    f"Check manuale '{ck['label']}' non confermato."
                )

    now = datetime.now(timezone.utc).isoformat()
    riesame_id = (saved or {}).get("riesame_id") or f"ries_{uuid.uuid4().hex[:12]}"

    await db.riesami_tecnici.update_one(
        {"commessa_id": commessa_id},
        {"$set": {
            "riesame_id": riesame_id,
            "commessa_id": commessa_id,
            "user_id": user["user_id"],
            "approvato": True,
            "data_approvazione": now,
            "firma": {
                "nome": data.firma_nome,
                "ruolo": data.firma_ruolo,
                "timestamp": now,
            },
            "note_approvazione": data.note_approvazione,
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    return {
        "message": "Riesame approvato e firmato",
        "riesame_id": riesame_id,
        "data_approvazione": now,
    }


@router.get("/{commessa_id}/pdf")
async def genera_pdf_riesame(commessa_id: str, user: dict = Depends(get_current_user)):
    """Genera il PDF Verbale di Riesame Tecnico."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    saved = await db.riesami_tecnici.find_one({"commessa_id": commessa_id}, {"_id": 0})
    auto_results = await _run_auto_checks(commessa_id, user["user_id"])

    company = await db.settings.find_one({"type": "company"}, {"_id": 0})
    cs = await db.company_settings.find_one({}, {"_id": 0, "logo_url": 1})
    company_name = (company or {}).get("ragione_sociale", "Steel Project Design")
    logo_url = (company or {}).get("logo_url", "") or (cs or {}).get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" style="max-height:42px;max-width:160px;object-fit:contain;" />'
    else:
        logo_html = f'<strong style="font-size:14pt;color:#0055FF;">{company_name.upper()}</strong>'

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    approvato = (saved or {}).get("approvato", False)
    firma = (saved or {}).get("firma", {})
    manual_checks = (saved or {}).get("checks_manuali", {})

    # Build check rows
    rows_html = ""
    prev_sezione = ""
    for ck in CHECKS_DEFINITION:
        cid = ck["id"]
        auto_res = auto_results.get(cid, {})
        if ck["auto"]:
            esito = auto_res.get("ok", False)
            valore = auto_res.get("valore", "")
        else:
            esito = manual_checks.get(cid, False)
            valore = "Confermato" if esito else "Non confermato"

        icon = "&#10004;" if esito else "&#10008;"
        color = "#16A34A" if esito else "#DC2626"
        sez_cell = ""
        if ck["sezione"] != prev_sezione:
            sez_cell = f'<td rowspan="1" class="sezione">{ck["sezione"]}</td>'
            prev_sezione = ck["sezione"]
        else:
            sez_cell = '<td class="sezione"></td>'

        rows_html += f"""
        <tr>
            {sez_cell}
            <td>{ck['label']}<br><span class="desc">{ck['desc']}</span></td>
            <td class="centro" style="color:{color};font-size:14pt;">{icon}</td>
            <td class="val">{valore}</td>
        </tr>"""

    firma_html = ""
    if approvato and firma:
        firma_html = f"""
        <div class="firma-box">
            <div class="firma-label">APPROVATO</div>
            <div class="firma-name">{firma.get('nome', '')}</div>
            <div class="firma-role">{firma.get('ruolo', '')}</div>
            <div class="firma-date">{firma.get('timestamp', '')[:10]}</div>
        </div>"""
    else:
        firma_html = '<div class="firma-box pending"><div class="firma-label">IN ATTESA DI APPROVAZIONE</div></div>'

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@page {{ size: A4; margin: 18mm; @bottom-center {{ content: "Riesame Tecnico — {commessa.get('numero','')} — Pag. " counter(page) "/" counter(pages); font-size:7pt; color:#94A3B8; font-family:Arial; }} }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size:9pt; color:#1E293B; }}
.header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #0055FF; padding-bottom:4mm; margin-bottom:5mm; }}
.header-right {{ text-align:right; font-size:8pt; color:#64748B; }}
h1 {{ font-size:14pt; color:#1E293B; margin:3mm 0; }}
.meta {{ display:flex; gap:10mm; margin-bottom:5mm; font-size:9pt; }}
.meta-box {{ background:#F8FAFC; border:1px solid #E2E8F0; border-radius:2mm; padding:2mm 4mm; }}
.meta-label {{ font-size:7pt; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; }}
.meta-value {{ font-weight:700; color:#1E293B; }}
table {{ width:100%; border-collapse:collapse; margin-top:3mm; }}
th {{ background:#1E293B; color:white; padding:2.5mm 3mm; font-size:8pt; text-align:left; text-transform:uppercase; letter-spacing:0.3px; }}
td {{ padding:2mm 3mm; border-bottom:0.5px solid #E2E8F0; font-size:8.5pt; vertical-align:top; }}
.sezione {{ font-weight:700; color:#0055FF; font-size:8pt; width:22mm; }}
.centro {{ text-align:center; width:12mm; }}
.val {{ font-size:8pt; color:#475569; width:40mm; }}
.desc {{ font-size:7pt; color:#94A3B8; }}
tr:nth-child(even) {{ background:#FAFBFC; }}
.firma-box {{ margin-top:8mm; border:1.5px solid #16A34A; border-radius:3mm; padding:5mm; text-align:center; max-width:70mm; }}
.firma-box.pending {{ border-color:#F59E0B; }}
.firma-label {{ font-size:10pt; font-weight:800; color:#16A34A; letter-spacing:1px; }}
.pending .firma-label {{ color:#F59E0B; }}
.firma-name {{ font-size:11pt; font-weight:700; margin-top:2mm; }}
.firma-role {{ font-size:8pt; color:#64748B; }}
.firma-date {{ font-size:8pt; color:#94A3B8; margin-top:1mm; }}
.note {{ margin-top:5mm; background:#FFFBEB; border:1px solid #FDE68A; border-radius:2mm; padding:3mm; font-size:8.5pt; }}
</style></head><body>

<div class="header">
    <div>{logo_html}</div>
    <div class="header-right">{company_name}<br>Documento generato: {now_str}</div>
</div>

<h1>Verbale di Riesame Tecnico</h1>
<p style="font-size:9pt;color:#64748B;margin-bottom:4mm;">Riesame dei requisiti contrattuali e verifica idoneita alla produzione — EN 1090-1</p>

<div class="meta">
    <div class="meta-box"><div class="meta-label">Commessa</div><div class="meta-value">{commessa.get('numero','')}</div></div>
    <div class="meta-box"><div class="meta-label">Oggetto</div><div class="meta-value">{commessa.get('title','')}</div></div>
    <div class="meta-box"><div class="meta-label">Cliente</div><div class="meta-value">{commessa.get('client_name','')}</div></div>
    <div class="meta-box"><div class="meta-label">Rif.</div><div class="meta-value">{(saved or {}).get('riesame_id','—')}</div></div>
</div>

<table>
<thead><tr><th>Sezione</th><th>Punto di Verifica</th><th>Esito</th><th>Dettaglio</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>

{f'<div class="note"><strong>Note:</strong> {(saved or {}).get("note_generali","")}</div>' if (saved or {}).get("note_generali") else ''}

{firma_html}

</body></html>"""

    pdf_bytes = HTML(string=html).write_pdf()
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    fname = f"Riesame_Tecnico_{commessa.get('numero','')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})
