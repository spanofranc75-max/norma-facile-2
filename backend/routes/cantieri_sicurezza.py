"""
Cantieri Sicurezza — API Routes (Safety Branch v2)
=====================================================
Libreria a 3 livelli: lib_fasi_lavoro → lib_rischi_sicurezza → lib_dpi_misure
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from core.security import get_current_user
from services.cantieri_sicurezza_service import (
    crea_cantiere, get_cantiere, get_cantieri_by_commessa, list_cantieri,
    aggiorna_cantiere, elimina_cantiere,
    get_fasi_lavoro, get_rischi_sicurezza, get_dpi_misure,
    get_rischi_per_codici, get_dpi_per_codici,
    seed_libreria_v2, calcola_gate_pos,
    ALL_RUOLI,
)

router = APIRouter(tags=["cantieri_sicurezza"])
logger = logging.getLogger(__name__)


# ── Pydantic Models ──

class CreaCantiereSicurezzaRequest(BaseModel):
    commessa_id: Optional[str] = None
    pre_fill: Optional[dict] = None

class AggiornaCantiereSicurezzaRequest(BaseModel):
    dati_cantiere: Optional[dict] = None
    soggetti: Optional[List[dict]] = None
    lavoratori_coinvolti: Optional[List[dict]] = None
    turni_lavoro: Optional[dict] = None
    subappalti: Optional[List[dict]] = None
    dpi_presenti: Optional[List[dict]] = None
    macchine_attrezzature: Optional[List[dict]] = None
    sostanze_chimiche: Optional[List[dict]] = None
    stoccaggio_materiali: Optional[str] = None
    servizi_igienici: Optional[str] = None
    fasi_lavoro_selezionate: Optional[List[dict]] = None
    dpi_calcolati: Optional[List[dict]] = None
    misure_calcolate: Optional[List[dict]] = None
    apprestamenti_calcolati: Optional[List[dict]] = None
    domande_residue: Optional[List[dict]] = None
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
    return await crea_cantiere(user["user_id"], body.commessa_id, body.pre_fill)


@router.get("/cantieri-sicurezza")
async def api_list_cantieri(user: dict = Depends(get_current_user)):
    return await list_cantieri(user["user_id"])


@router.get("/cantieri-sicurezza/{cantiere_id}")
async def api_get_cantiere(cantiere_id: str, user: dict = Depends(get_current_user)):
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return doc


@router.get("/cantieri-sicurezza/commessa/{commessa_id}")
async def api_get_cantieri_by_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    return await get_cantieri_by_commessa(commessa_id, user["user_id"])


@router.put("/cantieri-sicurezza/{cantiere_id}")
async def api_aggiorna_cantiere(cantiere_id: str, body: AggiornaCantiereSicurezzaRequest, user: dict = Depends(get_current_user)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    result = await aggiorna_cantiere(cantiere_id, user["user_id"], updates)
    if not result:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return result


@router.delete("/cantieri-sicurezza/{cantiere_id}")
async def api_elimina_cantiere(cantiere_id: str, user: dict = Depends(get_current_user)):
    if not await elimina_cantiere(cantiere_id, user["user_id"]):
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return {"deleted": True}


@router.get("/cantieri-sicurezza/{cantiere_id}/gate")
async def api_gate_pos(cantiere_id: str, user: dict = Depends(get_current_user)):
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return calcola_gate_pos(doc)



@router.get("/ruoli-disponibili")
async def api_ruoli_disponibili(user: dict = Depends(get_current_user)):
    """Lista ruoli disponibili per soggetti commessa/cantiere."""
    return ALL_RUOLI

# ═══════════════════════════════════════════════════════════════════
#  LIBRERIA 3 LIVELLI — Read APIs
# ═══════════════════════════════════════════════════════════════════

@router.get("/libreria/fasi")
async def api_fasi_lavoro(normativa: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista fasi di lavoro, opzionalmente filtrate per normativa."""
    await seed_libreria_v2(user["user_id"])
    return await get_fasi_lavoro(user["user_id"], normativa)


@router.get("/libreria/rischi")
async def api_rischi_sicurezza(categoria: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista rischi sicurezza, opzionalmente filtrati per categoria."""
    await seed_libreria_v2(user["user_id"])
    return await get_rischi_sicurezza(user["user_id"], categoria)


@router.get("/libreria/dpi-misure")
async def api_dpi_misure(tipo: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Lista DPI/misure/apprestamenti, opzionalmente filtrati per tipo."""
    await seed_libreria_v2(user["user_id"])
    return await get_dpi_misure(user["user_id"], tipo)


@router.post("/libreria/seed")
async def api_seed_libreria(user: dict = Depends(get_current_user)):
    """Forza il seed della libreria a 3 livelli (idempotente)."""
    return await seed_libreria_v2(user["user_id"])


@router.post("/libreria/resolve-rischi")
async def api_resolve_rischi(body: dict, user: dict = Depends(get_current_user)):
    """Risolve una lista di codici rischio nei loro dettagli completi."""
    codici = body.get("codici", [])
    if not codici:
        return []
    return await get_rischi_per_codici(user["user_id"], codici)


@router.post("/libreria/resolve-dpi")
async def api_resolve_dpi(body: dict, user: dict = Depends(get_current_user)):
    """Risolve una lista di codici DPI/misure nei loro dettagli completi."""
    codici = body.get("codici", [])
    if not codici:
        return []
    return await get_dpi_per_codici(user["user_id"], codici)


# ═══════════════════════════════════════════════════════════════════
#  BACKWARD COMPAT — old /libreria-rischi endpoints (redirect to v2)
# ═══════════════════════════════════════════════════════════════════

@router.get("/libreria-rischi")
async def api_libreria_rischi_compat(tipo: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Backward compatible: returns all library entries in flat format."""
    await seed_libreria_v2(user["user_id"])
    if tipo == "fase_lavoro":
        return await get_fasi_lavoro(user["user_id"])
    elif tipo == "dpi":
        return await get_dpi_misure(user["user_id"], tipo="dpi")
    else:
        fasi = await get_fasi_lavoro(user["user_id"])
        rischi = await get_rischi_sicurezza(user["user_id"])
        dpi = await get_dpi_misure(user["user_id"])
        return fasi + rischi + dpi


@router.get("/libreria-rischi/fasi/{normativa}")
async def api_fasi_normativa_compat(normativa: str, user: dict = Depends(get_current_user)):
    await seed_libreria_v2(user["user_id"])
    return await get_fasi_lavoro(user["user_id"], normativa)


@router.post("/libreria-rischi/seed")
async def api_seed_compat(user: dict = Depends(get_current_user)):
    return await seed_libreria_v2(user["user_id"])
