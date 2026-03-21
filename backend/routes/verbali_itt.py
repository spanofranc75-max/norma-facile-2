"""
Verbali ITT (Initial Type Testing) — Qualifica processi produttivi.

Ogni ITT qualifica un processo (taglio, foratura, piegatura) per determinati
spessori/diametri su materiali specifici. Il Riesame Tecnico verifica
automaticamente che esistano ITT validi per i processi della commessa.

Fili conduttori:
  - ITT → Riesame Tecnico (nuovo check itt_processi_qualificati)
  - ITT → Commessa (matching tipo processo)
"""
import uuid
import logging
from datetime import datetime, timezone, date
from typing import Optional, List
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.security import get_current_user
from core.database import db

router = APIRouter(prefix="/verbali-itt", tags=["verbali_itt"])
logger = logging.getLogger(__name__)

PROCESSI_ITT = [
    "taglio_termico",
    "taglio_meccanico",
    "foratura",
    "piegatura",
    "punzonatura",
    "raddrizzatura",
]


class ProvaITT(BaseModel):
    parametro: str
    valore_misurato: str
    valore_atteso: str
    conforme: bool


class VerbaleITTCreate(BaseModel):
    processo: str
    descrizione: Optional[str] = ""
    macchina: str
    materiale: str
    spessore_min_mm: Optional[float] = None
    spessore_max_mm: Optional[float] = None
    diametro_mm: Optional[float] = None
    norma_riferimento: str = "EN 1090-2"
    data_prova: str
    data_scadenza: str
    prove: List[ProvaITT] = []
    esito_globale: bool = False
    note: Optional[str] = ""


@router.post("")
async def create_verbale_itt(data: VerbaleITTCreate, user: dict = Depends(get_current_user)):
    if data.processo not in PROCESSI_ITT:
        raise HTTPException(400, f"Processo non valido. Valori: {PROCESSI_ITT}")

    itt_id = f"itt_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    doc = {
        "itt_id": itt_id,
        "user_id": user["user_id"],
        "processo": data.processo,
        "descrizione": data.descrizione or "",
        "macchina": data.macchina,
        "materiale": data.materiale,
        "spessore_min_mm": data.spessore_min_mm,
        "spessore_max_mm": data.spessore_max_mm,
        "diametro_mm": data.diametro_mm,
        "norma_riferimento": data.norma_riferimento,
        "data_prova": data.data_prova,
        "data_scadenza": data.data_scadenza,
        "prove": [p.dict() for p in data.prove],
        "esito_globale": data.esito_globale,
        "note": data.note or "",
        "firma": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.verbali_itt.insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"[ITT] Creato verbale {itt_id} — processo: {data.processo}")
    return doc


@router.get("")
async def list_verbali_itt(
    user: dict = Depends(get_current_user),
    processo: str = "",
):
    query = {"user_id": user["user_id"]}
    if processo:
        query["processo"] = processo

    items = await db.verbali_itt.find(query, {"_id": 0}).sort("data_scadenza", 1).to_list(200)

    today_ = date.today()
    for item in items:
        try:
            scad = date.fromisoformat(item["data_scadenza"][:10])
            delta = (scad - today_).days
            item["scaduto"] = delta < 0
            item["in_scadenza"] = 0 <= delta <= 30
            item["giorni_rimasti"] = delta
        except (ValueError, KeyError):
            item["scaduto"] = False
            item["in_scadenza"] = False
            item["giorni_rimasti"] = None

    return {"verbali": items, "total": len(items)}


@router.get("/check-validita")
async def check_validita_itt(user: dict = Depends(get_current_user)):
    """Verifica quali processi hanno ITT validi — usato dal Riesame Tecnico."""
    today_ = date.today()
    items = await db.verbali_itt.find(
        {"user_id": user["user_id"], "esito_globale": True},
        {"_id": 0, "processo": 1, "data_scadenza": 1, "macchina": 1, "materiale": 1}
    ).to_list(200)

    validi = {}
    scaduti = {}
    for item in items:
        proc = item["processo"]
        try:
            scad = date.fromisoformat(item["data_scadenza"][:10])
            if scad >= today_:
                validi.setdefault(proc, []).append(item)
            else:
                scaduti.setdefault(proc, []).append(item)
        except (ValueError, KeyError):
            pass

    return {
        "processi_qualificati": list(validi.keys()),
        "processi_scaduti": list(scaduti.keys()),
        "dettaglio_validi": validi,
        "dettaglio_scaduti": scaduti,
        "tutti_i_processi": PROCESSI_ITT,
    }


