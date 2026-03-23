"""
Admin Data Integrity Tool — Reusable endpoint for DB consistency checks.
Based on /app/backend/scripts/data_integrity_check.py, transformed into
a proper admin API with report storage and history.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.database import db
from core.security import get_current_user
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/data-integrity", tags=["admin"])

COLLECTION = "data_integrity_reports"


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accesso riservato agli admin")


# ─── Check Functions ──────────────────────────────────────────────


async def _check_duplicates():
    """1/6 — Duplicati vs unique constraints."""
    results = []

    checks = [
        ("obblighi_commessa", [
            {"$group": {"_id": {"dedupe_key": "$dedupe_key", "user_id": "$user_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
        ("commesse_normative", [
            {"$group": {"_id": {"commessa_id": "$commessa_id", "normativa": "$normativa", "user_id": "$user_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
        ("emissioni_documentali", [
            {"$group": {"_id": {"ramo_id": "$ramo_id", "emission_type": "$emission_type", "emission_seq": "$emission_seq", "user_id": "$user_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
        ("cantieri_sicurezza", [
            {"$group": {"_id": {"user_id": "$user_id", "cantiere_id": "$cantiere_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
        ("pacchetti_committenza", [
            {"$group": {"_id": {"package_id": "$package_id", "user_id": "$user_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
        ("analisi_committenza", [
            {"$group": {"_id": {"analysis_id": "$analysis_id", "user_id": "$user_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]),
    ]

    for coll_name, pipeline in checks:
        dupes = await db[coll_name].aggregate(pipeline).to_list(100)
        if dupes:
            severity = "critical" if coll_name in ("obblighi_commessa", "commesse_normative", "emissioni_documentali") else "warning"
            results.append({
                "severity": severity,
                "message": f"{coll_name}: {len(dupes)} gruppi di duplicati",
                "details": [{"key": str(d["_id"]), "count": d["count"]} for d in dupes[:5]]
            })
        else:
            results.append({"severity": "ok", "message": f"{coll_name}: nessun duplicato"})

    return results


async def _check_broken_refs():
    """2/6 — Riferimenti rotti (foreign keys logiche)."""
    results = []

    all_commesse_ids = set()
    async for doc in db.commesse.find({}, {"commessa_id": 1}):
        all_commesse_ids.add(doc.get("commessa_id"))

    ref_checks = [
        ("commesse_normative", "commessa_id", all_commesse_ids),
        ("obblighi_commessa", "commessa_id", all_commesse_ids),
        ("pacchetti_documentali", "commessa_id", all_commesse_ids),
    ]

    for coll_name, field, valid_ids in ref_checks:
        broken = 0
        async for doc in db[coll_name].find({}, {field: 1}):
            if doc.get(field) and doc[field] not in valid_ids:
                broken += 1
        if broken:
            results.append({"severity": "warning", "message": f"{coll_name}: {broken} record con {field} inesistente"})
        else:
            results.append({"severity": "ok", "message": f"{coll_name} -> commesse ({field}): OK"})

    # emissioni -> rami
    all_ramo_ids = set()
    async for doc in db.commesse_normative.find({}, {"ramo_id": 1}):
        rid = doc.get("ramo_id")
        if rid:
            all_ramo_ids.add(rid)

    broken = 0
    async for doc in db.emissioni_documentali.find({}, {"ramo_id": 1}):
        if doc.get("ramo_id") and doc["ramo_id"] not in all_ramo_ids:
            broken += 1
    if broken:
        results.append({"severity": "critical", "message": f"emissioni_documentali: {broken} con ramo_id inesistente"})
    else:
        results.append({"severity": "ok", "message": "emissioni_documentali -> commesse_normative: OK"})

    # documenti_archivio -> commesse
    broken = 0
    async for doc in db.documenti_archivio.find({}, {"commessa_id": 1}):
        if doc.get("commessa_id") and doc["commessa_id"] not in all_commesse_ids:
            broken += 1
    if broken:
        results.append({"severity": "warning", "message": f"documenti_archivio: {broken} con commessa_id inesistente"})
    else:
        results.append({"severity": "ok", "message": "documenti_archivio -> commesse: OK"})

    # cantieri_sicurezza -> commesse
    broken = 0
    async for doc in db.cantieri_sicurezza.find({}, {"parent_commessa_id": 1}):
        pcid = doc.get("parent_commessa_id")
        if pcid and pcid not in all_commesse_ids:
            broken += 1
    if broken:
        results.append({"severity": "warning", "message": f"cantieri_sicurezza: {broken} con parent_commessa_id inesistente"})
    else:
        results.append({"severity": "ok", "message": "cantieri_sicurezza -> commesse: OK"})

    return results


async def _check_inconsistent_states():
    """3/6 — Stati logicamente incoerenti."""
    results = []

    # Emissioni "emessa" con gate non coerente
    emissioni = await db.emissioni_documentali.find(
        {"status": "emessa"}, {"_id": 0, "emission_id": 1, "gate_status": 1}
    ).to_list(500)
    bad_gates = [e for e in emissioni if e.get("gate_status") not in ("passed", "approved", None)]
    if bad_gates:
        results.append({"severity": "warning",
            "message": f"emissioni_documentali: {len(bad_gates)} emesse con gate non coerente",
            "details": [{"emission_id": e.get("emission_id"), "gate": e.get("gate_status")} for e in bad_gates[:5]]})
    else:
        results.append({"severity": "ok", "message": "emissioni emesse con gate coerente: OK"})

    # Obblighi "completato" ancora con blocking hard
    completed = await db.obblighi_commessa.find(
        {"status": "completato"}, {"_id": 0, "obbligo_id": 1, "blocking_level": 1}
    ).to_list(500)
    still_blocking = [o for o in completed if o.get("blocking_level") in ("hard_block", "hard")]
    if still_blocking:
        results.append({"severity": "warning",
            "message": f"obblighi_commessa: {len(still_blocking)} completati ma ancora hard_block"})
    else:
        results.append({"severity": "ok", "message": "obblighi completati senza blocking: OK"})

    # Pacchetti "pronto_invio" con documenti mancanti
    pacchetti = await db.pacchetti_documentali.find(
        {"status": "pronto_invio"}, {"_id": 0, "pack_id": 1, "summary": 1}
    ).to_list(200)
    bad_packs = [p for p in pacchetti if p.get("summary", {}).get("missing", 0) > 0 or p.get("summary", {}).get("expired", 0) > 0]
    if bad_packs:
        results.append({"severity": "critical",
            "message": f"pacchetti_documentali: {len(bad_packs)} pronto_invio con documenti mancanti/scaduti"})
    else:
        results.append({"severity": "ok", "message": "pacchetti pronto_invio coerenti: OK"})

    return results


async def _check_missing_fields():
    """4/6 — Campi obbligatori mancanti."""
    results = []

    checks = [
        ("obblighi_commessa", ["user_id", "commessa_id", "dedupe_key", "status"]),
        ("commesse_normative", ["user_id", "commessa_id", "normativa", "ramo_id"]),
        ("emissioni_documentali", ["user_id", "commessa_id", "ramo_id"]),
        ("cantieri_sicurezza", ["user_id", "cantiere_id"]),
        ("pacchetti_documentali", ["user_id", "commessa_id"]),
        ("documenti_archivio", ["user_id"]),
        ("audits", ["user_id", "audit_id"]),
        ("non_conformities", ["user_id", "nc_id"]),
        ("instruments", ["user_id", "instrument_id"]),
        ("welders", ["user_id", "welder_id"]),
    ]

    for coll_name, required_fields in checks:
        total = await db[coll_name].count_documents({})
        if total == 0:
            continue
        for field in required_fields:
            missing = await db[coll_name].count_documents(
                {"$or": [{field: {"$exists": False}}, {field: None}]}
            )
            if missing > 0:
                pct = round(missing / total * 100, 1)
                severity = "critical" if field == "user_id" and pct > 50 else "warning"
                results.append({"severity": severity,
                    "message": f"{coll_name}.{field}: mancante in {missing}/{total} ({pct}%)"})

    if not results:
        results.append({"severity": "ok", "message": "Tutti i campi obbligatori presenti"})

    return results


async def _check_snapshot_coherence():
    """5/6 — Coerenza snapshot vs stato reale."""
    results = []

    pacchetti = await db.pacchetti_documentali.find(
        {}, {"_id": 0, "pack_id": 1, "summary": 1, "items": 1}
    ).to_list(200)

    mismatches = []
    for p in pacchetti:
        stored = p.get("summary", {}).get("total_required", 0)
        actual = len(p.get("items", []))
        if stored != actual:
            mismatches.append({"pack_id": p.get("pack_id"), "summary": stored, "actual": actual})

    if mismatches:
        results.append({"severity": "warning",
            "message": f"pacchetti_documentali: {len(mismatches)} con summary != items count",
            "details": mismatches[:5]})
    else:
        results.append({"severity": "ok", "message": "pacchetti_documentali snapshot coerente: OK"})

    return results


async def _check_legacy():
    """6/6 — Duplicati logici e dati legacy."""
    results = []

    # Commesse con numero duplicato per stesso utente
    pipeline = [
        {"$group": {"_id": {"numero": "$numero", "user_id": "$user_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.commesse.aggregate(pipeline).to_list(100)
    if dupes:
        results.append({"severity": "warning",
            "message": f"commesse: {len(dupes)} numeri duplicati per stesso utente",
            "details": [{"numero": d["_id"]["numero"], "count": d["count"]} for d in dupes[:5]]})
    else:
        results.append({"severity": "ok", "message": "commesse: nessun numero duplicato"})

    # Documenti archivio logicamente duplicati
    pipeline = [
        {"$match": {"doc_type": {"$exists": True, "$nin": [None, ""]}, "filename": {"$exists": True, "$nin": [None, ""]}, "entity_id": {"$exists": True, "$nin": [None, ""]}}},
        {"$group": {"_id": {"entity_type": "$entity_type", "entity_id": "$entity_id", "doc_type": "$doc_type", "filename": "$filename"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.documenti_archivio.aggregate(pipeline).to_list(100)
    if dupes:
        results.append({"severity": "warning",
            "message": f"documenti_archivio: {len(dupes)} duplicati logici"})
    else:
        results.append({"severity": "ok", "message": "documenti_archivio: nessun duplicato logico"})

    # Zombie collections
    for coll_name in ["download_tokens", "sessions"]:
        count = await db[coll_name].count_documents({})
        if count > 0:
            results.append({"severity": "ok", "message": f"Collezione '{coll_name}': {count} documenti"})

    return results


# ─── API Endpoints ────────────────────────────────────────────────


@router.post("/run")
async def run_integrity_check(user: dict = Depends(get_current_user)):
    """Execute a full data integrity check and store the report."""
    _require_admin(user)

    logger.info(f"Data integrity check started by {user['user_id']}")

    sections = {
        "1_duplicati": await _check_duplicates(),
        "2_riferimenti_rotti": await _check_broken_refs(),
        "3_stati_incoerenti": await _check_inconsistent_states(),
        "4_campi_mancanti": await _check_missing_fields(),
        "5_snapshot_coerenza": await _check_snapshot_coherence(),
        "6_legacy_duplicati": await _check_legacy(),
    }

    # Build summary
    total_checks = 0
    critical_count = 0
    warning_count = 0
    ok_count = 0

    for checks in sections.values():
        for check in checks:
            total_checks += 1
            sev = check["severity"]
            if sev == "critical":
                critical_count += 1
            elif sev == "warning":
                warning_count += 1
            elif sev == "ok":
                ok_count += 1

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    report = {
        "report_id": f"dir_{uuid.uuid4().hex[:12]}",
        "status": status,
        "total_checks": total_checks,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "ok_count": ok_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user["user_id"],
        "sections": sections,
    }

    # Store in DB (let MongoDB generate _id)
    store_doc = {**report}
    await db[COLLECTION].insert_one(store_doc)

    logger.info(f"Data integrity check completed: {status} ({critical_count}C/{warning_count}W/{ok_count}OK)")

    return report


@router.get("/latest")
async def get_latest_report(user: dict = Depends(get_current_user)):
    """Get the most recent data integrity report."""
    _require_admin(user)

    report = await db[COLLECTION].find_one(
        {},
        {"_id": 0},
        sort=[("generated_at", -1)]
    )

    if not report:
        raise HTTPException(status_code=404, detail="Nessun report disponibile. Esegui prima un check con POST /run")

    return report


@router.get("/history")
async def get_report_history(user: dict = Depends(get_current_user), limit: int = 10):
    """Get history of past data integrity reports (summary only)."""
    _require_admin(user)

    cursor = db[COLLECTION].find(
        {},
        {"_id": 0, "sections": 0}  # Exclude heavy sections
    ).sort("generated_at", -1).limit(min(limit, 50))

    reports = await cursor.to_list(min(limit, 50))

    return {
        "total": await db[COLLECTION].count_documents({}),
        "reports": reports
    }
