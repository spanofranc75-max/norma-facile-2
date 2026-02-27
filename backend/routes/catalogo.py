"""Catalogo Profili Personalizzato (Custom Warehouse) routes."""
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
router = APIRouter(prefix="/catalogo", tags=["catalogo"])


# ── Models ───────────────────────────────────────────────────────

class ProfileCategory(str, Enum):
    FERRO = "ferro"
    ALLUMINIO = "alluminio"
    ACCESSORI = "accessori"
    VERNICIATURA = "verniciatura"
    ALTRO = "altro"


class UserProfileCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    description: str = Field(..., min_length=1, max_length=200)
    category: ProfileCategory = ProfileCategory.FERRO
    weight_m: float = Field(0, ge=0, description="kg/m")
    surface_m: float = Field(0, ge=0, description="m2/m")
    price_m: Optional[float] = Field(None, ge=0, description="EUR/m")
    supplier: Optional[str] = None
    notes: Optional[str] = None


class UserProfileUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ProfileCategory] = None
    weight_m: Optional[float] = None
    surface_m: Optional[float] = None
    price_m: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None


class BulkPriceUpdate(BaseModel):
    percentage: float = Field(..., description="Percentage to increase prices (e.g. 5.0 for +5%)")
    category: Optional[ProfileCategory] = None


class UserProfileResponse(BaseModel):
    profile_id: str
    code: str
    description: str
    category: str
    weight_m: float = 0
    surface_m: float = 0
    price_m: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── CRUD ─────────────────────────────────────────────────────────

