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
