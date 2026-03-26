"""Client snapshot migration — backfills client_snapshot on all existing documents.

This endpoint is intended to be called ONCE after deploying the snapshot feature.
It reads each document's client_id, fetches the current client data, and stores
a snapshot on the document. For documents where the client has already been modified,
a manual review may be needed.
"""
import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from core.database import db
from core.security import get_current_user
from core.rbac import require_role
from services.client_snapshot import build_snapshot

router = APIRouter(prefix="/admin/migration", tags=["migration"])
logger = logging.getLogger(__name__)

MIGRATION_KEY = os.environ.get("MIGRATION_KEY", "nf2026-snapshot-run")

DOCUMENT_COLLECTIONS = [
    {"name": "invoices", "id_field": "invoice_id", "label_field": "document_number"},
    {"name": "preventivi", "id_field": "preventivo_id", "label_field": "number"},
    {"name": "ddt", "id_field": "ddt_id", "label_field": "number"},
    {"name": "commesse", "id_field": "commessa_id", "label_field": "numero"},
]


@router.get("/run-snapshot", response_class=HTMLResponse)
async def run_snapshot_via_link(key: str = Query(...)):
    """Browser-friendly migration endpoint. Access via URL with secret key."""
    if key != MIGRATION_KEY:
        return HTMLResponse("<h2>Chiave non valida</h2>", status_code=403)

    # Find ALL users to migrate (not user-specific since no auth)
    all_users = await db.users.distinct("user_id")
    grand_report = {}

    for uid in all_users:
        tid = "default"  # migration backfill — all existing data is in default tenant
        client_cache = {}
        user_report = {"total_updated": 0, "total_skipped": 0, "total_no_client": 0, "collections": {}}

        for coll_info in DOCUMENT_COLLECTIONS:
            coll_name = coll_info["name"]
            id_field = coll_info["id_field"]
            label_field = coll_info["label_field"]
            coll = db[coll_name]

            coll_report = {"updated": 0, "skipped": 0, "no_client": 0, "errors": []}

            cursor = coll.find(
                {"user_id": uid, "tenant_id": tid, "client_snapshot": {"$exists": False}},
                {"_id": 0, id_field: 1, label_field: 1, "client_id": 1}
            )
            docs = await cursor.to_list(length=5000)

            for doc in docs:
                client_id = doc.get("client_id")
                doc_id = doc.get(id_field, "?")

                if not client_id:
                    coll_report["no_client"] += 1
                    continue

                if client_id not in client_cache:
                    client_cache[client_id] = await build_snapshot(client_id)

                snapshot = client_cache[client_id]
                if not snapshot:
                    coll_report["errors"].append(f"client {client_id} non trovato")
                    continue

                await coll.update_one(
                    {id_field: doc_id},
                    {"$set": {"client_snapshot": snapshot, "updated_at": datetime.now(timezone.utc)}}
                )
                coll_report["updated"] += 1

            already = await coll.count_documents(
                {"user_id": uid, "tenant_id": tid, "client_snapshot": {"$exists": True}}
            )
            coll_report["skipped"] = already - coll_report["updated"]

            user_report["collections"][coll_name] = coll_report
            user_report["total_updated"] += coll_report["updated"]
            user_report["total_skipped"] += coll_report["skipped"]
            user_report["total_no_client"] += coll_report["no_client"]

        grand_report[uid] = user_report

    # Build HTML response
    total_updated = sum(r["total_updated"] for r in grand_report.values())
    total_skipped = sum(r["total_skipped"] for r in grand_report.values())

    rows_html = ""
    for uid, r in grand_report.items():
        if r["total_updated"] == 0 and r["total_skipped"] == 0 and r["total_no_client"] == 0:
            continue
        for coll_name, c in r["collections"].items():
            if c["updated"] > 0 or c["skipped"] > 0:
                rows_html += f"<tr><td>{coll_name}</td><td><b>{c['updated']}</b></td><td>{c['skipped']}</td><td>{c['no_client']}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
    <style>body{{font-family:Arial;max-width:600px;margin:40px auto;padding:20px}}
    h1{{color:#1e40af}}table{{border-collapse:collapse;width:100%}}
    th,td{{border:1px solid #ddd;padding:8px;text-align:center}}
    th{{background:#f0f4ff}}.ok{{color:#16a34a;font-size:24px}}</style></head>
    <body><h1>Migrazione Snapshot Completata</h1>
    <p class='ok'>&#10004; {total_updated} documenti aggiornati, {total_skipped} gia completi</p>
    <table><thead><tr><th>Collezione</th><th>Aggiornati</th><th>Gia OK</th><th>Senza cliente</th></tr></thead>
    <tbody>{rows_html if rows_html else '<tr><td colspan=4>Nessun documento da aggiornare</td></tr>'}</tbody></table>
    <p style='margin-top:20px;color:#666;font-size:12px'>Puoi chiudere questa pagina.</p></body></html>"""

    logger.info(f"Snapshot migration via link: {total_updated} updated, {total_skipped} skipped")
    return HTMLResponse(html)


@router.post("/backfill-client-snapshots")
async def backfill_client_snapshots(user: dict = Depends(require_role("admin"))):
    """Add client_snapshot to all documents that don't have one yet.
    
    This reads the current client data and stores it as a snapshot.
    IMPORTANT: Run this only after verifying client data is correct.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    report = {"total_updated": 0, "total_skipped": 0, "total_no_client": 0, "collections": {}}
    
    # Cache client data to avoid repeated lookups
    client_cache = {}
    
    for coll_info in DOCUMENT_COLLECTIONS:
        coll_name = coll_info["name"]
        id_field = coll_info["id_field"]
        label_field = coll_info["label_field"]
        coll = db[coll_name]
        
        coll_report = {"updated": 0, "skipped": 0, "no_client": 0, "errors": []}
        
        # Find documents without client_snapshot
        cursor = coll.find(
            {"user_id": uid, "tenant_id": tid, "client_snapshot": {"$exists": False}},
            {"_id": 0, id_field: 1, label_field: 1, "client_id": 1}
        )
        docs = await cursor.to_list(length=5000)
        
        for doc in docs:
            client_id = doc.get("client_id")
            doc_id = doc.get(id_field, "?")
            doc_label = doc.get(label_field, "?")
            
            if not client_id:
                coll_report["no_client"] += 1
                continue
            
            # Use cache
            if client_id not in client_cache:
                client_cache[client_id] = await build_snapshot(client_id)
            
            snapshot = client_cache[client_id]
            if not snapshot:
                coll_report["errors"].append(f"{doc_label}: client {client_id} non trovato")
                continue
            
            await coll.update_one(
                {id_field: doc_id},
                {"$set": {"client_snapshot": snapshot, "updated_at": datetime.now(timezone.utc)}}
            )
            coll_report["updated"] += 1
        
        # Count already-migrated docs
        already = await coll.count_documents(
            {"user_id": uid, "tenant_id": tid, "client_snapshot": {"$exists": True}}
        )
        coll_report["skipped"] = already - coll_report["updated"]
        
        report["collections"][coll_name] = coll_report
        report["total_updated"] += coll_report["updated"]
        report["total_skipped"] += coll_report["skipped"]
        report["total_no_client"] += coll_report["no_client"]
    
    logger.info(f"Client snapshot migration completed: {report['total_updated']} updated")
    return {"message": "Migrazione snapshot completata", "report": report}


@router.get("/snapshot-status")
async def snapshot_status(user: dict = Depends(require_role("admin"))):
    """Check how many documents have/lack client_snapshot."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    result = {}
    
    for coll_info in DOCUMENT_COLLECTIONS:
        coll_name = coll_info["name"]
        coll = db[coll_name]
        total = await coll.count_documents({"user_id": uid, "tenant_id": tid})
        with_snapshot = await coll.count_documents({"user_id": uid, "tenant_id": tid, "client_snapshot": {"$exists": True}})
        without = total - with_snapshot
        result[coll_name] = {
            "total": total,
            "with_snapshot": with_snapshot,
            "without_snapshot": without,
            "coverage": f"{(with_snapshot / total * 100):.0f}%" if total > 0 else "N/A"
        }
    
    return result


@router.post("/set-default-client-status")
async def set_default_client_status(user: dict = Depends(require_role("admin"))):
    """Set status='active' on all clients that don't have a status field yet."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin possono eseguire migrazioni")
    
    uid = user["user_id"]
    tid = user["tenant_id"]
    result = await db.clients.update_many(
        {"user_id": uid, "tenant_id": tid, "status": {"$exists": False}},
        {"$set": {"status": "active"}}
    )
    
    return {
        "message": f"Status impostato su {result.modified_count} clienti",
        "modified_count": result.modified_count
    }
