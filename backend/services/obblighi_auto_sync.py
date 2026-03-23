"""
Auto-Sync Obblighi Commessa
============================
Trigger automatico asincrono per sincronizzare il Registro Obblighi
quando un modulo sorgente cambia stato.

Debounce strategy: in-memory single-instance (temporaneo per v1).
Non blocca la response principale. Log strutturato per debug.
"""

import asyncio
import logging
import time
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

# ─── Debounce in-memory (v1 — single instance) ───
_last_sync: dict[str, float] = {}
DEBOUNCE_SECONDS = 5.0


async def resolve_commessa_from_preventivo(preventivo_id: str, user_id: str) -> Optional[str]:
    """Resolve commessa_id from a preventivo_id (via commesse or commesse_preistruite)."""
    preistruita = await db.commesse_preistruite.find_one(
        {"preventivo_id": preventivo_id, "user_id": user_id},
        {"_id": 0, "commessa_id": 1}
    )
    if preistruita and preistruita.get("commessa_id"):
        return preistruita["commessa_id"]
    commessa = await db.commesse.find_one(
        {"user_id": user_id, "$or": [
            {"moduli.preventivo_id": preventivo_id},
            {"linked_preventivo_id": preventivo_id},
        ]},
        {"_id": 0, "commessa_id": 1}
    )
    return commessa["commessa_id"] if commessa else None

# ─── Debounce in-memory (v1 — single instance) ───
_last_sync: dict[str, float] = {}
DEBOUNCE_SECONDS = 5.0


async def trigger_sync_obblighi(
    commessa_id: str,
    user_id: str,
    trigger_source: str,
    trigger_entity_id: str = "",
):
    """
    Fire-and-forget async sync of obligations for a commessa.
    Called after substantive state changes in source modules.

    - Non-blocking (runs as background task)
    - Debounced (skips if < DEBOUNCE_SECONDS since last sync for same commessa)
    - Never breaks the caller's flow
    """
    if not commessa_id or not user_id:
        return

    now = time.monotonic()
    cache_key = f"{commessa_id}|{user_id}"
    last = _last_sync.get(cache_key, 0)

    if now - last < DEBOUNCE_SECONDS:
        logger.debug(
            f"[OBBLIGHI AUTO-SYNC] Skipped (debounce): commessa={commessa_id}, "
            f"trigger={trigger_source}, entity={trigger_entity_id}"
        )
        return

    _last_sync[cache_key] = now
    from core.background import safe_background_task
    safe_background_task(_run_sync(commessa_id, user_id, trigger_source, trigger_entity_id), "obblighi_sync")


async def _run_sync(
    commessa_id: str,
    user_id: str,
    trigger_source: str,
    trigger_entity_id: str,
):
    """Execute sync in background, never raise."""
    try:
        from services.obblighi_commessa_service import sync_obblighi_commessa

        logger.info(
            f"[OBBLIGHI AUTO-SYNC] Started: commessa={commessa_id}, "
            f"trigger={trigger_source}, entity={trigger_entity_id}"
        )
        result = await sync_obblighi_commessa(commessa_id, user_id)

        if result.get("error"):
            logger.warning(
                f"[OBBLIGHI AUTO-SYNC] Error: commessa={commessa_id}, "
                f"trigger={trigger_source}, error={result['error']}"
            )
        else:
            logger.info(
                f"[OBBLIGHI AUTO-SYNC] Completed: commessa={commessa_id}, "
                f"trigger={trigger_source}, "
                f"created={result.get('created', 0)}, "
                f"updated={result.get('updated', 0)}, "
                f"closed={result.get('closed', 0)}"
            )
    except Exception as e:
        logger.error(
            f"[OBBLIGHI AUTO-SYNC] Failed: commessa={commessa_id}, "
            f"trigger={trigger_source}, error={e}"
        )