@router.delete("/{itt_id}")
async def delete_verbale_itt(itt_id: str, user: dict = Depends(get_current_user)):
    result = await db.verbali_itt.delete_one({"itt_id": itt_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Verbale ITT non trovato")
    return {"message": "Verbale ITT eliminato"}


@router.post("/{itt_id}/firma")
async def firma_verbale_itt(itt_id: str, body: dict, user: dict = Depends(get_current_user)):
    nome = body.get("nome", "")
    ruolo = body.get("ruolo", "")
    if not nome:
        raise HTTPException(400, "Nome obbligatorio per la firma")

    now = datetime.now(timezone.utc)
    result = await db.verbali_itt.update_one(
        {"itt_id": itt_id, "user_id": user["user_id"]},
        {"$set": {
            "firma": {"nome": nome, "ruolo": ruolo, "data": now.isoformat()},
            "updated_at": now.isoformat(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Verbale ITT non trovato")
    return {"message": "Verbale firmato", "itt_id": itt_id}


@router.get("/{itt_id}/pdf")
async def generate_itt_pdf(itt_id: str, user: dict = Depends(get_current_user)):
    doc = await db.verbali_itt.find_one(
        {"itt_id": itt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Verbale ITT non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    import html as html_mod
    _e = html_mod.escape

    biz = _e(company.get("business_name", ""))
    logo = company.get("logo_url", "")
    logo_html = f'<img src="{logo}" style="max-height:40px;" />' if logo else ""

    prove_rows = ""
    for p in doc.get("prove", []):
        esito = "Conforme" if p.get("conforme") else "Non conforme"
        cls = "color:#276749;" if p.get("conforme") else "color:#c53030;"
        prove_rows += f"""<tr>
            <td>{_e(p.get('parametro', ''))}</td>
            <td style="text-align:center;">{_e(p.get('valore_atteso', ''))}</td>
            <td style="text-align:center;">{_e(p.get('valore_misurato', ''))}</td>
            <td style="text-align:center;{cls}font-weight:700;">{esito}</td>
        </tr>"""

    esito_glob = "CONFORME" if doc.get("esito_globale") else "NON CONFORME"
    esito_cls = "color:#276749;" if doc.get("esito_globale") else "color:#c53030;"
    firma = doc.get("firma", {})

    spessore = ""
    if doc.get("spessore_min_mm") is not None and doc.get("spessore_max_mm") is not None:
        spessore = f'{doc["spessore_min_mm"]} — {doc["spessore_max_mm"]} mm'
    elif doc.get("spessore_min_mm") is not None:
        spessore = f'{doc["spessore_min_mm"]} mm'

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ size: A4; margin: 18mm 15mm; }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1E293B; }}
    h1 {{ font-size: 16pt; margin: 0 0 4mm; }}
    h2 {{ font-size: 12pt; color: #334155; margin: 6mm 0 2mm; border-bottom: 1px solid #e2e8f0; padding-bottom: 1mm; }}
    table {{ width: 100%; border-collapse: collapse; margin: 2mm 0 4mm; }}
    th, td {{ border: 1px solid #CBD5E1; padding: 2mm 3mm; font-size: 9pt; }}
    th {{ background: #1E293B; color: white; font-weight: 700; text-align: left; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4mm; }}
    .meta td {{ border: none; padding: 1.5mm 3mm; }}
    .meta .lbl {{ font-weight: 700; color: #475569; width: 35%; background: #f0f4f8; }}
    </style></head><body>
    <div class="header">
        <div>{logo_html}<br/><strong>{biz}</strong></div>
        <div style="text-align:right;">
            <strong>VERBALE ITT</strong><br/>
            <span style="font-size:9pt;color:#64748b;">Initial Type Testing — {_e(doc.get('norma_riferimento', ''))}</span>
        </div>
    </div>

    <h2>Dati Processo</h2>
    <table class="meta">
        <tr><td class="lbl">Processo</td><td>{_e(doc.get('processo', '').replace('_', ' ').title())}</td></tr>
        <tr><td class="lbl">Macchina</td><td>{_e(doc.get('macchina', ''))}</td></tr>
        <tr><td class="lbl">Materiale</td><td>{_e(doc.get('materiale', ''))}</td></tr>
        {'<tr><td class="lbl">Spessore</td><td>' + _e(spessore) + '</td></tr>' if spessore else ''}
        {'<tr><td class="lbl">Diametro</td><td>' + str(doc.get('diametro_mm', '')) + ' mm</td></tr>' if doc.get('diametro_mm') else ''}
        <tr><td class="lbl">Data Prova</td><td>{_e(doc.get('data_prova', ''))}</td></tr>
        <tr><td class="lbl">Validita fino al</td><td>{_e(doc.get('data_scadenza', ''))}</td></tr>
    </table>

    <h2>Prove Effettuate</h2>
    <table>
        <tr><th>Parametro</th><th>Valore Atteso</th><th>Valore Misurato</th><th>Esito</th></tr>
        {prove_rows if prove_rows else '<tr><td colspan="4" style="text-align:center;color:#94a3b8;">Nessuna prova registrata</td></tr>'}
    </table>

    <h2>Esito Globale</h2>
    <p style="font-size:14pt;font-weight:900;{esito_cls}">{esito_glob}</p>
    {f'<p style="font-size:9pt;color:#64748b;">{_e(doc.get("note", ""))}</p>' if doc.get("note") else ''}

    <h2>Firma</h2>
    <table class="meta">
        <tr><td class="lbl">Nome</td><td>{_e(firma.get('nome', '—'))}</td></tr>
        <tr><td class="lbl">Ruolo</td><td>{_e(firma.get('ruolo', ''))}</td></tr>
        <tr><td class="lbl">Data</td><td>{_e((firma.get('data', '') or '')[:10])}</td></tr>
    </table>
    </body></html>"""

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html).write_pdf(buf)
    proc_label = doc.get("processo", "itt").replace("_", "-")
    fname = f"Verbale_ITT_{proc_label}_{itt_id}.pdf"
    return StreamingResponse(
        BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )
