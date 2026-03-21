"""
DoP Frazionata — Generazione DoP multiple per la stessa commessa con suffissi (/A, /B, /C).
Ogni DoP traccia solo i materiali associati ai DDT di consegna specifici.

POST /api/fascicolo-tecnico/{cid}/dop-frazionata          — Crea una nuova DoP frazionata
GET  /api/fascicolo-tecnico/{cid}/dop-frazionate          — Lista DoP frazionate
GET  /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}/pdf — Genera PDF DoP
DELETE /api/fascicolo-tecnico/{cid}/dop-frazionata/{dop_id}   — Elimina DoP
"""
import uuid
import logging
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/fascicolo-tecnico", tags=["dop_frazionata"])
logger = logging.getLogger(__name__)

SUFFISSI = [
    "/A", "/B", "/C", "/D", "/E", "/F", "/G", "/H",
    "/I", "/L", "/M", "/N", "/O", "/P", "/Q", "/R",
]


class DopFrazionataCreate(BaseModel):
    ddt_ids: List[str] = []
    descrizione: Optional[str] = ""
    note: Optional[str] = ""


class DopFrazionataUpdate(BaseModel):
    ddt_ids: Optional[List[str]] = None
    descrizione: Optional[str] = None
    note: Optional[str] = None


async def _get_commessa(cid: str, uid: str):
    c = await db.commesse.find_one({"commessa_id": cid, "user_id": uid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Commessa non trovata")
    return c


@router.get("/{cid}/dop-frazionate")
async def list_dop_frazionate(cid: str, user: dict = Depends(get_current_user)):
    """Lista tutte le DoP frazionate per una commessa."""
    await _get_commessa(cid, user["user_id"])
    dops = await db.dop_frazionate.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)

    return {"dop_frazionate": dops, "total": len(dops)}


@router.post("/{cid}/dop-frazionata")
async def create_dop_frazionata(cid: str, data: DopFrazionataCreate, user: dict = Depends(get_current_user)):
    """Crea una nuova DoP frazionata con suffisso progressivo."""
    commessa = await _get_commessa(cid, user["user_id"])
    numero_commessa = commessa.get("numero", cid)

    # Count existing DoP for this commessa to determine suffix
    count = await db.dop_frazionate.count_documents(
        {"commessa_id": cid, "user_id": user["user_id"]}
    )
    if count >= len(SUFFISSI):
        raise HTTPException(400, f"Numero massimo DoP frazionate raggiunto ({len(SUFFISSI)})")

    suffisso = SUFFISSI[count]
    dop_numero = f"{numero_commessa}{suffisso}"
    dop_id = f"dop_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # Fetch materials from selected DDTs
    materiali_tracciati = []
    for ddt_id in (data.ddt_ids or []):
        ddt = await db.ddt_documents.find_one(
            {"ddt_id": ddt_id, "user_id": user["user_id"]},
            {"_id": 0, "number": 1, "lines": 1, "client_name": 1, "created_at": 1}
        )
        if ddt:
            for line in ddt.get("lines", []):
                materiali_tracciati.append({
                    "ddt_id": ddt_id,
                    "ddt_number": ddt.get("number", ""),
                    "descrizione": line.get("description", ""),
                    "quantita": line.get("quantity", 0),
                    "unita": line.get("unit", "pz"),
                    "peso": line.get("weight", ""),
                })

    # Also check for indexed certificate pages (from Smistatore)
    page_index_entries = await db.doc_page_index.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "page_pdf_b64": 0}
    ).to_list(500)

    # Filter pages related to these DDTs
    cert_pages = []
    for p in page_index_entries:
        if p.get("doc_id") in (data.ddt_ids or []):
            cert_pages.append({
                "page_id": p.get("page_id", ""),
                "numero_colata": p.get("numero_colata", ""),
                "tipo_materiale": p.get("tipo_materiale", ""),
                "dimensioni": p.get("dimensioni", ""),
            })

    # === AUTO-POPULATION: EXC class from Riesame Tecnico ===
    exc_class = commessa.get("exc_class") or commessa.get("execution_class") or commessa.get("classe_esecuzione", "")
    if not exc_class:
        riesame = await db.riesami_tecnici.find_one(
            {"commessa_id": cid}, {"_id": 0, "checks": 1}
        )
        if riesame:
            for ck in (riesame.get("checks") or []):
                if ck.get("id") == "exc_class" and ck.get("valore"):
                    exc_class = ck["valore"]
                    break
        fpc_prj = await db.fpc_projects.find_one(
            {"commessa_id": cid}, {"_id": 0, "fpc_data": 1}
        )
        if not exc_class and fpc_prj:
            exc_class = fpc_prj.get("fpc_data", {}).get("execution_class", "")
    exc_class = exc_class or "EXC2"

    # === AUTO-POPULATION: Material batches for traceability ===
    batches_rintracciabilita = []
    batch_docs = await db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}
    ).to_list(200)
    for b in batch_docs:
        batches_rintracciabilita.append({
            "batch_id": b.get("batch_id", ""),
            "descrizione": b.get("dimensions", b.get("material_type", "")),
            "material_type": b.get("material_type", ""),
            "numero_colata": b.get("heat_number", b.get("numero_colata", "")),
            "certificato_31": b.get("numero_certificato", b.get("certificate_31", "")),
            "fornitore": b.get("supplier_name", b.get("fornitore", "")),
            "ddt_numero": b.get("ddt_numero", ""),
        })

    dop = {
        "dop_id": dop_id,
        "commessa_id": cid,
        "user_id": user["user_id"],
        "dop_numero": dop_numero,
        "suffisso": suffisso,
        "ddt_ids": data.ddt_ids or [],
        "descrizione": data.descrizione or f"DoP Frazionata {suffisso}",
        "note": data.note or "",
        "materiali_tracciati": materiali_tracciati,
        "cert_pages": cert_pages,
        "classe_esecuzione": exc_class,
        "batches_rintracciabilita": batches_rintracciabilita,
        "stato": "bozza",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.dop_frazionate.insert_one(dop)
    del dop["_id"]

    return {
        "message": f"DoP {dop_numero} creata con {len(materiali_tracciati)} materiali tracciati",
        "dop": dop,
    }


@router.put("/{cid}/dop-frazionata/{dop_id}")
async def update_dop_frazionata(cid: str, dop_id: str, data: DopFrazionataUpdate, user: dict = Depends(get_current_user)):
    """Aggiorna una DoP frazionata."""
    await _get_commessa(cid, user["user_id"])
    dop = await db.dop_frazionate.find_one(
        {"dop_id": dop_id, "commessa_id": cid}, {"_id": 0}
    )
    if not dop:
        raise HTTPException(404, "DoP non trovata")

    upd = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if data.ddt_ids is not None:
        upd["ddt_ids"] = data.ddt_ids
    if data.descrizione is not None:
        upd["descrizione"] = data.descrizione
    if data.note is not None:
        upd["note"] = data.note

    await db.dop_frazionate.update_one({"dop_id": dop_id}, {"$set": upd})
    return {"message": "DoP aggiornata"}


@router.delete("/{cid}/dop-frazionata/{dop_id}")
async def delete_dop_frazionata(cid: str, dop_id: str, user: dict = Depends(get_current_user)):
    """Elimina una DoP frazionata."""
    await _get_commessa(cid, user["user_id"])
    result = await db.dop_frazionate.delete_one(
        {"dop_id": dop_id, "commessa_id": cid, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "DoP non trovata")
    return {"message": "DoP eliminata"}


@router.get("/{cid}/dop-frazionata/{dop_id}/pdf")
async def generate_dop_frazionata_pdf(cid: str, dop_id: str, user: dict = Depends(get_current_user)):
    """Genera il PDF della DoP frazionata."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    commessa = await _get_commessa(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    dop = await db.dop_frazionate.find_one(
        {"dop_id": dop_id, "commessa_id": cid}, {"_id": 0}
    )
    if not dop:
        raise HTTPException(404, "DoP non trovata")

    # Check if there are unreturned C/L items (stored in commesse collection)
    cl_items = commessa.get("conto_lavoro", [])
    non_rientrati = [cl for cl in cl_items if cl.get("stato") in ("da_inviare", "inviato", "in_lavorazione")]
    if non_rientrati:
        tipi = ", ".join(set(cl.get("tipo", "?") for cl in non_rientrati))
        raise HTTPException(
            400,
            f"Impossibile generare la DoP: {len(non_rientrati)} lavorazioni in conto terzi non rientrate ({tipi}). "
            "Registrare il rientro di tutti i C/L prima di procedere."
        )

    # Get client name
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one(
            {"client_id": commessa["client_id"]},
            {"_id": 0, "business_name": 1, "name": 1}
        )
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")

    pdf_bytes = _generate_dop_pdf(dop, commessa, company, client_name)

    # Mark as emessa
    await db.dop_frazionate.update_one(
        {"dop_id": dop_id},
        {"$set": {"stato": "emessa", "emessa_at": datetime.now(timezone.utc).isoformat()}}
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="DoP_{dop["dop_numero"].replace("/", "_")}.pdf"'}
    )


@router.post("/{cid}/dop-automatica")
async def create_dop_automatica(cid: str, user: dict = Depends(get_current_user)):
    """Crea una DOP EN 1090 completamente automatica — zero input manuale.
    Raccoglie dati da: Riesame Tecnico, Material Batches, Controllo Finale, Report Ispezioni."""
    commessa = await _get_commessa(cid, user["user_id"])
    numero_commessa = commessa.get("numero", cid)

    # Count existing DoP to determine suffix
    count = await db.dop_frazionate.count_documents(
        {"commessa_id": cid, "user_id": user["user_id"]}
    )
    if count >= len(SUFFISSI):
        raise HTTPException(400, f"Numero massimo DoP raggiunto ({len(SUFFISSI)})")

    suffisso = SUFFISSI[count]
    dop_numero = f"{numero_commessa}{suffisso}"
    dop_id = f"dop_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # === 1. EXC class from Riesame Tecnico ===
    exc_class = commessa.get("exc_class") or commessa.get("classe_esecuzione", "")
    riesame = await db.riesami_tecnici.find_one(
        {"commessa_id": cid}, {"_id": 0, "checks": 1, "approvato": 1,
         "firma": 1, "data_approvazione": 1}
    )
    riesame_approvato = bool(riesame and riesame.get("approvato"))
    riesame_firma = (riesame or {}).get("firma", {})
    riesame_data = (riesame or {}).get("data_approvazione", "")
    if not exc_class and riesame:
        for ck in (riesame.get("checks") or []):
            if ck.get("id") == "exc_class" and ck.get("valore"):
                exc_class = ck["valore"]
                break
    if not exc_class:
        fpc_prj = await db.fpc_projects.find_one(
            {"commessa_id": cid}, {"_id": 0, "fpc_data": 1}
        )
        if fpc_prj:
            exc_class = fpc_prj.get("fpc_data", {}).get("execution_class", "")
    exc_class = exc_class or "EXC2"

    # === 2. Material Batches (rintracciabilita + CAM) ===
    batches_rintracciabilita = []
    cam_materiali = []
    batch_docs = await db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}
    ).to_list(200)
    for b in batch_docs:
        batches_rintracciabilita.append({
            "batch_id": b.get("batch_id", ""),
            "descrizione": b.get("dimensions", b.get("material_type", "")),
            "numero_colata": b.get("heat_number", b.get("numero_colata", "")),
            "certificato_31": b.get("numero_certificato", b.get("certificate_31", "")),
            "fornitore": b.get("supplier_name", b.get("fornitore", "")),
            "ddt_numero": b.get("ddt_numero", ""),
            "material_type": b.get("material_type", ""),
        })
        # Collect CAM data from enriched batches
        perc_ric = b.get("percentuale_riciclato")
        if perc_ric is not None:
            cam_materiali.append({
                "descrizione": b.get("dimensions") or b.get("material_type", "Acciaio"),
                "peso_kg": b.get("peso_kg", 0),
                "percentuale_riciclato": perc_ric,
                "metodo_produttivo": b.get("metodo_produttivo", "forno_elettrico_non_legato"),
                "distanza_trasporto_km": b.get("distanza_trasporto_km"),
                "fornitore": b.get("supplier_name", ""),
                "numero_colata": b.get("heat_number", ""),
                "certificazione_epd": b.get("certificazione_epd", ""),
            })

    # === 2b. Also check lotti_cam for this commessa ===
    lotti_cam_docs = await db.lotti_cam.find(
        {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0}
    ).to_list(100)
    for lc in lotti_cam_docs:
        already_tracked = any(
            cm.get("numero_colata") == lc.get("numero_colata") and cm.get("numero_colata")
            for cm in cam_materiali
        )
        if not already_tracked:
            cam_materiali.append({
                "descrizione": lc.get("descrizione", "Materiale"),
                "peso_kg": lc.get("peso_kg", 0),
                "percentuale_riciclato": lc.get("percentuale_riciclato", 0),
                "metodo_produttivo": lc.get("metodo_produttivo", "forno_elettrico_non_legato"),
                "distanza_trasporto_km": lc.get("km_approvvigionamento"),
                "fornitore": lc.get("fornitore", ""),
                "numero_colata": lc.get("numero_colata", ""),
                "certificazione_epd": lc.get("numero_certificazione", ""),
            })

    # Compute CAM summary
    cam_summary = None
    if cam_materiali:
        from models.cam import calcola_cam_commessa, calcola_co2_risparmiata
        cam_calc = calcola_cam_commessa([
            {**m, "uso_strutturale": True, "certificazione": m.get("certificazione_epd") or "dichiarazione_produttore"}
            for m in cam_materiali
        ])
        peso_tot = cam_calc.get("peso_totale_kg", 0)
        peso_ric = cam_calc.get("peso_riciclato_kg", 0)
        co2 = calcola_co2_risparmiata(peso_tot, peso_ric)
        # Compute average transport distance
        distanze = [m["distanza_trasporto_km"] for m in cam_materiali if m.get("distanza_trasporto_km")]
        dist_media = round(sum(distanze) / len(distanze), 1) if distanze else None
        cam_summary = {
            "conforme_cam": cam_calc.get("conforme_cam", False),
            "peso_totale_kg": peso_tot,
            "peso_riciclato_kg": peso_ric,
            "percentuale_riciclato": cam_calc.get("percentuale_riciclato_totale", 0),
            "soglia_minima": cam_calc.get("soglia_minima_richiesta", 75),
            "co2_risparmiata_kg": co2.get("co2_risparmiata_kg", 0),
            "distanza_media_km": dist_media,
            "materiali": cam_materiali,
        }

    # === 3. Report Ispezioni status ===
    report_isp = await db.report_ispezioni.find_one(
        {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0}
    )
    ispezioni_status = {
        "approvato": bool(report_isp and report_isp.get("approvato")),
        "firma": (report_isp or {}).get("firma", {}),
        "data_approvazione": (report_isp or {}).get("data_approvazione", ""),
        "vt_ok": sum(1 for r in (report_isp or {}).get("ispezioni_vt", []) if r.get("esito") is True),
        "vt_totale": len((report_isp or {}).get("ispezioni_vt", [])),
        "dim_ok": sum(1 for r in (report_isp or {}).get("ispezioni_dim", []) if r.get("esito") is True),
        "dim_totale": len((report_isp or {}).get("ispezioni_dim", [])),
    }

    # === 4. Controllo Finale status ===
    ctrl_finale = await db.controlli_finali.find_one(
        {"commessa_id": cid}, {"_id": 0}
    )
    controllo_status = {
        "approvato": bool(ctrl_finale and ctrl_finale.get("approvato")),
        "firma": (ctrl_finale or {}).get("firma", {}),
        "data_approvazione": (ctrl_finale or {}).get("data_approvazione", ""),
    }

    dop = {
        "dop_id": dop_id,
        "commessa_id": cid,
        "user_id": user["user_id"],
        "dop_numero": dop_numero,
        "suffisso": suffisso,
        "ddt_ids": [],
        "descrizione": f"DoP Automatica — Commessa {numero_commessa}",
        "note": "",
        "materiali_tracciati": [],
        "cert_pages": [],
        "classe_esecuzione": exc_class,
        "batches_rintracciabilita": batches_rintracciabilita,
        "cam_summary": cam_summary,
        "automatica": True,
        "riesame": {
            "approvato": riesame_approvato,
            "firma": riesame_firma,
            "data_approvazione": riesame_data,
        },
        "ispezioni": ispezioni_status,
        "controllo_finale": controllo_status,
        "stato": "bozza",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.dop_frazionate.insert_one(dop)
    del dop["_id"]

    return {
        "message": f"DoP automatica {dop_numero} creata — {len(batches_rintracciabilita)} lotti tracciati",
        "dop": dop,
    }


@router.get("/{cid}/etichetta-ce-1090/pdf")
async def generate_ce_label_1090(cid: str, user: dict = Depends(get_current_user)):
    """Genera Etichetta CE per EN 1090 — auto-compilata da Riesame e dati commessa."""
    from fastapi.responses import StreamingResponse
    import html as html_mod
    _e = html_mod.escape

    commessa = await _get_commessa(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # EXC class
    exc_class = commessa.get("exc_class") or commessa.get("classe_esecuzione", "")
    if not exc_class:
        riesame = await db.riesami_tecnici.find_one(
            {"commessa_id": cid}, {"_id": 0, "checks": 1}
        )
        if riesame:
            for ck in (riesame.get("checks") or []):
                if ck.get("id") == "exc_class" and ck.get("valore"):
                    exc_class = ck["valore"]
                    break
    exc_class = exc_class or "EXC2"

    num = commessa.get("numero", "")
    biz = _e(company.get("business_name", ""))
    addr = _e(f"{company.get('address', '')} {company.get('cap', '')} {company.get('city', '')}")
    cert_num = _e(company.get("certificato_en1090_numero", ""))
    ente = _e(company.get("ente_certificatore", ""))
    ente_num = _e(company.get("ente_certificatore_numero", ""))
    logo = company.get("logo_url", "")
    logo_html = f'<img src="{logo}" style="max-height:30px;max-width:120px;margin-bottom:4px;" />' if logo else ""
    anno = datetime.now().year

    # DOP numero (use the latest if exists)
    latest_dop = await db.dop_frazionate.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "dop_numero": 1}
    ).sort("created_at", -1).to_list(1)
    dop_ref = latest_dop[0]["dop_numero"] if latest_dop else f"{num}/A"

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: 148mm 105mm; margin: 4mm; }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1E293B; margin: 0; padding: 0; }}
    .ce-box {{
        border: 3px solid #1E293B; padding: 5mm; height: 92mm;
        position: relative;
    }}
    .ce {{ font-size: 38pt; font-weight: 900; letter-spacing: 4mm; margin: 0; text-align: center; }}
    .info-table {{ width: 94%; margin: 2mm auto 0; font-size: 8pt; border-collapse: collapse; }}
    .info-table td {{ border: none; padding: 1.5mm 3mm; vertical-align: top; }}
    .info-table .lbl {{ text-align: right; width: 42%; font-weight: 700; color: #475569; }}
    .info-table .val {{ text-align: left; color: #1E293B; }}
    .top-bar {{
        display: table; width: 100%; margin-bottom: 2mm;
    }}
    .top-left {{ display: table-cell; width: 50%; vertical-align: middle; }}
    .top-right {{ display: table-cell; width: 50%; text-align: right; vertical-align: middle; }}
    .norma-badge {{
        display: inline-block; background: #1E293B; color: #fff; padding: 2px 8px;
        font-size: 7pt; font-weight: 700; letter-spacing: 0.5px;
    }}
    </style></head><body>
    <div class="ce-box">
        <div class="top-bar">
            <div class="top-left">
                {logo_html}
            </div>
            <div class="top-right">
                <span class="norma-badge">EN 1090-1:2009+A1:2011</span>
            </div>
        </div>
        <div class="ce">CE</div>
        <p style="font-size:11pt;font-weight:700;margin:1mm 0 0;text-align:center;">{biz}</p>
        <p style="font-size:7pt;color:#64748b;margin:0.5mm 0 0;text-align:center;">{addr}</p>
        <hr style="margin:2mm auto;border:none;border-top:1.5px solid #1E293B;width:85%;"/>
        <table class="info-table">
            <tr><td class="lbl">Certificato FPC:</td><td class="val"><strong>{cert_num}</strong></td></tr>
            <tr><td class="lbl">Ente Notificato:</td><td class="val">{ente} (N. {ente_num})</td></tr>
            <tr><td class="lbl">Classe Esecuzione:</td><td class="val"><strong style="font-size:10pt;">{_e(exc_class)}</strong></td></tr>
            <tr><td class="lbl">Commessa:</td><td class="val">{_e(num)}</td></tr>
            <tr><td class="lbl">DoP Rif.:</td><td class="val">{_e(dop_ref)}</td></tr>
            <tr><td class="lbl">Anno Produzione:</td><td class="val">{anno}</td></tr>
        </table>
        <div style="position:absolute;bottom:4mm;left:0;right:0;text-align:center;">
            <span style="font-size:6.5pt;color:#94A3B8;">Reg. UE n. 305/2011 — Prodotti da Costruzione</span>
        </div>
    </div>
    </body></html>"""

    from weasyprint import HTML as WP_HTML
    buf = BytesIO()
    WP_HTML(string=html).write_pdf(buf)
    fname = f"Etichetta_CE_1090_{num.replace('/', '-')}.pdf"
    return StreamingResponse(
        BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


def _build_rintracciabilita_html(dop: dict) -> str:
    """Build professional traceability table from auto-populated material batches."""
    import html as html_mod
    _e = html_mod.escape
    batches = dop.get("batches_rintracciabilita", [])
    if not batches:
        return ""
    rows = ""
    for i, b in enumerate(batches, 1):
        rows += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_e(b.get('descrizione', ''))}</td>
            <td>{_e(b.get('material_type', ''))}</td>
            <td style="font-family:monospace;font-weight:700;color:#1a3a6b;">{_e(b.get('numero_colata', ''))}</td>
            <td>{_e(b.get('certificato_31', ''))}</td>
            <td>{_e(b.get('fornitore', ''))}</td>
            <td>{_e(b.get('ddt_numero', ''))}</td>
        </tr>"""
    return f"""
    <h2>3b. Rintracciabilita Materiali (EN 1090-2, Cap. 5)</h2>
    <div style="background:#e8f0e8;padding:6px 10px;margin-bottom:8px;font-size:8pt;border-left:4px solid #276749;">
        <strong>Catena di tracciabilita:</strong> Riga di Commessa / Disegno -> DDT Fornitore -> Numero Colata -> Certificato 3.1 (EN 10204)
    </div>
    <table>
        <tr><th style="width:5%;">N.</th><th>Profilo / Dimensioni</th><th>Qualita</th>
            <th>N. Colata</th><th>Cert. 3.1</th><th>Fornitore</th><th>DDT</th></tr>
        {rows}
    </table>"""


def _build_verifiche_html(dop: dict) -> str:
    """Build verification sections for auto-DOPs (Riesame, Ispezioni, Controllo Finale)."""
    if not dop.get("automatica"):
        return ""
    import html as html_mod
    _e = html_mod.escape

    sections = []

    # Riesame Tecnico
    ries = dop.get("riesame", {})
    stato_r = "Approvato" if ries.get("approvato") else "Non approvato"
    cls_r = "color:#276749;font-weight:700;" if ries.get("approvato") else "color:#c53030;font-weight:700;"
    firma_r = ries.get("firma", {})
    data_r = (ries.get("data_approvazione") or "")[:10]
    sections.append(f"""
    <h2>4. Riesame Tecnico Pre-Produzione</h2>
    <table>
        <tr><td style="font-weight:700;background:#f0f4f8;width:35%;">Stato</td>
            <td style="{cls_r}">{stato_r}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Firmato da</td>
            <td>{_e(firma_r.get('nome', '—'))} — {_e(firma_r.get('ruolo', ''))}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Data approvazione</td>
            <td>{_e(data_r) if data_r else '—'}</td></tr>
    </table>""")

    # Report Ispezioni VT/Dimensionale
    isp = dop.get("ispezioni", {})
    stato_i = "Approvato" if isp.get("approvato") else "Non approvato"
    cls_i = "color:#276749;font-weight:700;" if isp.get("approvato") else "color:#c53030;font-weight:700;"
    firma_i = isp.get("firma", {})
    data_i = (isp.get("data_approvazione") or "")[:10]
    sections.append(f"""
    <h2>5. Controlli Ispezioni VT / Dimensionali</h2>
    <table>
        <tr><td style="font-weight:700;background:#f0f4f8;width:35%;">Stato</td>
            <td style="{cls_i}">{stato_i}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">VT (Visual Testing)</td>
            <td>{isp.get('vt_ok', 0)}/{isp.get('vt_totale', 0)} conformi — ISO 5817 Livello C</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Dimensionale</td>
            <td>{isp.get('dim_ok', 0)}/{isp.get('dim_totale', 0)} conformi — EN 1090-2 B6/B8</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Firmato da</td>
            <td>{_e(firma_i.get('nome', '—'))} — {_e(firma_i.get('ruolo', ''))}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Data</td>
            <td>{_e(data_i) if data_i else '—'}</td></tr>
    </table>""")

    # Controllo Finale
    cf = dop.get("controllo_finale", {})
    stato_cf = "Approvato" if cf.get("approvato") else "Non approvato"
    cls_cf = "color:#276749;font-weight:700;" if cf.get("approvato") else "color:#c53030;font-weight:700;"
    firma_cf = cf.get("firma", {})
    data_cf = (cf.get("data_approvazione") or "")[:10]
    sections.append(f"""
    <h2>6. Controllo Finale Pre-Spedizione</h2>
    <table>
        <tr><td style="font-weight:700;background:#f0f4f8;width:35%;">Stato</td>
            <td style="{cls_cf}">{stato_cf}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Firmato da</td>
            <td>{_e(firma_cf.get('nome', '—'))} — {_e(firma_cf.get('ruolo', ''))}</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Data</td>
            <td>{_e(data_cf) if data_cf else '—'}</td></tr>
    </table>""")

    return "\n".join(sections)


def _build_cam_section_html(dop: dict) -> str:
    """Build the CAM (Criteri Ambientali Minimi) compliance section for DOP PDF."""
    import html as html_mod
    _e = html_mod.escape
    cam = dop.get("cam_summary")
    if not cam:
        return ""

    conforme = cam.get("conforme_cam", False)
    badge_color = "#276749" if conforme else "#c53030"
    badge_bg = "#d4edda" if conforme else "#f8d7da"
    badge_text = "CONFORME" if conforme else "NON CONFORME"
    peso_tot = cam.get("peso_totale_kg", 0)
    peso_ric = cam.get("peso_riciclato_kg", 0)
    perc = cam.get("percentuale_riciclato", 0)
    soglia = cam.get("soglia_minima", 75)
    co2 = cam.get("co2_risparmiata_kg", 0)
    dist = cam.get("distanza_media_km")

    # Build material rows
    rows = ""
    for i, m in enumerate(cam.get("materiali", []), 1):
        rows += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_e(m.get('descrizione', ''))}</td>
            <td>{_e(m.get('fornitore', ''))}</td>
            <td style="font-family:monospace;font-weight:700;">{_e(m.get('numero_colata', ''))}</td>
            <td style="text-align:right;">{m.get('peso_kg', 0):,.1f} kg</td>
            <td style="text-align:center;font-weight:700;">{m.get('percentuale_riciclato', 0):.1f}%</td>
            <td style="text-align:center;">{_e(_metodo_label(m.get('metodo_produttivo', '')))}</td>
            <td style="text-align:center;">{f"{m['distanza_trasporto_km']:.0f} km" if m.get('distanza_trasporto_km') else '—'}</td>
        </tr>"""

    dist_html = f"""
    <tr><td style="font-weight:700;background:#f0f4f8;">Distanza Media Trasporto</td>
        <td>{dist:.0f} km</td></tr>""" if dist else ""

    return f"""
    <div style="page-break-before: always;"></div>
    <h2 style="color:#1a3a6b;border-bottom:3px solid #1a3a6b;padding-bottom:4px;">
        ALLEGATO CAM — Criteri Ambientali Minimi
    </h2>
    <div style="background:#f8f4e8;border:2px solid #d4a017;padding:10px 14px;margin:10px 0;font-size:9pt;">
        <strong style="color:#8B6914;">DOCUMENTAZIONE PNRR</strong> — Prodotta ai sensi del DM 23 giugno 2022 n. 256
        (Criteri Ambientali Minimi per l'Edilizia) per interventi finanziati con fondi PNRR.
    </div>

    <table style="width:100%;border-collapse:collapse;margin:12px 0;">
        <tr>
            <td style="width:25%;text-align:center;padding:12px;border:2px solid #1a3a6b;background:#f0f4f8;">
                <div style="font-size:7.5pt;color:#555;text-transform:uppercase;">Peso Totale</div>
                <div style="font-size:14pt;font-weight:700;color:#1a3a6b;">{peso_tot:,.1f} kg</div>
            </td>
            <td style="width:25%;text-align:center;padding:12px;border:2px solid #1a3a6b;background:#f0f4f8;">
                <div style="font-size:7.5pt;color:#555;text-transform:uppercase;">Peso Riciclato</div>
                <div style="font-size:14pt;font-weight:700;color:#1a3a6b;">{peso_ric:,.1f} kg</div>
            </td>
            <td style="width:25%;text-align:center;padding:12px;border:2px solid #1a3a6b;background:#f0f4f8;">
                <div style="font-size:7.5pt;color:#555;text-transform:uppercase;">% Riciclato / Soglia</div>
                <div style="font-size:14pt;font-weight:700;color:{badge_color};">{perc:.1f}% / {soglia:.0f}%</div>
            </td>
            <td style="width:25%;text-align:center;padding:12px;border:2px solid #1a3a6b;background:#f0f4f8;">
                <div style="font-size:7.5pt;color:#555;text-transform:uppercase;">CO2 Risparmiata</div>
                <div style="font-size:14pt;font-weight:700;color:#276749;">{co2:,.1f} kg</div>
            </td>
        </tr>
    </table>

    <div style="text-align:center;padding:10px;margin:8px 0;background:{badge_bg};border:3px solid {badge_color};font-size:12pt;font-weight:800;color:{badge_color};">
        {badge_text} AI CRITERI AMBIENTALI MINIMI (DM 256/2022)
    </div>

    <h3 style="color:#1a3a6b;font-size:10pt;margin:16px 0 6px;">Dettaglio Materiali — Dati Estratti da Certificati 3.1</h3>
    <table>
        <tr><th style="width:5%;">N.</th><th>Materiale</th><th>Fornitore</th><th>N. Colata</th>
            <th style="text-align:right;">Peso</th><th style="text-align:center;">% Ric.</th>
            <th style="text-align:center;">Metodo Prod.</th><th style="text-align:center;">Distanza</th></tr>
        {rows}
    </table>

    <table style="margin-top:12px;">
        <tr><td style="font-weight:700;background:#f0f4f8;width:35%;">Soglia Minima Richiesta (DM 256)</td>
            <td>{soglia:.0f}% contenuto riciclato</td></tr>
        <tr><td style="font-weight:700;background:#f0f4f8;">Contenuto Riciclato Medio Ponderato</td>
            <td style="font-weight:700;color:{badge_color};">{perc:.1f}%</td></tr>
        {dist_html}
        <tr><td style="font-weight:700;background:#f0f4f8;">CO2 Risparmiata vs Acciaio Primario</td>
            <td>{co2:,.1f} kg CO2 (fonte: World Steel Association 2023)</td></tr>
    </table>

    <div style="background:#f0f4f8;padding:8px 12px;margin-top:12px;border-left:4px solid #1a3a6b;font-size:8.5pt;color:#333;">
        <strong>Nota:</strong> I valori di contenuto riciclato sono stati estratti dai certificati di colata EN 10204 3.1
        e/o dichiarazioni del produttore. Per acciaio da forno elettrico (EAF), la soglia minima è 75% (non legato)
        o 60% (legato). Per ciclo integrale (BOF/BF), 12%.
    </div>
    """


def _metodo_label(metodo: str) -> str:
    return {
        "forno_elettrico_non_legato": "EAF (non leg.)",
        "forno_elettrico_legato": "EAF (legato)",
        "ciclo_integrale": "BOF/BF",
        "sconosciuto": "N/D",
    }.get(metodo, metodo or "N/D")


def _generate_dop_pdf(dop: dict, commessa: dict, company: dict, client_name: str) -> bytes:
    """Generate a professional, audit-ready DoP PDF for EN 1090 — with CAM integration."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(500, "WeasyPrint non disponibile")

    import html as html_mod
    _e = html_mod.escape

    biz = _e(company.get("business_name", ""))
    addr = _e(f"{company.get('address', '')}".strip())
    cap_city = _e(f"{company.get('cap', '')} {company.get('city', '')}".strip())
    piva = _e(company.get("partita_iva", company.get("vat_number", "")))
    cert_num = _e(company.get("certificato_en1090_numero", ""))
    ente = _e(company.get("ente_certificatore", ""))
    ente_num = _e(company.get("ente_certificatore_numero", ""))
    resp = _e(company.get("responsabile_nome", ""))
    ruolo = _e(company.get("ruolo_firmatario", "Legale Rappresentante"))
    city = _e(company.get("city", ""))
    logo = company.get("logo_url", "")
    firma = company.get("firma_digitale", "")
    phone = _e(company.get("phone", company.get("telefono", "")))
    email = _e(company.get("email", ""))
    pec = _e(company.get("pec", ""))
    now = datetime.now(timezone.utc)

    # Materials table
    materiali_html = ""
    for i, m in enumerate(dop.get("materiali_tracciati", []), 1):
        materiali_html += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_e(m.get('ddt_number', ''))}</td>
            <td>{_e(m.get('descrizione', ''))}</td>
            <td style="text-align:center;">{m.get('quantita', '')}</td>
            <td style="text-align:center;">{_e(m.get('unita', 'pz'))}</td>
            <td style="text-align:right;">{_e(m.get('peso', ''))}</td>
        </tr>"""

    firma_html = f'<img src="{firma}" style="max-height:45px;max-width:160px;" />' if firma else ""

    # Performance table (EN 1090 specific)
    exc = _e(dop.get('classe_esecuzione', commessa.get('classe_esecuzione', 'EXC2')))
    dop_num = _e(dop.get('dop_numero', ''))
    comm_num = _e(commessa.get('numero', ''))
    comm_title = _e(commessa.get('title', commessa.get('oggetto', '')))

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{
        size: A4;
        margin: 18mm 14mm 22mm 14mm;
        @bottom-left {{
            content: "DoP {dop_num} — {biz}";
            font-size: 7pt; color: #999; font-family: Helvetica, Arial, sans-serif;
        }}
        @bottom-right {{
            content: "Pag. " counter(page) " di " counter(pages);
            font-size: 7pt; color: #777; font-family: Helvetica, Arial, sans-serif;
        }}
    }}
    body {{
        font-family: Helvetica, 'Segoe UI', Arial, sans-serif;
        font-size: 9.5pt; color: #111; line-height: 1.5; margin: 0; padding: 0;
    }}
    h1 {{
        font-size: 17pt; color: #1a3a6b; margin: 0 0 4px; text-align: center;
        letter-spacing: 1px; font-weight: 800;
    }}
    h2 {{
        font-size: 11pt; color: #1a3a6b; border-bottom: 2.5px solid #1a3a6b;
        padding-bottom: 3px; margin: 22px 0 8px; font-weight: 700;
    }}
    h3 {{
        font-size: 10pt; color: #1a3a6b; margin: 14px 0 6px; font-weight: 700;
    }}
    table {{
        width: 100%; border-collapse: collapse; margin: 8px 0;
    }}
    td, th {{
        padding: 5px 7px; font-size: 8.5pt; border: 1px solid #bbb;
    }}
    th {{
        background: #1a3a6b; color: #fff; text-align: left; font-size: 8pt;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px;
    }}
    .lbl {{
        font-weight: 700; background: #f0f4f8; width: 30%; color: #1a3a6b;
        font-size: 8.5pt;
    }}
    tr:nth-child(even) {{ background: #f8f9fb; }}
    .badge {{
        display: inline-block; padding: 3px 10px; border-radius: 3px;
        font-size: 8pt; font-weight: 700;
    }}
    .badge-blue {{ background: #dbeafe; color: #1e40af; }}
    .badge-green {{ background: #d4edda; color: #276749; }}
    .badge-red {{ background: #f8d7da; color: #c53030; }}
    .header-bar {{
        background: #1a3a6b; color: #fff; padding: 12px 16px; margin-bottom: 14px;
    }}
    .header-bar table {{ margin: 0; }}
    .header-bar td {{ border: none; padding: 2px 8px; color: #fff; font-size: 8.5pt; }}
    .seal-box {{
        border: 2px solid #1a3a6b; padding: 8px; text-align: center; margin: 6px 0;
    }}
    </style></head><body>

    <!-- ═══ INTESTAZIONE PROFESSIONALE ═══ -->
    <div class="header-bar">
        <table>
            <tr>
                <td style="width:60%;vertical-align:middle;">
                    {f'<img src="{logo}" style="max-height:40px;max-width:160px;margin-right:12px;vertical-align:middle;" />' if logo else ''}
                    <span style="font-size:14pt;font-weight:800;vertical-align:middle;">{biz}</span>
                </td>
                <td style="width:40%;text-align:right;vertical-align:middle;font-size:8pt;line-height:1.6;">
                    {addr}{f"<br/>{cap_city}" if cap_city.strip() else ""}
                    {f"<br/>P.IVA: {piva}" if piva else ""}
                    {f"<br/>Tel: {phone}" if phone else ""}
                </td>
            </tr>
        </table>
    </div>

    <!-- ═══ TITOLO ═══ -->
    <h1>DICHIARAZIONE DI PRESTAZIONE (DoP)</h1>
    <div style="text-align:center;margin:6px 0 14px;">
        <span class="badge badge-blue" style="font-size:11pt;padding:5px 16px;">
            N. {dop_num}
        </span>
    </div>
    <div style="text-align:center;font-size:8.5pt;color:#555;margin-bottom:16px;">
        ai sensi del Regolamento UE n. 305/2011 — Norma armonizzata <strong>EN 1090-1:2009+A1:2011</strong>
        <br/><span class="badge {'badge-green' if dop.get('automatica') else 'badge-blue'}" style="margin-top:4px;">
            {'DoP AUTOMATICA — Compilazione integrale da sistema FPC' if dop.get('automatica') else f"CONSEGNA FRAZIONATA {_e(dop.get('suffisso', ''))}"}
        </span>
    </div>

    <!-- ═══ SEZ. 1 — IDENTIFICAZIONE ═══ -->
    <h2>1. Identificazione del Prodotto</h2>
    <table>
        <tr><td class="lbl">N. Dichiarazione di Prestazione</td><td><strong>{dop_num}</strong></td></tr>
        <tr><td class="lbl">Commessa di Riferimento</td><td>{comm_num} — {comm_title}</td></tr>
        <tr><td class="lbl">Committente</td><td>{_e(client_name)}</td></tr>
        <tr><td class="lbl">Classe di Esecuzione (EN 1090-2)</td><td><strong style="font-size:11pt;">{exc}</strong></td></tr>
        <tr><td class="lbl">Uso Previsto</td><td>Componenti strutturali in acciaio per opere di costruzione</td></tr>
        <tr><td class="lbl">Data di Emissione</td><td>{now.strftime('%d/%m/%Y')}</td></tr>
    </table>

    <!-- ═══ SEZ. 2 — FABBRICANTE ═══ -->
    <h2>2. Fabbricante</h2>
    <table>
        <tr><td class="lbl">Ragione Sociale</td><td><strong>{biz}</strong></td></tr>
        <tr><td class="lbl">Sede Legale / Stabilimento</td><td>{addr} {cap_city}</td></tr>
        {f'<tr><td class="lbl">P.IVA</td><td>{piva}</td></tr>' if piva else ''}
        {f'<tr><td class="lbl">Email / PEC</td><td>{email}{f" — PEC: {pec}" if pec else ""}</td></tr>' if email else ''}
        <tr><td class="lbl">Certificato FPC EN 1090</td><td><strong>{cert_num}</strong></td></tr>
        <tr><td class="lbl">Ente Notificato</td><td>{ente} (N. {ente_num})</td></tr>
    </table>

    <!-- ═══ SEZ. 3 — PRESTAZIONI DICHIARATE ═══ -->
    <h2>3. Prestazioni Dichiarate (EN 1090-1, Tabella ZA.1)</h2>
    <table>
        <tr><th style="width:8%;">Rif.</th><th style="width:35%;">Caratteristica Essenziale</th>
            <th style="width:25%;">Metodo Valutazione</th><th style="width:32%;">Prestazione</th></tr>
        <tr><td style="text-align:center;">ZA.1</td><td>Resistenza meccanica e stabilita</td>
            <td>EN 1090-2, EN 1993</td><td>Classe {exc} — Componenti conformi</td></tr>
        <tr><td style="text-align:center;">ZA.2</td><td>Tolleranze dimensionali</td>
            <td>EN 1090-2, Tab. D.2</td><td>Classe 1 (tolleranze essenziali)</td></tr>
        <tr><td style="text-align:center;">ZA.3</td><td>Saldabilita</td>
            <td>EN ISO 3834-3/2</td><td>Qualificato per classe {exc}</td></tr>
        <tr><td style="text-align:center;">ZA.4</td><td>Tenacita del materiale</td>
            <td>EN 10025, Cert. 3.1</td><td>Certificati di colata verificati</td></tr>
        <tr><td style="text-align:center;">ZA.5</td><td>Reazione al fuoco</td>
            <td>EN 13501-1</td><td>Classe A1 (acciaio non rivestito)</td></tr>
        <tr><td style="text-align:center;">ZA.6</td><td>Resistenza al fuoco</td>
            <td>EN 13501-2</td><td>NPD (da progetto strutturale)</td></tr>
        <tr><td style="text-align:center;">ZA.7</td><td>Durabilita</td>
            <td>EN 1090-2, Cap. 10</td><td>Come da specifica di progetto</td></tr>
    </table>

    <!-- ═══ SEZ. 3b — MATERIALI (se presenti) ═══ -->
    {"" if not materiali_html else f'''
    <h2>3a. Materiali Consegnati con questa DoP</h2>
    <table>
        <tr><th style="width:5%;">N.</th><th>DDT Rif.</th><th>Descrizione</th><th>Qta</th><th>U.M.</th><th style="text-align:right;">Peso</th></tr>
        {materiali_html}
    </table>
    '''}

    {_build_rintracciabilita_html(dop)}

    {_build_verifiche_html(dop)}

    {_build_cam_section_html(dop)}

    {f'<h2>Note Aggiuntive</h2><p style="font-size:9pt;">{_e(dop.get("note", ""))}</p>' if dop.get("note") else ''}

    <!-- ═══ DICHIARAZIONE DI CONFORMITA ═══ -->
    <h2>Dichiarazione di Conformita</h2>
    <div style="border:2px solid #1a3a6b;padding:12px 16px;background:#f8f9fb;margin:8px 0;">
        <p style="font-size:9.5pt;line-height:1.6;margin:0;">
            Il sottoscritto, in qualita di {ruolo} della <strong>{biz}</strong>, dichiara sotto la propria
            responsabilita che i componenti strutturali in acciaio descritti nella presente Dichiarazione di Prestazione
            n. <strong>{dop_num}</strong>, relativi alla commessa <strong>{comm_num}</strong>,
            sono conformi alla norma armonizzata <strong>EN 1090-1:2009+A1:2011</strong> e sono stati prodotti
            in accordo al sistema di Controllo della Produzione in Fabbrica (FPC) certificato dall'Ente Notificato
            <strong>{ente}</strong> con certificato n. <strong>{cert_num}</strong>.
        </p>
    </div>

    <!-- ═══ FIRMA ═══ -->
    <div style="margin-top:28px;">
        <table style="border:none;">
            <tr style="border:none;">
                <td style="border:none;width:50%;vertical-align:bottom;">
                    <p style="font-size:9pt;margin-bottom:4px;"><strong>{resp}</strong></p>
                    <p style="font-size:8pt;color:#555;margin:0;">{ruolo}</p>
                    {firma_html}
                    <div style="border-bottom:1px solid #333;width:220px;margin-top:10px;"></div>
                    <p style="font-size:7.5pt;color:#888;margin-top:2px;">Firma e Timbro</p>
                </td>
                <td style="border:none;width:50%;text-align:right;vertical-align:bottom;">
                    <p style="font-size:9pt;">{city}, {now.strftime('%d/%m/%Y')}</p>
                </td>
            </tr>
        </table>
    </div>

    </body></html>"""

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    return buf.getvalue()


@router.get("/{cid}/rintracciabilita-totale/pdf")
async def generate_rintracciabilita_totale_pdf(cid: str, user: dict = Depends(get_current_user)):
    """Genera la Scheda di Rintracciabilità Totale per una commessa.
    Mostra il legame: Riga Commessa -> DDT Fornitore -> N. Colata -> Cert. 3.1"""
    from fastapi.responses import StreamingResponse
    import html as html_mod
    _e = html_mod.escape

    commessa = await _get_commessa(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Get all material batches
    batch_docs = await db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}
    ).to_list(500)

    if not batch_docs:
        raise HTTPException(400, "Nessun lotto materiale registrato per questa commessa.")

    biz = _e(company.get("business_name", ""))
    addr = _e(f"{company.get('address', '')}".strip())
    cap_city = _e(f"{company.get('cap', '')} {company.get('city', '')}".strip())
    cert_num = _e(company.get("certificato_en1090_numero", ""))
    logo = company.get("logo_url", "")
    now = datetime.now(timezone.utc)
    num = _e(commessa.get("numero", ""))
    title = _e(commessa.get("title", ""))

    rows = ""
    total_peso = 0
    for i, b in enumerate(batch_docs, 1):
        peso = b.get("peso_kg", 0) or 0
        total_peso += peso
        perc_ric = b.get("percentuale_riciclato")
        perc_str = f"{perc_ric:.1f}%" if perc_ric is not None else "—"
        dist = b.get("distanza_trasporto_km")
        dist_str = f"{dist:.0f} km" if dist else "—"

        rows += f"""<tr>
            <td style="text-align:center;">{i}</td>
            <td>{_e(b.get('dimensions', '') or '')}</td>
            <td>{_e(b.get('material_type', ''))}</td>
            <td style="font-family:monospace;font-weight:700;color:#1a3a6b;">{_e(b.get('heat_number', ''))}</td>
            <td>{_e(b.get('numero_certificato', ''))}</td>
            <td>{_e(b.get('supplier_name', ''))}</td>
            <td>{_e(b.get('ddt_numero', ''))}</td>
            <td style="text-align:right;">{f'{peso:,.1f}' if peso else '—'}</td>
            <td style="text-align:center;">{perc_str}</td>
            <td style="text-align:center;">{dist_str}</td>
            <td>{_e(b.get('posizione', '') or '')}</td>
            <td>{_e(b.get('disegno_numero', '') or '')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{
        size: A4 landscape; margin: 14mm 10mm 18mm 10mm;
        @bottom-left {{ content: "Rintracciabilita — {num}"; font-size: 7pt; color: #999; font-family: Helvetica, Arial, sans-serif; }}
        @bottom-right {{ content: "Pag. " counter(page) " di " counter(pages); font-size: 7pt; color: #777; font-family: Helvetica, Arial, sans-serif; }}
    }}
    body {{ font-family: Helvetica, 'Segoe UI', Arial, sans-serif; font-size: 8.5pt; color: #111; line-height: 1.4; margin: 0; }}
    h1 {{ font-size: 14pt; color: #1a3a6b; text-align: center; margin: 0 0 4px; font-weight: 800; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
    td, th {{ padding: 4px 5px; font-size: 7.5pt; border: 1px solid #aaa; }}
    th {{ background: #1a3a6b; color: #fff; font-size: 7pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
    tr:nth-child(even) {{ background: #f8f9fb; }}
    .header-bar {{ background: #1a3a6b; color: #fff; padding: 8px 12px; margin-bottom: 10px; }}
    .header-bar table {{ margin: 0; }}
    .header-bar td {{ border: none; padding: 2px 6px; color: #fff; font-size: 8pt; }}
    .chain {{ background: #e8f0e8; padding: 6px 10px; margin: 6px 0; font-size: 8pt; border-left: 4px solid #276749; }}
    .total-row td {{ font-weight: 700; background: #e8f0f7; }}
    </style></head><body>

    <div class="header-bar">
        <table><tr>
            <td style="width:60%;vertical-align:middle;">
                {f'<img src="{logo}" style="max-height:30px;max-width:140px;margin-right:10px;vertical-align:middle;" />' if logo else ''}
                <span style="font-size:12pt;font-weight:800;vertical-align:middle;">{biz}</span>
            </td>
            <td style="width:40%;text-align:right;font-size:7.5pt;line-height:1.5;">
                {addr} {cap_city}<br/>Cert. EN 1090: {cert_num}
            </td>
        </tr></table>
    </div>

    <h1>SCHEDA DI RINTRACCIABILITA MATERIALI</h1>
    <p style="text-align:center;font-size:9pt;color:#555;margin:0 0 6px;">
        EN 1090-2, Capitolo 5 — Tracciabilita dei prodotti costituenti
    </p>

    <table style="margin-bottom:8px;">
        <tr><td style="font-weight:700;background:#f0f4f8;width:20%;border:1px solid #aaa;">Commessa</td>
            <td style="border:1px solid #aaa;"><strong>{num}</strong> — {title}</td>
            <td style="font-weight:700;background:#f0f4f8;width:15%;border:1px solid #aaa;">Data</td>
            <td style="border:1px solid #aaa;width:15%;">{now.strftime('%d/%m/%Y')}</td></tr>
    </table>

    <div class="chain">
        <strong>Catena di Tracciabilita:</strong>
        Posizione Disegno &#8594; Profilo/Dimensione &#8594; DDT Fornitore &#8594; N. Colata &#8594; Certificato 3.1 (EN 10204)
    </div>

    <table>
        <tr>
            <th style="width:3%;">N.</th>
            <th style="width:12%;">Profilo/Dim.</th>
            <th style="width:7%;">Qualita</th>
            <th style="width:10%;">N. Colata</th>
            <th style="width:10%;">Cert. 3.1</th>
            <th style="width:12%;">Fornitore</th>
            <th style="width:8%;">DDT</th>
            <th style="width:7%;text-align:right;">Peso (kg)</th>
            <th style="width:6%;text-align:center;">% Ric.</th>
            <th style="width:6%;text-align:center;">Dist.</th>
            <th style="width:8%;">Posizione</th>
            <th style="width:8%;">Disegno</th>
        </tr>
        {rows}
        <tr class="total-row">
            <td colspan="7" style="text-align:right;">TOTALE</td>
            <td style="text-align:right;">{total_peso:,.1f}</td>
            <td colspan="4"></td>
        </tr>
    </table>

    <div style="margin-top:14px;font-size:7.5pt;color:#555;border-top:1px solid #ccc;padding-top:6px;">
        <strong>Legenda:</strong> N. Colata = Numero di colata dal certificato del produttore (EN 10204 3.1) |
        % Ric. = Contenuto riciclato dichiarato (CAM DM 256/2022) |
        Dist. = Distanza di trasporto dal fornitore (km)
    </div>

    </body></html>"""

    try:
        from weasyprint import HTML as WP_HTML
        buf = BytesIO()
        WP_HTML(string=html).write_pdf(buf)
    except Exception as e:
        logger.error(f"Rintracciabilita PDF error: {e}")
        raise HTTPException(500, f"Errore generazione PDF: {str(e)}")

    fname = f"Rintracciabilita_{num.replace('/', '-')}.pdf"
    return StreamingResponse(
        BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"'}
    )
