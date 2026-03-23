"""Routes for Registro Saldatori & Patentini — isolated welder qualification registry."""
import uuid
import os
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from core.database import db
from core.security import get_current_user
from models.welder import (
    WelderCreate, WelderResponse, WelderList,
    QualificationCreate, QualificationResponse,
)

router = APIRouter(prefix="/welders", tags=["welders"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "welder_certs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Safety certification types for the expiry matrix
SAFETY_CERT_TYPES = [
    {"code": "patentino_saldatura", "label": "Patentino Saldatura", "category": "tecnico"},
    {"code": "formazione_base_8108", "label": "Formazione Base 81/08", "category": "sicurezza"},
    {"code": "formazione_specifica", "label": "Form. Specifica Rischio Alto", "category": "sicurezza"},
    {"code": "primo_soccorso", "label": "Primo Soccorso", "category": "sicurezza"},
    {"code": "antincendio", "label": "Antincendio", "category": "sicurezza"},
    {"code": "lavori_quota", "label": "Lavori in Quota", "category": "sicurezza"},
    {"code": "ple", "label": "PLE (Piattaforme)", "category": "sicurezza"},
    {"code": "idoneita_sanitaria", "label": "Idoneita Sanitaria", "category": "medico"},
]


def _qual_status(expiry_str: str) -> tuple[str, int | None]:
    """Compute qualification status from expiry date."""
    try:
        exp = date.fromisoformat(expiry_str) if isinstance(expiry_str, str) else expiry_str
        delta = (exp - date.today()).days
        if delta < 0:
            return "scaduto", delta
        if delta <= 30:
            return "in_scadenza", delta
        return "attivo", delta
    except (ValueError, TypeError):
        return "attivo", None


def _qual_to_response(q: dict) -> dict:
    status, days = _qual_status(q.get("expiry_date", ""))
    return {
        "qual_id": q["qual_id"],
        "standard": q.get("standard", ""),
        "process": q.get("process", ""),
        "material_group": q.get("material_group"),
        "thickness_range": q.get("thickness_range"),
        "position": q.get("position"),
        "issue_date": q.get("issue_date"),
        "expiry_date": q.get("expiry_date", ""),
        "cert_code": q.get("cert_code") or _guess_cert_code(q.get("standard", "")),
        "status": status,
        "days_until_expiry": days,
        "has_file": bool(q.get("safe_filename")),
        "filename": q.get("filename"),
        "notes": q.get("notes"),
    }


def _welder_to_response(doc: dict) -> dict:
    quals_raw = doc.get("qualifications", [])
    quals = [_qual_to_response(q) for q in quals_raw]

    active = sum(1 for q in quals if q["status"] == "attivo")
    expiring = sum(1 for q in quals if q["status"] == "in_scadenza")
    expired = sum(1 for q in quals if q["status"] == "scaduto")

    if not quals:
        overall = "no_qual"
    elif expired > 0 and active == 0 and expiring == 0:
        overall = "expired"
    elif expiring > 0 or expired > 0:
        overall = "warning"
    else:
        overall = "ok"

    return {
        "welder_id": doc["welder_id"],
        "name": doc["name"],
        "stamp_id": doc["stamp_id"],
        "role": doc.get("role", "saldatore"),
        "phone": doc.get("phone"),
        "email": doc.get("email"),
        "hire_date": doc.get("hire_date"),
        "is_active": doc.get("is_active", True),
        "notes": doc.get("notes"),
        "qualifications": quals,
        "overall_status": overall,
        "active_quals": active,
        "expiring_quals": expiring,
        "expired_quals": expired,
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


def _compute_stats(docs: list[dict]) -> dict:
    total = len(docs)
    active_welders = sum(1 for d in docs if d.get("is_active", True))
    responses = [_welder_to_response(d) for d in docs]
    ok = sum(1 for r in responses if r["overall_status"] == "ok")
    warning = sum(1 for r in responses if r["overall_status"] == "warning")
    expired = sum(1 for r in responses if r["overall_status"] == "expired")
    no_qual = sum(1 for r in responses if r["overall_status"] == "no_qual")
    total_quals = sum(len(d.get("qualifications", [])) for d in docs)
    return {
        "total": total,
        "active_welders": active_welders,
        "ok": ok,
        "warning": warning,
        "expired": expired,
        "no_qual": no_qual,
        "total_qualifications": total_quals,
    }


@router.get("/", response_model=WelderList)
async def list_welders(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"stamp_id": {"$regex": search, "$options": "i"}},
        ]

    all_docs = await db.welders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("name", 1).to_list(200)
    stats = _compute_stats(all_docs)

    query["user_id"] = user["user_id"]
    filtered = await db.welders.find(query, {"_id": 0}).sort("name", 1).to_list(200)
    items = [_welder_to_response(d) for d in filtered]

    if status:
        items = [i for i in items if i["overall_status"] == status]

    return WelderList(items=items, total=len(items), stats=stats)


def _guess_cert_code(standard: str) -> str:
    """Map existing qualification standard names to safety cert codes."""
    s = standard.lower()
    if "9606" in s or "287" in s or "14732" in s or "saldatura" in s:
        return "patentino_saldatura"
    if "81/08" in s or "81-08" in s:
        if "specif" in s or "rischio" in s:
            return "formazione_specifica"
        return "formazione_base_8108"
    if "soccorso" in s:
        return "primo_soccorso"
    if "antincendio" in s or "incendio" in s:
        return "antincendio"
    if "quota" in s:
        return "lavori_quota"
    if "ple" in s or "piattaform" in s:
        return "ple"
    if "sanitaria" in s or "medic" in s or "idone" in s:
        return "idoneita_sanitaria"
    return ""


# ── Safety Certification Types ──

@router.get("/safety-cert-types")
async def get_safety_cert_types(user: dict = Depends(get_current_user)):
    return {"cert_types": SAFETY_CERT_TYPES}


# ── Matrice Scadenze ──

@router.get("/matrice-scadenze")
async def matrice_scadenze(user: dict = Depends(get_current_user)):
    """
    Returns a matrix: rows = workers, columns = cert types.
    Each cell has status: 'valido', 'in_scadenza', 'scaduto', 'mancante'.
    """
    all_docs = await db.welders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("name", 1).to_list(200)
    today = date.today()

    cert_codes = [c["code"] for c in SAFETY_CERT_TYPES]
    rows = []

    for doc in all_docs:
        quals = doc.get("qualifications", [])
        cert_map = {}
        for q in quals:
            code = q.get("cert_code") or _guess_cert_code(q.get("standard", ""))
            if code and code in cert_codes:
                existing = cert_map.get(code)
                if existing:
                    if (q.get("expiry_date", "") or "") > (existing.get("expiry_date", "") or ""):
                        cert_map[code] = q
                else:
                    cert_map[code] = q

        cells = {}
        has_any_expired = False
        for code in cert_codes:
            q = cert_map.get(code)
            if not q:
                cells[code] = {"status": "mancante", "days": None, "expiry": None}
            else:
                exp_str = q.get("expiry_date", "")
                try:
                    exp = date.fromisoformat(exp_str) if exp_str else None
                except (ValueError, TypeError):
                    exp = None

                if exp:
                    days = (exp - today).days
                    if days < 0:
                        cells[code] = {"status": "scaduto", "days": days, "expiry": exp_str}
                        has_any_expired = True
                    elif days <= 15:
                        cells[code] = {"status": "in_scadenza", "days": days, "expiry": exp_str}
                    else:
                        cells[code] = {"status": "valido", "days": days, "expiry": exp_str}
                else:
                    cells[code] = {"status": "valido", "days": None, "expiry": None}

        can_go = not has_any_expired and all(
            cells[c]["status"] != "mancante" for c in cert_codes
        )

        rows.append({
            "welder_id": doc["welder_id"],
            "name": doc["name"],
            "stamp_id": doc.get("stamp_id", ""),
            "role": doc.get("role", ""),
            "cells": cells,
            "can_go_to_cantiere": can_go,
        })

    return {
        "cert_types": SAFETY_CERT_TYPES,
        "workers": rows,
        "total": len(rows),
    }


# ── POS Worker Selection ──

@router.get("/per-pos")
async def workers_for_pos(user: dict = Depends(get_current_user)):
    """
    Return worker list enriched with safety compliance status for POS selection.
    """
    all_docs = await db.welders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("name", 1).to_list(200)
    today = date.today()
    cert_codes = [c["code"] for c in SAFETY_CERT_TYPES]

    results = []
    for doc in all_docs:
        quals = doc.get("qualifications", [])
        cert_map = {}
        for q in quals:
            code = q.get("cert_code") or _guess_cert_code(q.get("standard", ""))
            if code and code in cert_codes:
                existing = cert_map.get(code)
                if not existing or (q.get("expiry_date", "") or "") > (existing.get("expiry_date", "") or ""):
                    cert_map[code] = q

        warnings = []
        blockers = []
        for c in SAFETY_CERT_TYPES:
            code = c["code"]
            q = cert_map.get(code)
            if not q:
                blockers.append(f"{c['label']}: mancante")
            else:
                exp_str = q.get("expiry_date", "")
                try:
                    exp = date.fromisoformat(exp_str) if exp_str else None
                except (ValueError, TypeError):
                    exp = None
                if exp:
                    days = (exp - today).days
                    if days < 0:
                        blockers.append(f"{c['label']}: scaduto ({exp_str})")
                    elif days <= 15:
                        warnings.append(f"{c['label']}: scade tra {days}gg")

        cert_files = []
        for q in quals:
            if q.get("safe_filename"):
                cert_files.append({
                    "qual_id": q["qual_id"],
                    "standard": q.get("standard", ""),
                    "filename": q.get("filename", ""),
                    "safe_filename": q["safe_filename"],
                })

        results.append({
            "welder_id": doc["welder_id"],
            "name": doc["name"],
            "stamp_id": doc.get("stamp_id", ""),
            "role": doc.get("role", ""),
            "can_deploy": len(blockers) == 0,
            "warnings": warnings,
            "blockers": blockers,
            "cert_files_count": len(cert_files),
        })

    return {"workers": results}


@router.get("/{welder_id}", response_model=WelderResponse)
async def get_welder(welder_id: str, user: dict = Depends(get_current_user)):
    doc = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Saldatore non trovato")
    return WelderResponse(**_welder_to_response(doc))


@router.post("/", response_model=WelderResponse)
async def create_welder(payload: WelderCreate, user: dict = Depends(get_current_user)):
    welder_id = f"wld_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "welder_id": welder_id,
        "user_id": user["user_id"],
        "name": payload.name.strip(),
        "stamp_id": payload.stamp_id.strip(),
        "role": payload.role or "saldatore",
        "phone": payload.phone or "",
        "email": payload.email or "",
        "hire_date": payload.hire_date or "",
        "is_active": True,
        "notes": payload.notes or "",
        "qualifications": [],
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    await db.welders.insert_one(doc)
    return WelderResponse(**_welder_to_response(doc))


@router.put("/{welder_id}", response_model=WelderResponse)
async def update_welder(welder_id: str, payload: WelderCreate, user: dict = Depends(get_current_user)):
    existing = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Saldatore non trovato")

    now_iso = datetime.now(timezone.utc).isoformat()
    update = {
        "name": payload.name.strip(),
        "stamp_id": payload.stamp_id.strip(),
        "role": payload.role or "saldatore",
        "phone": payload.phone or "",
        "email": payload.email or "",
        "hire_date": payload.hire_date or "",
        "notes": payload.notes or "",
        "updated_at": now_iso,
    }

    await db.welders.update_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"$set": update})
    updated = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    return WelderResponse(**_welder_to_response(updated))


