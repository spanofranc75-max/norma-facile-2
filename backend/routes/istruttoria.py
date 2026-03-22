"""
Istruttoria Automatica — API Routes
=====================================
Motore di istruttoria tecnica automatica da preventivo.
Fase 1: Analisi AI + Classificazione + Regole deterministiche.
"""

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from core.database import db
from services.ai_compliance_engine import analizza_preventivo_completo

router = APIRouter(prefix="/istruttoria", tags=["istruttoria"])
logger = logging.getLogger(__name__)


@router.post("/analizza-preventivo/{preventivo_id}")
async def analizza_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Fase 1 — Analisi completa del preventivo:
    1A: Estrazione tecnica strutturata (GPT)
    1B: Classificazione normativa + proposta istruttoria (GPT + Rules)

    Salva il risultato in DB e lo restituisce.
    """
    uid = user["user_id"]

    # Load preventivo
    preventivo = await db.preventivi.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not preventivo:
        raise HTTPException(404, "Preventivo non trovato")

    # Check if analysis already exists (allow re-analysis)
    existing = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0, "istruttoria_id": 1, "created_at": 1}
    )

    # Run full analysis
    logger.info(f"[ISTRUTTORIA] Avvio analisi per preventivo {preventivo_id}")
    result = await analizza_preventivo_completo(preventivo)

    if result.get("stato") == "errore":
        logger.error(f"[ISTRUTTORIA] Analisi fallita: {result.get('errore')}")
        raise HTTPException(500, f"Errore analisi: {result.get('errore')}")

    # Save to DB
    istr_id = existing.get("istruttoria_id") if existing else f"istr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc = {
        **result,
        "istruttoria_id": istr_id,
        "preventivo_id": preventivo_id,
        "user_id": uid,
        "versione": (existing.get("versione", 0) + 1) if existing else 1,
        "updated_at": now,
    }

    if existing:
        await db.istruttorie.update_one(
            {"istruttoria_id": istr_id},
            {"$set": doc}
        )
        logger.info(f"[ISTRUTTORIA] Aggiornata {istr_id} (v{doc['versione']})")
    else:
        doc["created_at"] = now
        await db.istruttorie.insert_one(doc)
        logger.info(f"[ISTRUTTORIA] Creata {istr_id}")

    # Clean response
    doc.pop("_id", None)
    return doc


@router.get("/preventivo/{preventivo_id}")
async def get_istruttoria_by_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Recupera l'istruttoria salvata per un preventivo (se esiste)."""
    doc = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Nessuna istruttoria trovata per questo preventivo")
    return doc


@router.get("/{istruttoria_id}")
async def get_istruttoria(istruttoria_id: str, user: dict = Depends(get_current_user)):
    """Recupera un'istruttoria per ID."""
    doc = await db.istruttorie.find_one(
        {"istruttoria_id": istruttoria_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Istruttoria non trovata")
    return doc


@router.get("")
async def list_istruttorie(user: dict = Depends(get_current_user)):
    """Lista tutte le istruttorie dell'utente."""
    docs = await db.istruttorie.find(
        {"user_id": user["user_id"]},
        {"_id": 0, "istruttoria_id": 1, "preventivo_id": 1, "preventivo_number": 1,
         "classificazione": 1, "exc_proposta": 1, "stato_conoscenza": 1,
         "stato": 1, "created_at": 1, "updated_at": 1, "versione": 1}
    ).sort("updated_at", -1).to_list(100)
    return {"istruttorie": docs, "total": len(docs)}
