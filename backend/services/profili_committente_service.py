"""
Profili Documentali per Committente (D6)
=========================================
Gestione profili riutilizzabili per committenti ricorrenti.
Un profilo cattura le regole documentali tipiche di un committente.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  CRUD — Profili Committente
# ═══════════════════════════════════════════════════════════════

async def crea_profilo(user_id: str, data: dict) -> dict:
    """Create a new document profile for a client."""
    profile_id = f"prof_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    profilo = {
        "profile_id": profile_id,
        "user_id": user_id,
        "client_name": data.get("client_name", "").strip(),
        "client_id": data.get("client_id", ""),
        "description": data.get("description", ""),
        "rules": data.get("rules", []),
        "notes": data.get("notes", ""),
        "warnings": data.get("warnings", []),
        "usage_count": 0,
        "last_used_at": None,
        "created_at": now,
        "updated_at": now,
    }

    if not profilo["client_name"]:
        return {"error": "Nome committente obbligatorio"}

    await db.profili_committente.insert_one(profilo)
    profilo.pop("_id", None)
    return profilo


async def crea_profilo_da_pacchetto(user_id: str, pack_id: str, client_name: str, description: str = "") -> dict:
    """Create a profile from an existing package's items (semi-automatic creation)."""
    pack = await db.pacchetti_documentali.find_one(
        {"pack_id": pack_id, "user_id": user_id}, {"_id": 0}
    )
    if not pack:
        return {"error": "Pacchetto non trovato"}

    # Extract unique document type rules from pack items
    seen = set()
    rules = []
    for item in pack.get("items", []):
        code = item.get("document_type_code", "")
        entity = item.get("entity_type", "azienda")
        key = f"{code}|{entity}"
        if key not in seen and code:
            seen.add(key)
            # Check if it was a per-worker/per-equipment item
            scope = None
            if entity == "persona" and item.get("entity_id"):
                scope = "all_assigned_workers"
            elif entity == "mezzo" and item.get("entity_id"):
                scope = "all_assigned_equipment"
            rule = {
                "document_type_code": code,
                "entity_type": entity,
                "required": item.get("required", True),
            }
            if scope:
                rule["scope"] = scope
            rules.append(rule)

    profilo = await crea_profilo(user_id, {
        "client_name": client_name,
        "description": description or f"Generato da pacchetto {pack.get('label', pack_id)}",
        "rules": rules,
    })

    if profilo.get("error"):
        return profilo

    # Audit: track that this profile came from a pack
    profilo["source_pack_id"] = pack_id
    await db.profili_committente.update_one(
        {"profile_id": profilo["profile_id"]},
        {"$set": {"source_pack_id": pack_id}},
    )

    return profilo


async def get_profilo(profile_id: str, user_id: str) -> Optional[dict]:
    doc = await db.profili_committente.find_one(
        {"profile_id": profile_id, "user_id": user_id}, {"_id": 0}
    )
    return doc


async def list_profili(user_id: str) -> list:
    cursor = db.profili_committente.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("updated_at", -1)
    return await cursor.to_list(200)


