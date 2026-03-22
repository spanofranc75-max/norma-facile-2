"""
Pacchetti Documentali — API Routes (D1 + D2 + D3)
===================================================
D1: /api/documenti/* — Archivio documenti
D2: /api/pacchetti-documentali/* — Template e pacchetti
D3: /api/pacchetti-documentali/{id}/verifica — Motore verifica
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional

from core.security import get_current_user
from services.pacchetti_documentali_service import (
    get_tipi_documento, upload_documento, list_documenti, get_documento, update_documento,
    get_templates, crea_pacchetto, get_pacchetto, list_pacchetti, verifica_pacchetto,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  D1 — TIPI DOCUMENTO & ARCHIVIO
# ═══════════════════════════════════════════════════════════════

@router.get("/documenti/tipi")
async def api_tipi_documento(user: dict = Depends(get_current_user)):
    """Get document types library."""
    return await get_tipi_documento(user["user_id"])


@router.post("/documenti")
async def api_upload_documento(
    document_type_code: str = Form(""),
    entity_type: str = Form("azienda"),
    entity_id: str = Form(""),
    owner_label: str = Form(""),
    title: str = Form(""),
    issue_date: str = Form(""),
    expiry_date: str = Form(""),
    privacy_level: str = Form("cliente_condivisibile"),
    verified: bool = Form(False),
    notes: str = Form(""),
    tags: str = Form(""),
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    """Upload a document to archive."""
    data = {
        "document_type_code": document_type_code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "owner_label": owner_label,
        "title": title or (file.filename if file else ""),
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "privacy_level": privacy_level,
        "verified": verified,
        "notes": notes,
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    }

    file_data = None
    filename = None
    content_type = None
    if file:
        file_data = await file.read()
        filename = file.filename
        content_type = file.content_type

    doc = await upload_documento(user["user_id"], data, file_data, filename, content_type)
    return doc


@router.get("/documenti")
async def api_list_documenti(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    document_type_code: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List documents with optional filters."""
    return await list_documenti(user["user_id"], entity_type, entity_id, document_type_code, status)


@router.get("/documenti/{doc_id}")
async def api_get_documento(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await get_documento(doc_id, user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    return doc


@router.patch("/documenti/{doc_id}")
async def api_update_documento(doc_id: str, updates: dict, user: dict = Depends(get_current_user)):
    doc = await update_documento(doc_id, user["user_id"], updates)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    return doc


# ═══════════════════════════════════════════════════════════════
#  D2 — TEMPLATE & PACCHETTI
# ═══════════════════════════════════════════════════════════════

@router.get("/pacchetti-documentali/templates")
async def api_templates(user: dict = Depends(get_current_user)):
    """Get available package templates."""
    return await get_templates(user["user_id"])


@router.post("/pacchetti-documentali")
async def api_crea_pacchetto(data: dict, user: dict = Depends(get_current_user)):
    """Create a new document package (from template or manual)."""
    return await crea_pacchetto(user["user_id"], data)


@router.get("/pacchetti-documentali")
async def api_list_pacchetti(
    commessa_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List document packages."""
    return await list_pacchetti(user["user_id"], commessa_id)


@router.get("/pacchetti-documentali/{pack_id}")
async def api_get_pacchetto(pack_id: str, user: dict = Depends(get_current_user)):
    pack = await get_pacchetto(pack_id, user["user_id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Pacchetto non trovato")
    return pack


# ═══════════════════════════════════════════════════════════════
#  D3 — VERIFICA
# ═══════════════════════════════════════════════════════════════

@router.post("/pacchetti-documentali/{pack_id}/verifica")
async def api_verifica_pacchetto(pack_id: str, user: dict = Depends(get_current_user)):
    """D3: Verify package — match items against archive, calculate status."""
    result = await verifica_pacchetto(pack_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
