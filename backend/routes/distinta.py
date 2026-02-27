"""Distinta Materiali (Bill of Materials) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.distinta import (
    DistintaCreate, DistintaUpdate, DistintaResponse, DistintaListResponse,
    DistintaStatus, DistintaTotals, MaterialItem
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/distinte", tags=["distinte"])


def calculate_item(item: dict) -> dict:
    """Calculate totals for a single item."""
    quantity = item.get("quantity", 1)
    length_mm = item.get("length_mm", 0)
    weight_per_unit = item.get("weight_per_unit", 0)
    cost_per_unit = item.get("cost_per_unit", 0)
    unit = item.get("unit", "pz")
    
    # Calculate total length
    if unit == "m":
        total_length = quantity  # Already in meters
    else:
        total_length = (length_mm * quantity) / 1000  # Convert to meters
    
    # Calculate weight and cost
    if unit == "m":
        total_weight = weight_per_unit * quantity
        total_cost = cost_per_unit * quantity
    elif unit == "m²":
        # For sheets: weight/cost per m²
        width_mm = item.get("width_mm", 0)
        area_m2 = (length_mm * width_mm) / 1_000_000 * quantity
        total_weight = weight_per_unit * area_m2
        total_cost = cost_per_unit * area_m2
    else:
        # Per piece
        total_weight = weight_per_unit * quantity
        total_cost = cost_per_unit * quantity
    
    item["total_length"] = round(total_length, 3)
    item["total_weight"] = round(total_weight, 3)
    item["total_cost"] = round(total_cost, 2)
    
    return item


def calculate_totals(items: List[dict]) -> DistintaTotals:
    """Calculate overall totals for the BOM."""
    total_length = 0
    total_weight = 0
    total_cost = 0
    by_category = {}
    
    for item in items:
        category = item.get("category", "altro")
        
        total_length += item.get("total_length", 0)
        total_weight += item.get("total_weight", 0)
        total_cost += item.get("total_cost", 0)
        
        if category not in by_category:
            by_category[category] = {"count": 0, "weight": 0, "cost": 0}
        
        by_category[category]["count"] += 1
        by_category[category]["weight"] += item.get("total_weight", 0)
        by_category[category]["cost"] += item.get("total_cost", 0)
    
    # Round category totals
    for cat in by_category:
        by_category[cat]["weight"] = round(by_category[cat]["weight"], 3)
        by_category[cat]["cost"] = round(by_category[cat]["cost"], 2)
    
    return DistintaTotals(
        total_items=len(items),
        total_length_m=round(total_length, 3),
        total_weight_kg=round(total_weight, 3),
        total_cost=round(total_cost, 2),
        by_category=by_category
    )


@router.get("/", response_model=DistintaListResponse)
async def get_distinte(
    rilievo_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[DistintaStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get all distinte for current user with optional filters."""
    query = {"user_id": user["user_id"]}
    
    if rilievo_id:
        query["rilievo_id"] = rilievo_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status.value
    
    total = await db.distinte.count_documents(query)
    
    distinte_cursor = db.distinte.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    distinte = await distinte_cursor.to_list(length=limit)
    
    # Populate names
    for distinta in distinte:
        if distinta.get("rilievo_id"):
            rilievo = await db.rilievi.find_one(
                {"rilievo_id": distinta["rilievo_id"]},
                {"_id": 0, "project_name": 1}
            )
            distinta["rilievo_name"] = rilievo.get("project_name") if rilievo else None
        
        if distinta.get("client_id"):
            client = await db.clients.find_one(
                {"client_id": distinta["client_id"]},
                {"_id": 0, "business_name": 1}
            )
            distinta["client_name"] = client.get("business_name") if client else None
    
    return DistintaListResponse(
        distinte=[DistintaResponse(**d) for d in distinte],
        total=total
    )


