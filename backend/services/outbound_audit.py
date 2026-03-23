"""
Outbound Audit Logger — Logs all external actions (email, SDI, document sends).
Every outbound action must pass through log_outbound() for traceability.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from core.database import db

logger = logging.getLogger(__name__)

COLL = "outbound_audit_log"


async def log_outbound(
    user_id: str,
    action_type: str,
    recipient: str,
    details: dict,
    status: str = "sent",
    external_id: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Log an outbound action to the audit collection.

    action_type: "email_invoice", "email_ddt", "email_rdp", "email_oda",
                 "email_conto_lavoro", "email_preventivo", "email_perizia",
                 "email_pacchetto", "sdi_send", "fic_sync"
    status: "sent", "failed", "blocked_safe_mode", "blocked_demo"
    """
    doc = {
        "user_id": user_id,
        "action_type": action_type,
        "recipient": recipient,
        "details": details,
        "status": status,
        "external_id": external_id,
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await db[COLL].insert_one(doc)
        logger.info(f"[OUTBOUND] {action_type} → {recipient} [{status}]")
    except Exception as e:
        logger.error(f"[OUTBOUND LOG ERROR] {e}")
