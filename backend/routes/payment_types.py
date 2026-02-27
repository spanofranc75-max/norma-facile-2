"""Payment Types CRUD routes — Tipi Pagamento."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.payment_type import (
    PaymentTypeCreate, PaymentTypeUpdate, PaymentTypeResponse, PaymentTypeListResponse,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment-types", tags=["payment-types"])

COLLECTION = "payment_types"


@router.get("/", response_model=PaymentTypeListResponse)
async def get_payment_types(
    search: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if search:
        q["$or"] = [
            {"codice": {"$regex": search, "$options": "i"}},
            {"descrizione": {"$regex": search, "$options": "i"}},
        ]
    if tipo:
        q["tipo"] = tipo
    total = await db[COLLECTION].count_documents(q)
    items = await db[COLLECTION].find(q, {"_id": 0}).sort("codice", 1).to_list(200)
    return PaymentTypeListResponse(
        items=[PaymentTypeResponse(**i) for i in items], total=total
    )


@router.get("/{pt_id}", response_model=PaymentTypeResponse)
async def get_payment_type(pt_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Tipo pagamento non trovato")
    return PaymentTypeResponse(**doc)


@router.post("/", response_model=PaymentTypeResponse, status_code=201)
async def create_payment_type(
    data: PaymentTypeCreate, user: dict = Depends(get_current_user)
):
    # Duplicate codice check
    dup = await db[COLLECTION].find_one(
        {"user_id": user["user_id"], "codice": data.codice}
    )
    if dup:
        raise HTTPException(400, f"Codice '{data.codice}' già esistente")
    pt_id = f"pt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "payment_type_id": pt_id,
        "user_id": user["user_id"],
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"payment_type_id": pt_id}, {"_id": 0})
    logger.info(f"Payment type created: {pt_id}")
    return PaymentTypeResponse(**created)


@router.put("/{pt_id}", response_model=PaymentTypeResponse)
async def update_payment_type(
    pt_id: str, data: PaymentTypeUpdate, user: dict = Depends(get_current_user)
):
    existing = await db[COLLECTION].find_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}
    )
    if not existing:
        raise HTTPException(404, "Tipo pagamento non trovato")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db[COLLECTION].update_one({"payment_type_id": pt_id}, {"$set": update})
    updated = await db[COLLECTION].find_one({"payment_type_id": pt_id}, {"_id": 0})
    return PaymentTypeResponse(**updated)


@router.delete("/{pt_id}")
async def delete_payment_type(pt_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Tipo pagamento non trovato")
    logger.info(f"Payment type deleted: {pt_id}")
    return {"message": "Tipo pagamento eliminato"}


@router.post("/seed-defaults")
async def seed_default_payment_types(user: dict = Depends(get_current_user)):
    """Seed common Italian payment types if none exist."""
    count = await db[COLLECTION].count_documents({"user_id": user["user_id"]})
    if count > 0:
        return {"message": f"Già presenti {count} tipi pagamento", "seeded": 0}

    defaults = [
        {"codice": "BB30", "tipo": "BON", "descrizione": "Bonifico Bancario 30 gg", "gg_30": True},
        {"codice": "BB60", "tipo": "BON", "descrizione": "Bonifico Bancario 60 gg", "gg_60": True},
        {"codice": "BB30-60", "tipo": "BON", "descrizione": "Bonifico Bancario 30/60 gg", "gg_30": True, "gg_60": True},
        {"codice": "BB60FM", "tipo": "BON", "descrizione": "Bonifico Bancario 60 gg FM", "gg_60": True, "fine_mese": True},
        {"codice": "BB30-60-90", "tipo": "BON", "descrizione": "Bonifico Bancario 30/60/90 gg", "gg_30": True, "gg_60": True, "gg_90": True},
        {"codice": "RB30", "tipo": "RIB", "descrizione": "Ricevuta Bancaria 30 gg", "gg_30": True, "banca_necessaria": True},
        {"codice": "RB60", "tipo": "RIB", "descrizione": "Ricevuta Bancaria 60 gg", "gg_60": True, "banca_necessaria": True},
        {"codice": "RB30-60", "tipo": "RIB", "descrizione": "Ricevuta Bancaria 30/60 gg", "gg_30": True, "gg_60": True, "banca_necessaria": True},
        {"codice": "RB90", "tipo": "RIB", "descrizione": "Ricevuta Bancaria 90 gg", "gg_90": True, "banca_necessaria": True},
        {"codice": "CON", "tipo": "CON", "descrizione": "Contanti / Rimessa Diretta", "immediato": True},
        {"codice": "ELETT", "tipo": "ELE", "descrizione": "Pagamento Elettronico", "immediato": True},
    ]

    now = datetime.now(timezone.utc)
    docs = []
    for d in defaults:
        pt_id = f"pt_{uuid.uuid4().hex[:12]}"
        base = PaymentTypeCreate(**{**{
            "codice": "", "tipo": "BON", "descrizione": "",
        }, **d}).model_dump()
        docs.append({
            "payment_type_id": pt_id,
            "user_id": user["user_id"],
            **base,
            "created_at": now,
            "updated_at": now,
        })
    await db[COLLECTION].insert_many(docs)
    return {"message": f"Creati {len(docs)} tipi pagamento predefiniti", "seeded": len(docs)}
