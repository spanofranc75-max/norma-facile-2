"""Articoli (Product/Service Catalog) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/articoli", tags=["articoli"])


# ── Models ───────────────────────────────────────────────────────

class ArticoloCategoria(str, Enum):
    MATERIALE = "materiale"
    LAVORAZIONE = "lavorazione"
    SERVIZIO = "servizio"
    ACCESSORIO = "accessorio"
    TRASPORTO = "trasporto"
    ALTRO = "altro"


class UnitaMisura(str, Enum):
    PZ = "pz"
    ML = "ml"
    MQ = "mq"
    KG = "kg"
    H = "h"
    CORPO = "corpo"
    LT = "lt"


class ArticoloCreate(BaseModel):
    codice: str = Field(..., min_length=1, max_length=30)
    descrizione: str = Field(..., min_length=1, max_length=500)
    categoria: ArticoloCategoria = ArticoloCategoria.MATERIALE
    unita_misura: UnitaMisura = UnitaMisura.PZ
    prezzo_unitario: float = Field(0, ge=0)
    aliquota_iva: str = "22"
    fornitore_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    note: Optional[str] = None


class ArticoloUpdate(BaseModel):
    codice: Optional[str] = None
    descrizione: Optional[str] = None
    categoria: Optional[ArticoloCategoria] = None
    unita_misura: Optional[UnitaMisura] = None
    prezzo_unitario: Optional[float] = None
    aliquota_iva: Optional[str] = None
    fornitore_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    note: Optional[str] = None


class ArticoloResponse(BaseModel):
    articolo_id: str
    codice: str
    descrizione: str
    categoria: str
    unita_misura: str
    prezzo_unitario: float
    aliquota_iva: str
    fornitore_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    note: Optional[str] = None
    giacenza: float = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Price history
    storico_prezzi: List[dict] = []


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/")
async def list_articoli(
    q: Optional[str] = None,
    categoria: Optional[ArticoloCategoria] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user)
):
    """List articoli with optional search and category filter."""
    query = {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    if categoria:
        query["categoria"] = categoria.value
    if q:
        query["$or"] = [
            {"codice": {"$regex": q, "$options": "i"}},
            {"descrizione": {"$regex": q, "$options": "i"}},
            {"fornitore_nome": {"$regex": q, "$options": "i"}},
        ]

    total = await db.articoli.count_documents(query)
    cursor = db.articoli.find(query, {"_id": 0}).skip(skip).limit(limit).sort("codice", 1)
    items = await cursor.to_list(length=limit)

    return {"articoli": items, "total": total}


@router.get("/search")
async def search_articoli(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """Fast search for autocomplete in invoice editor."""
    query = {
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "$or": [
            {"codice": {"$regex": q, "$options": "i"}},
            {"descrizione": {"$regex": q, "$options": "i"}},
        ]
    }
    cursor = db.articoli.find(
        query,
        {"_id": 0, "articolo_id": 1, "codice": 1, "descrizione": 1,
         "prezzo_unitario": 1, "aliquota_iva": 1, "unita_misura": 1, "categoria": 1,
         "giacenza": 1}
    ).limit(limit).sort("codice", 1)
    items = await cursor.to_list(length=limit)
    return {"results": items}


@router.get("/{articolo_id}", response_model=ArticoloResponse)
async def get_articolo(
    articolo_id: str,
    user: dict = Depends(get_current_user)
):
    """Get single articolo."""
    item = await db.articoli.find_one(
        {"articolo_id": articolo_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not item:
        raise HTTPException(404, "Articolo non trovato")
    return ArticoloResponse(**item)


@router.post("/", response_model=ArticoloResponse, status_code=201)
async def create_articolo(
    data: ArticoloCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new articolo."""
    # Check for duplicate code
    existing = await db.articoli.find_one(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "codice": data.codice},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(400, f"Codice '{data.codice}' già esistente")

    now = datetime.now(timezone.utc)
    doc = {
        "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        **data.model_dump(),
        "storico_prezzi": [{"prezzo": data.prezzo_unitario, "data": now.isoformat(), "fonte": "manuale"}],
        "created_at": now,
        "updated_at": now,
    }
    await db.articoli.insert_one(doc)
    created = await db.articoli.find_one({"articolo_id": doc["articolo_id"]}, {"_id": 0})
    return ArticoloResponse(**created)


@router.put("/{articolo_id}", response_model=ArticoloResponse)
async def update_articolo(
    articolo_id: str,
    data: ArticoloUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an articolo."""
    existing = await db.articoli.find_one(
        {"articolo_id": articolo_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Articolo non trovato")

    update_dict = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}

    # If price changed, add to history
    if "prezzo_unitario" in update_dict and update_dict["prezzo_unitario"] != existing.get("prezzo_unitario"):
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.articoli.update_one(
            {"articolo_id": articolo_id},
            {"$push": {"storico_prezzi": {"prezzo": update_dict["prezzo_unitario"], "data": now_iso, "fonte": "modifica"}}}
        )

    # Check duplicate code
    if "codice" in update_dict and update_dict["codice"] != existing.get("codice"):
        dup = await db.articoli.find_one(
            {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "codice": update_dict["codice"]},
            {"_id": 0}
        )
        if dup:
            raise HTTPException(400, f"Codice '{update_dict['codice']}' già esistente")

    update_dict["updated_at"] = datetime.now(timezone.utc)
    await db.articoli.update_one({"articolo_id": articolo_id}, {"$set": update_dict})

    updated = await db.articoli.find_one({"articolo_id": articolo_id}, {"_id": 0})
    return ArticoloResponse(**updated)


@router.delete("/{articolo_id}")
async def delete_articolo(
    articolo_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete an articolo."""
    result = await db.articoli.delete_one(
        {"articolo_id": articolo_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Articolo non trovato")
    return {"message": "Articolo eliminato"}


@router.post("/bulk-import")
async def bulk_import_articoli(
    items: List[ArticoloCreate],
    user: dict = Depends(get_current_user)
):
    """Bulk import articoli (from received invoices)."""
    now = datetime.now(timezone.utc)
    created_count = 0
    updated_count = 0
    errors = []

    for item in items:
        existing = await db.articoli.find_one(
            {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "codice": item.codice},
            {"_id": 0}
        )
        if existing:
            # Update price if different
            if item.prezzo_unitario != existing.get("prezzo_unitario", 0):
                await db.articoli.update_one(
                    {"articolo_id": existing["articolo_id"]},
                    {
                        "$set": {
                            "prezzo_unitario": item.prezzo_unitario,
                            "updated_at": now,
                        },
                        "$push": {
                            "storico_prezzi": {
                                "prezzo": item.prezzo_unitario,
                                "data": now.isoformat(),
                                "fonte": f"fattura fornitore: {item.fornitore_nome or 'N/A'}"
                            }
                        }
                    }
                )
                updated_count += 1
        else:
            doc = {
                "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"], "tenant_id": user["tenant_id"],
                **item.model_dump(),
                "storico_prezzi": [{"prezzo": item.prezzo_unitario, "data": now.isoformat(), "fonte": f"fattura fornitore: {item.fornitore_nome or 'N/A'}"}],
                "created_at": now,
                "updated_at": now,
            }
            await db.articoli.insert_one(doc)
            created_count += 1

    return {
        "message": f"Import completato: {created_count} creati, {updated_count} aggiornati",
        "created": created_count,
        "updated": updated_count,
        "errors": errors,
    }
