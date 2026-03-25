"""Routes for Audit & Non-Conformity module — isolated audit and NC registry."""
import uuid
import os
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from core.database import db
from core.security import get_current_user, tenant_match
from models.audit import (
    AuditCreate, AuditResponse, AuditList,
    NCCreate, NCUpdate, NCResponse, NCList,
)

router = APIRouter(tags=["audits"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "audit_reports")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ──

def _audit_to_response(doc: dict, ncs: list[dict] | None = None) -> dict:
    nc_list = ncs or []
    linked = [n for n in nc_list if n.get("audit_id") == doc["audit_id"]]
    return {
        "audit_id": doc["audit_id"],
        "date": doc.get("date", ""),
        "audit_type": doc.get("audit_type", "interno"),
        "auditor_name": doc.get("auditor_name", ""),
        "scope": doc.get("scope"),
        "outcome": doc.get("outcome", "positivo"),
        "notes": doc.get("notes"),
        "next_audit_date": doc.get("next_audit_date"),
        "has_report": bool(doc.get("safe_filename")),
        "report_filename": doc.get("report_filename"),
        "nc_count": len(linked),
        "nc_open": sum(1 for n in linked if n.get("status") != "chiusa"),
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


def _nc_to_response(doc: dict, audit_map: dict | None = None) -> dict:
    days_open = None
    try:
        open_date = date.fromisoformat(doc.get("date", ""))
        if doc.get("status") == "chiusa" and doc.get("closure_date"):
            close_date = date.fromisoformat(doc["closure_date"])
            days_open = (close_date - open_date).days
        else:
            days_open = (date.today() - open_date).days
    except (ValueError, TypeError):
        pass

    audit_ref = None
    if doc.get("audit_id") and audit_map:
        audit = audit_map.get(doc["audit_id"])
        if audit:
            audit_ref = f"{audit.get('date','')} - {audit.get('auditor_name','')}"

    return {
        "nc_id": doc["nc_id"],
        "nc_number": doc.get("nc_number", ""),
        "date": doc.get("date", ""),
        "description": doc.get("description", ""),
        "source": doc.get("source"),
        "cause": doc.get("cause"),
        "corrective_action": doc.get("corrective_action"),
        "preventive_action": doc.get("preventive_action"),
        "priority": doc.get("priority", "media"),
        "status": doc.get("status", "aperta"),
        "audit_id": doc.get("audit_id"),
        "audit_ref": audit_ref,
        "commessa_ref": doc.get("commessa_ref"),
        "closure_date": doc.get("closure_date"),
        "closed_by": doc.get("closed_by"),
        "notes": doc.get("notes"),
        "days_open": days_open,
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


async def _next_nc_number() -> str:
    year = date.today().year
    count = await db.non_conformities.count_documents({"nc_number": {"$regex": f"^NC-{year}"}})
    return f"NC-{year}-{count + 1:03d}"


def _compute_audit_stats(audits: list[dict], ncs: list[dict]) -> dict:
    current_year = date.today().year
    year_audits = [a for a in audits if a.get("date", "").startswith(str(current_year))]
    open_ncs = sum(1 for n in ncs if n.get("status") != "chiusa")
    closed_ncs = sum(1 for n in ncs if n.get("status") == "chiusa")
    high_priority = sum(1 for n in ncs if n.get("status") != "chiusa" and n.get("priority") == "alta")

    next_audit = None
    today_str = date.today().isoformat()
    future = [a.get("next_audit_date") for a in audits if a.get("next_audit_date") and a["next_audit_date"] >= today_str]
    if future:
        next_audit = min(future)

    return {
        "total_audits": len(audits),
        "audits_this_year": len(year_audits),
        "nc_open": open_ncs,
        "nc_closed": closed_ncs,
        "nc_total": len(ncs),
        "nc_high_priority": high_priority,
        "next_audit_date": next_audit,
    }


# ══════════════════════ AUDIT ROUTES ══════════════════════

@router.get("/audits", response_model=AuditList)
async def list_audits(
    search: Optional[str] = Query(None),
    audit_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    user: dict = Depends(get_current_user),
):
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).sort("date", -1).to_list(500)
    all_ncs = await db.non_conformities.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(1000)
    stats = _compute_audit_stats(all_audits, all_ncs)

    query = {}
    conditions = []
    if search:
        conditions.append({"$or": [
            {"auditor_name": {"$regex": search, "$options": "i"}},
            {"scope": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
        ]})
    if audit_type:
        conditions.append({"audit_type": audit_type})
    if outcome:
        conditions.append({"outcome": outcome})
    if year:
        conditions.append({"date": {"$regex": f"^{year}"}})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    query["user_id"] = user["user_id"]
    query["tenant_id"] = user["tenant_id"]

    filtered = await db.audits.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    items = [_audit_to_response(d, all_ncs) for d in filtered]

    return AuditList(items=items, total=len(items), stats=stats)


@router.get("/audits/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Audit non trovato")
    all_ncs = await db.non_conformities.find({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(100)
    return AuditResponse(**_audit_to_response(doc, all_ncs))


@router.post("/audits", response_model=AuditResponse)
async def create_audit(
    date: str = Form(...),
    audit_type: str = Form("interno"),
    auditor_name: str = Form(...),
    scope: str = Form(""),
    outcome: str = Form("positivo"),
    notes: str = Form(""),
    next_audit_date: str = Form(""),
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    if not auditor_name.strip():
        raise HTTPException(400, "Nome auditor obbligatorio")

    audit_id = f"aud_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    safe_filename = ""
    report_filename = ""
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {".pdf", ".jpg", ".jpeg", ".png", ".docx"}:
            raise HTTPException(400, "Tipo file non supportato")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(400, "File troppo grande (max 20 MB)")
        safe_filename = f"{audit_id}{ext}"
        with open(os.path.join(UPLOAD_DIR, safe_filename), "wb") as f:
            f.write(content)
        report_filename = file.filename

    doc = {
        "audit_id": audit_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "date": date.strip(),
        "audit_type": audit_type.strip(),
        "auditor_name": auditor_name.strip(),
        "scope": scope.strip() or None,
        "outcome": outcome.strip(),
        "notes": notes.strip() or None,
        "next_audit_date": next_audit_date.strip() or None,
        "safe_filename": safe_filename,
        "report_filename": report_filename,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.audits.insert_one(doc)
    return AuditResponse(**_audit_to_response(doc))


@router.put("/audits/{audit_id}", response_model=AuditResponse)
async def update_audit(audit_id: str, payload: AuditCreate, user: dict = Depends(get_current_user)):
    existing = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Audit non trovato")

    now_iso = datetime.now(timezone.utc).isoformat()
    update = {
        "date": payload.date,
        "audit_type": payload.audit_type,
        "auditor_name": payload.auditor_name.strip(),
        "scope": payload.scope,
        "outcome": payload.outcome,
        "notes": payload.notes,
        "next_audit_date": payload.next_audit_date,
        "updated_at": now_iso,
    }
    await db.audits.update_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"$set": update})
    updated = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    all_ncs = await db.non_conformities.find({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(100)
    return AuditResponse(**_audit_to_response(updated, all_ncs))


@router.delete("/audits/{audit_id}")
async def delete_audit(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Audit non trovato")

    sf = doc.get("safe_filename")
    if sf:
        fpath = os.path.join(UPLOAD_DIR, sf)
        if os.path.exists(fpath):
            os.remove(fpath)

    await db.audits.delete_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    # Unlink NCs from this audit (don't delete them)
    await db.non_conformities.update_many({"audit_id": audit_id}, {"$set": {"audit_id": None}})
    return {"message": "Audit eliminato", "audit_id": audit_id}


@router.get("/audits/{audit_id}/report/download")
async def download_audit_report(audit_id: str, user: dict = Depends(get_current_user)):
    doc = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Audit non trovato")
    sf = doc.get("safe_filename")
    if not sf:
        raise HTTPException(404, "Nessun report allegato")
    fpath = os.path.join(UPLOAD_DIR, sf)
    if not os.path.exists(fpath):
        raise HTTPException(404, "File non trovato su disco")
    return FileResponse(fpath, filename=doc.get("report_filename", sf))


# ══════════════════════ NC ROUTES ══════════════════════

@router.get("/ncs", response_model=NCList)
async def list_ncs(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    audit_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    all_ncs = await db.non_conformities.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).sort("date", -1).to_list(1000)
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(500)
    audit_map = {a["audit_id"]: a for a in all_audits}

    nc_stats = {
        "total": len(all_ncs),
        "aperte": sum(1 for n in all_ncs if n.get("status") == "aperta"),
        "in_lavorazione": sum(1 for n in all_ncs if n.get("status") == "in_lavorazione"),
        "chiuse": sum(1 for n in all_ncs if n.get("status") == "chiusa"),
        "alta": sum(1 for n in all_ncs if n.get("status") != "chiusa" and n.get("priority") == "alta"),
        "media": sum(1 for n in all_ncs if n.get("status") != "chiusa" and n.get("priority") == "media"),
        "bassa": sum(1 for n in all_ncs if n.get("status") != "chiusa" and n.get("priority") == "bassa"),
    }

    query = {}
    conditions = []
    if search:
        conditions.append({"$or": [
            {"description": {"$regex": search, "$options": "i"}},
            {"nc_number": {"$regex": search, "$options": "i"}},
            {"cause": {"$regex": search, "$options": "i"}},
            {"source": {"$regex": search, "$options": "i"}},
        ]})
    if status:
        conditions.append({"status": status})
    if priority:
        conditions.append({"priority": priority})
    if audit_id:
        conditions.append({"audit_id": audit_id})
    if conditions:
        query = {"$and": conditions} if len(conditions) > 1 else conditions[0]
    query["user_id"] = user["user_id"]
    query["tenant_id"] = user["tenant_id"]

    filtered = await db.non_conformities.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    items = [_nc_to_response(d, audit_map) for d in filtered]

    return NCList(items=items, total=len(items), stats=nc_stats)


@router.post("/ncs", response_model=NCResponse)
async def create_nc(payload: NCCreate, user: dict = Depends(get_current_user)):
    nc_id = f"nc_{uuid.uuid4().hex[:10]}"
    nc_number = await _next_nc_number()
    now_iso = datetime.now(timezone.utc).isoformat()

    if payload.audit_id:
        audit = await db.audits.find_one({"audit_id": payload.audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
        if not audit:
            raise HTTPException(404, "Audit di riferimento non trovato")

    doc = {
        "nc_id": nc_id,
        "nc_number": nc_number,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "date": payload.date,
        "description": payload.description.strip(),
        "source": payload.source,
        "cause": None,
        "corrective_action": None,
        "preventive_action": None,
        "priority": payload.priority,
        "status": "aperta",
        "audit_id": payload.audit_id,
        "commessa_ref": payload.commessa_ref,
        "closure_date": None,
        "closed_by": None,
        "notes": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.non_conformities.insert_one(doc)
    return NCResponse(**_nc_to_response(doc))


@router.post("/audits/{audit_id}/ncs", response_model=NCResponse)
async def create_nc_for_audit(audit_id: str, payload: NCCreate, user: dict = Depends(get_current_user)):
    audit = await db.audits.find_one({"audit_id": audit_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not audit:
        raise HTTPException(404, "Audit non trovato")

    payload.audit_id = audit_id
    nc_id = f"nc_{uuid.uuid4().hex[:10]}"
    nc_number = await _next_nc_number()
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "nc_id": nc_id,
        "nc_number": nc_number,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "date": payload.date,
        "description": payload.description.strip(),
        "source": payload.source or f"Audit {audit.get('date','')}",
        "cause": None,
        "corrective_action": None,
        "preventive_action": None,
        "priority": payload.priority,
        "status": "aperta",
        "audit_id": audit_id,
        "commessa_ref": payload.commessa_ref,
        "closure_date": None,
        "closed_by": None,
        "notes": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.non_conformities.insert_one(doc)
    return NCResponse(**_nc_to_response(doc))


@router.get("/ncs/{nc_id}", response_model=NCResponse)
async def get_nc(nc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Non conformità non trovata")
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(500)
    audit_map = {a["audit_id"]: a for a in all_audits}
    return NCResponse(**_nc_to_response(doc, audit_map))


@router.put("/ncs/{nc_id}", response_model=NCResponse)
async def update_nc(nc_id: str, payload: NCUpdate, user: dict = Depends(get_current_user)):
    doc = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Non conformità non trovata")

    now_iso = datetime.now(timezone.utc).isoformat()
    update = {"updated_at": now_iso}
    if payload.description is not None:
        update["description"] = payload.description.strip()
    if payload.cause is not None:
        update["cause"] = payload.cause.strip() or None
    if payload.corrective_action is not None:
        update["corrective_action"] = payload.corrective_action.strip() or None
    if payload.preventive_action is not None:
        update["preventive_action"] = payload.preventive_action.strip() or None
    if payload.priority is not None:
        update["priority"] = payload.priority
    if payload.status is not None:
        update["status"] = payload.status
    if payload.notes is not None:
        update["notes"] = payload.notes.strip() or None

    await db.non_conformities.update_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"$set": update})
    updated = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(500)
    audit_map = {a["audit_id"]: a for a in all_audits}
    return NCResponse(**_nc_to_response(updated, audit_map))


@router.put("/ncs/{nc_id}/close", response_model=NCResponse)
async def close_nc(nc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Non conformità non trovata")
    if doc.get("status") == "chiusa":
        raise HTTPException(400, "NC già chiusa")

    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = date.today().isoformat()
    user_name = user.get("name", user.get("email", "Sistema"))

    await db.non_conformities.update_one(
        {"nc_id": nc_id},
        {"$set": {
            "status": "chiusa",
            "closure_date": today_str,
            "closed_by": user_name,
            "updated_at": now_iso,
        }},
    )
    updated = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(500)
    audit_map = {a["audit_id"]: a for a in all_audits}
    return NCResponse(**_nc_to_response(updated, audit_map))


@router.put("/ncs/{nc_id}/reopen", response_model=NCResponse)
async def reopen_nc(nc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Non conformità non trovata")
    if doc.get("status") != "chiusa":
        raise HTTPException(400, "NC non è chiusa")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.non_conformities.update_one(
        {"nc_id": nc_id},
        {"$set": {"status": "aperta", "closure_date": None, "closed_by": None, "updated_at": now_iso}},
    )
    updated = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}).to_list(500)
    audit_map = {a["audit_id"]: a for a in all_audits}
    return NCResponse(**_nc_to_response(updated, audit_map))


@router.delete("/ncs/{nc_id}")
async def delete_nc(nc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.non_conformities.find_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Non conformità non trovata")
    await db.non_conformities.delete_one({"nc_id": nc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    return {"message": "Non conformità eliminata", "nc_id": nc_id}