async def update_profilo(profile_id: str, user_id: str, updates: dict) -> Optional[dict]:
    allowed = {"client_name", "client_id", "description", "rules", "notes", "warnings"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return await get_profilo(profile_id, user_id)

    filtered["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.profili_committente.find_one_and_update(
        {"profile_id": profile_id, "user_id": user_id},
        {"$set": filtered},
        return_document=True,
        projection={"_id": 0},
    )
    return result


async def delete_profilo(profile_id: str, user_id: str) -> bool:
    result = await db.profili_committente.delete_one(
        {"profile_id": profile_id, "user_id": user_id}
    )
    return result.deleted_count > 0


# ═══════════════════════════════════════════════════════════════
#  Applica Profilo — crea pacchetto documentale da profilo
# ═══════════════════════════════════════════════════════════════

async def applica_profilo(user_id: str, profile_id: str, commessa_id: str, cantiere_id: str = "", label: str = "") -> dict:
    """Apply a profile to create a new document package for a commessa."""
    profilo = await get_profilo(profile_id, user_id)
    if not profilo:
        return {"error": "Profilo non trovato"}

    # Import crea_pacchetto logic — we'll construct template-like data

    pack_data = {
        "commessa_id": commessa_id,
        "cantiere_id": cantiere_id,
        "label": label or f"{profilo['client_name']} — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "recipient": {},
    }

    # We create the pack manually to use the profile's rules directly
    pack_id = f"pack_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    items = []
    for rule in profilo.get("rules", []):
        scope = rule.get("scope")
        if scope == "all_assigned_workers":
            workers = await _get_assigned_workers(user_id, cantiere_id)
            if workers:
                for w in workers:
                    items.append({
                        "document_type_code": rule["document_type_code"],
                        "entity_type": "persona",
                        "entity_id": w.get("worker_id", ""),
                        "entity_label": w.get("nominativo", ""),
                        "required": rule.get("required", True),
                        "document_id": None,
                        "status": "pending",
                        "blocking": False,
                    })
            else:
                items.append({
                    "document_type_code": rule["document_type_code"],
                    "entity_type": "persona",
                    "entity_id": "",
                    "entity_label": "(nessun lavoratore assegnato)",
                    "required": rule.get("required", True),
                    "document_id": None,
                    "status": "pending",
                    "blocking": False,
                })
        elif scope == "all_assigned_equipment":
            equip = await _get_assigned_equipment(user_id, cantiere_id)
            if equip:
                for e in equip:
                    items.append({
                        "document_type_code": rule["document_type_code"],
                        "entity_type": "mezzo",
                        "entity_id": e.get("mezzo_id", ""),
                        "entity_label": e.get("nome", ""),
                        "required": rule.get("required", True),
                        "document_id": None,
                        "status": "pending",
                        "blocking": False,
                    })
            else:
                items.append({
                    "document_type_code": rule["document_type_code"],
                    "entity_type": "mezzo",
                    "entity_id": "",
                    "entity_label": "(nessun mezzo assegnato)",
                    "required": rule.get("required", True),
                    "document_id": None,
                    "status": "pending",
                    "blocking": False,
                })
        else:
            items.append({
                "document_type_code": rule["document_type_code"],
                "entity_type": rule.get("entity_type", "azienda"),
                "entity_id": "",
                "entity_label": "",
                "required": rule.get("required", True),
                "document_id": None,
                "status": "pending",
                "blocking": False,
            })

    pack = {
        "pack_id": pack_id,
        "user_id": user_id,
        "commessa_id": commessa_id,
        "cantiere_id": cantiere_id,
        "template_code": f"profilo:{profilo['profile_id']}",
        "label": pack_data["label"],
        "status": "draft",
        "recipient": {},
        "items": items,
        "summary": {"total_required": 0, "attached": 0, "missing": 0, "expired": 0, "in_scadenza": 0, "sensibile": 0},
        "created_at": now,
        "updated_at": now,
    }

    await db.pacchetti_documentali.insert_one(pack)
    pack.pop("_id", None)

    # Update profile usage stats
    await db.profili_committente.update_one(
        {"profile_id": profile_id, "user_id": user_id},
        {"$inc": {"usage_count": 1}, "$set": {"last_used_at": now}},
    )

    return {"pack": pack, "profile": profilo}


# ═══════════════════════════════════════════════════════════════
#  Suggerisci Profilo — per un committente di una commessa
# ═══════════════════════════════════════════════════════════════

async def suggerisci_profilo(user_id: str, commessa_id: str) -> Optional[dict]:
    """Suggest a profile matching the client of a given commessa."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "client_name": 1, "client_id": 1},
    )
    if not commessa:
        return None

    client_name = commessa.get("client_name", "")
    client_id = commessa.get("client_id", "")

    # Try exact client_id match first
    if client_id:
        profilo = await db.profili_committente.find_one(
            {"user_id": user_id, "client_id": client_id}, {"_id": 0}
        )
        if profilo:
            return profilo

    # Try fuzzy client_name match
    if client_name:
        profilo = await db.profili_committente.find_one(
            {"user_id": user_id, "client_name": {"$regex": f"^{client_name[:20]}", "$options": "i"}},
            {"_id": 0},
        )
        if profilo:
            return profilo

    return None


# ── Helpers ──

async def _get_assigned_workers(user_id: str, cantiere_id: str = None) -> list:
    if not cantiere_id:
        return []
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return []
    return cantiere.get("lavoratori_coinvolti", [])


async def _get_assigned_equipment(user_id: str, cantiere_id: str = None) -> list:
    if not cantiere_id:
        return []
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return []
    return cantiere.get("mezzi_attrezzature", [])
