"""Backup & Restore — Full JSON dump of all critical business data.

Async backup: start → poll status → download when ready.
Portable: JSON format with manifest, independent of DB name.
"""
import io
import json
import os
import logging
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/admin/backup", tags=["backup"])
logger = logging.getLogger(__name__)

# In-memory job tracker: {backup_id: {status, progress, filepath, error, ...}}
_backup_jobs: dict = {}

# All critical collections to backup
BACKUP_COLLECTIONS = [
    "commesse",
    "preventivi",
    "clients",
    "invoices",
    "ddt",
    "fpc_projects",
    "gate_certifications",
    "welders",
    "instruments",
    "company_docs",
    "distinte",
    "rilievi",
    "fatture_ricevute",
    "consumable_batches",
    "project_costs",
    "audit_findings",
    "company_settings",
    "catalogo_profili",
    "articoli",
    "document_counters",
    "perizie",
    "sopralluoghi",
]


def _serialize(obj):
    """JSON serializer for MongoDB-specific types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__str__'):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _strip_large_base64(doc: dict) -> dict:
    """Remove large base64 data from backup to keep file size manageable.
    Object storage paths are kept; only inline base64 blobs > 10KB are stripped.
    """
    cleaned = {}
    for k, v in doc.items():
        if isinstance(v, str) and len(v) > 10_000 and v.startswith("data:"):
            cleaned[k] = "__BASE64_STRIPPED__"
        elif isinstance(v, list):
            cleaned[k] = [_strip_large_base64(item) if isinstance(item, dict) else
                          ("__BASE64_STRIPPED__" if isinstance(item, str) and len(item) > 10_000 and item.startswith("data:") else item)
                          for item in v]
        elif isinstance(v, dict):
            cleaned[k] = _strip_large_base64(v)
        else:
            cleaned[k] = v
    return cleaned


# ── Async Backup Job ──

async def _run_backup_job(backup_id: str, uid: str, user_email: str):
    """Background task: export all collections to a JSON file."""
    job = _backup_jobs[backup_id]
    try:
        now = datetime.now(timezone.utc)
        backup = {
            "manifest": {
                "version": "2.0",
                "app": "Norma Facile 2.0",
                "created_at": now.isoformat(),
                "user_id": uid,
                "user_email": user_email,
                "collections": {},
            },
            "data": {},
        }

        total_records = 0
        total_colls = len(BACKUP_COLLECTIONS)

        for idx, coll_name in enumerate(BACKUP_COLLECTIONS):
            job["progress"] = f"{idx + 1}/{total_colls} — {coll_name}"
            try:
                docs = await db[coll_name].find(
                    {"user_id": uid}, {"_id": 0}
                ).to_list(None)
                # Strip large base64 to keep backup portable
                docs_clean = [_strip_large_base64(d) for d in docs]
                backup["data"][coll_name] = docs_clean
                backup["manifest"]["collections"][coll_name] = len(docs)
                total_records += len(docs)
            except Exception as e:
                logger.warning(f"Backup collection {coll_name} failed: {e}")
                backup["data"][coll_name] = []
                backup["manifest"]["collections"][coll_name] = 0

        backup["manifest"]["total_records"] = total_records

        # Write to temp file
        json_bytes = json.dumps(backup, default=_serialize, ensure_ascii=False, indent=2).encode("utf-8")
        date_str = now.strftime("%Y%m%d_%H%M")
        filename = f"backup_normafacile_{date_str}.json"
        filepath = os.path.join(tempfile.gettempdir(), filename)

        with open(filepath, "wb") as f:
            f.write(json_bytes)

        # Log to DB
        await db.backup_log.insert_one({
            "user_id": uid,
            "date": now,
            "filename": filename,
            "total_records": total_records,
            "stats": backup["manifest"]["collections"],
            "size_bytes": len(json_bytes),
            "auto": False,
        })

        job.update({
            "status": "completato",
            "progress": "Completato",
            "filepath": filepath,
            "filename": filename,
            "total_records": total_records,
            "size_bytes": len(json_bytes),
            "completed_at": now.isoformat(),
        })
        logger.info(f"[BACKUP] Job {backup_id} completato: {total_records} record, {len(json_bytes)} bytes")

    except Exception as e:
        job.update({"status": "errore", "error": str(e)})
        logger.error(f"[BACKUP] Job {backup_id} fallito: {e}")


@router.post("/start")
async def start_backup(user: dict = Depends(get_current_user)):
    """Start an async backup job. Returns backup_id for polling."""
    uid = user["user_id"]

    # Check no other job is running for this user
    for bid, job in _backup_jobs.items():
        if job.get("user_id") == uid and job.get("status") == "in_corso":
            return {"backup_id": bid, "status": "in_corso", "message": "Backup gia in corso"}

    backup_id = f"bk_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uid[:8]}"
    _backup_jobs[backup_id] = {
        "status": "in_corso",
        "user_id": uid,
        "progress": "Avvio...",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    from core.background import safe_background_task
    safe_background_task(_run_backup_job(backup_id, uid, user.get("email", "")), "backup")
    return {"backup_id": backup_id, "status": "in_corso"}


@router.get("/status/{backup_id}")
async def get_backup_status(backup_id: str, user: dict = Depends(get_current_user)):
    """Poll backup job status."""
    job = _backup_jobs.get(backup_id)
    if not job or job.get("user_id") != user["user_id"]:
        raise HTTPException(404, "Backup job non trovato")
    return {
        "backup_id": backup_id,
        "status": job["status"],
        "progress": job.get("progress", ""),
        "error": job.get("error"),
        "total_records": job.get("total_records"),
        "size_bytes": job.get("size_bytes"),
        "filename": job.get("filename"),
    }


@router.get("/download/{backup_id}")
async def download_backup(backup_id: str, user: dict = Depends(get_current_user)):
    """Download completed backup file."""
    job = _backup_jobs.get(backup_id)
    if not job or job.get("user_id") != user["user_id"]:
        raise HTTPException(404, "Backup job non trovato")
    if job["status"] != "completato":
        raise HTTPException(400, "Backup non ancora completato")

    filepath = job.get("filepath")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(404, "File backup non trovato")

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=job.get("filename", "backup.json"),
    )


# ── Legacy export (kept for backward compat) ──

@router.get("/export")
async def export_backup(user: dict = Depends(get_current_user)):
    """Export a full JSON backup of all user data (synchronous, legacy)."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)

    backup = {
        "manifest": {
            "version": "2.0",
            "app": "Norma Facile 2.0",
            "created_at": now.isoformat(),
            "user_id": uid,
            "user_email": user.get("email", ""),
            "collections": {},
        },
        "metadata": {
            "date": now.isoformat(),
            "version": "2.0",
            "app": "Norma Facile 2.0",
            "user_id": uid,
            "user_email": user.get("email", ""),
        },
        "data": {},
        "stats": {},
    }

    total_records = 0
    for coll_name in BACKUP_COLLECTIONS:
        try:
            docs = await db[coll_name].find(
                {"user_id": uid}, {"_id": 0}
            ).to_list(None)
            docs_clean = [_strip_large_base64(d) for d in docs]
            backup["data"][coll_name] = docs_clean
            backup["stats"][coll_name] = len(docs)
            backup["manifest"]["collections"][coll_name] = len(docs)
            total_records += len(docs)
        except Exception as e:
            logger.warning(f"Backup collection {coll_name} failed: {e}")
            backup["data"][coll_name] = []
            backup["stats"][coll_name] = 0

    backup["metadata"]["total_records"] = total_records
    backup["manifest"]["total_records"] = total_records

    json_bytes = json.dumps(backup, default=_serialize, ensure_ascii=False, indent=2).encode("utf-8")
    date_str = now.strftime("%Y%m%d_%H%M")
    filename = f"backup_normafacile_{date_str}.json"

    await db.backup_log.insert_one({
        "user_id": uid,
        "date": now,
        "filename": filename,
        "total_records": total_records,
        "stats": backup["stats"],
        "size_bytes": len(json_bytes),
    })

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/last")
async def get_last_backup(user: dict = Depends(get_current_user)):
    """Get info about the last backup performed."""
    uid = user["user_id"]
    last = await db.backup_log.find_one(
        {"user_id": uid},
        {"_id": 0},
        sort=[("date", -1)],
    )
    if not last:
        return {"last_backup": None}
    return {
        "last_backup": {
            "date": last["date"].isoformat() if isinstance(last["date"], datetime) else str(last["date"]),
            "filename": last.get("filename", ""),
            "total_records": last.get("total_records", 0),
            "size_bytes": last.get("size_bytes", 0),
            "stats": last.get("stats", {}),
        }
    }


