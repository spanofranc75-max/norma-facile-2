"""Client routes for anagrafica management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=ClientListResponse)
async def get_clients(
    search: Optional[str] = Query(None, description="Search by name or P.IVA"),
    client_type: Optional[str] = Query(None, description="Filter by client_type: cliente, fornitore, cliente_fornitore"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get all clients for current user with optional search and type filter."""
    query = {"user_id": user["user_id"]}
    
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
    
    return ClientListResponse(
        clients=[ClientResponse(**c) for c in clients],
        total=total
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific client by ID."""
    client = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    return ClientResponse(**client)


@router.post("/", response_model=ClientResponse, status_code=201)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new client."""
    # Check for duplicate P.IVA (skip empty/whitespace)
    piva = (client_data.partita_iva or "").strip()
    if piva:
        existing = await db.clients.find_one({
            "user_id": user["user_id"],
            "partita_iva": piva
        }, {"_id": 0, "client_id": 1, "business_name": 1, "client_type": 1})
        if existing:
            ex_type = existing.get("client_type", "")
            new_type = client_data.client_type or "cliente"
            # If same P.IVA exists as a different type, suggest merge
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
    
    client_doc = {
        "client_id": client_id,
        "user_id": user["user_id"],
        **client_data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    
    await db.clients.insert_one(client_doc)
    
    # Retrieve without _id
    created = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    
    logger.info(f"Client created: {client_id} by user {user['user_id']}")
    return ClientResponse(**created)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing client."""
    # Check client exists
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"]}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    # Check for duplicate P.IVA if changing
    new_piva = (client_data.partita_iva or "").strip()
    if new_piva and new_piva != (existing.get("partita_iva") or "").strip():
        duplicate = await db.clients.find_one({
            "user_id": user["user_id"],
            "partita_iva": new_piva,
            "client_id": {"$ne": client_id}
        }, {"_id": 0, "business_name": 1})
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Esiste già un record con questa Partita IVA: {duplicate.get('business_name', '')}"
            )
    
    # Build update dict (only non-None values)
    update_dict = {
        k: v for k, v in client_data.model_dump().items()
        if v is not None
    }
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    await db.clients.update_one(
        {"client_id": client_id},
        {"$set": update_dict}
    )
    
    updated = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    
    logger.info(f"Client updated: {client_id}")
    return ClientResponse(**updated)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a client."""
    uid = user["user_id"]
    
    # Check associated data
    blockers = []
    invoice_count = await db.invoices.count_documents({"client_id": client_id, "user_id": uid})
    if invoice_count > 0:
        blockers.append(f"{invoice_count} fatture")
    
    commessa_count = await db.commesse.count_documents({"client_id": client_id, "user_id": uid})
    if commessa_count > 0:
        blockers.append(f"{commessa_count} commesse")
    
    preventivo_count = await db.preventivi.count_documents({"client_id": client_id, "user_id": uid})
    if preventivo_count > 0:
        blockers.append(f"{preventivo_count} preventivi")
    
    if blockers:
        raise HTTPException(
            status_code=400,
            detail=f"Impossibile eliminare: il cliente ha {', '.join(blockers)} associat{'i' if len(blockers) > 1 else 'e'}"
        )
    
    result = await db.clients.delete_one({
        "client_id": client_id,
        "user_id": uid
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    logger.info(f"Client deleted: {client_id}")
    return {"message": "Cliente eliminato con successo"}



@router.post("/{client_id}/promote")
async def promote_to_cliente_fornitore(
    client_id: str,
    user: dict = Depends(get_current_user),
):
    """Promote a cliente or fornitore to cliente_fornitore."""
    existing = await db.clients.find_one(
        {"client_id": client_id, "user_id": user["user_id"]}
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



# ── Email Log per Cliente ──

@router.get("/{client_id}/email-log")
async def get_client_email_log(client_id: str, user: dict = Depends(get_current_user)):
    """Get all emails sent to documents linked to this client."""
    uid = user["user_id"]

    emails = []

    # Invoices with email_sent=true for this client
    async for inv in db.invoices.find(
        {"user_id": uid, "client_id": client_id, "email_sent": True},
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
        {"user_id": uid, "client_id": client_id, "email_sent": True},
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
        {"user_id": uid, "client_id": client_id, "email_sent": True},
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