@router.delete("/{welder_id}")
async def delete_welder(welder_id: str, user: dict = Depends(get_current_user)):
    doc = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Saldatore non trovato")

    # Delete all qualification files
    for q in doc.get("qualifications", []):
        sf = q.get("safe_filename")
        if sf:
            fpath = os.path.join(UPLOAD_DIR, sf)
            if os.path.exists(fpath):
                os.remove(fpath)

    await db.welders.delete_one({"welder_id": welder_id, "user_id": user["user_id"]})
    return {"message": "Saldatore eliminato", "welder_id": welder_id}


# ── Qualifications ──

@router.post("/{welder_id}/qualifications", response_model=WelderResponse)
async def add_qualification(
    welder_id: str,
    standard: str = Form("ISO 9606-1"),
    process: str = Form(""),
    material_group: str = Form(""),
    thickness_range: str = Form(""),
    position: str = Form(""),
    issue_date: str = Form(""),
    expiry_date: str = Form(...),
    notes: str = Form(""),
    cert_code: str = Form(""),
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    doc = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Saldatore non trovato")

    qual_id = f"qual_{uuid.uuid4().hex[:8]}"
    safe_filename = ""
    filename = ""

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
            raise HTTPException(400, "Tipo file non supportato (solo PDF/immagini)")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(400, "File troppo grande (max 20 MB)")
        safe_filename = f"{qual_id}{ext}"
        with open(os.path.join(UPLOAD_DIR, safe_filename), "wb") as f:
            f.write(content)
        filename = file.filename

    qual = {
        "qual_id": qual_id,
        "standard": standard.strip(),
        "process": process.strip(),
        "material_group": material_group.strip() or None,
        "thickness_range": thickness_range.strip() or None,
        "position": position.strip() or None,
        "issue_date": issue_date.strip() or None,
        "expiry_date": expiry_date.strip(),
        "notes": notes.strip() or None,
        "cert_code": cert_code.strip() or _guess_cert_code(standard.strip()),
        "safe_filename": safe_filename,
        "filename": filename,
    }

    await db.welders.update_one(
        {"welder_id": welder_id},
        {
            "$push": {"qualifications": qual},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )

    updated = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    return WelderResponse(**_welder_to_response(updated))


@router.delete("/{welder_id}/qualifications/{qual_id}")
async def delete_qualification(welder_id: str, qual_id: str, user: dict = Depends(get_current_user)):
    doc = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Saldatore non trovato")

    qual = next((q for q in doc.get("qualifications", []) if q["qual_id"] == qual_id), None)
    if not qual:
        raise HTTPException(404, "Qualifica non trovata")

    sf = qual.get("safe_filename")
    if sf:
        fpath = os.path.join(UPLOAD_DIR, sf)
        if os.path.exists(fpath):
            os.remove(fpath)

    await db.welders.update_one(
        {"welder_id": welder_id},
        {
            "$pull": {"qualifications": {"qual_id": qual_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return {"message": "Qualifica eliminata", "qual_id": qual_id}


@router.get("/{welder_id}/qualifications/{qual_id}/download")
async def download_qualification(welder_id: str, qual_id: str, user: dict = Depends(get_current_user)):
    doc = await db.welders.find_one({"welder_id": welder_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Saldatore non trovato")

    qual = next((q for q in doc.get("qualifications", []) if q["qual_id"] == qual_id), None)
    if not qual:
        raise HTTPException(404, "Qualifica non trovata")

    sf = qual.get("safe_filename")
    if not sf:
        raise HTTPException(404, "Nessun file allegato")

    fpath = os.path.join(UPLOAD_DIR, sf)
    if not os.path.exists(fpath):
        raise HTTPException(404, "File non trovato su disco")

    return FileResponse(fpath, filename=qual.get("filename", sf))
