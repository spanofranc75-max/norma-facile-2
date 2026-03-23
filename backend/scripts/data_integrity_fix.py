"""
NormaFacile 2.0 — Data Integrity Fix (Batch 1)
Fixes a-e as approved by user:
  a) Backfill user_id on legacy records
  b) Export + delete orphaned records
  c) Fix inconsistent obblighi states
  d) Delete corrupted records without primary ID
  e) Recalculate package summaries
"""
import asyncio
import json
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import db

LOG = []

def log(action, severity, message, details=None):
    entry = {"action": action, "severity": severity, "message": message, "details": details}
    LOG.append(entry)
    icon = {"fix": "+", "delete": "X", "export": ">", "info": "."}
    print(f"  [{icon.get(action, '?')}] {message}")


async def fix_a_backfill_user_id():
    """Backfill user_id on legacy records using commessa ownership."""
    print("\n=== FIX A: Backfill user_id ===")

    # Build commessa -> user_id map
    commessa_owner = {}
    async for doc in db.commesse.find({}, {"commessa_id": 1, "user_id": 1}):
        if doc.get("user_id"):
            commessa_owner[doc["commessa_id"]] = doc["user_id"]

    # Get all distinct user_ids to find the fallback
    all_users = await db.users.find({}, {"user_id": 1}).to_list(100)
    fallback_user = all_users[0]["user_id"] if all_users else None

    # a1) non_conformities (CRITICAL - 4/4 missing)
    ncs = await db.non_conformities.find(
        {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
        {"_id": 1, "nc_id": 1, "audit_id": 1}
    ).to_list(100)

    for nc in ncs:
        # Try to find owner via linked audit
        owner = None
        if nc.get("audit_id"):
            audit = await db.audits.find_one({"audit_id": nc["audit_id"]}, {"user_id": 1})
            if audit and audit.get("user_id"):
                owner = audit["user_id"]
        if not owner:
            owner = fallback_user
        if owner:
            await db.non_conformities.update_one({"_id": nc["_id"]}, {"$set": {"user_id": owner}})
    log("fix", "critical", f"non_conformities: backfilled user_id on {len(ncs)} records")

    # a2) audits (check if any missing)
    count = await db.audits.count_documents({"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]})
    if count > 0 and fallback_user:
        await db.audits.update_many(
            {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
            {"$set": {"user_id": fallback_user}}
        )
        log("fix", "warning", f"audits: backfilled user_id on {count} records")
    else:
        log("info", "info", f"audits: user_id OK ({count} missing)")

    # a3) instruments
    count = await db.instruments.count_documents({"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]})
    if count > 0 and fallback_user:
        await db.instruments.update_many(
            {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
            {"$set": {"user_id": fallback_user}}
        )
        log("fix", "warning", f"instruments: backfilled user_id on {count} records")

    # a4) welders
    count = await db.welders.count_documents({"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]})
    if count > 0 and fallback_user:
        await db.welders.update_many(
            {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
            {"$set": {"user_id": fallback_user}}
        )
        log("fix", "warning", f"welders: backfilled user_id on {count} records")

    # a5) pacchetti_documentali
    packs = await db.pacchetti_documentali.find(
        {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
        {"_id": 1, "commessa_id": 1}
    ).to_list(200)
    fixed = 0
    for p in packs:
        owner = commessa_owner.get(p.get("commessa_id"), fallback_user)
        if owner:
            await db.pacchetti_documentali.update_one({"_id": p["_id"]}, {"$set": {"user_id": owner}})
            fixed += 1
    if fixed:
        log("fix", "warning", f"pacchetti_documentali: backfilled user_id on {fixed} records")


async def fix_b_delete_orphans():
    """Export and delete records pointing to non-existent commesse."""
    print("\n=== FIX B: Export + delete record orfani ===")

    all_commesse_ids = set()
    async for doc in db.commesse.find({}, {"commessa_id": 1}):
        all_commesse_ids.add(doc.get("commessa_id"))

    collections_to_check = [
        ("commesse_normative", "commessa_id"),
        ("obblighi_commessa", "commessa_id"),
        ("pacchetti_documentali", "commessa_id"),
    ]

    backup_data = {}
    for coll_name, field in collections_to_check:
        orphans = []
        async for doc in db[coll_name].find({field: {"$nin": list(all_commesse_ids)}}, {"_id": 0}):
            if doc.get(field):  # Skip docs without the field
                orphans.append(doc)

        if orphans:
            backup_data[coll_name] = orphans
            # Delete orphans
            orphan_values = [o[field] for o in orphans]
            result = await db[coll_name].delete_many({
                field: {"$in": orphan_values, "$nin": list(all_commesse_ids)}
            })
            log("delete", "warning",
                f"{coll_name}: eliminati {result.deleted_count} record orfani (backup salvato)")
        else:
            log("info", "info", f"{coll_name}: nessun orfano")

    # Save backup
    if backup_data:
        backup_path = "/app/backend/scripts/orphans_backup.json"
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2, default=str)
        log("export", "info", f"Backup orfani salvato: {backup_path}")


async def fix_c_inconsistent_obblighi():
    """Fix obblighi with status=completato but blocking_level=hard_block."""
    print("\n=== FIX C: Obblighi stato incoerente ===")

    bad = await db.obblighi_commessa.find(
        {"status": "completato", "blocking_level": {"$in": ["hard_block", "hard"]}},
        {"_id": 1, "obbligo_id": 1, "blocking_level": 1, "fonte": 1}
    ).to_list(100)

    for doc in bad:
        await db.obblighi_commessa.update_one(
            {"_id": doc["_id"]},
            {"$set": {"blocking_level": "none", "blocking_level_sort": 99}}
        )
        log("fix", "warning",
            f"obbligo {doc.get('obbligo_id')}: blocking_level hard_block -> none (status gia completato)")

    if not bad:
        log("info", "info", "Nessun obbligo incoerente trovato")


async def fix_d_corrupted_records():
    """Delete records missing their primary ID field."""
    print("\n=== FIX D: Record corrotti senza ID primario ===")

    checks = [
        ("instruments", "instrument_id"),
        ("welders", "welder_id"),
    ]

    for coll_name, id_field in checks:
        corrupted = await db[coll_name].find(
            {"$or": [{id_field: {"$exists": False}}, {id_field: None}, {id_field: ""}]},
            {"_id": 1}
        ).to_list(50)

        if corrupted:
            # Backup before delete
            backup = []
            for c in corrupted:
                doc = await db[coll_name].find_one({"_id": c["_id"]}, {"_id": 0})
                if doc:
                    backup.append(doc)

            backup_path = f"/app/backend/scripts/{coll_name}_corrupted_backup.json"
            with open(backup_path, "w") as f:
                json.dump(backup, f, indent=2, default=str)

            result = await db[coll_name].delete_many(
                {"_id": {"$in": [c["_id"] for c in corrupted]}}
            )
            log("delete", "warning",
                f"{coll_name}: eliminati {result.deleted_count} record senza {id_field} (backup: {backup_path})")
        else:
            log("info", "info", f"{coll_name}: tutti i record hanno {id_field}")


async def fix_e_recalculate_summaries():
    """Recalculate package summaries from actual items."""
    print("\n=== FIX E: Ricalcolo summary pacchetti documentali ===")

    from datetime import date
    today_str = date.today().isoformat()

    packs = await db.pacchetti_documentali.find({}, {"_id": 1, "pack_id": 1, "items": 1, "summary": 1}).to_list(500)

    fixed = 0
    for p in packs:
        items = p.get("items", [])
        total = len(items)
        attached = sum(1 for i in items if i.get("status") in ("allegato", "attached", "valido"))
        missing = sum(1 for i in items if i.get("status") in ("mancante", "missing", "da_allegare", None, ""))
        expired = sum(1 for i in items if i.get("status") in ("scaduto", "expired"))

        # Also check by scadenza date
        for item in items:
            scad = item.get("scadenza") or item.get("expiry_date")
            if scad and scad < today_str and item.get("status") not in ("scaduto", "expired"):
                expired += 1
                missing = max(0, missing - 1)  # Reclassify

        new_summary = {
            "total_required": total,
            "attached": attached,
            "missing": missing,
            "expired": expired,
        }

        old_summary = p.get("summary", {})
        if (old_summary.get("total_required") != total or
            old_summary.get("attached") != attached or
            old_summary.get("missing") != missing or
            old_summary.get("expired") != expired):
            await db.pacchetti_documentali.update_one(
                {"_id": p["_id"]},
                {"$set": {"summary": new_summary}}
            )
            fixed += 1

    log("fix", "warning" if fixed > 0 else "info",
        f"pacchetti_documentali: {fixed}/{len(packs)} summary ricalcolati")


async def main():
    print("=" * 60)
    print("NormaFacile 2.0 — Data Integrity Fix (Batch 1)")
    print("=" * 60)

    await fix_a_backfill_user_id()
    await fix_b_delete_orphans()
    await fix_c_inconsistent_obblighi()
    await fix_d_corrupted_records()
    await fix_e_recalculate_summaries()

    # Save log
    log_path = "/app/DATA_INTEGRITY_FIX_LOG.json"
    with open(log_path, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions": LOG,
            "summary": {
                "fixes": sum(1 for l in LOG if l["action"] == "fix"),
                "deletes": sum(1 for l in LOG if l["action"] == "delete"),
                "exports": sum(1 for l in LOG if l["action"] == "export"),
            }
        }, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("COMPLETATO")
    print("=" * 60)
    fixes = sum(1 for l in LOG if l["action"] == "fix")
    deletes = sum(1 for l in LOG if l["action"] == "delete")
    print(f"  Fix applicati: {fixes}")
    print(f"  Record eliminati: {deletes} operazioni")
    print(f"  Log salvato: {log_path}")


if __name__ == "__main__":
    asyncio.run(main())
