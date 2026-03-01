"""Routes for Archivio Documentale Aziendale — isolated company document storage."""
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
    return CompanyDocumentList(items=docs, total=len(docs))


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
    safe_filename = f"{doc_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

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
        "upload_date": datetime.now(timezone.utc).isoformat(),
    }

    await db.company_documents.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("safe_filename", None)
    return CompanyDocumentResponse(**doc)


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

    file_path = os.path.join(UPLOAD_DIR, doc["safe_filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    await db.company_documents.delete_one({"doc_id": doc_id})
    return {"message": "Documento eliminato", "doc_id": doc_id}
