"""Client routes for anagrafica management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.security import get_current_user, tenant_match
from core.rbac import require_role
from core.database import db
from models.client import (
    ClientCreate, ClientUpdate
)
from services.audit_trail import log_activity
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


def _build_client_response(doc: dict) -> dict:
    """Build a safe response dict from a MongoDB document, tolerating nulls."""
    if not doc:
        return {}
    resp = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        resp[k] = v
    # Ensure created_at is present
    if "created_at" in resp and hasattr(resp["created_at"], "isoformat"):
        resp["created_at"] = resp["created_at"].isoformat()
    if "updated_at" in resp and resp["updated_at"] and hasattr(resp["updated_at"], "isoformat"):
        resp["updated_at"] = resp["updated_at"].isoformat()
    return resp


@router.get("/")
async def get_clients(
    search: Optional[str] = Query(None, description="Search by name or P.IVA"),
    client_type: Optional[str] = Query(None, description="Filter by client_type: cliente, fornitore, cliente_fornitore"),
    status: Optional[str] = Query(None, description="Filter by status: active, archived, blocked. Default: active only"),
    include_archived: bool = Query(False, description="Include archived/blocked clients"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))
):
    """Get all clients for current user with optional search and type filter."""
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    
    # Status filter
    if status:
        if status == "active":
            # "active" means all non-archived: includes explicit "active" AND null/missing
            query["status"] = {"$in": ["active", None]}
        else:
            query["status"] = status
    elif not include_archived:
        query["status"] = {"$in": ["active", None]}
    
    if client_type:
        if client_type == "fornitore":
            query["client_type"] = {"$in": ["fornitore", "cliente_fornitore"]}
        elif client_type == "cliente":
            query["client_type"] = {"$in": ["cliente", "cliente_fornitore"]}
        else:
            query["client_type"] = client_type
    
    if search:
        query["$or"] = [
            {"business_name": {"$regex": search, "$options": "i"}},
            {"partita_iva": {"$regex": search, "$options": "i"}},
            {"codice_fiscale": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.clients.count_documents(query)
    
    clients_cursor = db.clients.find(query, {"_id": 0}).skip(skip).limit(limit).sort("business_name", 1)
    clients = await clients_cursor.to_list(length=limit)
    
    return {"clients": [_build_client_response(c) for c in clients], "total": total}


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))
):
    """Get a specific client by ID."""
    client = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    return _build_client_response(client)


@router.post("/", status_code=201)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))
):
    """Create a new client. Pydantic validates and strips null values automatically."""
    raw = client_data.model_dump()

    logger.info(f"[CREATE CLIENT] validated keys: {list(raw.keys())}")

    # Defaults for optional fields that need them
    raw.setdefault("codice_sdi", "0000000")
    raw.setdefault("country", "IT")

    # Check for duplicate P.IVA (skip empty/whitespace)
    piva = (raw.get("partita_iva") or "").strip()
    if piva:
        existing = await db.clients.find_one({
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "partita_iva": piva
        }, {"_id": 0, "client_id": 1, "business_name": 1, "client_type": 1})
        if existing:
            ex_type = existing.get("client_type", "")
            new_type = raw.get("client_type", "cliente")
            if ex_type != new_type and ex_type != "cliente_fornitore":
                raise HTTPException(
                    status_code=409,
                    detail=f"La P.IVA {piva} è già registrata come '{existing.get('business_name', '')}' "
                           f"(tipo: {ex_type}). Puoi convertirlo in Cliente/Fornitore dalla sua scheda.",
                )
            raise HTTPException(
                status_code=400,
                detail=f"Esiste già un record con questa Partita IVA: {existing.get('business_name', '')}"
            )

    client_id = f"cli_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # Build document from validated data
    client_doc = {k: v for k, v in raw.items()}
    # Serialize contacts to dicts for MongoDB
    if "contacts" in client_doc:
        client_doc["contacts"] = [
            c if isinstance(c, dict) else c.model_dump() if hasattr(c, 'model_dump') else dict(c)
            for c in (client_doc["contacts"] or [])
        ]
    client_doc["client_id"] = client_id
    client_doc["user_id"] = user["user_id"]
    client_doc["tenant_id"] = user["tenant_id"]
    client_doc["created_at"] = now
    client_doc["updated_at"] = now

    await db.clients.insert_one(client_doc)

    # Retrieve without _id
    created = await db.clients.find_one({"client_id": client_id}, {"_id": 0})

    logger.info(f"Client created: {client_id} by user {user['user_id']}")
    await log_activity(user, "create", "cliente", client_id, label=raw.get("business_name", ""))

    return _build_client_response(created)


@router.put("/{client_id}")
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))
):
    """Update an existing client."""
    # Check client exists
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    raw = update_data.model_dump(exclude_unset=True)
    
    # Check for duplicate P.IVA if changing
    new_piva = (raw.get("partita_iva") or "").strip()
    if new_piva and new_piva != (existing.get("partita_iva") or "").strip():
        duplicate = await db.clients.find_one({
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "partita_iva": new_piva,
            "client_id": {"$ne": client_id}
        }, {"_id": 0, "business_name": 1})
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Esiste già un record con questa Partita IVA: {duplicate.get('business_name', '')}"
            )
    
    # Serialize contacts to dicts for MongoDB
    if "contacts" in raw and raw["contacts"] is not None:
        raw["contacts"] = [
            c if isinstance(c, dict) else c.model_dump() if hasattr(c, 'model_dump') else dict(c)
            for c in raw["contacts"]
        ]

    raw["updated_at"] = datetime.now(timezone.utc)
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": raw}
    )
    
    updated = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    
    logger.info(f"Client updated: {client_id}")
    await log_activity(user, "update", "cliente", client_id, label=updated.get("business_name", ""))
    return _build_client_response(updated)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))
):
    """Delete a client."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    
    # Check associated data
    blockers = []
    invoice_count = await db.invoices.count_documents({"client_id": client_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if invoice_count > 0:
        blockers.append(f"{invoice_count} fatture")
    
    commessa_count = await db.commesse.count_documents({"client_id": client_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if commessa_count > 0:
        blockers.append(f"{commessa_count} commesse")
    
    preventivo_count = await db.preventivi.count_documents({"client_id": client_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if preventivo_count > 0:
        blockers.append(f"{preventivo_count} preventivi")
    
    if blockers:
        raise HTTPException(
            status_code=400,
            detail=f"Impossibile eliminare: il cliente ha {', '.join(blockers)} associat{'i' if len(blockers) > 1 else 'e'}"
        )
    
    result = await db.clients.delete_one({
        "client_id": client_id,
        "user_id": uid, "tenant_id": tenant_match(user)
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    logger.info(f"Client deleted: {client_id}")
    await log_activity(user, "delete", "cliente", client_id)
    return {"message": "Cliente eliminato con successo"}



@router.post("/{client_id}/promote")
async def promote_to_cliente_fornitore(
    client_id: str,
    user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico")),
):
    """Promote a cliente or fornitore to cliente_fornitore."""
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Record non trovato")

    if existing.get("client_type") == "cliente_fornitore":
        return {"message": "Già di tipo Cliente/Fornitore", "client_id": client_id}

    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"client_type": "cliente_fornitore", "updated_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Client {client_id} promoted to cliente_fornitore")
    return {"message": "Convertito in Cliente/Fornitore", "client_id": client_id}


@router.post("/{client_id}/archive")
async def archive_client(client_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Archive a client — not usable for new documents, but visible in history."""
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0, "business_name": 1, "status": 1}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Client {client_id} archived")
    await log_activity(user, "archive", "cliente", client_id, label=existing.get("business_name", ""))
    return {"message": "Cliente archiviato", "client_id": client_id}


@router.post("/{client_id}/block")
async def block_client(client_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Block a client — fully locked."""
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0, "business_name": 1}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"status": "blocked", "updated_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Client {client_id} blocked")
    await log_activity(user, "block", "cliente", client_id, label=existing.get("business_name", ""))
    return {"message": "Cliente bloccato", "client_id": client_id}


@router.post("/{client_id}/reactivate")
async def reactivate_client(client_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Reactivate a previously archived or blocked client."""
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0, "business_name": 1}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Client {client_id} reactivated")
    await log_activity(user, "reactivate", "cliente", client_id, label=existing.get("business_name", ""))
    return {"message": "Cliente riattivato", "client_id": client_id}


@router.post("/{client_id}/set-successor")
async def set_successor(client_id: str, successor_id: str = Query(...), user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Link a successor client to this one (for client succession tracking)."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    existing = await db.clients.find_one({"client_id": client_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0, "business_name": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    successor = await db.clients.find_one({"client_id": successor_id, "user_id": uid, "tenant_id": tenant_match(user)}, {"_id": 0, "business_name": 1})
    if not successor:
        raise HTTPException(status_code=404, detail="Cliente successore non trovato")
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": {"successor_client_id": successor_id, "updated_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Client {client_id} successor set to {successor_id}")
    return {"message": f"Successore impostato: {successor.get('business_name', '')}", "client_id": client_id}



# ── Email Log per Cliente ──

@router.get("/{client_id}/email-log")
async def get_client_email_log(client_id: str, user: dict = Depends(require_role("admin", "amministrazione", "ufficio_tecnico"))):
    """Get all emails sent to documents linked to this client."""
    uid = user["user_id"]
    tid = user["tenant_id"]

    emails = []

    # Invoices with email_sent=true for this client
    async for inv in db.invoices.find(
        {"user_id": uid, "tenant_id": tenant_match(user), "client_id": client_id, "email_sent": True},
        {"_id": 0, "document_number": 1, "document_type": 1, "email_sent_to": 1, "email_sent_at": 1}
    ):
        type_labels = {"FT": "Fattura", "NC": "Nota di Credito"}
        emails.append({
            "type": type_labels.get(inv.get("document_type"), "Documento"),
            "number": inv.get("document_number", ""),
            "to": inv.get("email_sent_to", ""),
            "sent_at": inv.get("email_sent_at", ""),
        })

    # DDTs with email_sent=true
    async for ddt in db.ddt.find(
        {"user_id": uid, "tenant_id": tenant_match(user), "client_id": client_id, "email_sent": True},
        {"_id": 0, "number": 1, "ddt_type": 1, "email_sent_to": 1, "email_sent_at": 1}
    ):
        emails.append({
            "type": f"DDT ({ddt.get('ddt_type', 'vendita')})",
            "number": ddt.get("number", ""),
            "to": ddt.get("email_sent_to", ""),
            "sent_at": ddt.get("email_sent_at", ""),
        })

    # Preventivi with email_sent=true
    async for prev in db.preventivi.find(
        {"user_id": uid, "tenant_id": tenant_match(user), "client_id": client_id, "email_sent": True},
        {"_id": 0, "number": 1, "email_sent_to": 1, "email_sent_at": 1}
    ):
        emails.append({
            "type": "Preventivo",
            "number": prev.get("number", ""),
            "to": prev.get("email_sent_to", ""),
            "sent_at": prev.get("email_sent_at", ""),
        })

    # Sort by date (newest first)
    emails.sort(key=lambda e: e.get("sent_at", ""), reverse=True)

    return {"emails": emails, "total": len(emails)}
