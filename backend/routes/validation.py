"""
Validation P1 — API Routes
============================
Endpoints per la validazione del motore AI su preventivi reali.
"""

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from core.security import get_current_user
from core.database import db
from core.rate_limiter import limiter
from services.ai_compliance_engine import analizza_preventivo_completo
from services.validation_engine import (
    VALIDATION_SET, score_singolo_preventivo, score_batch
)

router = APIRouter(prefix="/validation", tags=["validation"])
logger = logging.getLogger(__name__)


@router.get("/set")
async def get_validation_set(user: dict = Depends(get_current_user)):
    """Restituisce il set di validazione con gli esiti attesi."""
    items = []
    for pid, gt in VALIDATION_SET.items():
        items.append({
            "preventivo_id": pid,
            "number": gt["number"],
            "subject": gt["subject"],
            "normativa_attesa": gt["normativa_attesa"],
            "note": gt["note"],
        })
    return {"validation_set": items, "total": len(items)}


@router.post("/run/{preventivo_id}")
@limiter.limit("10/minute")
async def run_single_validation(request: Request, preventivo_id: str, user: dict = Depends(get_current_user)):
    """Esegue la validazione su un singolo preventivo."""
    if preventivo_id not in VALIDATION_SET:
        raise HTTPException(400, "Preventivo non presente nel set di validazione")

    gt = {**VALIDATION_SET[preventivo_id], "preventivo_id": preventivo_id}

    preventivo = await db.preventivi.find_one(
        {"preventivo_id": preventivo_id},
        {"_id": 0}
    )
    if not preventivo:
        raise HTTPException(404, "Preventivo non trovato nel DB")

    logger.info(f"[VALIDATION] Avvio analisi per {preventivo_id} ({gt['number']})")
    ai_result = await analizza_preventivo_completo(preventivo)

    if ai_result.get("stato") == "errore":
        return {
            "preventivo_id": preventivo_id,
            "errore": ai_result.get("errore"),
            "stato": "errore_analisi",
        }

    scorecard = score_singolo_preventivo(ai_result, gt)

    # Save validation result
    val_id = f"val_{uuid.uuid4().hex[:12]}"
    doc = {
        "validation_id": val_id,
        "preventivo_id": preventivo_id,
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "scorecard": scorecard,
        "ai_result_raw": {
            "classificazione": ai_result.get("classificazione"),
            "profilo_tecnico": ai_result.get("profilo_tecnico"),
            "stato_conoscenza": ai_result.get("stato_conoscenza"),
            "n_domande": len(ai_result.get("domande_residue", [])),
            "n_elementi": len(ai_result.get("estrazione_tecnica", {}).get("elementi_strutturali", [])),
        },
        "created_at": datetime.now(timezone.utc),
    }

    await db.validazioni_p1.update_one(
        {"preventivo_id": preventivo_id},
        {"$set": doc},
        upsert=True
    )

    logger.info(
        f"[VALIDATION] {gt['number']}: score={scorecard['punteggio_globale']}, "
        f"class={'OK' if scorecard['classificazione']['corretto'] else 'FAIL'}"
    )

    return {
        "validation_id": val_id,
        "scorecard": scorecard,
    }


@router.post("/run-batch")
@limiter.limit("5/minute")
async def run_batch_validation(request: Request, body: dict = None, user: dict = Depends(get_current_user)):
    """Esegue la validazione su tutto il set (o un sottoinsieme).
    Body opzionale: {"preventivo_ids": ["prev_xxx", ...]}
    """
    ids = (body or {}).get("preventivo_ids", list(VALIDATION_SET.keys()))

    results = []
    errors = []

    for pid in ids:
        if pid not in VALIDATION_SET:
            errors.append({"preventivo_id": pid, "errore": "Non nel set di validazione"})
            continue

        gt = {**VALIDATION_SET[pid], "preventivo_id": pid}

        preventivo = await db.preventivi.find_one(
            {"preventivo_id": pid},
            {"_id": 0}
        )
        if not preventivo:
            errors.append({"preventivo_id": pid, "errore": "Non trovato nel DB"})
            continue

        logger.info(f"[VALIDATION BATCH] Analisi {pid} ({gt['number']})")

        try:
            ai_result = await analizza_preventivo_completo(preventivo)
            if ai_result.get("stato") == "errore":
                errors.append({"preventivo_id": pid, "errore": ai_result.get("errore")})
                continue

            scorecard = score_singolo_preventivo(ai_result, gt)
            results.append(scorecard)

            # Persist
            val_id = f"val_{uuid.uuid4().hex[:12]}"
            await db.validazioni_p1.update_one(
                {"preventivo_id": pid},
                {"$set": {
                    "validation_id": val_id,
                    "preventivo_id": pid,
                    "user_id": user["user_id"], "tenant_id": user["tenant_id"],
                    "scorecard": scorecard,
                    "ai_result_raw": {
                        "classificazione": ai_result.get("classificazione"),
                        "profilo_tecnico": ai_result.get("profilo_tecnico"),
                        "stato_conoscenza": ai_result.get("stato_conoscenza"),
                    },
                    "created_at": datetime.now(timezone.utc),
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"[VALIDATION] Errore su {pid}: {e}")
            errors.append({"preventivo_id": pid, "errore": str(e)})

    aggregato = score_batch(results) if results else {}

    # Save aggregate
    if results:
        await db.validazioni_p1.update_one(
            {"tipo": "aggregato"},
            {"$set": {
                "tipo": "aggregato",
                "user_id": user["user_id"], "tenant_id": user["tenant_id"],
                "aggregato": aggregato,
                "n_risultati": len(results),
                "n_errori": len(errors),
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True
        )

    return {
        "risultati": results,
        "aggregato": aggregato,
        "errori": errors,
    }


@router.get("/results")
async def get_validation_results(user: dict = Depends(get_current_user)):
    """Recupera tutti i risultati di validazione salvati."""
    docs = await db.validazioni_p1.find(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "scorecard": {"$exists": True}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    aggregato_doc = await db.validazioni_p1.find_one(
        {"tipo": "aggregato"},
        {"_id": 0}
    )

    return {
        "risultati": docs,
        "aggregato": aggregato_doc.get("aggregato") if aggregato_doc else None,
        "total": len(docs),
    }