@router.get("/{distinta_id}", response_model=DistintaResponse)
async def get_distinta(
    distinta_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific distinta by ID."""
    distinta = await db.distinte.find_one(
        {"distinta_id": distinta_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not distinta:
        raise HTTPException(status_code=404, detail="Distinta non trovata")
    
    # Populate names
    if distinta.get("rilievo_id"):
        rilievo = await db.rilievi.find_one(
            {"rilievo_id": distinta["rilievo_id"]},
            {"_id": 0, "project_name": 1}
        )
        distinta["rilievo_name"] = rilievo.get("project_name") if rilievo else None
    
    if distinta.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": distinta["client_id"]},
            {"_id": 0, "business_name": 1}
        )
        distinta["client_name"] = client.get("business_name") if client else None
    
    return DistintaResponse(**distinta)


@router.post("/", response_model=DistintaResponse, status_code=201)
async def create_distinta(
    distinta_data: DistintaCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new distinta."""
    distinta_id = f"dist_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Process items and calculate totals
    processed_items = []
    for item in distinta_data.items:
        item_dict = item.model_dump()
        if not item_dict.get("item_id"):
            item_dict["item_id"] = f"item_{uuid.uuid4().hex[:8]}"
        processed_items.append(calculate_item(item_dict))
    
    totals = calculate_totals(processed_items)
    
    distinta_doc = {
        "distinta_id": distinta_id,
        "user_id": user["user_id"],
        "name": distinta_data.name,
        "rilievo_id": distinta_data.rilievo_id,
        "client_id": distinta_data.client_id,
        "status": DistintaStatus.BOZZA.value,
        "items": processed_items,
        "totals": totals.model_dump(),
        "notes": distinta_data.notes,
        "created_at": now,
        "updated_at": now
    }
    
    await db.distinte.insert_one(distinta_doc)
    
    created = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    
    # Populate names
    if created.get("rilievo_id"):
        rilievo = await db.rilievi.find_one(
            {"rilievo_id": created["rilievo_id"]},
            {"_id": 0, "project_name": 1}
        )
        created["rilievo_name"] = rilievo.get("project_name") if rilievo else None
    
    if created.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": created["client_id"]},
            {"_id": 0, "business_name": 1}
        )
        created["client_name"] = client.get("business_name") if client else None
    
    logger.info(f"Distinta created: {distinta_id} by user {user['user_id']}")
    return DistintaResponse(**created)


