"""
Commesse Normative Service — Modello Gerarchico
=================================================
Logica di business per:
- Rami normativi (commesse_normative)
- Emissioni documentali (emissioni_documentali)
- Legacy adapter
- Numerazione strutturata

Livelli:
  Commessa Madre → Ramo Normativo → Emissione Documentale
"""

import uuid
import logging
from datetime import datetime, timezone

from core.database import db

logger = logging.getLogger(__name__)

# ─── Costanti ────────────────────────────────────────────────────

NORMATIVE_VALIDE = ("EN_1090", "EN_13241", "GENERICA")

RAMO_STATI = ("draft", "active", "in_lavorazione", "closed", "archived")
EMISSIONE_STATI = ("draft", "in_preparazione", "bloccata", "emettibile", "emessa", "annullata")

# Suffissi numerazione per normativa
SUFFISSO_NORMATIVA = {
    "EN_1090": "1090",
    "EN_13241": "13241",
    "GENERICA": "GEN",
}

# Tipo emissione per normativa
EMISSION_TYPE_MAP = {
    "EN_1090": "DOP",
    "EN_13241": "CE",
    "GENERICA": "LOT",
}

EMISSION_PREFIX_MAP = {
    "DOP": "D",
    "CE": "C",
    "LOT": "L",
}


# ═══════════════════════════════════════════════════════════════════
#  RAMI NORMATIVI
# ═══════════════════════════════════════════════════════════════════

