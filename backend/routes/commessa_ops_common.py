"""Commessa Operations — Shared helpers, models, and utilities.

Used by all commessa_ops sub-modules:
  approvvigionamento, produzione_ops, conto_lavoro, documenti_ops, consegne_ops
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from core.database import db
from core.security import tenant_match

logger = logging.getLogger(__name__)

COLL = "commesse"
DOC_COLL = "commessa_documents"


async def get_commessa_or_404(commessa_id, uid, tid="default"):
    doc = await db[COLL].find_one({"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")
    return doc


async def ensure_ops_fields(commessa_id):
    """Ensure operational fields exist in commessa document for backward compat."""
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "approvvigionamento": {"$exists": False}},
        {"$set": {"approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []}}}
    )
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "fasi_produzione": {"$exists": False}},
        {"$set": {"fasi_produzione": []}}
    )
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "conto_lavoro": {"$exists": False}},
        {"$set": {"conto_lavoro": []}}
    )
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "consegne": {"$exists": False}},
        {"$set": {"consegne": []}}
    )


def ts():
    return datetime.now(timezone.utc)


def new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def push_event(commessa_id, tipo, user, note="", payload=None):
    return {
        "$push": {"eventi": {
            "tipo": tipo,
            "data": ts().isoformat(),
            "operatore_id": user.get("user_id", ""),
            "operatore_nome": user.get("name", user.get("email", "")),
            "note": note,
            "payload": payload or {},
        }},
        "$set": {"updated_at": ts()},
    }


def build_update_with_event(push_items=None, set_items=None, commessa_id="", tipo="", user=None, note="", payload=None):
    """Build a MongoDB update with both data operations and event push."""
    update = {}

    push_dict = {}
    if push_items:
        push_dict.update(push_items)

    if user:
        push_dict["eventi"] = {
            "tipo": tipo,
            "data": ts().isoformat(),
            "operatore_id": user.get("user_id", ""),
            "operatore_nome": user.get("name", user.get("email", "")),
            "note": note,
            "payload": payload or {},
        }

    if push_dict:
        update["$push"] = push_dict

    set_dict = {"updated_at": ts()}
    if set_items:
        set_dict.update(set_items)
    update["$set"] = set_dict

    return update
