"""
Registro Obblighi Commessa — API Routes
=========================================
CRUD + sync + query per il registro obblighi centralizzato.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from core.security import get_current_user
from services.obblighi_commessa_service import (
    get_obbligo, list_obblighi, update_obbligo,
    get_summary, get_bloccanti, sync_obblighi_commessa,
)
from services.audit_trail import log_activity

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── List with query params (no path conflict) ───
@router.get("/obblighi")
async def api_list_obblighi(
    commessa_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source_module: Optional[str] = None,
    category: Optional[str] = None,
    blocking_level: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List obligations with optional filters."""
    return await list_obblighi(
        user["user_id"], commessa_id, status, severity,
        source_module, category, blocking_level,
    )


# ─── Specific sub-paths BEFORE generic {obbligo_id} ───

@router.post("/obblighi/sync/{commessa_id}")
async def api_sync_obblighi(commessa_id: str, user: dict = Depends(get_current_user)):
    """Trigger manual sync of obligations for a commessa."""
    result = await sync_obblighi_commessa(commessa_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    await log_activity(user, "sync_complete", "obbligo", commessa_id,
                       label=f"Sync obblighi: +{result.get('created',0)} ~{result.get('updated',0)} -{result.get('closed',0)}",
                       commessa_id=commessa_id,
                       details={"created": result.get("created", 0), "updated": result.get("updated", 0),
                                "closed": result.get("closed", 0), "total_expected": result.get("total_expected", 0)},
                       actor_type="system")
    return result


@router.get("/obblighi/commessa/{commessa_id}")
async def api_obblighi_commessa(
    commessa_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source_module: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get obligations for a specific commessa."""
    return await list_obblighi(
        user["user_id"], commessa_id, status, severity, source_module,
    )


@router.get("/obblighi/bloccanti/{commessa_id}")
async def api_bloccanti(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get only blocking obligations for a commessa."""
    return await get_bloccanti(commessa_id=commessa_id, user_id=user["user_id"])


@router.get("/obblighi/summary/{commessa_id}")
async def api_summary(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get obligation summary counts for a commessa."""
    return await get_summary(commessa_id=commessa_id, user_id=user["user_id"])


# ─── Generic by ID (MUST be LAST) ───

@router.get("/obblighi/{obbligo_id}")
async def api_get_obbligo(obbligo_id: str, user: dict = Depends(get_current_user)):
    obl = await get_obbligo(obbligo_id, user["user_id"])
    if not obl:
        raise HTTPException(status_code=404, detail="Obbligo non trovato")
    return obl


@router.patch("/obblighi/{obbligo_id}")
async def api_update_obbligo(obbligo_id: str, updates: dict, user: dict = Depends(get_current_user)):
    before = await get_obbligo(obbligo_id, user["user_id"])
    obl = await update_obbligo(obbligo_id, user["user_id"], updates)
    if not obl:
        raise HTTPException(status_code=404, detail="Obbligo non trovato")
    # Log meaningful changes
    tracked = {"status", "owner_user_id", "due_date", "blocking_level"}
    changed = {k: {"before": (before or {}).get(k), "after": obl.get(k)} for k in tracked if k in updates}
    if changed:
        await log_activity(user, "status_change", "obbligo", obbligo_id,
                           label=obl.get("title", "")[:60],
                           commessa_id=obl.get("commessa_id", ""),
                           details=changed)
    return obl
