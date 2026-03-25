"""Client snapshot migration — backfills client_snapshot on all existing documents.

This endpoint is intended to be called ONCE after deploying the snapshot feature.
It reads each document's client_id, fetches the current client data, and stores
a snapshot on the document. For documents where the client has already been modified,
a manual review may be needed.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.database import db
from core.security import get_current_user
from services.client_snapshot import build_snapshot

router = APIRouter(prefix="/admin/migration", tags=["migration"])
logger = logging.getLogger(__name__)

DOCUMENT_COLLECTIONS = [
    {"name": "invoices", "id_field": "invoice_id", "label_field": "document_number"},
    {"name": "preventivi", "id_field": "preventivo_id", "label_field": "number"},
    {"name": "ddt", "id_field": "ddt_id", "label_field": "number"},
    {"name": "commesse", "id_field": "commessa_id", "label_field": "numero"},
]


@router.post("/backfill-client-snapshots")
async def backfill_client_snapshots(user: dict = Depends(get_current_user)):
    """Add client_snapshot to all documents that don't have one yet.
    
    This reads the current client data and stores it as a snapshot.
    IMPORTANT: Run this only after verifying client data is correct.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin possono eseguire migrazioni")
    
    uid = user["user_id"]
    report = {"total_updated": 0, "total_skipped": 0, "total_no_client": 0, "collections": {}}
    
    # Cache client data to avoid repeated lookups
    client_cache = {}
    
    for coll_info in DOCUMENT_COLLECTIONS:
        coll_name = coll_info["name"]
        id_field = coll_info["id_field"]
        label_field = coll_info["label_field"]
        coll = db[coll_name]
        
        coll_report = {"updated": 0, "skipped": 0, "no_client": 0, "errors": []}
        
        # Find documents without client_snapshot
        cursor = coll.find(
            {"user_id": uid, "client_snapshot": {"$exists": False}},
            {"_id": 0, id_field: 1, label_field: 1, "client_id": 1}
        )
        docs = await cursor.to_list(length=5000)
        
        for doc in docs:
            client_id = doc.get("client_id")
            doc_id = doc.get(id_field, "?")
            doc_label = doc.get(label_field, "?")
            
            if not client_id:
                coll_report["no_client"] += 1
                continue
            
            # Use cache
            if client_id not in client_cache:
                client_cache[client_id] = await build_snapshot(client_id)
            
            snapshot = client_cache[client_id]
            if not snapshot:
                coll_report["errors"].append(f"{doc_label}: client {client_id} non trovato")
                continue
            
            await coll.update_one(
                {id_field: doc_id},
                {"$set": {"client_snapshot": snapshot, "updated_at": datetime.now(timezone.utc)}}
            )
            coll_report["updated"] += 1
        
        # Count already-migrated docs
        already = await coll.count_documents(
            {"user_id": uid, "client_snapshot": {"$exists": True}}
        )
        coll_report["skipped"] = already - coll_report["updated"]
        
        report["collections"][coll_name] = coll_report
        report["total_updated"] += coll_report["updated"]
        report["total_skipped"] += coll_report["skipped"]
        report["total_no_client"] += coll_report["no_client"]
    
    logger.info(f"Client snapshot migration completed: {report['total_updated']} updated")
    return {"message": "Migrazione snapshot completata", "report": report}


@router.get("/snapshot-status")
async def snapshot_status(user: dict = Depends(get_current_user)):
    """Check how many documents have/lack client_snapshot."""
    uid = user["user_id"]
    result = {}
    
    for coll_info in DOCUMENT_COLLECTIONS:
        coll_name = coll_info["name"]
        coll = db[coll_name]
        total = await coll.count_documents({"user_id": uid})
        with_snapshot = await coll.count_documents({"user_id": uid, "client_snapshot": {"$exists": True}})
        without = total - with_snapshot
        result[coll_name] = {
            "total": total,
            "with_snapshot": with_snapshot,
            "without_snapshot": without,
            "coverage": f"{(with_snapshot / total * 100):.0f}%" if total > 0 else "N/A"
        }
    
    return result


@router.post("/set-default-client-status")
async def set_default_client_status(user: dict = Depends(get_current_user)):
    """Set status='active' on all clients that don't have a status field yet."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin possono eseguire migrazioni")
    
    uid = user["user_id"]
    result = await db.clients.update_many(
        {"user_id": uid, "status": {"$exists": False}},
        {"$set": {"status": "active"}}
    )
    
    return {
        "message": f"Status impostato su {result.modified_count} clienti",
        "modified_count": result.modified_count
    }
