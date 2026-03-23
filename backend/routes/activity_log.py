"""Activity Log (Audit Trail) API — read-only log of all CRUD operations."""
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from core.database import db
from core.security import get_current_user
from services.audit_trail import COLLECTION, ENTITY_TYPES, ACTION_TYPES

router = APIRouter(prefix="/activity-log", tags=["activity-log"])
logger = logging.getLogger(__name__)

# ── Translations for the frontend ────────────────────────────────
ACTION_LABELS = {
    "create": "Creazione",
    "update": "Modifica",
    "delete": "Eliminazione",
    "import": "Importazione",
    "export": "Esportazione",
    "status_change": "Cambio stato",
    "email_sent": "Email inviata",
    "ai_precompile": "Pre-compilazione AI",
    "generate_docx": "Generazione DOCX",
    "sync_complete": "Sync completato",
    "verifica": "Verifica",
    "approve": "Approvazione",
    "reject": "Rifiuto",
    "gate_check": "Verifica Gate",
    "send_email": "Invio email",
    "issue_document": "Emissione documento",
    "genera_obblighi": "Generazione obblighi",
}

ENTITY_LABELS = {
    "commessa": "Commessa",
    "preventivo": "Preventivo",
    "fattura": "Fattura",
    "ddt": "DDT",
    "cliente": "Cliente",
    "fattura_ricevuta": "Fattura Ricevuta",
    "rilievo": "Rilievo",
    "distinta": "Distinta",
    "perizia": "Perizia",
    "saldatore": "Saldatore",
    "strumento": "Strumento",
    "audit_qualita": "Audit Qualita",
    "nc": "Non Conformita",
    "fpc_progetto": "Progetto FPC",
    "certificazione": "Certificazione",
    "impostazioni": "Impostazioni",
    "cantiere_sicurezza": "Cantiere Sicurezza",
    "obbligo": "Obbligo Commessa",
    "pacchetto_documentale": "Pacchetto Documentale",
    "documento_archivio": "Documento Archivio",
    "committenza_package": "Package Committenza",
    "committenza_analisi": "Analisi Committenza",
    "emissione": "Emissione Documentale",
    "ramo_normativo": "Ramo Normativo",
}

ACTOR_LABELS = {
    "user": "Utente",
    "system": "Sistema",
    "ai": "AI",
}


@router.get("")
async def list_activity_log(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    commessa_id: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """Paginated, filtered activity log. Admin only."""
    if user.get("role") not in ("admin", "amministrazione"):
        return {"items": [], "total": 0, "message": "Accesso non autorizzato"}

    query = {}
    conditions = []

    if entity_type:
        conditions.append({"entity_type": entity_type})
    if action:
        conditions.append({"action": action})
    if user_id:
        conditions.append({"user_id": user_id})
    if commessa_id:
        conditions.append({"commessa_id": commessa_id})
    if actor_type:
        conditions.append({"actor_type": actor_type})
    if date_from:
        conditions.append({"timestamp": {"$gte": date_from}})
    if date_to:
        # Include the full day
        conditions.append({"timestamp": {"$lte": date_to + "T23:59:59"}})
    if search:
        conditions.append({"$or": [
            {"label": {"$regex": search, "$options": "i"}},
            {"user_name": {"$regex": search, "$options": "i"}},
            {"entity_id": {"$regex": search, "$options": "i"}},
            {"commessa_id": {"$regex": search, "$options": "i"}},
        ]})

    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    total = await db[COLLECTION].count_documents(query)
    docs = await db[COLLECTION].find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    return {
        "items": docs,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats")
async def activity_log_stats(user: dict = Depends(get_current_user)):
    """Summary statistics for the audit trail dashboard card."""
    if user.get("role") not in ("admin", "amministrazione"):
        return {}

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).isoformat()

    total = await db[COLLECTION].count_documents({})
    today_count = await db[COLLECTION].count_documents({"timestamp": {"$gte": today_str}})
    week_count = await db[COLLECTION].count_documents({"timestamp": {"$gte": week_ago}})

    # Top users this week
    pipeline = [
        {"$match": {"timestamp": {"$gte": week_ago}}},
        {"$group": {"_id": "$user_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_users = await db[COLLECTION].aggregate(pipeline).to_list(5)

    # Top entity types this week
    pipeline_entities = [
        {"$match": {"timestamp": {"$gte": week_ago}}},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_entities = await db[COLLECTION].aggregate(pipeline_entities).to_list(5)

    return {
        "total": total,
        "today": today_count,
        "this_week": week_count,
        "top_users": [{"name": u["_id"], "count": u["count"]} for u in top_users],
        "top_entities": [
            {"type": e["_id"], "label": ENTITY_LABELS.get(e["_id"], e["_id"]), "count": e["count"]}
            for e in top_entities
        ],
        "action_labels": ACTION_LABELS,
        "entity_labels": ENTITY_LABELS,
        "actor_labels": ACTOR_LABELS,
        "entity_types": ENTITY_TYPES,
        "action_types": ACTION_TYPES,
    }
