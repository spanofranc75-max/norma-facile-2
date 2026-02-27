"""Distinta Materiali (Smart BOM for Fabbri) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.distinta import (
    DistintaCreate, DistintaUpdate, DistintaResponse, DistintaListResponse,
    DistintaStatus, DistintaTotals, MaterialItem, BarCalculationResponse, BarCalculationResult
)
from services.profiles_data import (
    STANDARD_PROFILES, PROFILE_TYPES,
    get_profiles_by_type, get_profile_by_id, calculate_bars_needed,
)
from services.distinta_pdf_service import generate_cutting_list_pdf
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/distinte", tags=["distinte"])


# ── Calculation helpers ──────────────────────────────────────────

def calculate_item(item: dict) -> dict:
    """Calculate weight, surface, and cost for a single item."""
    quantity = float(item.get("quantity", 1))
    length_mm = float(item.get("length_mm", 0))
    length_m = length_mm / 1000

    weight_per_meter = float(item.get("weight_per_meter", 0))
    surface_per_meter = float(item.get("surface_per_meter", 0))
    cost_per_unit = float(item.get("cost_per_unit", 0))

    # Fallback: legacy weight_per_unit
    if weight_per_meter == 0 and item.get("weight_per_unit", 0) > 0:
        weight_per_meter = float(item["weight_per_unit"])

    total_length = length_m * quantity
    total_weight = length_m * quantity * weight_per_meter
    total_surface = length_m * quantity * surface_per_meter
    total_cost = cost_per_unit * quantity

    item["total_length"] = round(total_length, 3)
    item["total_weight"] = round(total_weight, 3)
    item["total_surface"] = round(total_surface, 3)
    item["total_cost"] = round(total_cost, 2)
    return item


def calculate_totals(items: List[dict]) -> DistintaTotals:
    """Calculate overall totals for the BOM."""
    total_length = total_weight = total_surface = total_cost = 0
    by_category = {}

    for item in items:
        cat = item.get("category", "altro")
        total_length += item.get("total_length", 0)
        total_weight += item.get("total_weight", 0)
        total_surface += item.get("total_surface", 0)
        total_cost += item.get("total_cost", 0)

        if cat not in by_category:
            by_category[cat] = {"count": 0, "weight": 0, "surface": 0, "cost": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["weight"] += item.get("total_weight", 0)
        by_category[cat]["surface"] += item.get("total_surface", 0)
        by_category[cat]["cost"] += item.get("total_cost", 0)

    for cat in by_category:
        by_category[cat]["weight"] = round(by_category[cat]["weight"], 3)
        by_category[cat]["surface"] = round(by_category[cat]["surface"], 3)
        by_category[cat]["cost"] = round(by_category[cat]["cost"], 2)

    return DistintaTotals(
        total_items=len(items),
        total_length_m=round(total_length, 3),
        total_weight_kg=round(total_weight, 3),
        total_surface_mq=round(total_surface, 3),
        total_cost=round(total_cost, 2),
        by_category=by_category,
    )


# ── Profiles ─────────────────────────────────────────────────────

@router.get("/profiles")
async def get_profiles(profile_type: Optional[str] = None):
    """Get standard metal profiles catalog."""
    profiles = get_profiles_by_type(profile_type)
    return {"profiles": profiles, "types": PROFILE_TYPES}


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """Get a single profile."""
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(404, "Profilo non trovato")
    return profile


# ── CRUD ─────────────────────────────────────────────────────────

async def _populate_names(doc: dict):
    if doc.get("rilievo_id"):
        r = await db.rilievi.find_one({"rilievo_id": doc["rilievo_id"]}, {"_id": 0, "project_name": 1})
        doc["rilievo_name"] = r.get("project_name") if r else None
    if doc.get("client_id"):
        c = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = c.get("business_name") if c else None


@router.get("/", response_model=DistintaListResponse)
async def get_distinte(
    rilievo_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[DistintaStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["user_id"]}
    if rilievo_id:
        query["rilievo_id"] = rilievo_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status.value

    total = await db.distinte.count_documents(query)
    cursor = db.distinte.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    distinte = await cursor.to_list(length=limit)

    for d in distinte:
        await _populate_names(d)

    return DistintaListResponse(distinte=[DistintaResponse(**d) for d in distinte], total=total)


@router.get("/{distinta_id}", response_model=DistintaResponse)
async def get_distinta(distinta_id: str, user: dict = Depends(get_current_user)):
    doc = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Distinta non trovata")
    await _populate_names(doc)
    return DistintaResponse(**doc)


@router.post("/", response_model=DistintaResponse, status_code=201)
async def create_distinta(data: DistintaCreate, user: dict = Depends(get_current_user)):
    distinta_id = f"dist_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    processed = []
    for item in data.items:
        d = item.model_dump()
        if not d.get("item_id"):
            d["item_id"] = f"item_{uuid.uuid4().hex[:8]}"
        processed.append(calculate_item(d))

    totals = calculate_totals(processed)

    doc = {
        "distinta_id": distinta_id,
        "user_id": user["user_id"],
        "name": data.name,
        "rilievo_id": data.rilievo_id,
        "client_id": data.client_id,
        "status": DistintaStatus.BOZZA.value,
        "items": processed,
        "totals": totals.model_dump(),
        "notes": data.notes,
        "created_at": now,
        "updated_at": now,
    }
    await db.distinte.insert_one(doc)

    created = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    await _populate_names(created)
    logger.info(f"Distinta created: {distinta_id}")
    return DistintaResponse(**created)


@router.put("/{distinta_id}", response_model=DistintaResponse)
async def update_distinta(distinta_id: str, data: DistintaUpdate, user: dict = Depends(get_current_user)):
    existing = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": user["user_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Distinta non trovata")

    upd = {}
    if data.name is not None:
        upd["name"] = data.name
    if data.rilievo_id is not None:
        upd["rilievo_id"] = data.rilievo_id
    if data.client_id is not None:
        upd["client_id"] = data.client_id
    if data.status is not None:
        upd["status"] = data.status.value
    if data.notes is not None:
        upd["notes"] = data.notes

    if data.items is not None:
        processed = []
        for item in data.items:
            d = item.model_dump()
            if not d.get("item_id"):
                d["item_id"] = f"item_{uuid.uuid4().hex[:8]}"
            processed.append(calculate_item(d))
        upd["items"] = processed
        upd["totals"] = calculate_totals(processed).model_dump()

    upd["updated_at"] = datetime.now(timezone.utc)
    await db.distinte.update_one({"distinta_id": distinta_id}, {"$set": upd})

    updated = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    await _populate_names(updated)
    logger.info(f"Distinta updated: {distinta_id}")
    return DistintaResponse(**updated)


@router.delete("/{distinta_id}")
async def delete_distinta(distinta_id: str, user: dict = Depends(get_current_user)):
    result = await db.distinte.delete_one({"distinta_id": distinta_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Distinta non trovata")
    logger.info(f"Distinta deleted: {distinta_id}")
    return {"message": "Distinta eliminata con successo"}


# ── Import from Rilievo ──────────────────────────────────────────

@router.post("/{distinta_id}/import-rilievo/{rilievo_id}", response_model=DistintaResponse)
async def import_from_rilievo(distinta_id: str, rilievo_id: str, user: dict = Depends(get_current_user)):
    distinta = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": user["user_id"]}, {"_id": 0})
    if not distinta:
        raise HTTPException(404, "Distinta non trovata")

    rilievo = await db.rilievi.find_one({"rilievo_id": rilievo_id, "user_id": user["user_id"]}, {"_id": 0})
    if not rilievo:
        raise HTTPException(404, "Rilievo non trovato")

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
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": width * 10,
                "quantity": 2,
                "unit": "pz",
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160,
                "cost_per_unit": 0,
            })
        if height > 0:
            mock_items.append({
                "item_id": f"item_{uuid.uuid4().hex[:8]}",
                "category": "profilo",
                "code": f"PRF-{i+1:03d}V",
                "name": f"Montante da {sketch.get('name', f'Schizzo {i+1}')}",
                "profile_id": "TQ-40x40x3",
                "profile_label": "Tubolare 40x40x3",
                "length_mm": height * 10,
                "quantity": 2,
                "unit": "pz",
                "weight_per_meter": 3.39,
                "surface_per_meter": 0.160,
                "cost_per_unit": 0,
            })

    processed = [calculate_item(item) for item in mock_items]
    all_items = distinta.get("items", []) + processed
    totals = calculate_totals(all_items)

    await db.distinte.update_one(
        {"distinta_id": distinta_id},
        {"$set": {
            "rilievo_id": rilievo_id,
            "client_id": rilievo.get("client_id"),
            "items": all_items,
            "totals": totals.model_dump(),
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    updated = await db.distinte.find_one({"distinta_id": distinta_id}, {"_id": 0})
    await _populate_names(updated)
    logger.info(f"Imported {len(mock_items)} items from rilievo {rilievo_id}")
    return DistintaResponse(**updated)


# ── Bar Calculation ──────────────────────────────────────────────

@router.post("/{distinta_id}/calcola-barre", response_model=BarCalculationResponse)
async def calcola_barre(distinta_id: str, user: dict = Depends(get_current_user)):
    """Calculate how many 6m bars are needed for each profile."""
    doc = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Distinta non trovata")

    items = doc.get("items", [])
    results = calculate_bars_needed(items)
    total_bars = sum(r["bars_needed"] for r in results)

    return BarCalculationResponse(
        results=[BarCalculationResult(**r) for r in results],
        total_bars=total_bars,
    )


# ── PDF: Lista Taglio ────────────────────────────────────────────

@router.get("/{distinta_id}/lista-taglio-pdf")
async def get_lista_taglio_pdf(distinta_id: str, user: dict = Depends(get_current_user)):
    """Generate and download the cutting list PDF for the workshop."""
    doc = await db.distinte.find_one({"distinta_id": distinta_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Distinta non trovata")

    bar_results = calculate_bars_needed(doc.get("items", []))
    pdf_buffer = generate_cutting_list_pdf(doc, bar_results)

    filename = f"lista_taglio_{doc.get('name', distinta_id).replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
