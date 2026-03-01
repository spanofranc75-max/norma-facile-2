"""Routes for Fascicolo Tecnico EN 1090 — DOP, CE, Piano di Controllo, Rapporto VT."""
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
    # Get preventivo for disegno info
    preventivo = None
    if commessa.get("preventivo_id"):
        preventivo = await db.preventivi.find_one({"preventivo_id": commessa["preventivo_id"]}, {"_id": 0})
    # Auto-populate disegno from preventivo if not set
    if not ft.get("disegno_numero") and preventivo:
        ft["disegno_numero"] = preventivo.get("numero_disegno", "")
    if not ft.get("disegno_riferimento") and preventivo:
        ft["disegno_riferimento"] = preventivo.get("numero_disegno", "")
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
    # Initialize default phases if not set
    if not ft.get("fasi"):
        from services.pdf_fascicolo_tecnico import DEFAULT_PHASES
        ft["fasi"] = [dict(p) for p in DEFAULT_PHASES]
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
