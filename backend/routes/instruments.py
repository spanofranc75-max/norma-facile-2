"""Routes for Registro Apparecchiature & Strumenti — isolated instrument/equipment registry."""
import uuid
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import db
from core.security import get_current_user
from models.instrument import InstrumentCreate, InstrumentResponse, InstrumentList

router = APIRouter(prefix="/instruments", tags=["instruments"])

VALID_TYPES = {"misura", "saldatura", "macchinario", "altro"}
VALID_STATUSES = {"attivo", "in_manutenzione", "fuori_uso", "scaduto"}


def _compute_status(doc: dict) -> tuple[str, int | None]:
    """Compute real-time status based on calibration expiry date.
    Returns (computed_status, days_until_expiry)."""
    base_status = doc.get("status", "attivo")
    if base_status in ("fuori_uso", "in_manutenzione"):
        return base_status, None

    next_cal = doc.get("next_calibration_date")
    if not next_cal:
        return base_status, None

    try:
        if isinstance(next_cal, str):
            exp_date = date.fromisoformat(next_cal)
        else:
            exp_date = next_cal
        today = date.today()
        delta = (exp_date - today).days

        if delta < 0:
            return "scaduto", delta
        if delta <= 30:
            return "in_scadenza", delta
        return "attivo", delta
    except (ValueError, TypeError):
        return base_status, None


def _doc_to_response(doc: dict) -> dict:
    computed, days = _compute_status(doc)
    return {
        "instrument_id": doc["instrument_id"],
        "name": doc["name"],
        "serial_number": doc["serial_number"],
        "type": doc.get("type", "altro"),
        "manufacturer": doc.get("manufacturer"),
        "purchase_date": doc.get("purchase_date"),
        "last_calibration_date": doc.get("last_calibration_date"),
        "next_calibration_date": doc.get("next_calibration_date"),
        "calibration_interval_months": doc.get("calibration_interval_months", 12),
        "status": doc.get("status", "attivo"),
        "computed_status": computed,
        "days_until_expiry": days,
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


def _compute_stats(docs: list[dict]) -> dict:
    total = len(docs)
    scaduti = 0
    in_scadenza = 0
    attivi = 0
    in_manutenzione = 0
    fuori_uso = 0

    for d in docs:
        cs, _ = _compute_status(d)
        if cs == "scaduto":
            scaduti += 1
        elif cs == "in_scadenza":
            in_scadenza += 1
        elif cs == "attivo":
            attivi += 1
        elif cs == "in_manutenzione":
            in_manutenzione += 1
        elif cs == "fuori_uso":
            fuori_uso += 1

    return {
        "total": total,
        "attivi": attivi,
        "in_scadenza": in_scadenza,
        "scaduti": scaduti,
        "in_manutenzione": in_manutenzione,
        "fuori_uso": fuori_uso,
    }


@router.get("/", response_model=InstrumentList)
async def list_instruments(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    query = {}
    if type and type in VALID_TYPES:
        query["type"] = type
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"serial_number": {"$regex": search, "$options": "i"}},
            {"manufacturer": {"$regex": search, "$options": "i"}},
        ]

    all_docs = await db.instruments.find({}, {"_id": 0}).sort("name", 1).to_list(500)
    stats = _compute_stats(all_docs)

    filtered = await db.instruments.find(query, {"_id": 0}).sort("name", 1).to_list(500)
    items = [_doc_to_response(d) for d in filtered]

    if status:
        items = [i for i in items if i["computed_status"] == status]

    return InstrumentList(items=items, total=len(items), stats=stats)


@router.post("/", response_model=InstrumentResponse)
async def create_instrument(
    payload: InstrumentCreate,
    user: dict = Depends(get_current_user),
):
    if payload.type not in VALID_TYPES:
        raise HTTPException(400, f"Tipo non valido. Validi: {VALID_TYPES}")

    instrument_id = f"inst_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "instrument_id": instrument_id,
        "name": payload.name.strip(),
        "serial_number": payload.serial_number.strip(),
        "type": payload.type,
        "manufacturer": payload.manufacturer or "",
        "purchase_date": payload.purchase_date or "",
        "last_calibration_date": payload.last_calibration_date or "",
        "next_calibration_date": payload.next_calibration_date or "",
        "calibration_interval_months": payload.calibration_interval_months or 12,
        "status": payload.status,
        "notes": payload.notes or "",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    await db.instruments.insert_one(doc)
    return InstrumentResponse(**_doc_to_response(doc))


@router.put("/{instrument_id}", response_model=InstrumentResponse)
async def update_instrument(
    instrument_id: str,
    payload: InstrumentCreate,
    user: dict = Depends(get_current_user),
):
    existing = await db.instruments.find_one({"instrument_id": instrument_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Strumento non trovato")

    now_iso = datetime.now(timezone.utc).isoformat()

    update = {
        "name": payload.name.strip(),
        "serial_number": payload.serial_number.strip(),
        "type": payload.type,
        "manufacturer": payload.manufacturer or "",
        "purchase_date": payload.purchase_date or "",
        "last_calibration_date": payload.last_calibration_date or "",
        "next_calibration_date": payload.next_calibration_date or "",
        "calibration_interval_months": payload.calibration_interval_months or 12,
        "status": payload.status,
        "notes": payload.notes or "",
        "updated_at": now_iso,
    }

    await db.instruments.update_one({"instrument_id": instrument_id}, {"$set": update})
    updated = await db.instruments.find_one({"instrument_id": instrument_id}, {"_id": 0})
    return InstrumentResponse(**_doc_to_response(updated))


@router.delete("/{instrument_id}")
async def delete_instrument(instrument_id: str, user: dict = Depends(get_current_user)):
    existing = await db.instruments.find_one({"instrument_id": instrument_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Strumento non trovato")

    await db.instruments.delete_one({"instrument_id": instrument_id})
    return {"message": "Strumento eliminato", "instrument_id": instrument_id}
