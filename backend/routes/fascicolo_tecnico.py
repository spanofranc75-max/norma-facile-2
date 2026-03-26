"""Routes for Fascicolo Tecnico EN 1090 — DOP, CE, Piano di Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.database import db
from core.security import get_current_user, tenant_match
from core.rbac import require_role

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
    redatto_da: Optional[str] = ""


async def _get_commessa(cid: str, uid: str, tid: str = "default"):
    c = await db.commesse.find_one({"commessa_id": cid, "user_id": uid, "tenant_id": tid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Commessa non trovata")
    return c


async def _get_context(cid: str, user: dict):
    """Get all context data needed for PDF generation — auto-populates ~90% of fields."""
    commessa = await _get_commessa(cid, user["user_id"], user["tenant_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}) or {}
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "name": 1, "business_name": 1})
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")
    ft = commessa.get("fascicolo_tecnico", {})

    # ── From preventivo ──
    preventivo = None
    prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
    if prev_id:
        preventivo = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    if preventivo:
        if not ft.get("disegno_numero"):
            ft["disegno_numero"] = preventivo.get("numero_disegno", "")
        if not ft.get("disegno_riferimento"):
            ft["disegno_riferimento"] = preventivo.get("numero_disegno", "")
        classe_prev = preventivo.get("classe_esecuzione", "")
        if classe_prev:
            commessa["classe_esecuzione"] = classe_prev
        # Mandatario = client from preventivo header
        if not client_name and preventivo.get("client_id"):
            cl_p = await db.clients.find_one({"client_id": preventivo["client_id"]}, {"_id": 0, "name": 1, "business_name": 1})
            if cl_p:
                client_name = cl_p.get("business_name") or cl_p.get("name", "")
        if not client_name:
            client_name = preventivo.get("client_name", "")

    # Fallback: disegno from commessa numero
    if not ft.get("disegno_numero"):
        ft["disegno_numero"] = commessa.get("numero", "")
    if not ft.get("disegno_riferimento"):
        ft["disegno_riferimento"] = commessa.get("numero", "")

    # ── Classe esecuzione fallback from settings ──
    if not commessa.get("classe_esecuzione") and company.get("classe_esecuzione_default"):
        commessa["classe_esecuzione"] = company["classe_esecuzione_default"]

    # ── From company settings ──
    if not ft.get("firmatario"):
        ft["firmatario"] = company.get("business_name", "")
    if not ft.get("ruolo_firmatario"):
        ft["ruolo_firmatario"] = company.get("ruolo_firmatario", "Legale Rappresentante")
    if not ft.get("ente_notificato"):
        ft["ente_notificato"] = company.get("ente_certificatore", "")
    if not ft.get("ente_numero"):
        ft["ente_numero"] = company.get("ente_certificatore_numero", "")
    if not ft.get("certificato_numero"):
        ft["certificato_numero"] = company.get("certificato_en1090_numero", "")
    if not ft.get("redatto_da"):
        ft["redatto_da"] = company.get("responsabile_nome", "")
    if not ft.get("firma_cs"):
        ft["firma_cs"] = company.get("responsabile_nome", "")
    # Mandatario = cliente
    if not ft.get("mandatario"):
        ft["mandatario"] = client_name

    # DOP numero = commessa numero
    if not ft.get("dop_numero"):
        ft["dop_numero"] = commessa.get("numero", "")
    # Report VT numero = commessa numero
    if not ft.get("report_numero"):
        ft["report_numero"] = commessa.get("numero", "")
    if not ft.get("report_data"):
        ft["report_data"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    # Ordine numero = commessa numero
    if not ft.get("ordine_numero"):
        ft["ordine_numero"] = commessa.get("numero", "")

    # ── From material batches ──
    batches = await db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).to_list(50)
    mat_types = []
    if batches:
        mat_types = list(set(b.get("material_type", "") for b in batches if b.get("material_type")))
        dims = list(set(b.get("dimensions", "") for b in batches if b.get("dimensions")))
        spessori = list(set(b.get("spessore", "") for b in batches if b.get("spessore")))
        if not ft.get("materiale"):
            ft["materiale"] = " / ".join(mat_types)
        if not ft.get("profilato"):
            ft["profilato"] = " + ".join(dims)
        if not ft.get("spessore") and spessori:
            ft["spessore"] = " / ".join(spessori)
        if not ft.get("materiali_saldabilita") and mat_types:
            ft["materiali_saldabilita"] = " - ".join(mat_types) + " in accordo alla EN 10025-2"

    # ── Resilienza auto from material type ──
    if not ft.get("resilienza") and mat_types:
        res_val = _lookup_resilienza(mat_types)
        if res_val:
            ft["resilienza"] = res_val

    # ── DDT auto — suffisso commessa/01, /02 etc. ──
    comm_num = commessa.get("numero", "")
    if not ft.get("ddt_riferimento") and comm_num:
        ddt_count = await db.ddt_counter.find_one({"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
        suffix = (ddt_count.get("count", 0) if ddt_count else 0) + 1
        ft["ddt_riferimento"] = f"{comm_num}/{str(suffix).zfill(2)}"
    if not ft.get("ddt_data"):
        ft["ddt_data"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    # Luogo e data firma
    if not ft.get("luogo_data_firma"):
        city = company.get("city", "")
        ft["luogo_data_firma"] = f"{city}, {datetime.now(timezone.utc).strftime('%d/%m/%Y')}" if city else ""

    # Data emissione for Registro Saldatura
    if not ft.get("data_emissione"):
        ft["data_emissione"] = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    return commessa, company, client_name, ft


# ── GET/PUT fascicolo data ──
@router.get("/{cid}")
async def get_fascicolo_data(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    commessa = await _get_commessa(cid, user["user_id"], user["tenant_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}) or {}
    ft = commessa.get("fascicolo_tecnico", {})

    # ── Auto-populate from preventivo ──
    prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
    preventivo = None
    if prev_id:
        preventivo = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0})
    client_name = ""
    if commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "name": 1, "business_name": 1})
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")
    # Fallback: client from preventivo header
    if not client_name and preventivo and preventivo.get("client_id"):
        cl_p = await db.clients.find_one({"client_id": preventivo["client_id"]}, {"_id": 0, "name": 1, "business_name": 1})
        if cl_p:
            client_name = cl_p.get("business_name") or cl_p.get("name", "")
    if not client_name and preventivo:
        client_name = preventivo.get("client_name", "")

    auto = {}  # track which fields were auto-populated
    # From preventivo
    if preventivo:
        if preventivo.get("numero_disegno"):
            auto["disegno_numero"] = preventivo["numero_disegno"]
            auto["disegno_riferimento"] = preventivo["numero_disegno"]
        if preventivo.get("classe_esecuzione"):
            auto["classe_esecuzione"] = preventivo["classe_esecuzione"]
        if preventivo.get("giorni_consegna"):
            auto["giorni_consegna"] = preventivo["giorni_consegna"]
    # Fallback: use commessa numero as disegno riferimento
    if not auto.get("disegno_numero") and not ft.get("disegno_numero"):
        auto["disegno_numero"] = commessa.get("numero", "")
        auto["disegno_riferimento"] = commessa.get("numero", "")
    # Classe esecuzione fallback from settings
    if not auto.get("classe_esecuzione") and company.get("classe_esecuzione_default"):
        auto["classe_esecuzione"] = company["classe_esecuzione_default"]
    auto["client_name"] = client_name
    auto["commessa_numero"] = commessa.get("numero", "")
    auto["commessa_title"] = commessa.get("title", "")

    # From company settings
    if company.get("business_name"):
        auto["firmatario"] = company["business_name"]
    if company.get("ruolo_firmatario"):
        auto["ruolo_firmatario"] = company["ruolo_firmatario"]
    if company.get("ente_certificatore"):
        auto["ente_notificato"] = company["ente_certificatore"]
    if company.get("ente_certificatore_numero"):
        auto["ente_numero"] = company["ente_certificatore_numero"]
    if company.get("certificato_en1090_numero"):
        auto["certificato_numero"] = company["certificato_en1090_numero"]
    if company.get("responsabile_nome"):
        auto["redatto_da"] = company["responsabile_nome"]
        auto["firma_cs"] = company["responsabile_nome"]
    # Mandatario = cliente (from preventivo header)
    if client_name:
        auto["mandatario"] = client_name
    # DOP numero = commessa numero
    if commessa.get("numero"):
        auto["dop_numero"] = commessa["numero"]
        auto["report_numero"] = commessa["numero"]
        auto["ordine_numero"] = commessa["numero"]

    # DDT auto — suffisso commessa/01, /02
    comm_num = commessa.get("numero", "")
    if comm_num:
        ddt_count = await db.ddt_counter.find_one({"commessa_id": commessa["commessa_id"], "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
        suffix = (ddt_count.get("count", 0) if ddt_count else 0) + 1
        auto["ddt_riferimento"] = f"{comm_num}/{str(suffix).zfill(2)}"

    # Date auto
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    auto["ddt_data"] = today
    auto["data_emissione"] = today
    auto["report_data"] = today
    city = company.get("city", "")
    if city:
        auto["luogo_data_firma"] = f"{city}, {today}"

    # Merge auto into ft (don't overwrite user edits)
    for k, v in auto.items():
        if not ft.get(k) and v:
            ft[k] = v

    # ── From material batches ──
    batches = await db.material_batches.find(
        {"commessa_id": commessa["commessa_id"], "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).to_list(50)
    mat_types = []
    if batches:
        mat_types = list(set(b.get("material_type", "") for b in batches if b.get("material_type")))
        dims = list(set(b.get("dimensions", "") for b in batches if b.get("dimensions")))
        spessori = list(set(b.get("spessore", "") for b in batches if b.get("spessore")))
        if not ft.get("materiale") and mat_types:
            ft["materiale"] = " / ".join(mat_types)
            auto["materiale"] = ft["materiale"]
        if not ft.get("profilato") and dims:
            ft["profilato"] = " + ".join(dims)
            auto["profilato"] = ft["profilato"]
        if not ft.get("spessore") and spessori:
            ft["spessore"] = " / ".join(spessori)
            auto["spessore"] = ft["spessore"]
        if not ft.get("materiali_saldabilita") and mat_types:
            ft["materiali_saldabilita"] = " - ".join(mat_types) + " in accordo alla EN 10025-2"
            auto["materiali_saldabilita"] = ft["materiali_saldabilita"]

    # Resilienza auto
    if not ft.get("resilienza") and mat_types:
        res_val = _lookup_resilienza(mat_types)
        if res_val:
            ft["resilienza"] = res_val
            auto["resilienza"] = res_val

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
async def update_fascicolo_data(cid: str, data: FascicoloData, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    await _get_commessa(cid, user["user_id"], user["tenant_id"])
    update = {k: v for k, v in data.dict().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.commesse.update_one(
        {"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {f"fascicolo_tecnico.{k}": v for k, v in update.items()}}
    )
    return {"message": "Dati fascicolo tecnico aggiornati"}


# ── PDF endpoints ──
@router.get("/{cid}/dop-pdf")
async def dop_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_dop_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_dop_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="DOP_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/ce-pdf")
async def ce_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_ce_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_ce_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="CE_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/piano-controllo-pdf")
async def piano_controllo_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_piano_controllo_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    if not ft.get("fasi"):
        from services.pdf_fascicolo_tecnico import DEFAULT_PHASES
        ft["fasi"] = [dict(p) for p in DEFAULT_PHASES]
    buf = generate_piano_controllo_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Piano_Controllo_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/rapporto-vt-pdf")
async def rapporto_vt_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_rapporto_vt_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_rapporto_vt_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Rapporto_VT_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/registro-saldatura-pdf")
async def registro_saldatura_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_registro_saldatura_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_registro_saldatura_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Registro_Saldatura_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/riesame-tecnico-pdf")
async def riesame_tecnico_pdf(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    from services.pdf_fascicolo_tecnico import generate_riesame_tecnico_pdf
    commessa, company, client_name, ft = await _get_context(cid, user)
    buf = generate_riesame_tecnico_pdf(company, commessa, client_name, ft)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Riesame_Tecnico_{commessa.get("numero","")}.pdf"'})


@router.get("/{cid}/fascicolo-completo-pdf")
async def fascicolo_completo_pdf(cid: str, docs: str = "dop,ce,piano,vt,registro,riesame", user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
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
