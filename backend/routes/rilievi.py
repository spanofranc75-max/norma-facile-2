"""Rilievo (On-Site Survey) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from io import BytesIO
import uuid
import base64
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.rilievo import (
    RilievoCreate, RilievoUpdate, RilievoResponse, RilievoListResponse,
    RilievoStatus, SketchData, PhotoData
)
from services.rilievo_pdf_service import rilievo_pdf_service
from services.audit_trail import log_activity
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rilievi", tags=["rilievi"])


@router.get("/", response_model=RilievoListResponse)
async def get_rilievi(
    client_id: Optional[str] = None,
    status: Optional[RilievoStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get all rilievi for current user with optional filters."""
    query = {"user_id": user["user_id"]}
    
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status.value
    
    total = await db.rilievi.count_documents(query)
    
    rilievi_cursor = db.rilievi.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    rilievi = await rilievi_cursor.to_list(length=limit)
    
    # Populate client names
    for rilievo in rilievi:
        client = await db.clients.find_one(
            {"client_id": rilievo.get("client_id")},
            {"_id": 0, "business_name": 1}
        )
        rilievo["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoListResponse(
        rilievi=[RilievoResponse(**r) for r in rilievi],
        total=total
    )


@router.get("/{rilievo_id}", response_model=RilievoResponse)
async def get_rilievo(
    rilievo_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific rilievo by ID."""
    rilievo = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": rilievo.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    rilievo["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**rilievo)


@router.post("/", response_model=RilievoResponse, status_code=201)
async def create_rilievo(
    rilievo_data: RilievoCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new rilievo."""
    # Verify client exists
    client = await db.clients.find_one(
        {"client_id": rilievo_data.client_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    rilievo_id = f"ril_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Process sketches - add IDs and timestamps
    sketches = []
    for sketch in rilievo_data.sketches:
        sketch_dict = sketch.model_dump()
        sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
        sketch_dict["created_at"] = now
        sketches.append(sketch_dict)
    
    # Process photos - add IDs and timestamps
    photos = []
    for photo in rilievo_data.photos:
        photo_dict = photo.model_dump()
        photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
        photo_dict["created_at"] = now
        photos.append(photo_dict)
    
    rilievo_doc = {
        "rilievo_id": rilievo_id,
        "user_id": user["user_id"],
        "client_id": rilievo_data.client_id,
        "project_name": rilievo_data.project_name,
        "survey_date": rilievo_data.survey_date.isoformat(),
        "location": rilievo_data.location,
        "status": RilievoStatus.BOZZA.value,
        "sketches": sketches,
        "photos": photos,
        "notes": rilievo_data.notes,
        "created_at": now,
        "updated_at": now
    }
    
    await db.rilievi.insert_one(rilievo_doc)
    
    created = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    created["client_name"] = client.get("business_name")
    
    logger.info(f"Rilievo created: {rilievo_id} by user {user['user_id']}")
    await log_activity(user, "create", "rilievo", rilievo_id, label=rilievo_data.project_name)
    return RilievoResponse(**created)


@router.put("/{rilievo_id}", response_model=RilievoResponse)
async def update_rilievo(
    rilievo_id: str,
    rilievo_data: RilievoUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    update_dict = {}
    now = datetime.now(timezone.utc)
    
    # Update client if changed
    if rilievo_data.client_id:
        client = await db.clients.find_one(
            {"client_id": rilievo_data.client_id, "user_id": user["user_id"]}
        )
        if not client:
            raise HTTPException(status_code=400, detail="Cliente non trovato")
        update_dict["client_id"] = rilievo_data.client_id
    
    # Update simple fields
    if rilievo_data.project_name is not None:
        update_dict["project_name"] = rilievo_data.project_name
    if rilievo_data.survey_date is not None:
        update_dict["survey_date"] = rilievo_data.survey_date.isoformat()
    if rilievo_data.location is not None:
        update_dict["location"] = rilievo_data.location
    if rilievo_data.notes is not None:
        update_dict["notes"] = rilievo_data.notes
    if rilievo_data.status is not None:
        update_dict["status"] = rilievo_data.status.value
    
    # Update sketches
    if rilievo_data.sketches is not None:
        sketches = []
        for sketch in rilievo_data.sketches:
            sketch_dict = sketch.model_dump()
            if not sketch_dict.get("sketch_id"):
                sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
                sketch_dict["created_at"] = now
            sketches.append(sketch_dict)
        update_dict["sketches"] = sketches
    
    # Update photos
    if rilievo_data.photos is not None:
        photos = []
        for photo in rilievo_data.photos:
            photo_dict = photo.model_dump()
            if not photo_dict.get("photo_id"):
                photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
                photo_dict["created_at"] = now
            photos.append(photo_dict)
        update_dict["photos"] = photos
    
    update_dict["updated_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {"$set": update_dict}
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Rilievo updated: {rilievo_id}")
    await log_activity(user, "update", "rilievo", rilievo_id, label=updated.get("project_name", ""))
    return RilievoResponse(**updated)


@router.delete("/{rilievo_id}")
async def delete_rilievo(
    rilievo_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a rilievo."""
    result = await db.rilievi.delete_one({
        "rilievo_id": rilievo_id,
        "user_id": user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    logger.info(f"Rilievo deleted: {rilievo_id}")
    await log_activity(user, "delete", "rilievo", rilievo_id)
    return {"message": "Rilievo eliminato con successo"}


@router.post("/{rilievo_id}/sketch", response_model=RilievoResponse)
async def add_sketch(
    rilievo_id: str,
    sketch: SketchData,
    user: dict = Depends(get_current_user)
):
    """Add a sketch to an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    now = datetime.now(timezone.utc)
    sketch_dict = sketch.model_dump()
    sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
    sketch_dict["created_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"sketches": sketch_dict},
            "$set": {"updated_at": now}
        }
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**updated)


@router.post("/{rilievo_id}/photo", response_model=RilievoResponse)
async def add_photo(
    rilievo_id: str,
    photo: PhotoData,
    user: dict = Depends(get_current_user)
):
    """Add a photo to an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    now = datetime.now(timezone.utc)
    photo_dict = photo.model_dump()
    photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
    photo_dict["created_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"photos": photo_dict},
            "$set": {"updated_at": now}
        }
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**updated)


@router.get("/{rilievo_id}/pdf")
async def get_rilievo_pdf(
    rilievo_id: str,
    user: dict = Depends(get_current_user)
):
    """Generate and download rilievo PDF summary."""
    rilievo = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    client = await db.clients.find_one(
        {"client_id": rilievo.get("client_id")},
        {"_id": 0}
    )
    if not client:
        client = {"business_name": "N/A"}
    
    # Get company settings for header
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    if not company:
        company = {"business_name": user.get("name", "")}
    
    # Generate PDF
    pdf_bytes = rilievo_pdf_service.generate_rilievo_pdf(rilievo, client, company)
    
    # Create filename
    project_name = rilievo.get("project_name", "rilievo").replace(" ", "_")
    filename = f"Rilievo_{project_name}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
