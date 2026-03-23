"""
Cantieri Sicurezza — API Routes (Safety Branch v2)
=====================================================
Libreria a 3 livelli: lib_fasi_lavoro → lib_rischi_sicurezza → lib_dpi_misure
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
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
from services.ai_safety_engine import ai_precompila_cantiere
from services.pos_docx_generator import genera_pos_docx
from services.audit_trail import log_activity

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
    result = await crea_cantiere(user["user_id"], body.commessa_id, body.pre_fill)
    await log_activity(user, "create", "cantiere_sicurezza", result.get("cantiere_id", ""),
                       label=result.get("nome_cantiere", "Nuovo cantiere"),
                       commessa_id=body.commessa_id or "")
    return result


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
    # R0: Auto-sync obblighi if substantive fields changed
    substantive = {"soggetti", "dati_cantiere", "rischi_confermati", "rischi_selezionati", "fasi_lavoro"}
    changed_substantive = substantive & set(updates.keys())
    if changed_substantive:
        commessa_id = result.get("parent_commessa_id") or result.get("commessa_id")
        if commessa_id:
            from services.obblighi_auto_sync import trigger_sync_obblighi
            await trigger_sync_obblighi(commessa_id, user["user_id"], "gate_pos", cantiere_id)
        await log_activity(user, "update", "cantiere_sicurezza", cantiere_id,
                           label=result.get("nome_cantiere", ""),
                           commessa_id=commessa_id or "",
                           details={"fields_changed": list(changed_substantive)})
    return result


@router.delete("/cantieri-sicurezza/{cantiere_id}")
async def api_elimina_cantiere(cantiere_id: str, user: dict = Depends(get_current_user)):
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not await elimina_cantiere(cantiere_id, user["user_id"]):
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    await log_activity(user, "delete", "cantiere_sicurezza", cantiere_id,
                       label=doc.get("nome_cantiere", "") if doc else "",
                       commessa_id=(doc or {}).get("parent_commessa_id", "") or (doc or {}).get("commessa_id", ""))
    return {"deleted": True}


@router.get("/cantieri-sicurezza/{cantiere_id}/gate")
async def api_gate_pos(cantiere_id: str, user: dict = Depends(get_current_user)):
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere sicurezza non trovato")
    return calcola_gate_pos(doc)


@router.post("/cantieri-sicurezza/{cantiere_id}/ai-precompila")
async def api_ai_precompila(cantiere_id: str, user: dict = Depends(get_current_user)):
    """S3 — AI precompilation of safety cantiere from commessa/istruttoria/preventivo data."""
    result = await ai_precompila_cantiere(cantiere_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    doc = await get_cantiere(cantiere_id, user["user_id"])
    await log_activity(user, "ai_precompile", "cantiere_sicurezza", cantiere_id,
                       label=f"AI precompilazione POS",
                       commessa_id=(doc or {}).get("parent_commessa_id", "") or (doc or {}).get("commessa_id", ""),
                       details={"fasi_proposte": result.get("n_fasi", 0), "rischi_attivati": result.get("n_rischi", 0)},
                       actor_type="ai")
    return result


@router.post("/cantieri-sicurezza/{cantiere_id}/genera-pos")
async def api_genera_pos(
    cantiere_id: str,
    mode: str = "bozza_revisione",
    user: dict = Depends(get_current_user),
):
    """S4 — Generate POS DOCX draft from cantiere data."""
    result = await genera_pos_docx(cantiere_id, user["user_id"], mode=mode)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    doc = await get_cantiere(cantiere_id, user["user_id"])
    await log_activity(user, "generate_docx", "cantiere_sicurezza", cantiere_id,
                       label=f"POS v{result['generazione']['versione']}",
                       commessa_id=(doc or {}).get("parent_commessa_id", "") or (doc or {}).get("commessa_id", ""),
                       details={"mode": mode, "versione": result["generazione"]["versione"],
                                "completezza": result["gate_completezza"]},
                       actor_type="system")
    return Response(
        content=result["file_bytes"],
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f"attachment; filename=\"{result['filename']}\"",
            "X-POS-Versione": str(result["generazione"]["versione"]),
            "X-POS-Completezza": str(result["gate_completezza"]),
            "X-POS-Mode": result["generazione"]["mode"],
        },
    )


@router.get("/cantieri-sicurezza/{cantiere_id}/pos-generazioni")
async def api_pos_generazioni(cantiere_id: str, user: dict = Depends(get_current_user)):
    """Get POS generation history for a cantiere."""
    doc = await get_cantiere(cantiere_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Cantiere non trovato")
    return {
        "cantiere_id": cantiere_id,
        "generazioni": doc.get("pos_generazioni", []),
        "ultima_generazione": doc.get("ultima_generazione_pos"),
    }



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
