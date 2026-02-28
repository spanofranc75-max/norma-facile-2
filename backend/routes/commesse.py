"""Commesse (Projects / Workshop Orders) — Kanban Planning routes."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/commesse", tags=["commesse"])
logger = logging.getLogger(__name__)
COLLECTION = "commesse"


# ── Enums & Models ───────────────────────────────────────────────

class CommessaStatus(str, Enum):
    PREVENTIVO = "preventivo"
    APPROVVIGIONAMENTO = "approvvigionamento"
    LAVORAZIONE = "lavorazione"
    CONTO_LAVORO = "conto_lavoro"
    PRONTO_CONSEGNA = "pronto_consegna"
    MONTAGGIO = "montaggio"
    COMPLETATO = "completato"


STATUS_META = {
    "preventivo":         {"label": "Nuove Commesse",     "order": 0},
    "approvvigionamento": {"label": "Approvvigionamento", "order": 1},
    "lavorazione":        {"label": "In Lavorazione",     "order": 2},
    "conto_lavoro":       {"label": "Conto Lavoro",       "order": 3},
    "pronto_consegna":    {"label": "Pronto / Consegna",  "order": 4},
    "montaggio":          {"label": "Montaggio / Posa",   "order": 5},
    "completato":         {"label": "Completato",         "order": 6},
}


class CommessaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    client_id: Optional[str] = None
    client_name: Optional[str] = ""
    description: Optional[str] = ""
    value: Optional[float] = 0
    deadline: Optional[str] = None
    status: CommessaStatus = CommessaStatus.PREVENTIVO
    priority: Optional[str] = "media"
    linked_preventivo_id: Optional[str] = None
    linked_distinta_id: Optional[str] = None
    linked_rilievo_id: Optional[str] = None
    notes: Optional[str] = ""


class CommessaUpdate(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    value: Optional[float] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


# ── CRUD ─────────────────────────────────────────────────────────

@router.get("/")
async def list_commesse(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if status:
        q["status"] = status
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
        ]
    items = await db[COLLECTION].find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items, "total": len(items)}


@router.post("/", status_code=201)
async def create_commessa(data: CommessaCreate, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    cid = f"com_{uuid.uuid4().hex[:12]}"

    # Auto-fill client name if client_id provided
    client_name = data.client_name or ""
    if data.client_id and not client_name:
        client = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0, "business_name": 1})
        client_name = client.get("business_name", "") if client else ""

    doc = {
        "commessa_id": cid,
        "user_id": uid,
        "title": data.title,
        "client_id": data.client_id or "",
        "client_name": client_name,
        "description": data.description or "",
        "value": float(data.value or 0),
        "deadline": data.deadline,
        "status": data.status.value,
        "priority": data.priority or "media",
        "linked_preventivo_id": data.linked_preventivo_id,
        "linked_distinta_id": data.linked_distinta_id,
        "linked_rilievo_id": data.linked_rilievo_id,
        "notes": data.notes or "",
        "status_history": [{"status": data.status.value, "date": now.isoformat(), "note": "Creazione"}],
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"commessa_id": cid}, {"_id": 0})
    return created


@router.get("/{commessa_id}")
async def get_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Commessa non trovata")
    return doc


@router.put("/{commessa_id}")
async def update_commessa(commessa_id: str, data: CommessaUpdate, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    existing = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not existing:
        raise HTTPException(404, "Commessa non trovata")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc)
    await db[COLLECTION].update_one({"commessa_id": commessa_id}, {"$set": updates})
    updated = await db[COLLECTION].find_one({"commessa_id": commessa_id}, {"_id": 0})
    return updated


@router.delete("/{commessa_id}")
async def delete_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one({"commessa_id": commessa_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Commessa non trovata")
    return {"message": "Commessa eliminata"}


# ── Kanban: Status Update (Drag & Drop) ─────────────────────────

@router.patch("/{commessa_id}/status")
async def update_commessa_status(
    commessa_id: str,
    new_status: str = Body(..., embed=True),
    user: dict = Depends(get_current_user),
):
    """Update commessa status — called on Kanban drag & drop."""
    uid = user["user_id"]
    if new_status not in STATUS_META:
        raise HTTPException(422, f"Stato non valido: {new_status}")

    existing = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not existing:
        raise HTTPException(404, "Commessa non trovata")

    now = datetime.now(timezone.utc)
    history_entry = {"status": new_status, "date": now.isoformat(), "note": f"Spostata a: {STATUS_META[new_status]['label']}"}

    await db[COLLECTION].update_one(
        {"commessa_id": commessa_id},
        {
            "$set": {"status": new_status, "updated_at": now},
            "$push": {"status_history": history_entry},
        },
    )
    updated = await db[COLLECTION].find_one({"commessa_id": commessa_id}, {"_id": 0})
    return updated


# ── Board View (grouped by status) ──────────────────────────────

@router.get("/board/view")
async def get_board_view(user: dict = Depends(get_current_user)):
    """Return all commesse grouped by status for the Kanban board."""
    uid = user["user_id"]
    items = await db[COLLECTION].find({"user_id": uid}, {"_id": 0}).sort("updated_at", -1).to_list(500)

    columns = {}
    for key, meta in STATUS_META.items():
        columns[key] = {
            "id": key,
            "label": meta["label"],
            "order": meta["order"],
            "items": [],
        }

    for item in items:
        st = item.get("status", "preventivo")
        if st in columns:
            columns[st]["items"].append(item)

    # Sort by order
    sorted_cols = sorted(columns.values(), key=lambda c: c["order"])
    return {"columns": sorted_cols, "total": len(items)}


# ── Quick Create from Preventivo ─────────────────────────────────

@router.post("/from-preventivo/{preventivo_id}")
async def create_commessa_from_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Create a commessa from an accepted Preventivo."""
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    client_name = ""
    if prev.get("client_id"):
        client = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1})
        client_name = client.get("business_name", "") if client else ""

    now = datetime.now(timezone.utc)
    cid = f"com_{uuid.uuid4().hex[:12]}"
    doc = {
        "commessa_id": cid,
        "user_id": uid,
        "title": prev.get("subject") or f"Commessa da {prev.get('number', preventivo_id)}",
        "client_id": prev.get("client_id", ""),
        "client_name": client_name,
        "description": prev.get("notes", ""),
        "value": float(prev.get("totals", {}).get("total", 0)),
        "deadline": None,
        "status": "preventivo",
        "priority": "media",
        "linked_preventivo_id": preventivo_id,
        "linked_distinta_id": None,
        "linked_rilievo_id": None,
        "notes": f"Generata da Preventivo {prev.get('number', '')}",
        "status_history": [{"status": "preventivo", "date": now.isoformat(), "note": f"Creata da preventivo {prev.get('number', '')}"}],
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"commessa_id": cid}, {"_id": 0})
    return created
