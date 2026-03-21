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

    # === 2. Material Batches (rintracciabilita) ===
    batches_rintracciabilita = []
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
        })

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
    @page {{ size: 148mm 105mm; margin: 5mm; }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1E293B; margin: 0; padding: 0; }}
    .ce-box {{ border: 3px solid #1E293B; padding: 6mm; text-align: center; height: 90mm; }}
    .ce {{ font-size: 36pt; font-weight: 900; letter-spacing: 3mm; margin: 0; }}
    .info-table {{ width: 92%; margin: 3mm auto 0; font-size: 8pt; border: none; }}
    .info-table td {{ border: none; padding: 1.2mm 3mm; }}
    .info-table .lbl {{ text-align: right; width: 45%; font-weight: 700; color: #475569; }}
    .info-table .val {{ text-align: left; color: #1E293B; }}
    </style></head><body>
    <div class="ce-box">
        {logo_html}
        <div class="ce">CE</div>
        <p style="font-size:10pt;font-weight:700;margin:2mm 0 0;">{biz}</p>
        <p style="font-size:7pt;color:#64748b;margin:1mm 0 0;">{addr}</p>
        <hr style="margin:3mm auto;border:none;border-top:1px solid #ccc;width:80%;"/>
        <table class="info-table">
            <tr><td class="lbl">Norma:</td><td class="val">EN 1090-1:2009+A1:2011</td></tr>
            <tr><td class="lbl">Certificato FPC:</td><td class="val">{cert_num}</td></tr>
            <tr><td class="lbl">Ente Notificato:</td><td class="val">{ente} (N. {ente_num})</td></tr>
            <tr><td class="lbl">Classe Esecuzione:</td><td class="val"><strong>{_e(exc_class)}</strong></td></tr>
            <tr><td class="lbl">Commessa:</td><td class="val">{_e(num)}</td></tr>
            <tr><td class="lbl">DoP Rif.:</td><td class="val">{_e(dop_ref)}</td></tr>
            <tr><td class="lbl">Anno:</td><td class="val">{anno}</td></tr>
        </table>
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
    """Build traceability table from auto-populated material batches."""
    import html as html_mod
    _e = html_mod.escape
    batches = dop.get("batches_rintracciabilita", [])
    if not batches:
        return ""
    rows = ""
    for b in batches:
        rows += f"""<tr>
            <td>{_e(b.get('descrizione', ''))}</td>
            <td style="font-family:monospace;font-weight:700;">{_e(b.get('numero_colata', ''))}</td>
            <td>{_e(b.get('certificato_31', ''))}</td>
            <td>{_e(b.get('fornitore', ''))}</td>
            <td>{_e(b.get('ddt_numero', ''))}</td>
        </tr>"""
    return f"""
    <h2>3b. Rintracciabilita Materiali</h2>
    <table>
        <tr><th>Materiale</th><th>N. Colata</th><th>Cert. 3.1</th><th>Fornitore</th><th>DDT</th></tr>
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


def _generate_dop_pdf(dop: dict, commessa: dict, company: dict, client_name: str) -> bytes:
    """Generate a DoP PDF for a fractioned delivery."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(500, "WeasyPrint non disponibile")

    import html as html_mod
    _e = html_mod.escape

    biz = _e(company.get("business_name", ""))
    cert_num = _e(company.get("certificato_en1090_numero", ""))
    ente = _e(company.get("ente_certificatore", ""))
    ente_num = _e(company.get("ente_certificatore_numero", ""))
    resp = _e(company.get("responsabile_nome", ""))
    ruolo = _e(company.get("ruolo_firmatario", "Legale Rappresentante"))
    city = _e(company.get("city", ""))
    logo = company.get("logo_url", "")
    firma = company.get("firma_digitale", "")
    now = datetime.now(timezone.utc)

    materiali_html = ""
    for m in dop.get("materiali_tracciati", []):
        materiali_html += f"""<tr>
            <td>{_e(m.get('ddt_number', ''))}</td>
            <td>{_e(m.get('descrizione', ''))}</td>
            <td style="text-align:center;">{m.get('quantita', '')}</td>
            <td style="text-align:center;">{_e(m.get('unita', 'pz'))}</td>
            <td>{_e(m.get('peso', ''))}</td>
        </tr>"""

    logo_html = f'<img src="{logo}" style="max-height:45px;max-width:180px;" />' if logo else ""
    firma_html = f'<img src="{firma}" style="max-height:40px;max-width:140px;" />' if firma else ""

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: A4; margin: 18mm 16mm 20mm 16mm;
        @bottom-left {{ content: "DoP {_e(dop.get('dop_numero', ''))}"; font-size: 7pt; color: #999; }}
        @bottom-right {{ content: "Pag. " counter(page); font-size: 7pt; color: #777; }}
    }}
    body {{ font-family: Calibri, Arial, sans-serif; font-size: 10pt; color: #111; line-height: 1.45; }}
    h1 {{ font-size: 16pt; color: #1a3a6b; margin: 0 0 6px; }}
    h2 {{ font-size: 12pt; color: #1a3a6b; border-bottom: 2px solid #1a3a6b; padding-bottom: 3px; margin: 20px 0 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
    td, th {{ padding: 4px 7px; font-size: 9pt; border: 1px solid #bbb; }}
    th {{ background: #1a3a6b; color: #fff; text-align: left; font-size: 8.5pt; }}
    .lbl {{ font-weight: 700; background: #f0f4f8; width: 30%; }}
    tr:nth-child(even) {{ background: #f8f9fb; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 8pt; font-weight: 700; background: #dbeafe; color: #1e40af; }}
    </style></head><body>

    <div style="text-align:center;margin-bottom:20px;">
        {logo_html}
        <h1>DICHIARAZIONE DI PRESTAZIONE (DoP)</h1>
        <div style="font-size:14pt;font-weight:800;color:#1a3a6b;margin:8px 0;">N. {_e(dop.get('dop_numero', ''))}</div>
        <div class="badge">EN 1090-1 — {_e('DoP AUTOMATICA' if dop.get('automatica') else f"CONSEGNA FRAZIONATA {dop.get('suffisso', '')}")}</div>
    </div>

    <h2>1. Identificazione</h2>
    <table>
        <tr><td class="lbl">N. DoP</td><td><strong>{_e(dop.get('dop_numero', ''))}</strong></td></tr>
        <tr><td class="lbl">Commessa</td><td>{_e(commessa.get('numero', ''))}</td></tr>
        <tr><td class="lbl">Oggetto</td><td>{_e(commessa.get('title', commessa.get('oggetto', '')))}</td></tr>
        <tr><td class="lbl">Committente</td><td>{_e(client_name)}</td></tr>
        <tr><td class="lbl">Descrizione Consegna</td><td>{_e(dop.get('descrizione', ''))}</td></tr>
        <tr><td class="lbl">Classe di Esecuzione</td><td><strong>{_e(dop.get('classe_esecuzione', commessa.get('classe_esecuzione', 'EXC2')))}</strong></td></tr>
    </table>

    <h2>2. Fabbricante</h2>
    <table>
        <tr><td class="lbl">Ragione Sociale</td><td>{biz}</td></tr>
        <tr><td class="lbl">Certificato EN 1090</td><td>{cert_num}</td></tr>
        <tr><td class="lbl">Ente Notificato</td><td>{ente} (N. {ente_num})</td></tr>
    </table>

    <h2>3. Materiali Consegnati con questa DoP</h2>
    <table>
        <tr><th>DDT Rif.</th><th>Descrizione Materiale</th><th>Qta</th><th>U.M.</th><th>Peso</th></tr>
        {materiali_html if materiali_html else '<tr><td colspan="5" style="text-align:center;color:#888;">Nessun materiale associato</td></tr>'}
    </table>

    {_build_rintracciabilita_html(dop)}

    {_build_verifiche_html(dop)}

    {f'<h2>Note</h2><p>{_e(dop.get("note", ""))}</p>' if dop.get("note") else ''}

    <h2>Dichiarazione di Conformita</h2>
    <p style="font-size:10pt;">
        Il fabbricante <strong>{biz}</strong> dichiara che i componenti strutturali sopra descritti,
        consegnati con questa DoP frazionata <strong>{_e(dop.get('dop_numero', ''))}</strong>,
        sono conformi alla norma armonizzata <strong>EN 1090-1</strong> e sono stati prodotti
        in accordo al sistema di controllo della produzione in fabbrica certificato dall'ente
        notificato <strong>{ente}</strong> con certificato n. <strong>{cert_num}</strong>.
    </p>

    <div style="margin-top:30px;">
        <table style="border:none;">
            <tr style="border:none;">
                <td style="border:none;width:50%;">
                    <p style="font-size:9pt;"><strong>{resp}</strong><br/>{ruolo}</p>
                    {firma_html}
                    <div style="border-bottom:1px solid #000;width:200px;margin-top:8px;"></div>
                </td>
                <td style="border:none;width:50%;text-align:right;">
                    <p style="font-size:9pt;">{city}, {now.strftime('%d/%m/%Y')}</p>
                </td>
            </tr>
        </table>
    </div>

    </body></html>"""

    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    return buf.getvalue()
