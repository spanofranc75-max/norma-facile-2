"""
Cantieri Sicurezza — API Routes (Safety Branch MVP)
=====================================================
Endpoints:
  - CRUD cantieri_sicurezza
  - Libreria rischi (read + seed)
  - Gate POS check
  - AI Safety pre-fill (to be added)
  - DOCX generation (to be added)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

from core.security import get_current_user
from core.database import db
from services.cantieri_sicurezza_service import (
    crea_cantiere,
    get_cantiere,
    get_cantieri_by_commessa,
    list_cantieri,
    aggiorna_cantiere,
    elimina_cantiere,
    get_libreria_rischi,
    get_fasi_per_normativa,
    seed_libreria_rischi,
    calcola_gate_pos,
)

router = APIRouter(tags=["cantieri_sicurezza"])
logger = logging.getLogger(__name__)


# ── Pydantic Models ──────────────────────────────────────────────

class CreaCantiereSicurezzaRequest(BaseModel):
    commessa_id: Optional[str] = None
    pre_fill: Optional[dict] = None

class AggiornaCantiereSicurezzaRequest(BaseModel):
    dati_cantiere: Optional[dict] = None
    soggetti_riferimento: Optional[dict] = None
    lavoratori_coinvolti: Optional[List[dict]] = None
    turni_lavoro: Optional[dict] = None
    subappalti: Optional[List[dict]] = None
    dpi_presenti: Optional[List[dict]] = None
    macchine_attrezzature: Optional[List[dict]] = None
    sostanze_chimiche: Optional[List[dict]] = None
    agenti_biologici: Optional[List[dict]] = None
    stoccaggio_materiali: Optional[str] = None
    servizi_igienici: Optional[str] = None
    fasi_lavoro_selezionate: Optional[List[dict]] = None
    numeri_utili: Optional[List[dict]] = None
    includi_covid19: Optional[bool] = None
    data_dichiarazione: Optional[str] = None
    note_aggiuntive: Optional[str] = None
    revisioni: Optional[List[dict]] = None
    status: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
#  CANTIERI SICUREZZA — CRUD
# ═══════════════════════════════════════════════════════════════════

@router.post("/cantieri-sicurezza")
async def api_crea_cantiere(body: CreaCantiereSicurezzaRequest, user: dict = Depends(get_current_user)):
    """Crea un nuovo cantiere sicurezza (Scheda Cantiere POS)."""
    result = await crea_cantiere(user["user_id"], body.commessa_id, body.pre_fill)
    return result


@router.get("/cantieri-sicurezza")
async def api_list_cantieri(user: dict = Depends(get_current_user)):
    """Lista tutti i cantieri sicurezza dell'utente."""
    return await list_cantieri(user["user_id"])


@router.get("/cantieri-sicurezza/{cantiere_id}")
async def api_get_cantiere(cantiere_id: str, user: dict = Depends(get_current_user)):
    """Dettaglio di un cantiere sicurezza."""
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return doc


@router.get("/cantieri-sicurezza/commessa/{commessa_id}")
async def api_get_cantieri_by_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    """Lista cantieri sicurezza per una commessa specifica."""
    return await get_cantieri_by_commessa(commessa_id, user["user_id"])


@router.put("/cantieri-sicurezza/{cantiere_id}")
async def api_aggiorna_cantiere(
    cantiere_id: str,
    body: AggiornaCantiereSicurezzaRequest,
    user: dict = Depends(get_current_user),
):
    """Aggiorna un cantiere sicurezza (partial update)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")

    result = await aggiorna_cantiere(cantiere_id, user["user_id"], updates)
    if not result:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return result


@router.delete("/cantieri-sicurezza/{cantiere_id}")
async def api_elimina_cantiere(cantiere_id: str, user: dict = Depends(get_current_user)):
    """Elimina un cantiere sicurezza."""
    deleted = await elimina_cantiere(cantiere_id, user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════
#  GATE POS
# ═══════════════════════════════════════════════════════════════════

@router.get("/cantieri-sicurezza/{cantiere_id}/gate")
async def api_gate_pos(cantiere_id: str, user: dict = Depends(get_current_user)):
    """Verifica completezza del cantiere per la generazione POS."""
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    gate = calcola_gate_pos(doc)
    return gate


# ═══════════════════════════════════════════════════════════════════
#  LIBRERIA RISCHI
# ═══════════════════════════════════════════════════════════════════

@router.get("/libreria-rischi")
async def api_libreria_rischi(tipo: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista la libreria rischi dell'utente (DPI, fasi lavoro, segnaletica)."""
    # Auto-seed if empty
    await seed_libreria_rischi(user["user_id"])
    return await get_libreria_rischi(user["user_id"], tipo)


@router.get("/libreria-rischi/fasi/{normativa}")
async def api_fasi_per_normativa(normativa: str, user: dict = Depends(get_current_user)):
    """Lista fasi di lavoro applicabili a una normativa specifica."""
    await seed_libreria_rischi(user["user_id"])
    return await get_fasi_per_normativa(user["user_id"], normativa)


@router.post("/libreria-rischi/seed")
async def api_seed_libreria(user: dict = Depends(get_current_user)):
    """Forza il seed della libreria rischi (idempotente)."""
    result = await seed_libreria_rischi(user["user_id"])
    return result
