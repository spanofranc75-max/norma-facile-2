"""
NormaFacile 2.0 — Data Integrity Check
Verifica coerenza dati su 6 aree critiche:
  1. Duplicati vs unique constraints
  2. Riferimenti rotti (foreign key logiche)
  3. Stati incoerenti
  4. Campi obbligatori mancanti
  5. Snapshot vs stato reale
  6. Documenti legacy / duplicati logici
"""
import asyncio
import json
from datetime import datetime, timezone
from collections import Counter

# Bootstrap DB connection
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import db


report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "checks": {},
    "summary": {"total_issues": 0, "critical": 0, "warning": 0, "info": 0}
}


def add_issue(section, severity, message, details=None):
    if section not in report["checks"]:
        report["checks"][section] = []
    report["checks"][section].append({
        "severity": severity,
        "message": message,
        "details": details
    })
    report["summary"]["total_issues"] += 1
    report["summary"][severity] += 1


async def check_1_duplicates():
    """Check duplicates where unique constraints now exist."""
    print("  [1/6] Duplicati vs unique constraints...")

    # 1a. obblighi_commessa.dedupe_key
    pipeline = [
        {"$group": {"_id": {"dedupe_key": "$dedupe_key", "user_id": "$user_id"}, "count": {"$sum": 1}, "ids": {"$push": "$obbligo_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.obblighi_commessa.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "critical",
                  f"obblighi_commessa: {len(dupes)} gruppi di duplicati su dedupe_key",
                  [{"dedupe_key": d["_id"]["dedupe_key"], "count": d["count"], "ids": d["ids"][:5]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "obblighi_commessa.dedupe_key: nessun duplicato")

    # 1b. commesse_normative (commessa_id + normativa + user_id)
    pipeline = [
        {"$group": {"_id": {"commessa_id": "$commessa_id", "normativa": "$normativa", "user_id": "$user_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.commesse_normative.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "critical",
                  f"commesse_normative: {len(dupes)} duplicati su (commessa_id, normativa, user_id)",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "commesse_normative: nessun duplicato")

    # 1c. emissioni_documentali (ramo_id + emission_type + emission_seq + user_id)
    pipeline = [
        {"$group": {"_id": {"ramo_id": "$ramo_id", "emission_type": "$emission_type", "emission_seq": "$emission_seq", "user_id": "$user_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.emissioni_documentali.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "critical",
                  f"emissioni_documentali: {len(dupes)} duplicati",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "emissioni_documentali: nessun duplicato")

    # 1d. cantieri_sicurezza (user_id + cantiere_id)
    pipeline = [
        {"$group": {"_id": {"user_id": "$user_id", "cantiere_id": "$cantiere_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.cantieri_sicurezza.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "critical",
                  f"cantieri_sicurezza: {len(dupes)} duplicati",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "cantieri_sicurezza: nessun duplicato")

    # 1e. pacchetti_committenza (package_id + user_id)
    pipeline = [
        {"$group": {"_id": {"package_id": "$package_id", "user_id": "$user_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.pacchetti_committenza.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "warning",
                  f"pacchetti_committenza: {len(dupes)} duplicati",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "pacchetti_committenza: nessun duplicato")

    # 1f. analisi_committenza (analysis_id + user_id)
    pipeline = [
        {"$group": {"_id": {"analysis_id": "$analysis_id", "user_id": "$user_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.analisi_committenza.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("1_duplicati", "warning",
                  f"analisi_committenza: {len(dupes)} duplicati",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("1_duplicati", "info", "analisi_committenza: nessun duplicato")


async def check_2_broken_refs():
    """Check broken references (logical foreign keys)."""
    print("  [2/6] Riferimenti rotti...")

    # 2a. commesse_normative -> commesse (commessa_id)
    all_commesse_ids = set()
    async for doc in db.commesse.find({}, {"commessa_id": 1}):
        all_commesse_ids.add(doc.get("commessa_id"))

    broken = 0
    async for doc in db.commesse_normative.find({}, {"commessa_id": 1, "normativa": 1}):
        if doc.get("commessa_id") not in all_commesse_ids:
            broken += 1
    if broken:
        add_issue("2_riferimenti_rotti", "warning",
                  f"commesse_normative: {broken} record con commessa_id inesistente")
    else:
        add_issue("2_riferimenti_rotti", "info", "commesse_normative -> commesse: OK")

    # 2b. emissioni_documentali -> commesse_normative (ramo_id)
    all_ramo_ids = set()
    async for doc in db.commesse_normative.find({}, {"ramo_id": 1}):
        rid = doc.get("ramo_id")
        if rid:
            all_ramo_ids.add(rid)

    broken = 0
    broken_details = []
    async for doc in db.emissioni_documentali.find({}, {"ramo_id": 1, "emission_id": 1}):
        if doc.get("ramo_id") and doc["ramo_id"] not in all_ramo_ids:
            broken += 1
            if len(broken_details) < 5:
                broken_details.append({"emission_id": doc.get("emission_id"), "ramo_id": doc.get("ramo_id")})
    if broken:
        add_issue("2_riferimenti_rotti", "critical",
                  f"emissioni_documentali: {broken} record con ramo_id inesistente",
                  broken_details)
    else:
        add_issue("2_riferimenti_rotti", "info", "emissioni_documentali -> commesse_normative: OK")

    # 2c. obblighi_commessa -> commesse (commessa_id)
    broken = 0
    async for doc in db.obblighi_commessa.find({}, {"commessa_id": 1, "obbligo_id": 1}):
        if doc.get("commessa_id") not in all_commesse_ids:
            broken += 1
    if broken:
        add_issue("2_riferimenti_rotti", "warning",
                  f"obblighi_commessa: {broken} record con commessa_id inesistente")
    else:
        add_issue("2_riferimenti_rotti", "info", "obblighi_commessa -> commesse: OK")

    # 2d. cantieri_sicurezza -> commesse (parent_commessa_id)
    broken = 0
    async for doc in db.cantieri_sicurezza.find({}, {"parent_commessa_id": 1, "cantiere_id": 1}):
        pcid = doc.get("parent_commessa_id")
        if pcid and pcid not in all_commesse_ids:
            broken += 1
    if broken:
        add_issue("2_riferimenti_rotti", "warning",
                  f"cantieri_sicurezza: {broken} record con parent_commessa_id inesistente")
    else:
        add_issue("2_riferimenti_rotti", "info", "cantieri_sicurezza -> commesse: OK")

    # 2e. pacchetti_documentali -> commesse (commessa_id)
    broken = 0
    async for doc in db.pacchetti_documentali.find({}, {"commessa_id": 1}):
        if doc.get("commessa_id") not in all_commesse_ids:
            broken += 1
    if broken:
        add_issue("2_riferimenti_rotti", "warning",
                  f"pacchetti_documentali: {broken} record con commessa_id inesistente")
    else:
        add_issue("2_riferimenti_rotti", "info", "pacchetti_documentali -> commesse: OK")

    # 2f. documenti_archivio -> commesse (commessa_id)
    broken = 0
    async for doc in db.documenti_archivio.find({}, {"commessa_id": 1}):
        if doc.get("commessa_id") and doc["commessa_id"] not in all_commesse_ids:
            broken += 1
    if broken:
        add_issue("2_riferimenti_rotti", "warning",
                  f"documenti_archivio: {broken} record con commessa_id inesistente")
    else:
        add_issue("2_riferimenti_rotti", "info", "documenti_archivio -> commesse: OK")


async def check_3_inconsistent_states():
    """Check logically inconsistent states."""
    print("  [3/6] Stati incoerenti...")

    # 3a. Emissioni "emessa" senza gate coerente
    emissioni = await db.emissioni_documentali.find(
        {"status": "emessa"}, {"_id": 0, "emission_id": 1, "gate_status": 1, "ramo_id": 1}
    ).to_list(500)
    bad_gates = [e for e in emissioni if e.get("gate_status") not in ("passed", "approved", None)]
    if bad_gates:
        add_issue("3_stati_incoerenti", "warning",
                  f"emissioni_documentali: {len(bad_gates)} emissioni con status='emessa' ma gate non coerente",
                  [{"emission_id": e.get("emission_id"), "gate_status": e.get("gate_status")} for e in bad_gates[:5]])
    else:
        add_issue("3_stati_incoerenti", "info", "emissioni emesse con gate coerente: OK")

    # 3b. Obblighi "completato" da fonte ancora bloccante
    completed_obblighi = await db.obblighi_commessa.find(
        {"status": "completato"}, {"_id": 0, "obbligo_id": 1, "blocking_level": 1}
    ).to_list(500)
    still_blocking = [o for o in completed_obblighi if o.get("blocking_level") in ("hard_block", "hard")]
    if still_blocking:
        add_issue("3_stati_incoerenti", "warning",
                  f"obblighi_commessa: {len(still_blocking)} obblighi completati ma ancora con blocking_level hard",
                  [{"obbligo_id": o.get("obbligo_id"), "blocking": o.get("blocking_level")} for o in still_blocking[:5]])
    else:
        add_issue("3_stati_incoerenti", "info", "obblighi completati senza blocking residuo: OK")

    # 3c. Pacchetti "pronto_invio" con documenti mancanti
    pacchetti = await db.pacchetti_documentali.find(
        {"status": "pronto_invio"}, {"_id": 0, "pack_id": 1, "summary": 1}
    ).to_list(200)
    bad_packs = []
    for p in pacchetti:
        s = p.get("summary", {})
        if s.get("missing", 0) > 0 or s.get("expired", 0) > 0:
            bad_packs.append({"pack_id": p.get("pack_id"), "missing": s.get("missing"), "expired": s.get("expired")})
    if bad_packs:
        add_issue("3_stati_incoerenti", "critical",
                  f"pacchetti_documentali: {len(bad_packs)} pacchetti 'pronto_invio' con documenti mancanti/scaduti",
                  bad_packs[:10])
    else:
        add_issue("3_stati_incoerenti", "info", "pacchetti pronto_invio coerenti: OK")


async def check_4_missing_fields():
    """Check mandatory fields missing in recent records."""
    print("  [4/6] Campi obbligatori mancanti...")

    checks = [
        ("obblighi_commessa", ["user_id", "commessa_id", "dedupe_key", "status", "created_at"]),
        ("commesse_normative", ["user_id", "commessa_id", "normativa", "ramo_id"]),
        ("emissioni_documentali", ["user_id", "commessa_id", "ramo_id", "emission_type"]),
        ("cantieri_sicurezza", ["user_id", "cantiere_id"]),
        ("pacchetti_documentali", ["user_id", "commessa_id"]),
        ("documenti_archivio", ["user_id"]),  # commessa_id is optional (docs can be azienda/persona/mezzo)
        ("analisi_committenza", ["user_id", "analysis_id"]),
        ("pacchetti_committenza", ["user_id", "package_id"]),
        ("audits", ["user_id", "audit_id", "date"]),
        ("non_conformities", ["user_id", "nc_id", "date"]),
        ("instruments", ["user_id", "instrument_id"]),
        ("welders", ["user_id", "welder_id"]),
    ]

    for coll_name, required_fields in checks:
        total = await db[coll_name].count_documents({})
        if total == 0:
            continue

        for field in required_fields:
            missing = await db[coll_name].count_documents({
                "$or": [{field: {"$exists": False}}, {field: None}]
            })
            if missing > 0:
                pct = round(missing / total * 100, 1)
                severity = "critical" if field == "user_id" and pct > 50 else "warning" if missing > 0 else "info"
                add_issue("4_campi_mancanti", severity,
                          f"{coll_name}.{field}: mancante in {missing}/{total} doc ({pct}%)")
            # Only report issues, not OKs to keep output clean


async def check_5_snapshot_coherence():
    """Check snapshot data vs live computation."""
    print("  [5/6] Coerenza snapshot vs stato reale...")

    # 5a. Pacchetti documentali: summary vs actual items
    pacchetti = await db.pacchetti_documentali.find(
        {}, {"_id": 0, "pack_id": 1, "commessa_id": 1, "summary": 1, "items": 1}
    ).to_list(200)

    mismatches = []
    for p in pacchetti:
        summary = p.get("summary", {})
        items = p.get("items", [])
        stored_total = summary.get("total_required", 0)
        actual_total = len(items)
        if stored_total != actual_total:
            mismatches.append({
                "pack_id": p.get("pack_id"),
                "summary_total": stored_total,
                "actual_items": actual_total
            })

    if mismatches:
        add_issue("5_snapshot_coerenza", "warning",
                  f"pacchetti_documentali: {len(mismatches)} pacchetti con summary.total_required != len(items)",
                  mismatches[:10])
    else:
        add_issue("5_snapshot_coerenza", "info", "pacchetti_documentali summary vs items: coerente")

    # 5b. Commesse normative: count rami vs emissioni
    rami = await db.commesse_normative.find({}, {"_id": 0, "ramo_id": 1, "commessa_id": 1}).to_list(500)
    for ramo in rami[:50]:  # Sample first 50
        ramo_id = ramo.get("ramo_id")
        if not ramo_id:
            continue
        em_count = await db.emissioni_documentali.count_documents({"ramo_id": ramo_id})
        # Just gathering data, no strict rule violation here


async def check_6_legacy_duplicates():
    """Check for logical duplicates and legacy data."""
    print("  [6/6] Documenti legacy e duplicati logici...")

    # 6a. Commesse with duplicate 'numero'
    pipeline = [
        {"$group": {"_id": {"numero": "$numero", "user_id": "$user_id"}, "count": {"$sum": 1}, "ids": {"$push": "$commessa_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.commesse.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("6_legacy_duplicati", "warning",
                  f"commesse: {len(dupes)} numeri commessa duplicati per stesso utente",
                  [{"numero": d["_id"]["numero"], "count": d["count"], "ids": d["ids"][:5]} for d in dupes[:10]])
    else:
        add_issue("6_legacy_duplicati", "info", "commesse: nessun numero duplicato per utente")

    # 6b. documenti_archivio: actual duplicates (same entity+doc_type+filename when ALL populated)
    pipeline = [
        {"$match": {
            "doc_type": {"$exists": True, "$nin": [None, ""]},
            "filename": {"$exists": True, "$nin": [None, ""]},
            "entity_id": {"$exists": True, "$nin": [None, ""]},
        }},
        {"$group": {"_id": {"entity_type": "$entity_type", "entity_id": "$entity_id", "doc_type": "$doc_type", "filename": "$filename"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dupes = await db.documenti_archivio.aggregate(pipeline).to_list(100)
    if dupes:
        add_issue("6_legacy_duplicati", "warning",
                  f"documenti_archivio: {len(dupes)} documenti logicamente duplicati (same type+commessa+filename)",
                  [{"key": d["_id"], "count": d["count"]} for d in dupes[:10]])
    else:
        add_issue("6_legacy_duplicati", "info", "documenti_archivio: nessun duplicato logico")

    # 6c. Zombie collections check
    for coll_name in ["download_tokens", "sessions"]:
        count = await db[coll_name].count_documents({})
        if count > 0:
            add_issue("6_legacy_duplicati", "info",
                      f"Collezione zombie '{coll_name}': {count} documenti (candidata per cleanup)")


async def main():
    print("=" * 60)
    print("NormaFacile 2.0 — Data Integrity Check")
    print("=" * 60)

    await check_1_duplicates()
    await check_2_broken_refs()
    await check_3_inconsistent_states()
    await check_4_missing_fields()
    await check_5_snapshot_coherence()
    await check_6_legacy_duplicates()

    # Write report
    output_path = "/app/DATA_INTEGRITY_REPORT.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("RISULTATO")
    print("=" * 60)
    s = report["summary"]
    print(f"  Totale issue: {s['total_issues']}")
    print(f"  CRITICAL:     {s['critical']}")
    print(f"  WARNING:      {s['warning']}")
    print(f"  INFO:         {s['info']}")
    print(f"\nReport salvato: {output_path}")

    # Print critical + warning details
    for section, issues in report["checks"].items():
        problems = [i for i in issues if i["severity"] in ("critical", "warning")]
        if problems:
            print(f"\n--- {section} ---")
            for i in problems:
                print(f"  [{i['severity'].upper()}] {i['message']}")
                if i.get("details"):
                    for d in (i["details"][:3] if isinstance(i["details"], list) else [i["details"]]):
                        print(f"    -> {d}")


if __name__ == "__main__":
    asyncio.run(main())