async def get_rami(commessa_id: str, user_id: str) -> list:
    """Lista rami normativi di una commessa."""
    return await db.commesse_normative.find(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(10)


async def get_ramo(ramo_id: str, user_id: str) -> dict | None:
    """Dettaglio singolo ramo."""
    return await db.commesse_normative.find_one(
        {"ramo_id": ramo_id, "user_id": user_id},
        {"_id": 0}
    )


async def get_ramo_by_normativa(commessa_id: str, normativa: str, user_id: str) -> dict | None:
    """Trova ramo per commessa + normativa (utile per idempotenza)."""
    return await db.commesse_normative.find_one(
        {"commessa_id": commessa_id, "normativa": normativa, "user_id": user_id},
        {"_id": 0}
    )


def _build_codice_ramo(numero_commessa: str, normativa: str) -> str:
    """Genera codice ramo: NF-2026-000125-1090"""
    suffisso = SUFFISSO_NORMATIVA.get(normativa, normativa)
    return f"{numero_commessa}-{suffisso}"


async def crea_ramo(
    commessa_id: str,
    user_id: str,
    normativa: str,
    line_ids: list | None = None,
    created_from: str = "manuale",
    source_istruttoria_id: str | None = None,
    source_segmentation_snapshot: dict | None = None,
) -> dict:
    """Crea un ramo normativo per la commessa.
    Idempotente: se esiste gia, restituisce quello esistente aggiornato.
    """
    if normativa not in NORMATIVE_VALIDE:
        raise ValueError(f"Normativa non valida: {normativa}")

    # Recupera numero commessa madre (cerca in commesse e commesse_preistruite)
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "numero": 1, "commessa_id": 1}
    )
    if not commessa:
        # Fallback: cerca in commesse_preistruite
        commessa = await db.commesse_preistruite.find_one(
            {"commessa_id": commessa_id, "user_id": user_id},
            {"_id": 0, "commessa_id": 1, "preventivo_number": 1}
        )
        if commessa:
            # Usa preventivo_number come base per il codice ramo
            commessa["numero"] = commessa.get("preventivo_number", commessa_id)
    if not commessa:
        raise ValueError(f"Commessa {commessa_id} non trovata")

    numero = commessa.get("numero", commessa_id)
    codice_ramo = _build_codice_ramo(numero, normativa)
    now = datetime.now(timezone.utc)

    # Idempotenza: check se esiste gia
    existing = await get_ramo_by_normativa(commessa_id, normativa, user_id)
    if existing:
        # Aggiorna line_ids se forniti
        update_set = {"updated_at": now.isoformat()}
        if line_ids is not None:
            update_set["line_ids"] = line_ids
        await db.commesse_normative.update_one(
            {"ramo_id": existing["ramo_id"]},
            {"$set": update_set}
        )
        existing.update(update_set)
        logger.info(f"[RAMI] Ramo esistente aggiornato: {existing['ramo_id']} ({normativa})")
        return existing

    ramo = {
        "ramo_id": f"ramo_{uuid.uuid4().hex[:12]}",
        "commessa_id": commessa_id,
        "user_id": user_id,
        "normativa": normativa,
        "codice_ramo": codice_ramo,
        "commessa_base_code": numero,
        "branch_type": normativa,
        "line_ids": line_ids or [],
        "status": "active",
        "created_from": created_from,
        "source_istruttoria_id": source_istruttoria_id,
        "source_segmentation_snapshot": source_segmentation_snapshot,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.commesse_normative.insert_one(ramo)
    ramo.pop("_id", None)

    logger.info(f"[RAMI] Ramo creato: {ramo['ramo_id']} — {codice_ramo} ({created_from})")
    return ramo


async def genera_rami_da_segmentazione(
    commessa_id: str,
    user_id: str,
    istruttoria: dict,
) -> list:
    """Auto-genera rami da segmentazione confermata. Idempotente.

    Legge official_segmentation.line_assignments e crea un ramo per ogni normativa distinta.
    Aggiorna anche normative_presenti e has_mixed_normative sulla commessa madre.
    """
    official_seg = istruttoria.get("official_segmentation")
    classif = istruttoria.get("classificazione", {})
    istr_id = istruttoria.get("istruttoria_id")

    # Determina le normative presenti
    normative_set = set()
    norm_to_lines = {}

    if official_seg and official_seg.get("confirmed"):
        for la in official_seg.get("line_assignments", []):
            norm = la.get("normativa")
            if norm in NORMATIVE_VALIDE:
                normative_set.add(norm)
                norm_to_lines.setdefault(norm, []).append(la.get("line_id"))
    else:
        # Commessa pura: usa classificazione
        norm = classif.get("normativa_proposta", "")
        if norm in NORMATIVE_VALIDE:
            normative_set.add(norm)

    if not normative_set:
        raise ValueError("Nessuna normativa valida trovata nella segmentazione/classificazione")

    # Crea snapshot segmentazione per tracciabilita
    seg_snapshot = None
    if official_seg:
        seg_snapshot = {
            "confirmed_at": official_seg.get("confirmed_at"),
            "confirmed_by": official_seg.get("confirmed_by"),
            "line_count": len(official_seg.get("line_assignments", [])),
        }

    rami_creati = []
    for norm in sorted(normative_set):
        ramo = await crea_ramo(
            commessa_id=commessa_id,
            user_id=user_id,
            normativa=norm,
            line_ids=norm_to_lines.get(norm, []),
            created_from="segmentazione",
            source_istruttoria_id=istr_id,
            source_segmentation_snapshot=seg_snapshot,
        )
        rami_creati.append(ramo)

    # Aggiorna commessa madre con metadati normativi (cerca in entrambe le collezioni)
    normative_list = sorted(normative_set)
    update_fields = {
        "normative_presenti": normative_list,
        "has_mixed_normative": len(normative_list) > 1,
        "primary_normativa": normative_list[0] if len(normative_list) == 1 else classif.get("normativa_proposta", normative_list[0]),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.commesse.update_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        # Fallback: aggiorna commesse_preistruite
        await db.commesse_preistruite.update_one(
            {"commessa_id": commessa_id, "user_id": user_id},
            {"$set": update_fields}
        )

    logger.info(f"[RAMI] Generati {len(rami_creati)} rami per commessa {commessa_id}: {normative_list}")
    return rami_creati


# ═══════════════════════════════════════════════════════════════════
#  EMISSIONI DOCUMENTALI
# ═══════════════════════════════════════════════════════════════════

async def _next_emission_seq(ramo_id: str, emission_type: str) -> int:
    """Counter atomico per progressivo emissione."""
    counter_id = f"emission_{ramo_id}_{emission_type}"
    result = await db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


async def get_emissioni(ramo_id: str, user_id: str) -> list:
    """Lista emissioni di un ramo."""
    return await db.emissioni_documentali.find(
        {"ramo_id": ramo_id, "user_id": user_id},
        {"_id": 0}
    ).sort("emission_seq", 1).to_list(100)


async def get_emissione(emissione_id: str, user_id: str) -> dict | None:
    """Dettaglio singola emissione."""
    return await db.emissioni_documentali.find_one(
        {"emissione_id": emissione_id, "user_id": user_id},
        {"_id": 0}
    )


async def crea_emissione(
    ramo_id: str,
    user_id: str,
    descrizione: str = "",
    voce_lavoro_ids: list | None = None,
    batch_ids: list | None = None,
    ddt_ids: list | None = None,
    line_ids: list | None = None,
    document_ids: list | None = None,
) -> dict:
    """Crea nuova emissione documentale dentro un ramo. Solo trigger esplicito utente."""
    ramo = await get_ramo(ramo_id, user_id)
    if not ramo:
        raise ValueError(f"Ramo {ramo_id} non trovato")

    normativa = ramo["normativa"]
    emission_type = EMISSION_TYPE_MAP.get(normativa, "LOT")
    prefix = EMISSION_PREFIX_MAP.get(emission_type, "X")

    seq = await _next_emission_seq(ramo_id, emission_type)
    codice_emissione = f"{ramo['codice_ramo']}-{prefix}{seq:02d}"

    now = datetime.now(timezone.utc)
    emissione = {
        "emissione_id": f"em_{uuid.uuid4().hex[:12]}",
        "ramo_id": ramo_id,
        "commessa_id": ramo["commessa_id"],
        "user_id": user_id,
        "codice_emissione": codice_emissione,
        "commessa_base_code": ramo["commessa_base_code"],
        "branch_type": normativa,
        "emission_type": emission_type,
        "emission_seq": seq,
        "stato": "draft",
        "descrizione": descrizione,
        "line_ids": line_ids or [],
        "voce_lavoro_ids": voce_lavoro_ids or [],
        "batch_ids": batch_ids or [],
        "ddt_ids": ddt_ids or [],
        "document_ids": document_ids or [],
        "element_ids": [],
        "evidence_gate": {
            "emittable": False,
            "checked_at": None,
            "blocking_reasons": [],
            "checks": {},
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "emessa_il": None,
        "emessa_da": None,
    }

    await db.emissioni_documentali.insert_one(emissione)
    emissione.pop("_id", None)

    logger.info(f"[EMISSIONI] Creata: {codice_emissione} (ramo {ramo_id})")
    return emissione


async def aggiorna_emissione(
    emissione_id: str,
    user_id: str,
    update_fields: dict,
) -> dict:
    """Aggiorna campi di un'emissione (descrizione, batch, ddt, etc.)."""
    allowed = {
        "descrizione", "voce_lavoro_ids", "batch_ids", "ddt_ids",
        "line_ids", "document_ids", "element_ids",
    }
    filtered = {k: v for k, v in update_fields.items() if k in allowed}
    if not filtered:
        raise ValueError("Nessun campo valido da aggiornare")

    filtered["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.emissioni_documentali.update_one(
        {"emissione_id": emissione_id, "user_id": user_id, "stato": {"$nin": ["emessa", "annullata"]}},
        {"$set": filtered}
    )
    if result.matched_count == 0:
        raise ValueError("Emissione non trovata o non modificabile (gia emessa/annullata)")

    return await get_emissione(emissione_id, user_id)


async def check_evidence_gate(emissione_id: str, user_id: str) -> dict:
    """Calcola l'Evidence Gate completo per una singola emissione.
    Usa il motore in evidence_gate_engine.py con output standardizzato."""
    from services.evidence_gate_engine import evaluate_gate

    emissione = await get_emissione(emissione_id, user_id)
    if not emissione:
        raise ValueError(f"Emissione {emissione_id} non trovata")

    ramo = await get_ramo(emissione["ramo_id"], user_id)
    if not ramo:
        raise ValueError(f"Ramo {emissione['ramo_id']} non trovato")

    commessa = await db.commesse.find_one(
        {"commessa_id": emissione["commessa_id"], "user_id": user_id},
        {"_id": 0}
    )
    if not commessa:
        commessa = {}

    gate_result = await evaluate_gate(emissione, ramo, commessa)

    # Snapshot cache su emissione
    now = gate_result["updated_at"]
    snapshot = {
        "evidence_gate": {
            "emittable": gate_result["emittable"],
            "checked_at": now,
            "completion_percent": gate_result["completion_percent"],
            "blocking_reasons": [b["message"] for b in gate_result["blockers"]],
            "checks": {c["code"]: c["status"] for c in gate_result["checks"]},
        },
        "last_gate_status": gate_result["stato_gate"],
        "last_gate_check_at": now,
        "last_completion_percent": gate_result["completion_percent"],
        "last_blockers_count": len(gate_result["blockers"]),
        "updated_at": now,
    }

    # Update stato if not already emessa/annullata
    if emissione.get("stato") not in ("emessa", "annullata"):
        snapshot["stato"] = gate_result["stato_gate"]

    await db.emissioni_documentali.update_one(
        {"emissione_id": emissione_id},
        {"$set": snapshot}
    )

    return gate_result


async def emetti_emissione(emissione_id: str, user_id: str, user_name: str = "") -> dict:
    """Emetti l'emissione (solo se gate OK). Ricalcola SEMPRE il gate prima di emettere."""
    gate = await check_evidence_gate(emissione_id, user_id)
    if not gate["emittable"]:
        reasons = "; ".join(b["message"] for b in gate.get("blockers", []))
        raise ValueError(f"Emissione non emettibile: {reasons}")

    now = datetime.now(timezone.utc).isoformat()
    await db.emissioni_documentali.update_one(
        {"emissione_id": emissione_id, "user_id": user_id},
        {"$set": {
            "stato": "emessa",
            "emessa_il": now,
            "emessa_da": user_id,
            "emessa_da_nome": user_name,
            "updated_at": now,
        }}
    )
    return {"emissione_id": emissione_id, "stato": "emessa", "emessa_il": now}


# ═══════════════════════════════════════════════════════════════════
#  LEGACY ADAPTER
# ═══════════════════════════════════════════════════════════════════

async def get_normative_branches(commessa_id: str, user_id: str, include_legacy_wrap: bool = True) -> list:
    """Adapter centralizzato: restituisce i rami normativi di una commessa.
    Se non esistono rami e include_legacy_wrap=True, genera un ramo virtuale
    dal campo normativa_tipo della commessa madre (senza salvarlo in DB).
    """
    rami = await get_rami(commessa_id, user_id)
    if rami:
        return rami

    if not include_legacy_wrap:
        return []

    # Legacy wrap: genera ramo virtuale dalla commessa madre
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "numero": 1, "normativa_tipo": 1, "commessa_id": 1}
    )
    if not commessa:
        commessa = await db.commesse_preistruite.find_one(
            {"commessa_id": commessa_id, "user_id": user_id},
            {"_id": 0, "commessa_id": 1, "normativa": 1, "preventivo_number": 1}
        )
        if commessa:
            commessa["numero"] = commessa.get("preventivo_number", commessa_id)
            commessa["normativa_tipo"] = commessa.get("normativa", "")
    if not commessa:
        return []

    norm = commessa.get("normativa_tipo", "")
    if norm not in NORMATIVE_VALIDE:
        return []

    numero = commessa.get("numero", commessa_id)
    return [{
        "ramo_id": None,
        "commessa_id": commessa_id,
        "user_id": user_id,
        "normativa": norm,
        "codice_ramo": _build_codice_ramo(numero, norm),
        "commessa_base_code": numero,
        "branch_type": norm,
        "line_ids": [],
        "status": "active",
        "created_from": "legacy_wrap",
        "is_virtual": True,
    }]


async def materializza_ramo_legacy(commessa_id: str, user_id: str) -> dict | None:
    """Converte un ramo legacy virtuale in un ramo reale nel DB (lazy on-access)."""
    rami = await get_rami(commessa_id, user_id)
    if rami:
        return rami[0]

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "numero": 1, "normativa_tipo": 1}
    )
    if not commessa or commessa.get("normativa_tipo") not in NORMATIVE_VALIDE:
        return None

    return await crea_ramo(
        commessa_id=commessa_id,
        user_id=user_id,
        normativa=commessa["normativa_tipo"],
        created_from="legacy_wrap",
    )


