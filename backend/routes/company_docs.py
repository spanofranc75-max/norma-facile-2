"""Routes for Archivio Documentale Aziendale — isolated company document storage with versioning."""
import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from core.database import db
from core.security import get_current_user
from models.company_doc import (
    CompanyDocumentResponse,
    CompanyDocumentList,
    VersionListResponse,
    VersionEntry,
    CATEGORIES,
)

router = APIRouter(prefix="/company/documents", tags=["company-documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "company_docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".txt", ".csv", ".xml", ".zip", ".rar", ".7z",
    ".dwg", ".dxf", ".step", ".stp", ".iges",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _doc_to_response(doc: dict) -> dict:
    """Convert a MongoDB doc to a response-safe dict."""
    versions = doc.get("versions", [])
    return {
        "doc_id": doc["doc_id"],
        "title": doc["title"],
        "category": doc["category"],
        "filename": doc["filename"],
        "content_type": doc.get("content_type", "application/octet-stream"),
        "size_kb": doc.get("size_kb", 0),
        "tags": doc.get("tags", []),
        "uploaded_by": doc.get("uploaded_by"),
        "upload_date": doc.get("upload_date", ""),
        "version": doc.get("version", 1),
        "version_count": len(versions) + 1,  # current + archived
    }


@router.get("/", response_model=CompanyDocumentList)
async def list_documents(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    query = {}
    if category and category in CATEGORIES:
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
            {"filename": {"$regex": search, "$options": "i"}},
        ]

    docs = await db.company_documents.find(query, {"_id": 0}).sort("upload_date", -1).to_list(500)
    items = [_doc_to_response(d) for d in docs]
    return CompanyDocumentList(items=items, total=len(items))


@router.post("/", response_model=CompanyDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("altro"),
    tags: str = Form(""),
    user: dict = Depends(get_current_user),
):
    if category not in CATEGORIES:
        raise HTTPException(400, f"Categoria non valida. Valide: {CATEGORIES}")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Tipo file non supportato: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File troppo grande (max 50 MB)")

    doc_id = f"cdoc_{uuid.uuid4().hex[:10]}"
    safe_filename = f"{doc_id}_v1{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "doc_id": doc_id,
        "title": title.strip(),
        "category": category,
        "filename": file.filename or safe_filename,
        "safe_filename": safe_filename,
        "content_type": file.content_type or "application/octet-stream",
        "size_kb": round(len(content) / 1024),
        "tags": tag_list,
        "uploaded_by": user.get("name", user.get("email", "")),
        "upload_date": now_iso,
        "version": 1,
        "versions": [],  # archived previous versions
    }

    await db.company_documents.insert_one(doc)
    return CompanyDocumentResponse(**_doc_to_response(doc))


@router.post("/{doc_id}/revision", response_model=CompanyDocumentResponse)
async def upload_revision(
    doc_id: str,
    file: UploadFile = File(...),
    note: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Upload a new revision of an existing document, archiving the current version."""
    doc = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Tipo file non supportato: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File troppo grande (max 50 MB)")

    current_version = doc.get("version", 1)
    new_version = current_version + 1

    # Archive current version into the versions array
    archived = {
        "version": current_version,
        "filename": doc["filename"],
        "safe_filename": doc["safe_filename"],
        "content_type": doc.get("content_type", "application/octet-stream"),
        "size_kb": doc.get("size_kb", 0),
        "uploaded_by": doc.get("uploaded_by", ""),
        "upload_date": doc.get("upload_date", ""),
        "note": "",
    }

    # Save new file
    new_safe = f"{doc_id}_v{new_version}{ext}"
    with open(os.path.join(UPLOAD_DIR, new_safe), "wb") as f:
        f.write(content)

    now_iso = datetime.now(timezone.utc).isoformat()
    uploader = user.get("name", user.get("email", ""))

    await db.company_documents.update_one(
        {"doc_id": doc_id},
        {
            "$push": {"versions": archived},
            "$set": {
                "version": new_version,
                "filename": file.filename or new_safe,
                "safe_filename": new_safe,
                "content_type": file.content_type or "application/octet-stream",
                "size_kb": round(len(content) / 1024),
                "uploaded_by": uploader,
                "upload_date": now_iso,
            },
        },
    )

    updated = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    return CompanyDocumentResponse(**_doc_to_response(updated))


@router.get("/{doc_id}/versions", response_model=VersionListResponse)
async def get_versions(doc_id: str, user: dict = Depends(get_current_user)):
    """Get all versions of a document including current."""
    doc = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    # Build version list: archived + current (current is the latest)
    archived = doc.get("versions", [])
    current = VersionEntry(
        version=doc.get("version", 1),
        filename=doc["filename"],
        safe_filename=doc["safe_filename"],
        content_type=doc.get("content_type", "application/octet-stream"),
        size_kb=doc.get("size_kb", 0),
        uploaded_by=doc.get("uploaded_by", ""),
        upload_date=doc.get("upload_date", ""),
        note="Versione corrente",
    )

    all_versions = [current] + [VersionEntry(**v) for v in reversed(archived)]

    return VersionListResponse(
        doc_id=doc_id,
        title=doc["title"],
        current_version=doc.get("version", 1),
        versions=all_versions,
    )


@router.get("/{doc_id}/versions/{version_num}/download")
async def download_version(doc_id: str, version_num: int, user: dict = Depends(get_current_user)):
    """Download a specific version of a document."""
    doc = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    # Check if it's the current version
    if doc.get("version", 1) == version_num:
        safe_fn = doc["safe_filename"]
        filename = doc["filename"]
        ct = doc.get("content_type", "application/octet-stream")
    else:
        # Find in archived versions
        found = None
        for v in doc.get("versions", []):
            if v.get("version") == version_num:
                found = v
                break
        if not found:
            raise HTTPException(404, f"Versione {version_num} non trovata")
        safe_fn = found["safe_filename"]
        filename = found["filename"]
        ct = found.get("content_type", "application/octet-stream")

    file_path = os.path.join(UPLOAD_DIR, safe_fn)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File non trovato su disco")

    return FileResponse(file_path, filename=filename, media_type=ct)


@router.get("/{doc_id}/download")
async def download_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    file_path = os.path.join(UPLOAD_DIR, doc["safe_filename"])
    if not os.path.exists(file_path):
        raise HTTPException(404, "File non trovato su disco")

    return FileResponse(
        file_path,
        filename=doc["filename"],
        media_type=doc.get("content_type", "application/octet-stream"),
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.company_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    # Delete current file
    file_path = os.path.join(UPLOAD_DIR, doc["safe_filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete all archived version files
    for v in doc.get("versions", []):
        vpath = os.path.join(UPLOAD_DIR, v.get("safe_filename", ""))
        if os.path.exists(vpath):
            os.remove(vpath)

    await db.company_documents.delete_one({"doc_id": doc_id})
    return {"message": "Documento eliminato", "doc_id": doc_id}



# ── Global Security Documents (DURC, Visura, White List, Patente a Crediti) ──

@router.get("/sicurezza-globali")
async def list_global_docs(user: dict = Depends(get_current_user)):
    """Lista documenti aziendali globali per sicurezza/POS con info scadenze."""
    from models.company_doc import GLOBAL_DOC_TYPES
    docs = await db.company_documents.find(
        {"category": "sicurezza_globale"},
        {"_id": 0}
    ).to_list(50)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = {}
    scadenze_alert = []

    for doc_type, meta in GLOBAL_DOC_TYPES.items():
        matching = [d for d in docs if d.get("tags") and doc_type in d.get("tags", [])]
        if matching:
            d = matching[0]
            scadenza = d.get("scadenza", "")
            days_to_expiry = None
            is_expiring = False
            is_expired = False
            if scadenza:
                try:
                    from datetime import date
                    exp_date = date.fromisoformat(scadenza)
                    today_date = date.fromisoformat(today)
                    days_to_expiry = (exp_date - today_date).days
                    is_expiring = 0 < days_to_expiry <= 15
                    is_expired = days_to_expiry <= 0
                except (ValueError, TypeError):
                    pass
            if is_expiring or is_expired:
                scadenze_alert.append({
                    "doc_type": doc_type,
                    "label": meta["label"],
                    "scadenza": scadenza,
                    "days_to_expiry": days_to_expiry,
                    "is_expired": is_expired,
                })
            result[doc_type] = {
                "doc_id": d["doc_id"],
                "title": d["title"],
                "filename": d["filename"],
                "upload_date": str(d.get("upload_date", "")),
                "scadenza": scadenza,
                "size_kb": d.get("size_kb", 0),
                "days_to_expiry": days_to_expiry,
                "is_expiring": is_expiring,
                "is_expired": is_expired,
                "presente": True,
                **meta,
            }
        else:
            result[doc_type] = {
                "doc_id": None,
                "presente": False,
                "days_to_expiry": None,
                "is_expiring": False,
                "is_expired": False,
                **meta,
            }

    total = len(GLOBAL_DOC_TYPES)
    caricati = sum(1 for v in result.values() if v["presente"])
    return {
        "documenti": result,
        "completo": caricati == total,
        "caricati": caricati,
        "totale": total,
        "scadenze_alert": scadenze_alert,
    }


@router.post("/sicurezza-globali/{doc_type}")
async def upload_global_doc(
    doc_type: str,
    file: UploadFile = File(...),
    scadenza: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Carica/aggiorna un documento globale di sicurezza."""
    from models.company_doc import GLOBAL_DOC_TYPES
    if doc_type not in GLOBAL_DOC_TYPES:
        raise HTTPException(400, f"Tipo non valido. Ammessi: {list(GLOBAL_DOC_TYPES.keys())}")

    meta = GLOBAL_DOC_TYPES[doc_type]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Estensione {ext} non ammessa")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File troppo grande (max 50MB)")

    # Check if exists
    existing = await db.company_documents.find_one(
        {"category": "sicurezza_globale", "tags": doc_type},
        {"_id": 0}
    )

    doc_id = existing["doc_id"] if existing else f"gdoc_{uuid.uuid4().hex[:12]}"
    safe_name = f"{doc_type}_{doc_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    now = datetime.now(timezone.utc).isoformat()
    doc_data = {
        "doc_id": doc_id,
        "user_id": user["user_id"],
        "title": meta["label"],
        "category": "sicurezza_globale",
        "filename": file.filename,
        "safe_filename": safe_name,
        "content_type": file.content_type or "application/octet-stream",
        "size_kb": round(len(content) / 1024, 1),
        "tags": [doc_type],
        "uploaded_by": user.get("name", user["user_id"]),
        "upload_date": now,
        "scadenza": scadenza or "",
        "version": 1,
    }

    if existing:
        # Delete old file
        old_path = os.path.join(UPLOAD_DIR, existing.get("safe_filename", ""))
        if os.path.exists(old_path):
            os.remove(old_path)
        await db.company_documents.update_one({"doc_id": doc_id}, {"$set": doc_data})
    else:
        await db.company_documents.insert_one(doc_data)

    return {
        "message": f"{meta['label']} caricato",
        "doc_id": doc_id,
        "filename": file.filename,
    }


@router.patch("/sicurezza-globali/{doc_type}")
async def update_global_doc_scadenza(
    doc_type: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Aggiorna la data di scadenza di un documento globale senza re-upload."""
    from models.company_doc import GLOBAL_DOC_TYPES
    if doc_type not in GLOBAL_DOC_TYPES:
        raise HTTPException(400, f"Tipo non valido. Ammessi: {list(GLOBAL_DOC_TYPES.keys())}")

    doc = await db.company_documents.find_one(
        {"category": "sicurezza_globale", "tags": doc_type}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato. Caricare prima il file.")

    scadenza = body.get("scadenza", "")
    await db.company_documents.update_one(
        {"doc_id": doc["doc_id"]},
        {"$set": {"scadenza": scadenza}}
    )
    return {"message": "Scadenza aggiornata", "doc_type": doc_type, "scadenza": scadenza}


# ── Allegati Tecnici POS (Rumore, Vibrazioni, MMC) ──

@router.get("/allegati-pos")
async def list_allegati_pos(user: dict = Depends(get_current_user)):
    """Lista allegati tecnici POS con stato inclusione."""
    from models.company_doc import ALLEGATI_POS_TYPES
    docs = await db.company_documents.find(
        {"category": "allegati_pos"}, {"_id": 0}
    ).to_list(50)

    result = {}
    for doc_type, meta in ALLEGATI_POS_TYPES.items():
        matching = [d for d in docs if d.get("tags") and doc_type in d.get("tags", [])]
        if matching:
            d = matching[0]
            result[doc_type] = {
                "doc_id": d["doc_id"],
                "title": d["title"],
                "filename": d["filename"],
                "upload_date": str(d.get("upload_date", "")),
                "size_kb": d.get("size_kb", 0),
                "includi_pos": d.get("includi_pos", True),
                "presente": True,
                **meta,
            }
        else:
            result[doc_type] = {
                "doc_id": None,
                "presente": False,
                "includi_pos": True,
                **meta,
            }

    total = len(ALLEGATI_POS_TYPES)
    caricati = sum(1 for v in result.values() if v["presente"])
    return {
        "allegati": result,
        "caricati": caricati,
        "totale": total,
    }


@router.post("/allegati-pos/{doc_type}")
async def upload_allegato_pos(
    doc_type: str,
    file: UploadFile = File(...),
    includi_pos: Optional[str] = Form("true"),
    user: dict = Depends(get_current_user),
):
    """Carica/aggiorna un allegato tecnico POS."""
    from models.company_doc import ALLEGATI_POS_TYPES
    if doc_type not in ALLEGATI_POS_TYPES:
        raise HTTPException(400, f"Tipo non valido. Ammessi: {list(ALLEGATI_POS_TYPES.keys())}")

    meta = ALLEGATI_POS_TYPES[doc_type]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Estensione {ext} non ammessa")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File troppo grande (max 50MB)")

    existing = await db.company_documents.find_one(
        {"category": "allegati_pos", "tags": doc_type}, {"_id": 0}
    )

    doc_id = existing["doc_id"] if existing else f"apos_{uuid.uuid4().hex[:12]}"
    safe_name = f"allegato_{doc_type}_{doc_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(content)

    now = datetime.now(timezone.utc).isoformat()
    include_flag = includi_pos.lower() in ("true", "1", "yes", "si")

    doc_data = {
        "doc_id": doc_id,
        "user_id": user["user_id"],
        "title": meta["label"],
        "category": "allegati_pos",
        "filename": file.filename,
        "safe_filename": safe_name,
        "content_type": file.content_type or "application/octet-stream",
        "size_kb": round(len(content) / 1024, 1),
        "tags": [doc_type],
        "uploaded_by": user.get("name", user["user_id"]),
        "upload_date": now,
        "includi_pos": include_flag,
        "version": 1,
    }

    if existing:
        old_path = os.path.join(UPLOAD_DIR, existing.get("safe_filename", ""))
        if os.path.exists(old_path):
            os.remove(old_path)
        await db.company_documents.update_one({"doc_id": doc_id}, {"$set": doc_data})
    else:
        await db.company_documents.insert_one(doc_data)

    return {
        "message": f"{meta['label']} caricato",
        "doc_id": doc_id,
        "filename": file.filename,
        "includi_pos": include_flag,
    }


@router.patch("/allegati-pos/{doc_type}")
async def toggle_allegato_pos(
    doc_type: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Aggiorna il flag 'includi_pos' di un allegato tecnico."""
    from models.company_doc import ALLEGATI_POS_TYPES
    if doc_type not in ALLEGATI_POS_TYPES:
        raise HTTPException(400, "Tipo non valido")

    doc = await db.company_documents.find_one(
        {"category": "allegati_pos", "tags": doc_type}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Allegato non trovato")

    includi = body.get("includi_pos", True)
    await db.company_documents.update_one(
        {"doc_id": doc["doc_id"]},
        {"$set": {"includi_pos": includi}}
    )
    return {"message": "Aggiornato", "doc_type": doc_type, "includi_pos": includi}


@router.delete("/allegati-pos/{doc_type}")
async def delete_allegato_pos(doc_type: str, user: dict = Depends(get_current_user)):
    """Elimina un allegato tecnico POS."""
    from models.company_doc import ALLEGATI_POS_TYPES
    if doc_type not in ALLEGATI_POS_TYPES:
        raise HTTPException(400, "Tipo non valido")

    doc = await db.company_documents.find_one(
        {"category": "allegati_pos", "tags": doc_type}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Allegato non trovato")

    filepath = os.path.join(UPLOAD_DIR, doc.get("safe_filename", ""))
    if os.path.exists(filepath):
        os.remove(filepath)

    await db.company_documents.delete_one({"doc_id": doc["doc_id"]})
    return {"message": "Allegato eliminato"}


@router.delete("/sicurezza-globali/{doc_type}")
async def delete_global_doc(doc_type: str, user: dict = Depends(get_current_user)):
    """Elimina un documento globale di sicurezza."""
    from models.company_doc import GLOBAL_DOC_TYPES
    if doc_type not in GLOBAL_DOC_TYPES:
        raise HTTPException(400, "Tipo non valido")

    doc = await db.company_documents.find_one(
        {"category": "sicurezza_globale", "tags": doc_type},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    filepath = os.path.join(UPLOAD_DIR, doc.get("safe_filename", ""))
    if os.path.exists(filepath):
        os.remove(filepath)

    await db.company_documents.delete_one({"doc_id": doc["doc_id"]})
    return {"message": "Documento eliminato"}
