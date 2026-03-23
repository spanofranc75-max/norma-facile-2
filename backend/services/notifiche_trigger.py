"""
Notifiche Smart — Trigger Engine (N2)
=======================================
Genera notifiche in-app da eventi significativi del sistema.
Chiamato dai route/service quando accade qualcosa di rilevante.
"""

import logging
from core.database import db
from services.notifiche_smart_service import crea_notifica

logger = logging.getLogger(__name__)


async def notify_semaforo_change(
    user_id: str,
    commessa_id: str,
    numero: str,
    old_semaforo: str,
    new_semaforo: str,
):
    """Trigger N2.1: Commessa semaphore worsened."""
    RANK = {"verde": 0, "giallo": 1, "rosso": 2}
    if RANK.get(new_semaforo, 0) <= RANK.get(old_semaforo, 0):
        return  # Not worsened, skip

    severity = "critica" if new_semaforo == "rosso" else "alta"
    title = f"Commessa {numero}: semaforo {old_semaforo} → {new_semaforo}"
    message = (
        f"La commessa {numero} e passata a {new_semaforo.upper()}."
        if new_semaforo == "rosso"
        else f"La commessa {numero} richiede attenzione."
    )

    await crea_notifica(
        user_id=user_id,
        notification_type="semaforo_peggiorato",
        title=title,
        message=message,
        commessa_id=commessa_id,
        entity_type="commessa",
        entity_id=commessa_id,
        linked_route=f"/commesse/{commessa_id}",
        dedupe_key=f"semaforo:{commessa_id}:{new_semaforo}",
        severity=severity,
    )


async def notify_nuovo_hard_block(
    user_id: str,
    commessa_id: str,
    numero: str,
    obbligo_title: str,
    obbligo_id: str,
    source_module: str,
):
    """Trigger N2.2: New hard-block obligation created."""
    await crea_notifica(
        user_id=user_id,
        notification_type="nuovo_hard_block",
        title=f"Nuovo blocco critico: {obbligo_title[:60]}",
        message=f"Commessa {numero} — blocco da {source_module}.",
        commessa_id=commessa_id,
        entity_type="obbligo",
        entity_id=obbligo_id,
        linked_route=f"/commesse/{commessa_id}",
        dedupe_key=f"hardblock:{obbligo_id}",
        severity="critica",
    )


async def notify_documento_scaduto(
    user_id: str,
    commessa_id: str,
    numero: str,
    doc_title: str,
    doc_id: str,
    days_expired: int = 0,
):
    """Trigger N2.3: Critical document expired."""
    msg = (
        f"Documento '{doc_title}' scaduto da {days_expired} giorni."
        if days_expired > 0
        else f"Documento '{doc_title}' in scadenza."
    )
    await crea_notifica(
        user_id=user_id,
        notification_type="documento_scaduto",
        title=f"Documento scaduto: {doc_title[:50]}",
        message=f"Commessa {numero} — {msg}",
        commessa_id=commessa_id,
        entity_type="documento_archivio",
        entity_id=doc_id,
        linked_route=f"/pacchetti-documentali",
        dedupe_key=f"docscad:{doc_id}",
        severity="alta",
    )


async def notify_emissione_bloccata(
    user_id: str,
    commessa_id: str,
    numero: str,
    emissione_codice: str,
    emissione_id: str,
    n_blockers: int = 0,
):
    """Trigger N2.4: Emission blocked by evidence gate."""
    await crea_notifica(
        user_id=user_id,
        notification_type="emissione_bloccata",
        title=f"Emissione bloccata: {emissione_codice}",
        message=f"Commessa {numero} — {n_blockers} blocchi su evidence gate.",
        commessa_id=commessa_id,
        entity_type="emissione",
        entity_id=emissione_id,
        linked_route=f"/commesse/{commessa_id}",
        dedupe_key=f"emblock:{emissione_id}",
        severity="alta",
    )


