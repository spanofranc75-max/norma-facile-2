"""Backup & Restore — Full JSON dump of all critical business data.

Allows the admin to download a complete backup of all collections
and optionally restore from a previous backup.
"""
import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/admin/backup", tags=["backup"])
logger = logging.getLogger(__name__)

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
]


def _serialize(obj):
    """JSON serializer for MongoDB-specific types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__str__'):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@router.get("/export")
async def export_backup(user: dict = Depends(get_current_user)):
    """Export a full JSON backup of all user data."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)

    backup = {
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
            coll = db[coll_name]
            # Sempre filtra per user_id — mai esportare
            # dati di altri utenti
            docs = await coll.find(
                {"user_id": uid},
                {"_id": 0}
            ).to_list(None)
            backup["data"][coll_name] = docs
            backup["stats"][coll_name] = len(docs)
            total_records += len(docs)
        except Exception as e:
            logger.warning(
                f"Backup collection {coll_name} failed: {e}"
            )
            backup["data"][coll_name] = []
            backup["stats"][coll_name] = 0

    backup["metadata"]["total_records"] = total_records

    # Generate JSON
    json_bytes = json.dumps(backup, default=_serialize, ensure_ascii=False, indent=2).encode("utf-8")
    date_str = now.strftime("%Y%m%d_%H%M")
    filename = f"backup_normafacile_{date_str}.json"

    # Save backup metadata
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

    if "metadata" not in backup or "data" not in backup:
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
    }
    return pk_map.get(coll_name, "")
