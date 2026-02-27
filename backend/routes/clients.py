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
    # Check for duplicate P.IVA
    if client_data.partita_iva:
        existing = await db.clients.find_one({
            "user_id": user["user_id"],
            "partita_iva": client_data.partita_iva
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Esiste già un cliente con questa Partita IVA"
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
    if client_data.partita_iva and client_data.partita_iva != existing.get("partita_iva"):
        duplicate = await db.clients.find_one({
            "user_id": user["user_id"],
            "partita_iva": client_data.partita_iva,
            "client_id": {"$ne": client_id}
        })
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Esiste già un cliente con questa Partita IVA"
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
    # Check if client has invoices
    invoice_count = await db.invoices.count_documents({
        "client_id": client_id,
        "user_id": user["user_id"]
    })
    
    if invoice_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossibile eliminare: il cliente ha {invoice_count} fatture associate"
        )
    
    result = await db.clients.delete_one({
        "client_id": client_id,
        "user_id": user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    logger.info(f"Client deleted: {client_id}")
    return {"message": "Cliente eliminato con successo"}