@router.get("/")
async def list_profiles(
    category: Optional[ProfileCategory] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """List user's custom profiles with optional filters."""
    query = {"user_id": user["user_id"]}
    if category:
        query["category"] = category.value
    if search:
        query["$or"] = [
            {"code": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"supplier": {"$regex": search, "$options": "i"}},
        ]

    total = await db.user_profiles.count_documents(query)
    cursor = db.user_profiles.find(query, {"_id": 0}).skip(skip).limit(limit).sort("code", 1)
    profiles = await cursor.to_list(length=limit)

    for p in profiles:
        if p.get("created_at"):
            p["created_at"] = p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"])
        if p.get("updated_at"):
            p["updated_at"] = p["updated_at"].isoformat() if hasattr(p["updated_at"], "isoformat") else str(p["updated_at"])

    return {"profiles": profiles, "total": total}


@router.post("/", status_code=201)
async def create_profile(data: UserProfileCreate, user: dict = Depends(get_current_user)):
    """Create a new custom profile."""
    # Check duplicate code
    existing = await db.user_profiles.find_one(
        {"user_id": user["user_id"], "code": data.code}, {"_id": 0}
    )
    if existing:
        raise HTTPException(409, f"Profilo con codice '{data.code}' gia esistente")

    now = datetime.now(timezone.utc)
    doc = {
        "profile_id": f"up_{uuid.uuid4().hex[:10]}",
        "user_id": user["user_id"],
        "code": data.code,
        "description": data.description,
        "category": data.category.value,
        "weight_m": data.weight_m,
        "surface_m": data.surface_m,
        "price_m": data.price_m,
        "supplier": data.supplier,
        "notes": data.notes,
        "created_at": now,
        "updated_at": now,
    }
    await db.user_profiles.insert_one(doc)
    created = await db.user_profiles.find_one({"profile_id": doc["profile_id"]}, {"_id": 0})
    if created.get("created_at"):
        created["created_at"] = created["created_at"].isoformat()
    if created.get("updated_at"):
        created["updated_at"] = created["updated_at"].isoformat()
    logger.info(f"Custom profile created: {doc['profile_id']} ({data.code})")
    return created


@router.get("/{profile_id}")
async def get_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Get a single custom profile."""
    doc = await db.user_profiles.find_one(
        {"profile_id": profile_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Profilo non trovato")
    if doc.get("created_at"):
        doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], "isoformat") else str(doc["created_at"])
    if doc.get("updated_at"):
        doc["updated_at"] = doc["updated_at"].isoformat() if hasattr(doc["updated_at"], "isoformat") else str(doc["updated_at"])
    return doc


@router.put("/{profile_id}")
async def update_profile(profile_id: str, data: UserProfileUpdate, user: dict = Depends(get_current_user)):
    """Update a custom profile."""
    existing = await db.user_profiles.find_one(
        {"profile_id": profile_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Profilo non trovato")

    upd = {"updated_at": datetime.now(timezone.utc)}
    for field in ["code", "description", "category", "weight_m", "surface_m", "price_m", "supplier", "notes"]:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val.value if hasattr(val, "value") else val

    # Check duplicate code if changing
    if data.code and data.code != existing["code"]:
        dup = await db.user_profiles.find_one(
            {"user_id": user["user_id"], "code": data.code, "profile_id": {"$ne": profile_id}}, {"_id": 0}
        )
        if dup:
            raise HTTPException(409, f"Profilo con codice '{data.code}' gia esistente")

    await db.user_profiles.update_one({"profile_id": profile_id}, {"$set": upd})
    updated = await db.user_profiles.find_one({"profile_id": profile_id}, {"_id": 0})
    if updated.get("created_at"):
        updated["created_at"] = updated["created_at"].isoformat() if hasattr(updated["created_at"], "isoformat") else str(updated["created_at"])
    if updated.get("updated_at"):
        updated["updated_at"] = updated["updated_at"].isoformat() if hasattr(updated["updated_at"], "isoformat") else str(updated["updated_at"])
    logger.info(f"Custom profile updated: {profile_id}")
    return updated


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Delete a custom profile."""
    result = await db.user_profiles.delete_one(
        {"profile_id": profile_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Profilo non trovato")
    logger.info(f"Custom profile deleted: {profile_id}")
    return {"message": "Profilo eliminato con successo"}


# ── Bulk Price Update ────────────────────────────────────────────

@router.post("/bulk-price-update")
async def bulk_price_update(data: BulkPriceUpdate, user: dict = Depends(get_current_user)):
    """Increase/decrease all prices by a percentage. Useful when steel prices spike."""
    query = {"user_id": user["user_id"], "price_m": {"$ne": None, "$gt": 0}}
    if data.category:
        query["category"] = data.category.value

    multiplier = 1 + (data.percentage / 100)

    profiles = await db.user_profiles.find(query, {"_id": 0, "profile_id": 1, "price_m": 1}).to_list(500)
    updated_count = 0
    for p in profiles:
        new_price = round(p["price_m"] * multiplier, 2)
        await db.user_profiles.update_one(
            {"profile_id": p["profile_id"]},
            {"$set": {"price_m": new_price, "updated_at": datetime.now(timezone.utc)}}
        )
        updated_count += 1

    logger.info(f"Bulk price update: {data.percentage}% on {updated_count} profiles")
    return {
        "message": f"Aggiornati {updated_count} profili ({'+' if data.percentage > 0 else ''}{data.percentage}%)",
        "updated_count": updated_count,
    }


# ── Merged Catalog (Standard + Custom) ──────────────────────────

@router.get("/merged/all")
async def get_merged_catalog(
    category: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get merged catalog: standard profiles + user custom profiles.
    Used by the Distinta editor for profile selection.
    """
    from services.profiles_data import STANDARD_PROFILES

    # Standard profiles (convert to unified format)
    merged = []
    for p in STANDARD_PROFILES:
        if category and p["type"] != category:
            continue
        if search and search.lower() not in p["label"].lower():
            continue
        merged.append({
            "profile_id": p["profile_id"],
            "code": p["profile_id"],
            "description": p["label"],
            "category": p["type"],
            "weight_m": p["weight_per_meter"],
            "surface_m": p["surface_per_meter"],
            "price_m": None,
            "supplier": "Standard",
            "source": "standard",
        })

    # User custom profiles
    query = {"user_id": user["user_id"]}
    if category:
        query["category"] = category
    custom = await db.user_profiles.find(query, {"_id": 0}).sort("code", 1).to_list(500)
    for p in custom:
        if search and search.lower() not in (p.get("description", "") + p.get("code", "")).lower():
            continue
        merged.append({
            "profile_id": p["profile_id"],
            "code": p["code"],
            "description": p["description"],
            "category": p["category"],
            "weight_m": p["weight_m"],
            "surface_m": p.get("surface_m", 0),
            "price_m": p.get("price_m"),
            "supplier": p.get("supplier", "Custom"),
            "source": "custom",
        })

    return {"profiles": merged, "total": len(merged)}
