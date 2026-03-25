"""
API per il sistema ML di Calibrazione del Preventivatore Predittivo.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import db
from core.security import get_current_user, tenant_match
from services.ml_calibrazione import (
    calcola_calibrazione,
    applica_calibrazione,
    registra_progetto_completato,
    get_training_stats,
)

router = APIRouter(prefix="/calibrazione", tags=["Calibrazione ML"])


class TargetParams(BaseModel):
    peso_kg: float = 0
    classe_antisismica: int = 0
    nodi_strutturali: int = 0
    tipologia: str = "media"


class CalibrazioneStimaRequest(BaseModel):
    ore_totali: float = 0
    costo_materiali: float = 0
    costo_manodopera: float = 0
    costo_cl: float = 0
    target: TargetParams = TargetParams()


class FeedbackRequest(BaseModel):
    commessa_id: Optional[str] = None
    title: str = ""
    peso_kg: float = 0
    classe_antisismica: int = 0
    nodi_strutturali: int = 0
    tipologia: str = "media"
    ore_stimate: float = 0
    ore_reali: float = 0
    costo_materiali_stimato: float = 0
    costo_materiali_reale: float = 0
    costo_manodopera_stimato: float = 0
    costo_manodopera_reale: float = 0
    costo_cl_stimato: float = 0
    costo_cl_reale: float = 0


@router.get("/status")
async def calibration_status(user: dict = Depends(get_current_user)):
    """Stato attuale della calibrazione ML e statistiche di training."""
    stats = await get_training_stats(db, user["user_id"])
    return stats


@router.post("/calcola-fattori")
async def calcola_fattori(target: TargetParams, user: dict = Depends(get_current_user)):
    """Calcola i fattori correttivi per un progetto target specifico."""
    cal = await calcola_calibrazione(db, user["user_id"], target.model_dump())
    return cal


@router.post("/applica")
async def applica_calibrazione_api(data: CalibrazioneStimaRequest, user: dict = Depends(get_current_user)):
    """Applica i fattori di calibrazione a una stima grezza."""
    stima = {
        "ore_totali": data.ore_totali,
        "costo_materiali": data.costo_materiali,
        "costo_manodopera": data.costo_manodopera,
        "costo_cl": data.costo_cl,
    }
    result = await applica_calibrazione(db, user["user_id"], stima, data.target.model_dump())
    return result


@router.post("/feedback")
async def submit_feedback(data: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Registra un progetto completato per migliorare il modello."""
    result = await registra_progetto_completato(db, user["user_id"], data.model_dump())
    return result
