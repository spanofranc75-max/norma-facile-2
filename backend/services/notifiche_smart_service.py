"""
Notifiche Smart In-App (N1)
=============================
Sistema di notifiche intelligenti in-app per eventi critici.
Deduplicazione obbligatoria per evitare rumore.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = [
    "semaforo_peggiorato",
    "nuovo_hard_block",
    "documento_scaduto",
    "emissione_bloccata",
    "gate_pos_peggiorato",
    "pacchetto_incompleto",
]

SEVERITY_MAP = {
    "semaforo_peggiorato": "alta",
    "nuovo_hard_block": "critica",
    "documento_scaduto": "alta",
    "emissione_bloccata": "alta",
    "gate_pos_peggiorato": "media",
    "pacchetto_incompleto": "media",
}


async def crea_notifica(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    commessa_id: str = "",
    entity_type: str = "",
    entity_id: str = "",
    linked_route: str = "",
    dedupe_key: str = "",
    severity: str = "",
) -> Optional[dict]:
    """Create a smart notification with deduplication.
    
    If a notification with the same dedupe_key exists and is unread,
    it gets updated (not duplicated). Returns None if deduplicated away.
    """
    now = datetime.now(timezone.utc).isoformat()
    sev = severity or SEVERITY_MAP.get(notification_type, "media")

    # Dedupe: check if an unread notification with same key exists
    if dedupe_key:
        existing = await db.notifiche_smart.find_one(
            {"user_id": user_id, "dedupe_key": dedupe_key, "status": "unread"},
            {"_id": 0},
        )
        if existing:
            # Update the existing one instead of creating new
            await db.notifiche_smart.update_one(
                {"notification_id": existing["notification_id"]},
                {"$set": {
                    "title": title,
                    "message": message,
                    "severity": sev,
                    "updated_at": now,
                    "update_count": existing.get("update_count", 0) + 1,
                }},
            )
            logger.info(f"Notifica deduplicata: {dedupe_key}")
            return None

    notification_id = f"notif_{uuid.uuid4().hex[:12]}"
    doc = {
        "notification_id": notification_id,
        "user_id": user_id,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "severity": sev,
        "commessa_id": commessa_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "linked_route": linked_route,
        "dedupe_key": dedupe_key,
        "status": "unread",
        "update_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    await db.notifiche_smart.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_notifiche(
    user_id: str,
    status: str = "",
    limit: int = 50,
    skip: int = 0,
) -> dict:
    """List notifications for a user, ordered by most recent."""
    query = {"user_id": user_id}
    if status:
        query["status"] = status

    total = await db.notifiche_smart.count_documents(query)
    cursor = db.notifiche_smart.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)
    return {"items": items, "total": total}


async def count_unread(user_id: str) -> int:
    return await db.notifiche_smart.count_documents(
        {"user_id": user_id, "status": "unread"}
    )


async def mark_read(notification_id: str, user_id: str) -> bool:
    result = await db.notifiche_smart.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"status": "read", "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count > 0


async def mark_all_read(user_id: str) -> int:
    result = await db.notifiche_smart.update_many(
        {"user_id": user_id, "status": "unread"},
        {"$set": {"status": "read", "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count


async def archive_notification(notification_id: str, user_id: str) -> bool:
    result = await db.notifiche_smart.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"status": "archived"}},
    )
    return result.modified_count > 0
