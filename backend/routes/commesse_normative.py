"""
Commesse Normative — API Routes
=================================
Endpoint per il modello gerarchico:
  Commessa Madre → Ramo Normativo → Emissione Documentale
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from core.security import get_current_user
from core.database import db
from services.commesse_normative_service import (
    get_rami, get_ramo, crea_ramo,
    genera_rami_da_segmentazione,
    get_emissioni, get_emissione, crea_emissione,
    aggiorna_emissione, check_evidence_gate, emetti_emissione,
    get_normative_branches, materializza_ramo_legacy,
    get_gerarchia,
    NORMATIVE_VALIDE,
)
from services.audit_trail import log_activity

router = APIRouter(tags=["commesse_normative"])
logger = logging.getLogger(__name__)


# ── Pydantic Models ──────────────────────────────────────────────

class CreaRamoRequest(BaseModel):
    normativa: str
    line_ids: Optional[List[str]] = None

class CreaEmissioneRequest(BaseModel):
    descrizione: Optional[str] = ""
    voce_lavoro_ids: Optional[List[str]] = None
    batch_ids: Optional[List[str]] = None
    ddt_ids: Optional[List[str]] = None
    line_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None

class AggiornaEmissioneRequest(BaseModel):
    descrizione: Optional[str] = None
    voce_lavoro_ids: Optional[List[str]] = None
    batch_ids: Optional[List[str]] = None
    ddt_ids: Optional[List[str]] = None
    line_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None
    element_ids: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════
#  RAMI NORMATIVI
# ═══════════════════════════════════════════════════════════════════

@router.get("/commesse-normative/{commessa_id}")
async def list_rami_normativi(commessa_id: str, user: dict = Depends(get_current_user)):
    """Lista rami normativi di una commessa (include legacy wrap)."""
    branches = await get_normative_branches(commessa_id, user["user_id"])
    return {"rami": branches, "total": len(branches)}


@router.post("/commesse-normative/{commessa_id}", status_code=201)
async def create_ramo_normativo(commessa_id: str, body: CreaRamoRequest, user: dict = Depends(get_current_user)):
    """Crea un ramo normativo manualmente."""
    if body.normativa not in NORMATIVE_VALIDE:
        raise HTTPException(400, f"Normativa non valida. Valori ammessi: {', '.join(NORMATIVE_VALIDE)}")

    try:
        ramo = await crea_ramo(
            commessa_id=commessa_id,
            user_id=user["user_id"],
            normativa=body.normativa,
            line_ids=body.line_ids,
            created_from="manuale",
        )
        # R0: Auto-sync obblighi after branch creation
        from services.obblighi_auto_sync import trigger_sync_obblighi
        await trigger_sync_obblighi(commessa_id, user["user_id"], "rami_normativi", ramo.get("ramo_id", ""))
        await log_activity(user, "create", "ramo_normativo", ramo.get("ramo_id", ""),
                           label=f"{ramo.get('codice_ramo', '')} ({body.normativa})",
                           commessa_id=commessa_id,
                           details={"normativa": body.normativa, "created_from": "manuale"})
        return ramo
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/commesse-normative/{commessa_id}/{ramo_id}")
async def get_ramo_dettaglio(commessa_id: str, ramo_id: str, user: dict = Depends(get_current_user)):
    """Dettaglio singolo ramo con emissioni."""
    ramo = await get_ramo(ramo_id, user["user_id"])
    if not ramo or ramo["commessa_id"] != commessa_id:
        raise HTTPException(404, "Ramo non trovato")

    emissioni = await get_emissioni(ramo_id, user["user_id"])
    return {
        **ramo,
        "emissioni": emissioni,
        "n_emissioni": len(emissioni),
    }


@router.post("/commesse-normative/genera-da-istruttoria/{preventivo_id}")
async def genera_rami_da_istruttoria(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Auto-genera rami normativi dalla segmentazione confermata di un'istruttoria.
    Idempotente: se i rami esistono, li aggiorna senza duplicare.

    Richiede:
    - Istruttoria confermata con segmentazione (o classificazione pura)
    - Commessa madre collegata (da commesse_preistruite o commessa gia esistente)
    """
    uid = user["user_id"]

    istr = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not istr:
        raise HTTPException(404, "Istruttoria non trovata")

    if not istr.get("confermata"):
        raise HTTPException(400, "L'istruttoria non e ancora confermata")

    # Trova la commessa collegata
    # 1) Da commesse_preistruite
    preistruita = await db.commesse_preistruite.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0, "commessa_id": 1}
    )

    # 2) Cerca commessa madre con preventivo linkato
    commessa_id = None
    if preistruita:
        commessa_id = preistruita.get("commessa_id")

    if not commessa_id:
        # Cerca nelle commesse per preventivo linkato
        commessa = await db.commesse.find_one(
            {"user_id": uid, "$or": [
                {"moduli.preventivo_id": preventivo_id},
                {"linked_preventivo_id": preventivo_id},
            ]},
            {"_id": 0, "commessa_id": 1}
        )
        if commessa:
            commessa_id = commessa["commessa_id"]

    if not commessa_id:
        raise HTTPException(400, "Nessuna commessa madre trovata per questo preventivo. Crea prima la commessa.")

    try:
        rami = await genera_rami_da_segmentazione(commessa_id, uid, istr)
        # R0: Auto-sync obblighi after branches generated from istruttoria
        from services.obblighi_auto_sync import trigger_sync_obblighi
        await trigger_sync_obblighi(commessa_id, uid, "rami_normativi", preventivo_id)
        await log_activity(user, "create", "ramo_normativo", commessa_id,
                           label=f"Generati {len(rami)} rami da istruttoria",
                           commessa_id=commessa_id,
                           details={"created_from": "istruttoria", "preventivo_id": preventivo_id,
                                    "n_rami": len(rami)},
                           actor_type="system")
        return {"rami": rami, "commessa_id": commessa_id, "total": len(rami)}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ═══════════════════════════════════════════════════════════════════