@router.get("/stats")
async def get_backup_stats(user: dict = Depends(get_current_user)):
    """Get current data stats (how many records per collection)."""
    uid = user["user_id"]
    stats = {}
    total = 0
    for coll_name in BACKUP_COLLECTIONS:
        try:
            count = await db[coll_name].count_documents({"user_id": uid})
            stats[coll_name] = count
            total += count
        except Exception:
            stats[coll_name] = 0
    return {"stats": stats, "total": total}


@router.get("/history")
async def get_backup_history(user: dict = Depends(get_current_user)):
    """Get list of all backup logs for the current user."""
    uid = user["user_id"]
    logs = await db.backup_log.find(
        {"user_id": uid},
        {"_id": 0},
    ).sort("date", -1).to_list(20)

    items = []
    for log in logs:
        d = log.get("date")
        items.append({
            "date": d.isoformat() if isinstance(d, datetime) else str(d),
            "filename": log.get("filename", ""),
            "total_records": log.get("total_records", 0),
            "size_bytes": log.get("size_bytes", 0),
            "auto": log.get("auto", False),
        })
    return {"history": items}


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    mode: str = Form("merge"),
    user: dict = Depends(get_current_user),
):
    """Restore data from a JSON backup file.

    mode = "merge"  → UPSERT: existing records updated, new ones inserted.
    mode = "wipe"   → SOSTITUZIONE TOTALE: all user data wiped first, then imported.
    """
    uid = user["user_id"]

    if mode not in ("merge", "wipe"):
        raise HTTPException(400, "Modalità non valida. Usa 'merge' o 'wipe'.")

    content = await file.read()
    try:
        backup = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "File JSON non valido")

    if "metadata" not in backup and "manifest" not in backup or "data" not in backup:
        raise HTTPException(400, "Formato backup non riconosciuto")

    total_deleted = 0

    # --- WIPE MODE: cancella tutti i dati utente prima dell'importazione ---
    if mode == "wipe":
        for coll_name in BACKUP_COLLECTIONS:
            try:
                coll = db[coll_name]
                del_result = await coll.delete_many({"user_id": uid})
                total_deleted += del_result.deleted_count
            except Exception as e:
                logger.warning(f"Wipe error in {coll_name}: {e}")

    results = {}
    total_inserted = 0
    total_updated = 0
    total_errors = 0

    for coll_name, docs in backup.get("data", {}).items():
        if coll_name not in BACKUP_COLLECTIONS:
            continue
        if not docs:
            continue

        coll = db[coll_name]
        inserted = 0
        updated = 0
        errors = 0

        pk_field = _get_pk_field(coll_name)

        for doc in docs:
            # Forza sempre user_id dell'utente corrente
            # (gestisce migrazione preview → deploy)
            doc["user_id"] = uid
            doc.pop("_id", None)

            try:
                if pk_field and doc.get(pk_field):
                    # Upsert basato SOLO sul pk_field
                    # NON su user_id → evita duplicati
                    # quando user_id cambia tra ambienti
                    result = await coll.update_one(
                        {pk_field: doc[pk_field]},
                        {"$set": doc},
                        upsert=True,
                    )
                    if result.upserted_id:
                        inserted += 1
                    else:
                        updated += 1
                else:
                    # Documenti senza PK: verifica duplicati
                    # con hash del contenuto prima di inserire
                    import hashlib
                    import json as _json
                    doc_hash = hashlib.md5(
                        _json.dumps(
                            {k: v for k, v in doc.items()
                             if k != "user_id"},
                            sort_keys=True,
                            default=str
                        ).encode()
                    ).hexdigest()

                    existing = await coll.find_one(
                        {"_content_hash": doc_hash,
                         "user_id": uid}
                    )
                    if not existing:
                        doc["_content_hash"] = doc_hash
                        await coll.insert_one(doc)
                        inserted += 1
                    else:
                        updated += 1
            except Exception as e:
                logger.warning(
                    f"Restore error in {coll_name}: {e}"
                )
                errors += 1

        results[coll_name] = {"inserted": inserted, "updated": updated, "errors": errors}
        total_inserted += inserted
        total_updated += updated
        total_errors += errors

    msg_parts = []
    if mode == "wipe":
        msg_parts.append(f"{total_deleted} eliminati")
    msg_parts.append(f"{total_inserted} inseriti")
    msg_parts.append(f"{total_updated} aggiornati")
    msg_parts.append(f"{total_errors} errori")

    return {
        "message": f"Restore completato ({('Sostituzione Totale' if mode == 'wipe' else 'Unisci/Aggiorna')}): {', '.join(msg_parts)}",
        "mode": mode,
        "total_deleted": total_deleted if mode == "wipe" else 0,
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "total_errors": total_errors,
        "details": results,
    }


def _get_pk_field(coll_name: str) -> str:
    """Get the primary key field name for a given collection."""
    pk_map = {
        "commesse": "commessa_id",
        "preventivi": "preventivo_id",
        "clients": "client_id",
        "invoices": "invoice_id",
        "ddt": "ddt_id",
        "fpc_projects": "project_id",
        "gate_certifications": "cert_id",
        "welders": "welder_id",
        "instruments": "instrument_id",
        "company_docs": "doc_id",
        "distinte": "distinta_id",
        "rilievi": "rilievo_id",
        "fatture_ricevute": "fr_id",
        "consumable_batches": "batch_id",
        "project_costs": "cost_id",
        "audit_findings": "finding_id",
        "articoli": "articolo_id",
        "company_settings": "user_id",
        "catalogo_profili": "codice",
        "document_counters": "counter_id",
        "perizie": "perizia_id",
        "sopralluoghi": "sopralluogo_id",
    }
    return pk_map.get(coll_name, "")
