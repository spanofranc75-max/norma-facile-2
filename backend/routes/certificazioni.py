"""Certificazioni CE (EN 1090 / EN 13241) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.certificazione import (
    CertificazioneCreate, CertificazioneUpdate, CertificazioneResponse,
    CertificazioneListResponse, CertStatus,
)
from services.certificazione_pdf_service import generate_dop_ce_pdf
from core.engine.thermal import ThermalValidator, ThermalInput
from core.engine.ce import CEValidator
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/certificazioni", tags=["certificazioni"])


async def _populate_names(doc: dict):
    if doc.get("distinta_id"):
        d = await db.distinte.find_one({"distinta_id": doc["distinta_id"]}, {"_id": 0, "name": 1})
        doc["distinta_name"] = d.get("name") if d else None
    if doc.get("client_id"):
        c = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = c.get("business_name") if c else None


def _gen_declaration_number(standard: str) -> str:
    year = datetime.now().strftime("%Y")
    uid = uuid.uuid4().hex[:6].upper()
    prefix = "DOP" if "1090" in standard else "DOP-G"
    return f"{prefix}-{year}-{uid}"


@router.get("/", response_model=CertificazioneListResponse)
async def get_certificazioni(
    status: Optional[CertStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status.value

    total = await db.certificazioni.count_documents(query)
    cursor = db.certificazioni.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    certs = await cursor.to_list(length=limit)

    for c in certs:
        await _populate_names(c)

    return CertificazioneListResponse(
        certificazioni=[CertificazioneResponse(**c) for c in certs],
        total=total,
    )


@router.get("/{cert_id}", response_model=CertificazioneResponse)
async def get_certificazione(cert_id: str, user: dict = Depends(get_current_user)):
    doc = await db.certificazioni.find_one({"cert_id": cert_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Certificazione non trovata")
    await _populate_names(doc)
    return CertificazioneResponse(**doc)


@router.post("/", response_model=CertificazioneResponse, status_code=201)
async def create_certificazione(data: CertificazioneCreate, user: dict = Depends(get_current_user)):
    cert_id = f"cert_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc = {
        "cert_id": cert_id,
        "user_id": user["user_id"],
        "project_name": data.project_name,
        "distinta_id": data.distinta_id,
        "client_id": data.client_id,
        "standard": data.standard.value,
        "product_description": data.product_description,
        "product_type": data.product_type,
        "declaration_number": _gen_declaration_number(data.standard.value),
        "technical_specs": data.technical_specs.model_dump(),
        "status": CertStatus.BOZZA.value,
        "notes": data.notes,
        "created_at": now,
        "updated_at": now,
    }
    await db.certificazioni.insert_one(doc)

    created = await db.certificazioni.find_one({"cert_id": cert_id}, {"_id": 0})
    await _populate_names(created)
    logger.info(f"Certificazione created: {cert_id}")
    return CertificazioneResponse(**created)


@router.put("/{cert_id}", response_model=CertificazioneResponse)
async def update_certificazione(cert_id: str, data: CertificazioneUpdate, user: dict = Depends(get_current_user)):
    existing = await db.certificazioni.find_one({"cert_id": cert_id, "user_id": user["user_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Certificazione non trovata")

    upd = {}
    for field in ["project_name", "distinta_id", "client_id", "product_description", "product_type", "notes"]:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val
    if data.standard is not None:
        upd["standard"] = data.standard.value
    if data.status is not None:
        upd["status"] = data.status.value
    if data.technical_specs is not None:
        upd["technical_specs"] = data.technical_specs.model_dump()

    upd["updated_at"] = datetime.now(timezone.utc)
    await db.certificazioni.update_one({"cert_id": cert_id}, {"$set": upd})

    updated = await db.certificazioni.find_one({"cert_id": cert_id}, {"_id": 0})
    await _populate_names(updated)
    logger.info(f"Certificazione updated: {cert_id}")
    return CertificazioneResponse(**updated)


@router.delete("/{cert_id}")
async def delete_certificazione(cert_id: str, user: dict = Depends(get_current_user)):
    result = await db.certificazioni.delete_one({"cert_id": cert_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Certificazione non trovata")
    logger.info(f"Certificazione deleted: {cert_id}")
    return {"message": "Certificazione eliminata con successo"}


@router.get("/{cert_id}/fascicolo-pdf")
async def get_fascicolo_pdf(cert_id: str, user: dict = Depends(get_current_user)):
    """Generate DOP + CE Label PDF. Validates before generating."""
    doc = await db.certificazioni.find_one({"cert_id": cert_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Certificazione non trovata")

    # Validate before generating
    validation = CEValidator.validate(
        standard=doc.get("standard", ""),
        product_type=doc.get("product_type", ""),
        technical_specs=doc.get("technical_specs", {}),
        project_name=doc.get("project_name", ""),
    )
    if not validation.valid:
        raise HTTPException(422, detail=f"Certificazione incompleta: {'; '.join(validation.errors)}")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})

    pdf_buffer = generate_dop_ce_pdf(doc, company)
    filename = f"fascicolo_CE_{doc.get('project_name', cert_id).replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Thermal Calculator ───────────────────────────────────────────

@router.get("/thermal/reference-data")
async def get_thermal_reference_data():
    """Get glass, frame, spacer types and zone limits for thermal calculator."""
    return ThermalValidator.get_reference_data()


@router.post("/thermal/calculate")
async def calculate_thermal(inp: ThermalInput):
    """Calculate Uw thermal transmittance."""
    result = ThermalValidator.calculate(inp)
    return result.model_dump()


# ── CE Validation ────────────────────────────────────────────────

@router.post("/{cert_id}/validate")
async def validate_certificazione(cert_id: str, user: dict = Depends(get_current_user)):
    """Validate a certification before PDF generation."""
    doc = await db.certificazioni.find_one({"cert_id": cert_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Certificazione non trovata")

    result = CEValidator.validate(
        standard=doc.get("standard", ""),
        product_type=doc.get("product_type", ""),
        technical_specs=doc.get("technical_specs", {}),
        project_name=doc.get("project_name", ""),
    )
    return result.model_dump()