async def notify_gate_pos_peggiorato(
    user_id: str,
    commessa_id: str,
    numero: str,
    cantiere_id: str,
    n_mancanti: int = 0,
    n_blockers: int = 0,
):
    """Trigger N2.5: POS gate worsened (no longer ready)."""
    await crea_notifica(
        user_id=user_id,
        notification_type="gate_pos_peggiorato",
        title=f"Gate POS non pronto: {numero}",
        message=f"Commessa {numero} — {n_mancanti} campi mancanti, {n_blockers} blocchi.",
        commessa_id=commessa_id,
        entity_type="cantiere_sicurezza",
        entity_id=cantiere_id,
        linked_route=f"/sicurezza/{cantiere_id}",
        dedupe_key=f"gatepos:{cantiere_id}",
        severity="media",
    )


async def notify_pacchetto_incompleto(
    user_id: str,
    commessa_id: str,
    numero: str,
    pack_label: str,
    pack_id: str,
    n_missing: int = 0,
    n_expired: int = 0,
):
    """Trigger N2.6: Package incomplete after verification."""
    await crea_notifica(
        user_id=user_id,
        notification_type="pacchetto_incompleto",
        title=f"Pacchetto incompleto: {pack_label[:50]}",
        message=f"Commessa {numero} — {n_missing} mancanti, {n_expired} scaduti.",
        commessa_id=commessa_id,
        entity_type="pacchetto_documentale",
        entity_id=pack_id,
        linked_route=f"/pacchetti-documentali",
        dedupe_key=f"packinc:{pack_id}",
        severity="media",
    )


# ── High-level trigger: post-sync analysis ──

async def check_and_notify_post_sync(
    user_id: str,
    commessa_id: str,
    sync_result: dict,
):
    """Called after obblighi sync to generate relevant notifications.
    
    Checks for new hard blocks created during sync.
    Also computes semaphore change.
    """
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "numero": 1},
    )
    if not commessa:
        return

    numero = commessa.get("numero", commessa_id)
    created = sync_result.get("created", 0)

    if created == 0:
        return

    # Check if any new hard blocks were created
    new_blocks = await db.obblighi_commessa.find(
        {
            "user_id": user_id,
            "commessa_id": commessa_id,
            "blocking_level": "hard_block",
            "status": {"$in": ["nuovo", "da_verificare", "in_corso", "bloccante"]},
        },
        {"_id": 0, "obbligo_id": 1, "title": 1, "source_module": 1},
    ).sort("created_at", -1).to_list(5)

    for block in new_blocks:
        await notify_nuovo_hard_block(
            user_id=user_id,
            commessa_id=commessa_id,
            numero=numero,
            obbligo_title=block.get("title", ""),
            obbligo_id=block.get("obbligo_id", ""),
            source_module=block.get("source_module", ""),
        )


async def check_and_notify_semaforo(user_id: str, commessa_id: str):
    """Compare current semaphore with last known and notify if worsened."""
    from datetime import date

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0, "numero": 1},
    )
    if not commessa:
        return

    numero = commessa.get("numero", commessa_id)

    # Compute current semaphore from obblighi
    obblighi = await db.obblighi_commessa.find(
        {"user_id": user_id, "commessa_id": commessa_id,
         "status": {"$in": ["nuovo", "da_verificare", "in_corso", "bloccante"]}},
        {"_id": 0, "blocking_level": 1},
    ).to_list(500)

    bloccanti = sum(1 for o in obblighi if o.get("blocking_level") == "hard_block")
    warnings = sum(1 for o in obblighi if o.get("blocking_level") == "warning")
    aperti = len(obblighi)

    if bloccanti > 0:
        new_sem = "rosso"
    elif warnings > 0 or aperti > 3:
        new_sem = "giallo"
    else:
        new_sem = "verde"

    # Get last known semaphore from cache
    cache = await db.cache_semaforo.find_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"_id": 0},
    )
    old_sem = cache.get("semaforo", "verde") if cache else "verde"

    # Update cache
    await db.cache_semaforo.update_one(
        {"commessa_id": commessa_id, "user_id": user_id},
        {"$set": {"semaforo": new_sem, "updated_at": date.today().isoformat()}},
        upsert=True,
    )

    # Notify if worsened
    if new_sem != old_sem:
        await notify_semaforo_change(user_id, commessa_id, numero, old_sem, new_sem)
