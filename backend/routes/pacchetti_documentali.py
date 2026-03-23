"""
Pacchetti Documentali — API Routes (D1 + D2 + D3 + D4 + D5)
=============================================================
D1: /api/documenti/* — Archivio documenti
D2: /api/pacchetti-documentali/* — Template e pacchetti
D3: /api/pacchetti-documentali/{id}/verifica — Motore verifica
D4: /api/pacchetti-documentali/{id}/prepara-invio — Preview email
D5: /api/pacchetti-documentali/{id}/invia — Invio + log
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional

from core.security import get_current_user
from services.pacchetti_documentali_service import (
    get_tipi_documento, upload_documento, list_documenti, get_documento, update_documento,
    get_templates, crea_pacchetto, get_pacchetto, list_pacchetti, verifica_pacchetto,
    prepara_invio, invia_email_pacchetto, get_invii,
)
from services.audit_trail import log_activity

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
    await log_activity(user, "create", "documento_archivio", doc.get("doc_id", ""),
                       label=doc.get("title", filename or ""),
                       details={"document_type": document_type_code, "entity_type": entity_type})
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
    result = await crea_pacchetto(user["user_id"], data)
    await log_activity(user, "create", "pacchetto_documentale", result.get("pack_id", ""),
                       label=result.get("label", data.get("template_code", "")),
                       commessa_id=data.get("commessa_id", ""),
                       details={"template_code": data.get("template_code", ""), "n_items": len(result.get("items", []))})
    return result


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
    await log_activity(user, "verifica", "pacchetto_documentale", pack_id,
                       label=result.get("label", ""),
                       commessa_id=result.get("commessa_id", ""),
                       details={"attached": result.get("summary", {}).get("attached", 0),
                                "missing": result.get("summary", {}).get("missing", 0),
                                "expired": result.get("summary", {}).get("expired", 0)},
                       actor_type="system")
    # N2: Notify if package is incomplete
    summary = result.get("summary", {})
    if summary.get("missing", 0) > 0 or summary.get("expired", 0) > 0:
        from services.notifiche_trigger import notify_pacchetto_incompleto
        from core.database import db as _db
        cid = result.get("commessa_id", "")
        if cid:
            comm = await _db.commesse.find_one({"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0, "numero": 1})
            import asyncio
            asyncio.create_task(notify_pacchetto_incompleto(
                user["user_id"], cid, (comm or {}).get("numero", cid),
                result.get("label", ""), pack_id,
                summary.get("missing", 0), summary.get("expired", 0),
            ))
    return result


@router.patch("/pacchetti-documentali/{pack_id}")
async def api_update_pacchetto(pack_id: str, updates: dict, user: dict = Depends(get_current_user)):
    """Update package fields (recipient, label, etc.)."""
    from core.database import db
    from datetime import datetime, timezone
    pack = await get_pacchetto(pack_id, user["user_id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Pacchetto non trovato")
    allowed = {"label", "recipient", "commessa_id", "cantiere_id"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}
    if not filtered:
        return pack
    filtered["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.pacchetti_documentali.update_one(
        {"pack_id": pack_id, "user_id": user["user_id"]}, {"$set": filtered}
    )
    return await get_pacchetto(pack_id, user["user_id"])


# ═══════════════════════════════════════════════════════════════
#  D4 — PREPARA INVIO (preview email)
# ═══════════════════════════════════════════════════════════════

@router.post("/pacchetti-documentali/{pack_id}/prepara-invio")
async def api_prepara_invio(pack_id: str, user: dict = Depends(get_current_user)):
    """D4: Prepare send — generate email draft + attachment list + warnings."""
    result = await prepara_invio(pack_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ═══════════════════════════════════════════════════════════════
#  D5 — INVIO EMAIL + LOG
# ═══════════════════════════════════════════════════════════════

@router.post("/pacchetti-documentali/{pack_id}/invia")
async def api_invia_pacchetto(pack_id: str, send_data: dict, user: dict = Depends(get_current_user)):
    """D5: Send package email via Resend and log the send."""
    result = await invia_email_pacchetto(pack_id, user["user_id"], send_data)
    if result.get("error"):
        await log_activity(user, "send_email", "pacchetto_documentale", pack_id,
                           label=f"Invio FALLITO: {result['error'][:50]}",
                           details={"error": result["error"], "to": send_data.get("to", [])})
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "send_email", "pacchetto_documentale", pack_id,
                       label=f"Email inviata a {', '.join(send_data.get('to', []))}",
                       details={"to": send_data.get("to", []), "cc": send_data.get("cc", []),
                                "n_attachments": len(result.get("attachments_sent", []))})
    return result


@router.get("/pacchetti-documentali/{pack_id}/invii")
async def api_get_invii(pack_id: str, user: dict = Depends(get_current_user)):
    """D5: Get send history for a package."""
    return await get_invii(pack_id, user["user_id"])
