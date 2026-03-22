"""
Registro Obblighi Commessa — Service
=====================================
Modulo "collante" che centralizza tutti gli obblighi, blockers e requisiti
di una commessa in un unico punto.

Fonti MVP:
  A. Evidence Gate (emissioni)
  B. Gate POS (sicurezza cantiere)
  C. Soggetti & Ruoli obbligatori
  D. Istruttoria (domande residue, segmentazione)
  E. Rami normativi (stato rami)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  COSTANTI
# ═══════════════════════════════════════════════════════════════

STATI_APERTI = {"nuovo", "da_verificare", "in_corso", "bloccante"}
STATI_CHIUSI = {"completato", "chiuso", "non_applicabile"}


# ═══════════════════════════════════════════════════════════════
#  CRUD BASE
# ═══════════════════════════════════════════════════════════════

async def get_obbligo(obbligo_id: str, user_id: str) -> Optional[dict]:
    return await db.obblighi_commessa.find_one(
        {"obbligo_id": obbligo_id, "user_id": user_id}, {"_id": 0}
    )


async def list_obblighi(user_id: str, commessa_id: str = None,
                         status: str = None, severity: str = None,
                         source_module: str = None, category: str = None,
                         blocking_level: str = None) -> list:
    query = {"user_id": user_id}
    if commessa_id:
        query["commessa_id"] = commessa_id
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    if source_module:
        query["source_module"] = source_module
    if category:
        query["category"] = category
    if blocking_level:
        query["blocking_level"] = blocking_level
    return await db.obblighi_commessa.find(query, {"_id": 0}).sort(
        [("blocking_level_sort", 1), ("severity_sort", 1), ("created_at", -1)]
    ).to_list(500)


async def update_obbligo(obbligo_id: str, user_id: str, updates: dict) -> Optional[dict]:
    allowed = {"status", "owner_role", "owner_user_id", "due_date", "resolution_note"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return await get_obbligo(obbligo_id, user_id)

    now = datetime.now(timezone.utc).isoformat()
    filtered["updated_at"] = now

    if filtered.get("status") in STATI_CHIUSI:
        filtered["resolved_at"] = now

    await db.obblighi_commessa.update_one(
        {"obbligo_id": obbligo_id, "user_id": user_id}, {"$set": filtered}
    )
    return await get_obbligo(obbligo_id, user_id)


async def get_summary(user_id: str, commessa_id: str) -> dict:
    pipeline = [
        {"$match": {"user_id": user_id, "commessa_id": commessa_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "bloccanti": {"$sum": {"$cond": [{"$eq": ["$blocking_level", "hard_block"]}, 1, 0]}},
            "aperti": {"$sum": {"$cond": [{"$in": ["$status", list(STATI_APERTI)]}, 1, 0]}},
            "chiusi": {"$sum": {"$cond": [{"$in": ["$status", list(STATI_CHIUSI)]}, 1, 0]}},
            "da_verificare": {"$sum": {"$cond": [{"$eq": ["$status", "da_verificare"]}, 1, 0]}},
        }},
    ]
    results = await db.obblighi_commessa.aggregate(pipeline).to_list(1)
    if results:
        r = results[0]
        r.pop("_id", None)
        return r
    return {"total": 0, "bloccanti": 0, "aperti": 0, "chiusi": 0, "da_verificare": 0}


async def get_bloccanti(user_id: str, commessa_id: str) -> list:
    return await db.obblighi_commessa.find(
        {"user_id": user_id, "commessa_id": commessa_id, "blocking_level": "hard_block",
         "status": {"$in": list(STATI_APERTI)}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)


# ═══════════════════════════════════════════════════════════════
#  SYNC ENGINE
# ═══════════════════════════════════════════════════════════════

SEVERITY_SORT = {"alta": 1, "media": 2, "bassa": 3}
BLOCKING_SORT = {"hard_block": 1, "warning": 2, "none": 3}


def _make_obbligo(commessa_id: str, user_id: str, *,
                   source_module: str, source_entity_type: str, source_entity_id: str,
                   code: str, title: str, description: str = "",
                   category: str = "commessa", severity: str = "media",
                   blocking_level: str = "none", owner_role: str = "",
                   linked_route: str = "", linked_label: str = "",
                   context: dict = None,
                   ramo_id: str = "", emissione_id: str = "",
                   cantiere_id: str = "") -> dict:
    """Build an expected obligation dict with dedupe_key."""
    dedupe_key = f"{commessa_id}|{source_module}|{source_entity_id}|{code}"
    now = datetime.now(timezone.utc).isoformat()
    status = "bloccante" if blocking_level == "hard_block" else "nuovo"
    return {
        "obbligo_id": f"obl_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "tenant_id": None,
        "commessa_id": commessa_id,
        "cantiere_id": cantiere_id,
        "ramo_id": ramo_id,
        "emissione_id": emissione_id,
        "source_module": source_module,
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "code": code,
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "severity_sort": SEVERITY_SORT.get(severity, 9),
        "blocking_level": blocking_level,
        "blocking_level_sort": BLOCKING_SORT.get(blocking_level, 9),
        "status": status,
        "auto_generated": True,
        "owner_role": owner_role,
        "owner_user_id": None,
        "due_date": None,
        "linked_route": linked_route,
        "linked_label": linked_label,
        "context": context or {},
        "dedupe_key": dedupe_key,
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "resolved_by": None,
        "resolution_note": None,
    }


async def sync_obblighi_commessa(commessa_id: str, user_id: str) -> dict:
    """
    Master sync: reads all source modules, generates expected obligations,
    compares with DB, creates/updates/closes as needed.
    """
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    if not commessa:
        return {"error": "Commessa non trovata"}

    # Collect all expected obligations from sources
    expected = []

    # Source A: Evidence Gate (emissioni)
    expected.extend(await _collect_evidence_gate(commessa, user_id))

    # Source B: Gate POS (sicurezza)
    expected.extend(await _collect_gate_pos(commessa, user_id))

    # Source C: Soggetti obbligatori
    expected.extend(await _collect_soggetti(commessa, user_id))

    # Source D: Istruttoria
    expected.extend(await _collect_istruttoria(commessa, user_id))

    # Source E: Rami normativi
    expected.extend(await _collect_rami(commessa, user_id))

    # Reconcile with DB
    stats = await _reconcile(commessa_id, user_id, expected)

    logger.info(f"[OBBLIGHI SYNC] {commessa_id}: created={stats['created']}, "
                f"updated={stats['updated']}, closed={stats['closed']}, "
                f"total_expected={len(expected)}")
    return stats


async def _reconcile(commessa_id: str, user_id: str, expected: list) -> dict:
    """Compare expected obligations with DB, create/update/close."""
    now = datetime.now(timezone.utc).isoformat()

    # Load existing open obligations
    existing = await db.obblighi_commessa.find(
        {"commessa_id": commessa_id, "user_id": user_id,
         "auto_generated": True, "status": {"$in": list(STATI_APERTI)}},
        {"_id": 0}
    ).to_list(1000)

    existing_map = {doc["dedupe_key"]: doc for doc in existing}
    expected_keys = {obl["dedupe_key"] for obl in expected}

    created = 0
    updated = 0
    closed = 0

    # Create or update expected obligations
    for obl in expected:
        key = obl["dedupe_key"]
        if key in existing_map:
            # Exists — update severity/title/description if changed
            ex = existing_map[key]
            changes = {}
            if ex.get("severity") != obl.get("severity"):
                changes["severity"] = obl["severity"]
                changes["severity_sort"] = obl["severity_sort"]
            if ex.get("blocking_level") != obl.get("blocking_level"):
                changes["blocking_level"] = obl["blocking_level"]
                changes["blocking_level_sort"] = obl["blocking_level_sort"]
                if obl["blocking_level"] == "hard_block" and ex.get("status") != "bloccante":
                    changes["status"] = "bloccante"
            if ex.get("title") != obl.get("title"):
                changes["title"] = obl["title"]
            if ex.get("description") != obl.get("description"):
                changes["description"] = obl["description"]
            if changes:
                changes["updated_at"] = now
                await db.obblighi_commessa.update_one(
                    {"dedupe_key": key, "user_id": user_id}, {"$set": changes}
                )
                updated += 1
        else:
            # Check if it was previously closed — don't recreate if manually closed
            prev_closed = await db.obblighi_commessa.find_one(
                {"dedupe_key": key, "user_id": user_id,
                 "status": {"$in": list(STATI_CHIUSI)}, "auto_generated": True},
                {"_id": 0, "status": 1, "resolution_note": 1}
            )
            if prev_closed and prev_closed.get("status") == "non_applicabile":
                # User explicitly marked as non-applicable, don't reopen
                continue
            if prev_closed:
                # Was auto-closed but now source is active again — reopen
                await db.obblighi_commessa.update_one(
                    {"dedupe_key": key, "user_id": user_id},
                    {"$set": {
                        "status": obl["status"],
                        "severity": obl["severity"],
                        "severity_sort": obl["severity_sort"],
                        "blocking_level": obl["blocking_level"],
                        "blocking_level_sort": obl["blocking_level_sort"],
                        "title": obl["title"],
                        "description": obl["description"],
                        "resolved_at": None,
                        "resolution_note": None,
                        "updated_at": now,
                    }}
                )
                updated += 1
            else:
                # Brand new — insert
                await db.obblighi_commessa.insert_one(obl)
                created += 1

    # Close obligations whose source no longer produces them
    for key, ex in existing_map.items():
        if key not in expected_keys:
            await db.obblighi_commessa.update_one(
                {"dedupe_key": key, "user_id": user_id},
                {"$set": {
                    "status": "completato",
                    "resolved_at": now,
                    "resolution_note": f"Chiuso automaticamente: condizione non piu presente nella fonte {ex.get('source_module', '')}",
                    "updated_at": now,
                }}
            )
            closed += 1

    return {"created": created, "updated": updated, "closed": closed,
            "total_expected": len(expected)}


# ═══════════════════════════════════════════════════════════════
#  SOURCE A: EVIDENCE GATE (emissioni documentali)
# ═══════════════════════════════════════════════════════════════

async def _collect_evidence_gate(commessa: dict, user_id: str) -> list:
    """Collect obligations from Evidence Gate blockers on emissions."""
    obligations = []
    cid = commessa["commessa_id"]

    # Get all rami for this commessa
    rami = await db.rami_normativi.find(
        {"commessa_id": cid, "user_id": user_id}, {"_id": 0}
    ).to_list(50)

    for ramo in rami:
        ramo_id = ramo.get("ramo_id", "")
        normativa = ramo.get("normativa", "")

        # Get emissioni for this ramo
        emissioni = await db.emissioni_documentali.find(
            {"ramo_id": ramo_id, "user_id": user_id}, {"_id": 0}
        ).to_list(100)

        for emi in emissioni:
            emi_id = emi.get("emissione_id", "")
            codice = emi.get("codice_emissione", emi_id)
            gate = emi.get("gate_result", {})
            blockers = gate.get("blockers", [])

            for bl in blockers:
                bl_code = bl.get("code", "UNKNOWN_BLOCKER")
                bl_msg = bl.get("message", "")
                obligations.append(_make_obbligo(
                    cid, user_id,
                    source_module="evidence_gate",
                    source_entity_type="emissione_documentale",
                    source_entity_id=emi_id,
                    code=bl_code,
                    title=f"{bl_msg} ({codice})",
                    description=f"L'emissione {codice} e bloccata: {bl_msg}",
                    category="emissione",
                    severity="alta",
                    blocking_level="hard_block",
                    owner_role="ufficio_tecnico",
                    linked_route=f"/commesse/{cid}",
                    linked_label=f"Apri emissione {codice}",
                    context={"normativa": normativa, "phase": "emissione", "gate_type": "evidence_gate"},
                    ramo_id=ramo_id,
                    emissione_id=emi_id,
                ))

            # Warnings as low-priority obligations
            warnings = gate.get("warnings", [])
            for w in warnings:
                w_code = w.get("code", "WARNING")
                w_msg = w.get("message", "")
                obligations.append(_make_obbligo(
                    cid, user_id,
                    source_module="evidence_gate",
                    source_entity_type="emissione_documentale",
                    source_entity_id=emi_id,
                    code=f"WARN_{w_code}",
                    title=f"{w_msg} ({codice})",
                    description=f"Warning emissione {codice}: {w_msg}",
                    category="emissione",
                    severity="bassa",
                    blocking_level="warning",
                    owner_role="ufficio_tecnico",
                    linked_route=f"/commesse/{cid}",
                    linked_label=f"Apri emissione {codice}",
                    context={"normativa": normativa, "phase": "emissione"},
                    ramo_id=ramo_id,
                    emissione_id=emi_id,
                ))

    return obligations


# ═══════════════════════════════════════════════════════════════
#  SOURCE B: GATE POS (sicurezza cantiere)
# ═══════════════════════════════════════════════════════════════

async def _collect_gate_pos(commessa: dict, user_id: str) -> list:
    """Collect obligations from Gate POS blockers."""
    obligations = []
    cid = commessa["commessa_id"]

    # Find cantiere sicurezza linked to this commessa (check both commessa_id and parent_commessa_id)
    cantiere = await db.cantieri_sicurezza.find_one(
        {"$or": [{"commessa_id": cid}, {"parent_commessa_id": cid}], "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return obligations

    cantiere_id = cantiere.get("cantiere_id", "")
    gate = cantiere.get("gate_pos_status", {})
    campi_mancanti = gate.get("campi_mancanti", [])
    blockers = gate.get("blockers", [])

    for campo in campi_mancanti:
        code = "POS_" + campo.upper().replace(" ", "_").replace(":", "_")[:40]
        obligations.append(_make_obbligo(
            cid, user_id,
            source_module="gate_pos",
            source_entity_type="cantiere_sicurezza",
            source_entity_id=cantiere_id,
            code=code,
            title=f"Dato mancante POS: {campo}",
            description=f"Il campo '{campo}' e obbligatorio per la generazione del POS.",
            category="sicurezza",
            severity="alta",
            blocking_level="hard_block",
            owner_role="sicurezza",
            linked_route=f"/sicurezza/{cantiere_id}",
            linked_label="Apri scheda cantiere",
            context={"phase": "sicurezza", "gate_type": "gate_pos"},
            cantiere_id=cantiere_id,
        ))

    for bl_text in blockers:
        code = "POS_CRITICAL_" + bl_text[:30].upper().replace(" ", "_").replace(":", "_")
        obligations.append(_make_obbligo(
            cid, user_id,
            source_module="gate_pos",
            source_entity_type="cantiere_sicurezza",
            source_entity_id=cantiere_id,
            code=code,
            title=bl_text[:100],
            description=bl_text,
            category="sicurezza",
            severity="alta",
            blocking_level="hard_block",
            owner_role="sicurezza",
            linked_route=f"/sicurezza/{cantiere_id}",
            linked_label="Apri scheda cantiere",
            context={"phase": "sicurezza", "gate_type": "gate_pos"},
            cantiere_id=cantiere_id,
        ))

    return obligations


# ═══════════════════════════════════════════════════════════════
#  SOURCE C: SOGGETTI & RUOLI OBBLIGATORI
# ═══════════════════════════════════════════════════════════════

SOGGETTI_OBBLIGATORI_MAP = {
    "DATORE_LAVORO": ("Datore di Lavoro", "sicurezza"),
    "RSPP": ("RSPP", "sicurezza"),
    "COMMITTENTE": ("Committente", "soggetti"),
    "MEDICO_COMPETENTE": ("Medico Competente", "sicurezza"),
    "PREPOSTO_CANTIERE": ("Preposto Cantiere", "sicurezza"),
}


async def _collect_soggetti(commessa: dict, user_id: str) -> list:
    """Collect obligations for missing mandatory subjects."""
    obligations = []
    cid = commessa["commessa_id"]

    # Find cantiere sicurezza linked to this commessa (check both commessa_id and parent_commessa_id)
    cantiere = await db.cantieri_sicurezza.find_one(
        {"$or": [{"commessa_id": cid}, {"parent_commessa_id": cid}], "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return obligations

    cantiere_id = cantiere.get("cantiere_id", "")
    soggetti = cantiere.get("soggetti", [])

    for ruolo_code, (label, cat) in SOGGETTI_OBBLIGATORI_MAP.items():
        found = any(s.get("ruolo") == ruolo_code and s.get("nome") for s in soggetti)
        if not found:
            obligations.append(_make_obbligo(
                cid, user_id,
                source_module="soggetti",
                source_entity_type="cantiere_sicurezza",
                source_entity_id=cantiere_id,
                code=f"{ruolo_code}_MISSING",
                title=f"{label} non indicato",
                description=f"Il ruolo obbligatorio '{label}' non risulta compilato nella scheda cantiere.",
                category=cat,
                severity="alta" if ruolo_code in ("DATORE_LAVORO", "RSPP", "COMMITTENTE") else "media",
                blocking_level="hard_block" if ruolo_code in ("DATORE_LAVORO", "RSPP", "COMMITTENTE") else "warning",
                owner_role="sicurezza",
                linked_route=f"/sicurezza/{cantiere_id}",
                linked_label="Apri scheda cantiere",
                context={"phase": "sicurezza", "gate_type": "soggetti"},
                cantiere_id=cantiere_id,
            ))

    return obligations


# ═══════════════════════════════════════════════════════════════
#  SOURCE D: ISTRUTTORIA (domande residue, segmentazione)
# ═══════════════════════════════════════════════════════════════

async def _collect_istruttoria(commessa: dict, user_id: str) -> list:
    """Collect obligations from istruttoria issues."""
    obligations = []
    cid = commessa["commessa_id"]
    moduli = commessa.get("moduli", {})
    prev_id = moduli.get("preventivo_id")
    if not prev_id:
        return obligations

    # Find istruttoria for this preventivo
    istr = await db.istruttorie.find_one(
        {"preventivo_id": prev_id, "user_id": user_id}, {"_id": 0}
    )
    if not istr:
        return obligations

    istr_id = istr.get("istruttoria_id", "")

    # Segmentation pending
    seg = istr.get("segmentazione", {})
    if seg and seg.get("stato") == "proposta" and not seg.get("confermata"):
        obligations.append(_make_obbligo(
            cid, user_id,
            source_module="istruttoria",
            source_entity_type="istruttoria",
            source_entity_id=istr_id,
            code="SEGMENTATION_PENDING",
            title="Segmentazione da confermare",
            description="La segmentazione del preventivo e stata proposta ma non ancora confermata.",
            category="istruttoria",
            severity="media",
            blocking_level="warning",
            owner_role="ufficio_tecnico",
            linked_route=f"/commesse/{cid}",
            linked_label="Apri commessa",
            context={"phase": "istruttoria"},
        ))

    # Uncertain classification
    classificazione = istr.get("classificazione", {})
    confidence = classificazione.get("confidence", 1.0)
    if isinstance(confidence, (int, float)) and confidence < 0.7:
        obligations.append(_make_obbligo(
            cid, user_id,
            source_module="istruttoria",
            source_entity_type="istruttoria",
            source_entity_id=istr_id,
            code="CLASSIFICATION_UNCERTAIN",
            title="Classificazione normativa incerta",
            description=f"La classificazione ha confidenza {confidence:.0%}. Verificare manualmente.",
            category="istruttoria",
            severity="media",
            blocking_level="warning",
            owner_role="ufficio_tecnico",
            linked_route=f"/commesse/{cid}",
            linked_label="Apri commessa",
            context={"phase": "istruttoria"},
        ))

    # High-impact unanswered questions
    domande = istr.get("domande_residue", [])
    risposte = istr.get("risposte", {})
    for i, d in enumerate(domande):
        impatto = d.get("impatto", "")
        risposta = risposte.get(str(i), {})
        if impatto == "alto" and not risposta.get("valore"):
            dom_text = d.get("domanda", "")[:80]
            obligations.append(_make_obbligo(
                cid, user_id,
                source_module="istruttoria",
                source_entity_type="istruttoria",
                source_entity_id=istr_id,
                code=f"HIGH_IMPACT_Q_{i}",
                title=f"Domanda critica senza risposta: {dom_text}",
                description="Domanda ad alto impatto non risolta nell'istruttoria.",
                category="istruttoria",
                severity="alta",
                blocking_level="warning",
                owner_role="ufficio_tecnico",
                linked_route=f"/commesse/{cid}",
                linked_label="Apri commessa",
                context={"phase": "istruttoria", "domanda_index": i},
            ))

    return obligations


# ═══════════════════════════════════════════════════════════════
#  SOURCE E: RAMI NORMATIVI
# ═══════════════════════════════════════════════════════════════

async def _collect_rami(commessa: dict, user_id: str) -> list:
    """Collect obligations from normative branch issues."""
    obligations = []
    cid = commessa["commessa_id"]

    rami = await db.rami_normativi.find(
        {"commessa_id": cid, "user_id": user_id}, {"_id": 0}
    ).to_list(50)

    for ramo in rami:
        ramo_id = ramo.get("ramo_id", "")
        codice = ramo.get("codice_ramo", ramo_id)
        stato = ramo.get("stato", "")

        if stato in ("incompleto", "draft", ""):
            obligations.append(_make_obbligo(
                cid, user_id,
                source_module="rami_normativi",
                source_entity_type="ramo_normativo",
                source_entity_id=ramo_id,
                code="BRANCH_NOT_READY",
                title=f"Ramo {codice} non pronto",
                description=f"Il ramo normativo {codice} e in stato '{stato or 'draft'}'.",
                category="commessa",
                severity="media",
                blocking_level="warning",
                owner_role="ufficio_tecnico",
                linked_route=f"/commesse/{cid}",
                linked_label=f"Apri ramo {codice}",
                context={"phase": "rami", "normativa": ramo.get("normativa", "")},
                ramo_id=ramo_id,
            ))

    return obligations
