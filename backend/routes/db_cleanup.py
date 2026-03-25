"""Database cleanup utilities for production deployment.
Admin-only endpoints to clean test data and prepare for production use.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/admin/cleanup", tags=["admin"])
logger = logging.getLogger(__name__)


class CleanupRequest(BaseModel):
    confirm: bool = False
    keep_clients: bool = True
    keep_vendors: bool = True


async def _ensure_admin(user: dict):
    if user.get("role", "admin") != "admin":
        raise HTTPException(403, "Solo l'amministratore può eseguire la pulizia")


@router.get("/preview")
async def preview_cleanup(user: dict = Depends(get_current_user)):
    """Preview what would be deleted in a cleanup."""
    await _ensure_admin(user)

    counts = {}
    collections_to_check = [
        "commesse", "preventivi", "invoices", "ddts", "distinte",
        "rilievi", "perizie", "fpc_projects", "fpc_materials",
        "fpc_controls", "fpc_ce_labels", "consumable_batches",
        "project_costs", "gate_projects",
    ]
    for coll_name in collections_to_check:
        coll = db.client[db.name][coll_name]
        counts[coll_name] = await coll.count_documents({})

    client_count = await db.clients.count_documents({})
    vendor_count = await db.client[db.name]["vendors"].count_documents({})

    return {
        "operational_data": counts,
        "clients": client_count,
        "vendors": vendor_count,
        "note": "I dati anagrafici (clienti/fornitori) possono essere mantenuti",
    }


@router.post("/execute")
async def execute_cleanup(data: CleanupRequest, user: dict = Depends(get_current_user)):
    """Execute database cleanup. Deletes all operational/test data."""
    await _ensure_admin(user)

    if not data.confirm:
        raise HTTPException(400, "Devi confermare con confirm=true")

    results = {}

    # Operational collections to always clean
    collections_to_clean = [
        "commesse", "preventivi", "invoices", "ddts", "distinte",
        "rilievi", "perizie", "fpc_projects", "fpc_materials",
        "fpc_controls", "fpc_ce_labels", "consumable_batches",
        "project_costs", "gate_projects", "notification_logs",
        "commessa_events", "email_logs",
    ]

    for coll_name in collections_to_clean:
        coll = db.client[db.name][coll_name]
        r = await coll.delete_many({})
        results[coll_name] = r.deleted_count

    if not data.keep_clients:
        r = await db.clients.delete_many({})
        results["clients"] = r.deleted_count

    if not data.keep_vendors:
        coll = db.client[db.name]["vendors"]
        r = await coll.delete_many({})
        results["vendors"] = r.deleted_count

    # Log the cleanup
    await db.client[db.name]["audit_log"].insert_one({
        "action": "database_cleanup",
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "user_email": user.get("email"),
        "results": results,
        "keep_clients": data.keep_clients,
        "keep_vendors": data.keep_vendors,
        "executed_at": datetime.now(timezone.utc),
    })

    logger.info(f"[CLEANUP] Database cleanup executed by {user.get('email')}: {results}")

    return {
        "message": "Pulizia completata con successo",
        "deleted": results,
        "kept_clients": data.keep_clients,
        "kept_vendors": data.keep_vendors,
    }
