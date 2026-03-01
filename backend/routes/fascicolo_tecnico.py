"""Routes for Fascicolo Tecnico EN 1090 — DOP, CE, Piano di Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.database import db
from core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fascicolo-tecnico", tags=["fascicolo_tecnico"])

# ── Tabella resilienza per tipo acciaio (EN 10025) ──
RESILIENZA_TABLE = {
    "S235JR": "27 J a 20 °C",
    "S235J0": "27 J a 0 °C",
    "S235J2": "27 J a -20 °C",
    "S275JR": "27 J a 20 °C",
    "S275J0": "27 J a 0 °C",
    "S275J2": "27 J a -20 °C",
    "S355JR": "27 J a 20 °C",
    "S355J0": "27 J a 0 °C",
    "S355J2": "27 J a -20 °C",
    "S355K2": "40 J a -20 °C",
    "S420J2": "27 J a -20 °C",
    "S450J0": "27 J a 0 °C",
    "S460J2": "27 J a -20 °C",
    "S460N": "40 J a -20 °C",
    "S460NL": "27 J a -40 °C",
}

def _lookup_resilienza(material_types: list) -> str:
    """Lookup resilienza from material type list."""
    for mt in material_types:
        key = mt.strip().upper().replace("+AR", "").replace("+N", "").replace("+M", "").strip()
        if key in RESILIENZA_TABLE:
            return RESILIENZA_TABLE[key]
        # Partial match
        for k, v in RESILIENZA_TABLE.items():
            if k in key or key in k:
                return v
    return ""


# ── Models ──
class FasePianoControllo(BaseModel):
    fase: str = ""
    doc_rif: str = ""
    applicabile: bool = True
    periodo_pianificato: str = ""
    controllo_verbale: str = ""
    esito: str = ""  # "positivo", "negativo", ""
    data_effettiva: str = ""

class OggettoControllato(BaseModel):
    numero: str = ""
    disegno: str = ""
    marca: str = ""
    dimensioni: str = ""
    estensione_controllo: str = "100"
    esito: str = ""  # "Positivo", "Negativo"

class FascicoloData(BaseModel):
    """All editable fields for the 4 document types."""
    # DOP fields
    ddt_riferimento: Optional[str] = ""
    ddt_data: Optional[str] = ""
    mandatario: Optional[str] = ""
    firmatario: Optional[str] = ""
    ruolo_firmatario: Optional[str] = "Legale Rappresentante"
    luogo_data_firma: Optional[str] = ""
    certificato_numero: Optional[str] = ""
    ente_notificato: Optional[str] = ""
    ente_numero: Optional[str] = ""
    materiali_saldabilita: Optional[str] = "S355JR - S275JR in accordo alla EN 10025-2"
    resilienza: Optional[str] = "27 Joule a +/- 20 C"
    # CE extra
    disegno_riferimento: Optional[str] = ""
    dop_numero: Optional[str] = ""
    # Piano di Controllo
    ordine_numero: Optional[str] = ""
    disegno_numero: Optional[str] = ""
    fasi: Optional[List[Dict[str, Any]]] = None
    # Rapporto VT
    report_numero: Optional[str] = ""
    report_data: Optional[str] = ""
    processo_saldatura: Optional[str] = "135"
    norma_procedura: Optional[str] = "UNI EN ISO 17637 - IO 03"
    accettabilita: Optional[str] = "ISO 5817 livello C"
    materiale: Optional[str] = ""
    temperatura_pezzo: Optional[str] = ""
    profilato: Optional[str] = ""
    spessore: Optional[str] = ""
    condizioni_visione: Optional[Dict[str, bool]] = None
    stato_superficie: Optional[Dict[str, bool]] = None
    tipo_ispezione: Optional[Dict[str, bool]] = None
    attrezzatura: Optional[Dict[str, bool]] = None
    distanza_max_mm: Optional[str] = "600"
    angolo_min_gradi: Optional[str] = "30"
    tipo_illuminatore: Optional[str] = "LUX"
    calibro_info: Optional[str] = ""
    oggetti_controllati: Optional[List[Dict[str, Any]]] = None
    note_vt: Optional[str] = ""
    # Registro Saldatura
    data_emissione: Optional[str] = ""
    firma_cs: Optional[str] = ""
    perc_vt: Optional[str] = "100"
    perc_mt_pt: Optional[str] = "0"
    perc_rx_ut: Optional[str] = "0"
    saldature: Optional[List[Dict[str, Any]]] = None
    # Riesame Tecnico
    requisiti: Optional[List[Dict[str, Any]]] = None
    itt: Optional[List[Dict[str, Any]]] = None
    decisione: Optional[str] = "procedere"


async def _get_commessa(cid: str, uid: str):
    c = await db.commesse.find_one({"commessa_id": cid, "user_id": uid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Commessa non trovata")
    return c


async def _get_context(cid: str, user: dict):
    """Get all context data needed for PDF generation."""
    commessa = await _get_commessa(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "name": 1})
        client_name = cl.get("name", "") if cl else ""
    # Get fascicolo data stored on commessa
    ft = commessa.get("fascicolo_tecnico", {})
    # Get preventivo for disegno / classe esecuzione / ingegnere
    preventivo = None
    prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
    if prev_id:
        preventivo = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    if preventivo:
        if not ft.get("disegno_numero"):
            ft["disegno_numero"] = preventivo.get("numero_disegno", "")
        if not ft.get("disegno_riferimento"):
            ft["disegno_riferimento"] = preventivo.get("numero_disegno", "")
        if not ft.get("redatto_da"):
            ft["redatto_da"] = preventivo.get("ingegnere_disegno", "")
        # Classe esecuzione: preventivo sovrascrive commessa
        classe_prev = preventivo.get("classe_esecuzione", "")
        if classe_prev:
            commessa["classe_esecuzione"] = classe_prev
        # Client name from preventivo if not yet set
        if not client_name:
            client_name = preventivo.get("client_name", "")
    # Auto-populate materiali from batches
    if not ft.get("materiale") or not ft.get("profilato"):
        batches = await db.material_batches.find(
            {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0}
        ).to_list(50)
        if batches:
            types = list(set(b.get("material_type", "") for b in batches if b.get("material_type")))
            dims = list(set(b.get("dimensions", "") for b in batches if b.get("dimensions")))
            if not ft.get("materiale"):
                ft["materiale"] = " / ".join(types)
            if not ft.get("profilato"):
                ft["profilato"] = " + ".join(dims)
    return commessa, company, client_name, ft


# ── GET/PUT fascicolo data ──
@router.get("/{cid}")
async def get_fascicolo_data(cid: str, user: dict = Depends(get_current_user)):
    commessa = await _get_commessa(cid, user["user_id"])
    ft = commessa.get("fascicolo_tecnico", {})

    # ── Auto-populate from preventivo ──
    prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
    preventivo = None
    if prev_id:
        preventivo = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "name": 1})
        client_name = cl.get("name", "") if cl else ""
    if preventivo and not client_name:
        client_name = preventivo.get("client_name", "")

    auto = {}  # fields auto-populated
    if preventivo:
        if preventivo.get("numero_disegno"):
            auto["disegno_numero"] = preventivo["numero_disegno"]
            auto["disegno_riferimento"] = preventivo["numero_disegno"]
        if preventivo.get("ingegnere_disegno"):
            auto["redatto_da"] = preventivo["ingegnere_disegno"]
        if preventivo.get("classe_esecuzione"):
            auto["classe_esecuzione"] = preventivo["classe_esecuzione"]
        if preventivo.get("giorni_consegna"):
            auto["giorni_consegna"] = preventivo["giorni_consegna"]
    auto["client_name"] = client_name
    auto["commessa_numero"] = commessa.get("numero", "")
    auto["commessa_title"] = commessa.get("title", "")

    # Merge auto into ft (don't overwrite user edits)
    for k, v in auto.items():
        if not ft.get(k) and v:
            ft[k] = v

    # ── Auto-populate from material batches ──
    batches = await db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0}
    ).to_list(50)
    if batches:
        types = list(set(b.get("material_type", "") for b in batches if b.get("material_type")))
        dims = list(set(b.get("dimensions", "") for b in batches if b.get("dimensions")))
        if not ft.get("materiale") and types:
            ft["materiale"] = " / ".join(types)
            auto["materiale"] = ft["materiale"]
        if not ft.get("profilato") and dims:
            ft["profilato"] = " + ".join(dims)
            auto["profilato"] = ft["profilato"]
        if not ft.get("materiali_saldabilita") and types:
            ft["materiali_saldabilita"] = " - ".join(types) + " in accordo alla EN 10025-2"
            auto["materiali_saldabilita"] = ft["materiali_saldabilita"]

    # ── Initialize defaults ──
    if not ft.get("fasi"):
        from services.pdf_fascicolo_tecnico import DEFAULT_PHASES
        ft["fasi"] = [dict(p) for p in DEFAULT_PHASES]
    if not ft.get("requisiti"):
        from services.pdf_fascicolo_tecnico import DEFAULT_REQUISITI
        ft["requisiti"] = [{"requisito": r["requisito"], "risposta": "si", "note": r["note_default"]} for r in DEFAULT_REQUISITI]
    if not ft.get("itt"):
        from services.pdf_fascicolo_tecnico import DEFAULT_ITT
        ft["itt"] = [dict(c) for c in DEFAULT_ITT]

    # ── Timeline from produzione ──
    fasi_prod = commessa.get("fasi_produzione", [])
    timeline = []
    for fp in fasi_prod:
        timeline.append({
            "fase": fp.get("label", fp.get("tipo", "")),
            "stato": fp.get("stato", "da_fare"),
            "data_inizio": fp.get("data_inizio"),
            "data_fine": fp.get("data_fine"),
        })
    # Auto-populate piano controllo dates from produzione
    fase_map = {
        "taglio": ["Taglio - Foratura (a freddo sega/trapano)", "Taglio - Foratura lamiere/profili grigliati"],
        "foratura": ["Taglio - Foratura (a freddo sega/trapano)"],
        "assemblaggio": ["Puntatura lembi ed attacchi temporanei"],
        "saldatura": ["Esecuzione ed accettabilita' saldatura", "Preparazione lembi di saldatura"],
        "pulizia": ["Preparazione superficiale per finiture"],
    }
    for fp in fasi_prod:
        if fp.get("data_inizio") or fp.get("data_fine"):
            target_fasi = fase_map.get(fp.get("tipo"), [])
            for fase in ft.get("fasi", []):
                if fase.get("fase") in target_fasi and not fase.get("data_effettiva"):
                    fase["data_effettiva"] = fp.get("data_fine") or fp.get("data_inizio") or ""
                    if fp.get("stato") == "completato":
                        fase["esito"] = "positivo"

    ft["_auto_fields"] = list(auto.keys())
    ft["_timeline"] = timeline
    ft["_giorni_consegna"] = auto.get("giorni_consegna", 0)
    return ft


@router.put("/{cid}")
async def update_fascicolo_data(cid: str, data: FascicoloData, user: dict = Depends(get_current_user)):
    await _get_commessa(cid, user["user_id"])
    update = {k: v for k, v in data.dict().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.commesse.update_one(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"$set": {f"fascicolo_tecnico.{k}": v for k, v in update.items()}}
    )
    return {"message": "Dati fascicolo tecnico aggiornati"}


# ── PDF endpoints ──
@router.get("/{cid}/dop-pdf")
async def dop_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_dop_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_dop_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="DOP_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/ce-pdf")
async def ce_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_ce_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_ce_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="CE_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/piano-controllo-pdf")
async def piano_controllo_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_piano_controllo_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    if not ft.get("fasi"):
        from services.pdf_fascicolo_tecnico import DEFAULT_PHASES
        ft["fasi"] = [dict(p) for p in DEFAULT_PHASES]
    buf = generate_piano_controllo_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Piano_Controllo_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/rapporto-vt-pdf")
async def rapporto_vt_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_rapporto_vt_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_rapporto_vt_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Rapporto_VT_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/registro-saldatura-pdf")
async def registro_saldatura_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_registro_saldatura_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_registro_saldatura_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Registro_Saldatura_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/riesame-tecnico-pdf")
async def riesame_tecnico_pdf(cid: str, user: dict = Depends(get_current_user)):
    from services.pdf_fascicolo_tecnico import generate_riesame_tecnico_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_riesame_tecnico_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Riesame_Tecnico_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/fascicolo-completo-pdf")
async def fascicolo_completo_pdf(cid: str, docs: str = "dop,ce,piano,vt,registro,riesame", user: dict = Depends(get_current_user)):
    """Generate a combined PDF with all selected Fascicolo Tecnico documents."""
    from services.pdf_fascicolo_tecnico import (
        generate_dop_pdf, generate_ce_pdf, generate_piano_controllo_pdf,
        generate_rapporto_vt_pdf, generate_registro_saldatura_pdf,
        generate_riesame_tecnico_pdf, DEFAULT_PHASES
    )
    from pypdf import PdfReader, PdfWriter

    commessa, company, client_name, ft = await _get_context(cid, user)
    if not ft.get("fasi"):
        ft["fasi"] = [dict(p) for p in DEFAULT_PHASES]

    selected = [d.strip() for d in docs.split(",")]
    generators = {
        "dop": generate_dop_pdf,
        "ce": generate_ce_pdf,
        "piano": generate_piano_controllo_pdf,
        "vt": generate_rapporto_vt_pdf,
        "registro": generate_registro_saldatura_pdf,
        "riesame": generate_riesame_tecnico_pdf,
    }

    writer = PdfWriter()
    for key in selected:
        gen = generators.get(key)
        if gen:
            buf = gen(company, commessa, client_name, ft)
            reader = PdfReader(buf)
            for page in reader.pages:
                writer.add_page(page)

    from io import BytesIO
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Fascicolo_Tecnico_{commessa.get("numero","")}.pdf"'})