# ═══════════════════════════════════════════════════════════════════
#  VISTA AGGREGATA (GERARCHIA)
# ═══════════════════════════════════════════════════════════════════

async def get_gerarchia(commessa_id: str, user_id: str) -> dict:
    """Vista completa: commessa madre + rami + emissioni per ramo."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1,
         "normativa_tipo": 1, "normative_presenti": 1, "has_mixed_normative": 1,
         "stato": 1, "status": 1}
    )
    if not commessa:
        raise ValueError(f"Commessa {commessa_id} non trovata")

    rami = await get_rami(commessa_id, user_id)

    rami_con_emissioni = []
    for ramo in rami:
        emissioni = await get_emissioni(ramo["ramo_id"], user_id)
        rami_con_emissioni.append({
            **ramo,
            "emissioni": emissioni,
            "n_emissioni": len(emissioni),
            "n_emesse": sum(1 for e in emissioni if e["stato"] == "emessa"),
            "n_bloccate": sum(1 for e in emissioni if e["stato"] in ("bloccata", "in_preparazione")),
            "n_draft": sum(1 for e in emissioni if e["stato"] == "draft"),
        })

    return {
        "commessa": commessa,
        "rami": rami_con_emissioni,
        "n_rami": len(rami),
        "has_branches": len(rami) > 0,
    }