#  EMISSIONI DOCUMENTALI
# ═══════════════════════════════════════════════════════════════════

@router.get("/emissioni/{ramo_id}")
async def list_emissioni(ramo_id: str, user: dict = Depends(get_current_user)):
    """Lista emissioni di un ramo normativo."""
    ramo = await get_ramo(ramo_id, user["user_id"])
    if not ramo:
        raise HTTPException(404, "Ramo non trovato")

    emissioni = await get_emissioni(ramo_id, user["user_id"])
    return {"emissioni": emissioni, "total": len(emissioni), "ramo": ramo["codice_ramo"]}


@router.post("/emissioni/{ramo_id}", status_code=201)
async def create_emissione(ramo_id: str, body: CreaEmissioneRequest, user: dict = Depends(get_current_user)):
    """Crea una nuova emissione documentale. Solo trigger esplicito utente."""
    try:
        emissione = await crea_emissione(
            ramo_id=ramo_id,
            user_id=user["user_id"],
            descrizione=body.descrizione or "",
            voce_lavoro_ids=body.voce_lavoro_ids,
            batch_ids=body.batch_ids,
            ddt_ids=body.ddt_ids,
            line_ids=body.line_ids,
            document_ids=body.document_ids,
        )
        await log_activity(user, "create", "emissione", emissione.get("emissione_id", ""),
                           label=emissione.get("codice_emissione", ""),
                           commessa_id=emissione.get("commessa_id", ""),
                           details={"ramo_id": ramo_id})
        return emissione
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/emissioni/{ramo_id}/{emissione_id}")
async def get_emissione_dettaglio(ramo_id: str, emissione_id: str, user: dict = Depends(get_current_user)):
    """Dettaglio singola emissione."""
    emissione = await get_emissione(emissione_id, user["user_id"])
    if not emissione or emissione["ramo_id"] != ramo_id:
        raise HTTPException(404, "Emissione non trovata")
    return emissione


