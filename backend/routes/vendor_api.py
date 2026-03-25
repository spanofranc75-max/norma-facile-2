"""Vendor API — NF-Standard JSON import for manufacturer catalogs.

Multi-key system: each vendor gets a unique API key stored in vendor_keys collection.
Vendor catalogs are stored in vendor_catalogs collection, separate from user profiles.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import secrets
from datetime import datetime, timezone
from core.security import get_current_user, tenant_match
from core.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vendor", tags=["vendor"])


# ── Models ───────────────────────────────────────────────────────

class VendorProfile(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., min_length=1, max_length=100)
    uf: Optional[float] = Field(None, ge=0, description="Thermal transmittance W/m2K")
    ug: Optional[float] = Field(None, ge=0, description="Glass transmittance W/m2K")
    psi: Optional[float] = Field(None, ge=0, description="Spacer Psi value")
    weight: Optional[float] = Field(None, ge=0, description="kg/m")
    inertia: Optional[float] = Field(None, ge=0, description="Moment of inertia cm4")
    surface: Optional[float] = Field(None, ge=0, description="Surface area m2/m")
    price: Optional[float] = Field(None, ge=0, description="Price EUR/m")


class VendorCatalogImport(BaseModel):
    vendor: str = Field(..., min_length=1, max_length=100)
    system: str = Field(..., min_length=1, max_length=100)
    profiles: List[VendorProfile] = Field(..., min_length=1)


class VendorKeyCreate(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=100)
    contact_email: Optional[str] = None
    notes: Optional[str] = None


# ── API Key Middleware ───────────────────────────────────────────

async def verify_vendor_key(x_vendor_key: str = Header(...)):
    """Verify the vendor API key from the X-Vendor-Key header."""
    key_doc = await db.vendor_keys.find_one(
        {"api_key": x_vendor_key, "active": True}, {"_id": 0}
    )
    if not key_doc:
        raise HTTPException(403, "Chiave API vendor non valida o disattivata")
    # Update last_used
    await db.vendor_keys.update_one(
        {"api_key": x_vendor_key},
        {"$set": {"last_used": datetime.now(timezone.utc)}}
    )
    return key_doc


# ── Admin: Vendor Key Management (requires user auth) ───────────

@router.get("/keys")
async def list_vendor_keys(user: dict = Depends(get_current_user)):
    """List all vendor API keys (admin only)."""
    cursor = db.vendor_keys.find({"owner_id": user["user_id"]}, {"_id": 0})
    keys = await cursor.to_list(100)
    for k in keys:
        if k.get("created_at"):
            k["created_at"] = k["created_at"].isoformat() if hasattr(k["created_at"], "isoformat") else str(k["created_at"])
        if k.get("last_used"):
            k["last_used"] = k["last_used"].isoformat() if hasattr(k["last_used"], "isoformat") else str(k["last_used"])
        # Mask key for display
        k["api_key_masked"] = k["api_key"][:8] + "..." + k["api_key"][-4:]
    return {"keys": keys}


@router.post("/keys", status_code=201)
async def create_vendor_key(data: VendorKeyCreate, user: dict = Depends(get_current_user)):
    """Generate a new API key for a vendor partner."""
    api_key = f"nf_vk_{secrets.token_hex(24)}"
    now = datetime.now(timezone.utc)
    doc = {
        "key_id": f"vk_{uuid.uuid4().hex[:10]}",
        "owner_id": user["user_id"],
        "vendor_name": data.vendor_name,
        "contact_email": data.contact_email,
        "notes": data.notes,
        "api_key": api_key,
        "active": True,
        "created_at": now,
        "last_used": None,
    }
    await db.vendor_keys.insert_one(doc)
    logger.info(f"Vendor key created for {data.vendor_name} by {user['user_id']}")
    return {
        "key_id": doc["key_id"],
        "vendor_name": data.vendor_name,
        "api_key": api_key,
        "message": "Chiave generata. Condividila con il fornitore in modo sicuro.",
    }


@router.delete("/keys/{key_id}")
async def revoke_vendor_key(key_id: str, user: dict = Depends(get_current_user)):
    """Deactivate a vendor API key."""
    result = await db.vendor_keys.update_one(
        {"key_id": key_id, "owner_id": user["user_id"]},
        {"$set": {"active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Chiave non trovata")
    logger.info(f"Vendor key {key_id} revoked")
    return {"message": "Chiave revocata con successo"}


# ── Vendor Import (API Key protected) ───────────────────────────

@router.post("/import_catalog")
async def import_catalog(data: VendorCatalogImport, vendor: dict = Depends(verify_vendor_key)):
    """Import a vendor catalog in NF-Standard JSON format. Requires X-Vendor-Key header."""
    now = datetime.now(timezone.utc)
    catalog_id = f"vc_{uuid.uuid4().hex[:10]}"

    # Upsert: replace existing catalog for same vendor+system
    existing = await db.vendor_catalogs.find_one(
        {"vendor": data.vendor, "system": data.system}, {"_id": 0, "catalog_id": 1}
    )

    profiles = [p.model_dump() for p in data.profiles]

    if existing:
        await db.vendor_catalogs.update_one(
            {"catalog_id": existing["catalog_id"]},
            {"$set": {
                "profiles": profiles,
                "profile_count": len(profiles),
                "updated_at": now,
                "updated_by_key": vendor["key_id"],
            }}
        )
        catalog_id = existing["catalog_id"]
        action = "aggiornato"
    else:
        doc = {
            "catalog_id": catalog_id,
            "vendor": data.vendor,
            "system": data.system,
            "profiles": profiles,
            "profile_count": len(profiles),
            "imported_by_key": vendor["key_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.vendor_catalogs.insert_one(doc)
        action = "importato"

    logger.info(f"Vendor catalog {action}: {data.vendor} / {data.system} ({len(profiles)} profiles)")
    return {
        "catalog_id": catalog_id,
        "vendor": data.vendor,
        "system": data.system,
        "profiles_imported": len(profiles),
        "action": action,
        "message": f"Catalogo {action} con successo: {len(profiles)} profili.",
    }


# ── Public: Browse Vendor Catalogs ───────────────────────────────

@router.get("/catalogs")
async def list_catalogs(user: dict = Depends(get_current_user)):
    """List all available vendor catalogs."""
    cursor = db.vendor_catalogs.find({}, {"_id": 0, "profiles": 0}).sort("vendor", 1)
    catalogs = await cursor.to_list(100)
    for c in catalogs:
        if c.get("created_at"):
            c["created_at"] = c["created_at"].isoformat() if hasattr(c["created_at"], "isoformat") else str(c["created_at"])
        if c.get("updated_at"):
            c["updated_at"] = c["updated_at"].isoformat() if hasattr(c["updated_at"], "isoformat") else str(c["updated_at"])
    return {"catalogs": catalogs}


@router.get("/catalogs/{catalog_id}")
async def get_catalog(catalog_id: str, user: dict = Depends(get_current_user)):
    """Get a single vendor catalog with all profiles."""
    doc = await db.vendor_catalogs.find_one({"catalog_id": catalog_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Catalogo non trovato")
    if doc.get("created_at"):
        doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], "isoformat") else str(doc["created_at"])
    if doc.get("updated_at"):
        doc["updated_at"] = doc["updated_at"].isoformat() if hasattr(doc["updated_at"], "isoformat") else str(doc["updated_at"])
    return doc


@router.get("/catalogs/{vendor_name}/profiles")
async def get_vendor_profiles(vendor_name: str, user: dict = Depends(get_current_user)):
    """Get all profiles from a specific vendor."""
    catalogs = await db.vendor_catalogs.find(
        {"vendor": {"$regex": f"^{vendor_name}$", "$options": "i"}}, {"_id": 0}
    ).to_list(50)
    if not catalogs:
        raise HTTPException(404, f"Nessun catalogo trovato per '{vendor_name}'")

    all_profiles = []
    for cat in catalogs:
        for p in cat.get("profiles", []):
            p["vendor"] = cat["vendor"]
            p["system"] = cat["system"]
            p["catalog_id"] = cat["catalog_id"]
            all_profiles.append(p)

    return {"vendor": vendor_name, "profiles": all_profiles, "total": len(all_profiles)}


# ── Merged Thermal Profiles (for Calcolatore Termico dropdown) ──

@router.get("/thermal-profiles")
async def get_merged_thermal_profiles(user: dict = Depends(get_current_user)):
    """Return merged frame profiles for the thermal calculator dropdown.
    Combines: Built-in generic + Vendor catalog + User custom profiles.
    """
    from core.engine.thermal import FRAME_TYPES

    merged_frames = []

    # 1. Built-in generic profiles
    for f in FRAME_TYPES:
        merged_frames.append({
            "id": f["id"],
            "label": f["label"],
            "uf": f["uf"],
            "source": "builtin",
            "vendor": None,
        })

    # 2. Vendor catalog profiles (those with Uf values)
    vendor_catalogs = await db.vendor_catalogs.find({}, {"_id": 0}).to_list(100)
    for cat in vendor_catalogs:
        for p in cat.get("profiles", []):
            if p.get("uf") is not None:
                merged_frames.append({
                    "id": f"vendor_{cat['catalog_id']}_{p['code']}",
                    "label": f"{p['type']} ({cat['vendor']} {cat['system']})",
                    "uf": p["uf"],
                    "source": "vendor",
                    "vendor": cat["vendor"],
                })

    # 3. User custom profiles with Uf (from user_profiles with thermal data)
    user_profiles = await db.user_profiles.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).to_list(200)
    for p in user_profiles:
        if p.get("weight_m", 0) > 0:
            merged_frames.append({
                "id": f"custom_{p['profile_id']}",
                "label": f"{p['description']} (Custom)",
                "uf": 3.5,  # Default Uf for custom steel profiles
                "source": "custom",
                "vendor": None,
            })

    return {"frame_types": merged_frames}