@router.put("/{distinta_id}", response_model=DistintaResponse)
async def update_distinta(
    distinta_id: str,
    distinta_data: DistintaUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing distinta."""
    existing = await db.distinte.find_one(
        {"distinta_id": distinta_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Distinta non trovata")
    
    update_dict = {}
    now = datetime.now(timezone.utc)
    
    # Update simple fields
    if distinta_data.name is not None:
        update_dict["name"] = distinta_data.name
    if distinta_data.rilievo_id is not None:
        update_dict["rilievo_id"] = distinta_data.rilievo_id
    if distinta_data.client_id is not None:
        update_dict["client_id"] = distinta_data.client_id
    if distinta_data.status is not None:
        update_dict["status"] = distinta_data.status.value
    if distinta_data.notes is not None:
        update_dict["notes"] = distinta_data.notes
    
    # Update items and recalculate totals
    if distinta_data.items is not None:
        processed_items = []
        for item in distinta_data.items:
            item_dict = item.model_dump()
            if not item_dict.get("item_id"):
                item_dict["item_id"] = f"item_{uuid.uuid4().hex[:8]}"
            processed_items.append(calculate_item(item_dict))
        
        update_dict["items"] = processed_items
        update_dict["totals"] = calculate_totals(processed_items).model_dump()
    
    update_dict["updated_at"] = now
    
    await db.distinte.update_one(
        {"distinta_id": distinta_id},
        {"$set": update_dict}
    )
    
    updated = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    
    # Populate names
    if updated.get("rilievo_id"):
        rilievo = await db.rilievi.find_one(
            {"rilievo_id": updated["rilievo_id"]},
            {"_id": 0, "project_name": 1}
        )
        updated["rilievo_name"] = rilievo.get("project_name") if rilievo else None
    
    if updated.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": updated["client_id"]},
            {"_id": 0, "business_name": 1}
        )
        updated["client_name"] = client.get("business_name") if client else None
    
    logger.info(f"Distinta updated: {distinta_id}")
    return DistintaResponse(**updated)


@router.delete("/{distinta_id}")
async def delete_distinta(
    distinta_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a distinta."""
    result = await db.distinte.delete_one({
        "distinta_id": distinta_id,
        "user_id": user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Distinta non trovata")
    
    logger.info(f"Distinta deleted: {distinta_id}")
    return {"message": "Distinta eliminata con successo"}


@router.post("/{distinta_id}/import-rilievo/{rilievo_id}", response_model=DistintaResponse)
async def import_from_rilievo(
    distinta_id: str,
    rilievo_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Import data from a Rilievo into the Distinta.
    MOCK: This is a placeholder. Real implementation will parse
    sketches and dimensions to suggest materials.
    """
    # Verify distinta exists
    distinta = await db.distinte.find_one(
        {"distinta_id": distinta_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not distinta:
        raise HTTPException(status_code=404, detail="Distinta non trovata")
    
    # Verify rilievo exists
    rilievo = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    # MOCK: Create sample items based on rilievo sketches
    # In real implementation, this would analyze dimensions and suggest profiles
    mock_items = []
    
    for i, sketch in enumerate(rilievo.get("sketches", [])):
        dims = sketch.get("dimensions", {})
        width = float(dims.get("width", 0) or 0)
        height = float(dims.get("height", 0) or 0)
        
        if width > 0:
            mock_items.append({
                "item_id": f"item_{uuid.uuid4().hex[:8]}",
                "category": "profilo",
                "code": f"PRF-{i+1:03d}",
                "name": f"Profilo da {sketch.get('name', f'Schizzo {i+1}')}",
                "description": "Importato da rilievo",
                "length_mm": width * 10,  # cm to mm
                "quantity": 2,  # Top and bottom
                "unit": "pz",
                "weight_per_unit": 0.5,
                "cost_per_unit": 5.0,
                "notes": f"Dimensioni: {width}x{height}cm"
            })
        
        if height > 0:
            mock_items.append({
                "item_id": f"item_{uuid.uuid4().hex[:8]}",
                "category": "profilo",
                "code": f"PRF-{i+1:03d}V",
                "name": f"Montante da {sketch.get('name', f'Schizzo {i+1}')}",
                "description": "Importato da rilievo",
                "length_mm": height * 10,  # cm to mm
                "quantity": 2,  # Left and right
                "unit": "pz",
                "weight_per_unit": 0.5,
                "cost_per_unit": 5.0,
                "notes": f"Dimensioni: {width}x{height}cm"
            })
    
    # Calculate totals for mock items
    processed_items = [calculate_item(item) for item in mock_items]
    
    # Add to existing items
    existing_items = distinta.get("items", [])
    all_items = existing_items + processed_items
    
    totals = calculate_totals(all_items)
    
    # Update distinta
    await db.distinte.update_one(
        {"distinta_id": distinta_id},
        {"$set": {
            "rilievo_id": rilievo_id,
            "client_id": rilievo.get("client_id"),
            "items": all_items,
            "totals": totals.model_dump(),
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    updated = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    updated["rilievo_name"] = rilievo.get("project_name")
    
    if rilievo.get("client_id"):
        client = await db.clients.find_one(
            {"client_id": rilievo["client_id"]},
            {"_id": 0, "business_name": 1}
        )
        updated["client_name"] = client.get("business_name") if client else None
    
    logger.info(f"Imported {len(mock_items)} items from rilievo {rilievo_id} to distinta {distinta_id}")
    return DistintaResponse(**updated)