@router.patch("/emissioni/{ramo_id}/{emissione_id}")
async def update_emissione(ramo_id: str, emissione_id: str, body: AggiornaEmissioneRequest, user: dict = Depends(get_current_user)):
    """Aggiorna un'emissione (solo se non emessa/annullata)."""
    em = await get_emissione(emissione_id, user["user_id"])
    if not em or em["ramo_id"] != ramo_id:
        raise HTTPException(404, "Emissione non trovata")

    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(400, "Nessun campo da aggiornare")

    try:
        updated = await aggiorna_emissione(emissione_id, user["user_id"], update_fields)
        # R0: Auto-sync obblighi after emission update (may change gate state)
        commessa_id = updated.get("commessa_id") or em.get("commessa_id")
        if commessa_id:
            from services.obblighi_auto_sync import trigger_sync_obblighi
            await trigger_sync_obblighi(commessa_id, user["user_id"], "evidence_gate", emissione_id)
        await log_activity(user, "update", "emissione", emissione_id,
                           label=em.get("codice_emissione", ""),
                           commessa_id=commessa_id or "",
                           details={"fields_changed": list(update_fields.keys())})
        return updated
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/emissioni/{ramo_id}/{emissione_id}/gate")
async def get_evidence_gate(ramo_id: str, emissione_id: str, user: dict = Depends(get_current_user)):
    """Check Evidence Gate completo per una singola emissione.
    Restituisce: checks[], blockers[], warnings[], completion_percent, emittable."""
    em = await get_emissione(emissione_id, user["user_id"])
    if not em or em["ramo_id"] != ramo_id:
        raise HTTPException(404, "Emissione non trovata")

    try:
        gate = await check_evidence_gate(emissione_id, user["user_id"])
        # R0: Auto-sync obblighi after gate recalculation
        commessa_id = em.get("commessa_id")
        if commessa_id:
            from services.obblighi_auto_sync import trigger_sync_obblighi
            await trigger_sync_obblighi(commessa_id, user["user_id"], "evidence_gate", emissione_id)
        return gate
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/emissioni/{ramo_id}/{emissione_id}/emetti")
async def emetti(ramo_id: str, emissione_id: str, user: dict = Depends(get_current_user)):
    """Emetti l'emissione (solo se Evidence Gate OK)."""
    em = await get_emissione(emissione_id, user["user_id"])
    if not em or em["ramo_id"] != ramo_id:
        raise HTTPException(404, "Emissione non trovata")

    try:
        result = await emetti_emissione(
            emissione_id, user["user_id"],
            user_name=user.get("name", user.get("email", ""))
        )
        # R0: Auto-sync obblighi after emission completed
        commessa_id = em.get("commessa_id")
        if commessa_id:
            from services.obblighi_auto_sync import trigger_sync_obblighi
            await trigger_sync_obblighi(commessa_id, user["user_id"], "evidence_gate", emissione_id)
        await log_activity(user, "issue_document", "emissione", emissione_id,
                           label=f"Emesso: {em.get('codice_emissione', '')}",
                           commessa_id=commessa_id or "",
                           details={"before_status": em.get("stato", ""), "after_status": "emessa"})
        return result
    except ValueError as e:
        raise HTTPException(409, str(e))


# ═══════════════════════════════════════════════════════════════════
#  VISTA AGGREGATA
# ═══════════════════════════════════════════════════════════════════

@router.get("/commesse/{commessa_id}/gerarchia")
async def get_commessa_gerarchia(commessa_id: str, user: dict = Depends(get_current_user)):
    """Vista completa: commessa madre + rami + emissioni (struttura ad albero)."""
    try:
        gerarchia = await get_gerarchia(commessa_id, user["user_id"])
        return gerarchia
    except ValueError as e:
        raise HTTPException(404, str(e))


# ═══════════════════════════════════════════════════════════════════
#  LEGACY ADAPTER (materializzazione)
# ═══════════════════════════════════════════════════════════════════

@router.post("/commesse-normative/{commessa_id}/materializza-legacy")
async def materializza_legacy(commessa_id: str, user: dict = Depends(get_current_user)):
    """Converte una commessa legacy in un ramo normativo reale (lazy on-access)."""
    ramo = await materializza_ramo_legacy(commessa_id, user["user_id"])
    if not ramo:
        raise HTTPException(400, "Commessa non trovata o normativa non valida per materializzazione")
    return ramo
