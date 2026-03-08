"""Activity Audit Trail — fire-and-forget logger for all critical CRUD operations.

Usage in any route:
    from services.audit_trail import log_activity
    await log_activity(user, "create", "commessa", commessa_id, label="COM-001", details={...})
"""
import logging
from datetime import datetime, timezone
from core.database import db

logger = logging.getLogger(__name__)

COLLECTION = "activity_log"

# Supported entity types for filtering
ENTITY_TYPES = [
    "commessa", "preventivo", "fattura", "ddt", "cliente",
    "fattura_ricevuta", "rilievo", "distinta", "perizia",
    "saldatore", "strumento", "audit_qualita", "nc",
    "fpc_progetto", "certificazione", "impostazioni",
]

ACTION_TYPES = ["create", "update", "delete", "import", "export", "status_change", "email_sent"]


async def log_activity(
    user: dict,
    action: str,
    entity_type: str,
    entity_id: str,
    label: str = "",
    details: dict | None = None,
):
    """Write an activity record to the audit log.

    This is intentionally fire-and-forget: failures are logged but never
    propagate to the caller.
    """
    try:
        doc = {
            "user_id": user.get("user_id", "system"),
            "user_name": user.get("name", user.get("email", "Sistema")),
            "user_email": user.get("email", ""),
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "label": label,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await db[COLLECTION].insert_one(doc)
    except Exception as exc:
        logger.warning(f"Audit trail write failed: {exc}")
