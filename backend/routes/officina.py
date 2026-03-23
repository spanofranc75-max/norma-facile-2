"""
Vista Officina — API per l'interfaccia operaio blindata.
4 Ponti: Diario (Timer), Foto, Qualità (Checklist), Blocco Dati.
Accesso tramite QR Code + PIN 4 cifre.
"""
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core.database import db
from core.config import settings

router = APIRouter(prefix="/officina", tags=["officina"])
logger = logging.getLogger(__name__)

DIARIO_COLL = "diario_produzione"
DOC_COLL = "commessa_documents"
TIMER_COLL = "officina_timers"
CHECKLIST_COLL = "officina_checklist"
ALERT_COLL = "officina_alerts"


# ── MODELS ───────────────────────────────────────────────────────

class PinVerify(BaseModel):
    pin: str
    operatore_id: str


class TimerAction(BaseModel):
    action: str  # "start", "pause", "resume", "stop"
    operatore_id: str
    operatore_nome: str


class ChecklistItem(BaseModel):
    codice: str
    esito: bool  # True = OK (👍), False = NOK (👎)


class ChecklistSubmit(BaseModel):
    operatore_id: str
    operatore_nome: str
    items: List[ChecklistItem]


# ── CHECKLIST DEFINITIONS ────────────────────────────────────────

CHECKLIST_CONFIG = {
    "EN_1090": [
        {"codice": "saldature_pulite", "icona": "flame", "label_admin": "Saldature Pulite"},
        {"codice": "dimensioni_ok", "icona": "ruler", "label_admin": "Dimensioni OK"},
        {"codice": "materiale_ok", "icona": "package", "label_admin": "Materiale OK"},
    ],
    "EN_13241": [
        {"codice": "sicurezze_ok", "icona": "shield", "label_admin": "Sicurezze OK"},
        {"codice": "movimento_ok", "icona": "move", "label_admin": "Movimento OK"},
    ],
    "GENERICA": [
        {"codice": "lavoro_ok", "icona": "check", "label_admin": "Lavoro Completato"},
    ],
}


# ── CONTEXT: load commessa + voce info (no auth required, uses PIN) ──

async def _get_officina_context(commessa_id: str, voce_id: str = None):
    """Load commessa and voce data for the worker view."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "oggetto": 1,
         "normativa_tipo": 1, "user_id": 1, "stato": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    voce = None
    normativa = commessa.get("normativa_tipo", "GENERICA")
    voce_desc = commessa.get("title") or commessa.get("oggetto") or ""

    if voce_id and voce_id != "__principale__":
        voce = await db.voci_lavoro.find_one(
            {"voce_id": voce_id, "commessa_id": commessa_id},
            {"_id": 0}
        )
        if voce:
            normativa = voce.get("normativa_tipo", normativa)
            voce_desc = voce.get("descrizione", voce_desc)

    return commessa, voce, normativa, voce_desc


# ── PIN MANAGEMENT ───────────────────────────────────────────────

@router.post("/pin/set")
async def set_operator_pin(data: dict):
    """Admin sets a 4-digit PIN for an operator."""
    op_id = data.get("operatore_id")
    pin = data.get("pin", "")
    admin_id = data.get("admin_id")

    if not op_id or not pin or not admin_id:
        raise HTTPException(400, "operatore_id, pin e admin_id sono obbligatori")
    if len(pin) != 4 or not pin.isdigit():
        raise HTTPException(400, "Il PIN deve essere di 4 cifre")

    result = await db.operatori.update_one(
        {"op_id": op_id, "admin_id": admin_id},
        {"$set": {"pin": pin, "pin_set_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Operatore non trovato")
    return {"message": "PIN impostato"}


@router.post("/pin/verify")
async def verify_pin(data: PinVerify):
    """Verify operator PIN for workshop access."""
    op = await db.operatori.find_one(
        {"op_id": data.operatore_id, "pin": data.pin},
        {"_id": 0, "op_id": 1, "nome": 1, "pin": 1}
    )
    if not op:
        raise HTTPException(401, "PIN errato")
    return {"valid": True, "operatore_id": op["op_id"], "operatore_nome": op["nome"]}


@router.get("/operatori/{commessa_id}")
async def list_operatori_for_pin(commessa_id: str):
    """List operators (name + id only) for the PIN selection screen."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id},
        {"_id": 0, "user_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    ops = await db.operatori.find(
        {"admin_id": commessa["user_id"]},
        {"_id": 0, "op_id": 1, "nome": 1}
    ).sort("nome", 1).to_list(100)
    return {"operatori": ops}


# ── CONTEXT ENDPOINT ─────────────────────────────────────────────

@router.get("/context/{commessa_id}")
async def get_officina_context(commessa_id: str, voce_id: str = None):
    """Get commessa + voce context for the worker view."""
    commessa, voce, normativa, voce_desc = await _get_officina_context(commessa_id, voce_id)

    # Get all voci for this commessa
    voci = await db.voci_lavoro.find(
        {"commessa_id": commessa_id},
        {"_id": 0}
    ).sort("ordine", 1).to_list(50)

    # Get active timer if any
    timer = await db[TIMER_COLL].find_one(
        {"commessa_id": commessa_id, "voce_id": voce_id or "", "status": {"$in": ["running", "paused"]}},
        {"_id": 0}
    )

    # Get checklist config
    checklist_items = CHECKLIST_CONFIG.get(normativa, CHECKLIST_CONFIG["GENERICA"])

    return {
        "commessa": {
            "commessa_id": commessa["commessa_id"],
            "numero": commessa.get("numero", ""),
            "title": commessa.get("title", ""),
            "normativa_tipo": commessa.get("normativa_tipo", ""),
            "stato": commessa.get("stato", ""),
        },
        "voce": {
            "voce_id": voce_id or "__principale__",
            "descrizione": voce_desc,
            "normativa_tipo": normativa,
        },
        "voci": voci,
        "timer": timer,
        "checklist_config": checklist_items,
    }


# ── PONTE 1: DIARIO (TIMER) ─────────────────────────────────────

@router.post("/timer/{commessa_id}")
async def timer_action(commessa_id: str, data: TimerAction, voce_id: str = ""):
    """Handle START / PAUSE / RESUME / STOP timer actions."""
    commessa, voce, normativa, voce_desc = await _get_officina_context(commessa_id, voce_id)
    now = datetime.now(timezone.utc)
    voce_key = voce_id or ""

    active = await db[TIMER_COLL].find_one(
        {"commessa_id": commessa_id, "voce_id": voce_key, "status": {"$in": ["running", "paused"]}},
        {"_id": 0}
    )

    if data.action == "start":
        if active:
            raise HTTPException(400, "Timer già attivo")

        # ── WORKFLOW GATE: SICUREZZA → DIARIO ──
        # Check safety courses (D.Lgs 81/08) + patentini
        from routes.sicurezza import check_sicurezza_operatore
        sic_check = await check_sicurezza_operatore(data.operatore_id)
        if sic_check["bloccato"]:
            motivi = "; ".join(sic_check["motivi"])
            raise HTTPException(
                403,
                f"ACCESSO BLOCCATO — Profilo Sicurezza non conforme: {motivi}"
            )

        # ── BLOCCO PATENTINI: EN 1090 richiede patentino saldatura valido ──
        if normativa == "EN_1090":
            operatore = await db.operatori.find_one(
                {"op_id": data.operatore_id},
                {"_id": 0, "patentini": 1, "nome": 1}
            )
            patentini = operatore.get("patentini", []) if operatore else []
            has_valid = False
            for pat in patentini:
                scadenza = pat.get("scadenza", "")
                if scadenza and scadenza >= now.strftime("%Y-%m-%d"):
                    has_valid = True
                    break
            if not has_valid and patentini:
                raise HTTPException(
                    403,
                    "Patentino scaduto — impossibile lavorare su voci EN 1090. Contattare il responsabile."
                )

        timer_id = f"tmr_{uuid.uuid4().hex[:10]}"
        doc = {
            "timer_id": timer_id,
            "commessa_id": commessa_id,
            "voce_id": voce_key,
            "normativa_tipo": normativa,
            "admin_id": commessa["user_id"],
            "operatore_id": data.operatore_id,
            "operatore_nome": data.operatore_nome,
            "status": "running",
            "started_at": now.isoformat(),
            "pauses": [],
            "total_paused_seconds": 0,
            "stopped_at": None,
            "total_minutes": 0,
        }
        await db[TIMER_COLL].insert_one(doc)
        doc.pop("_id", None)
        return doc

    if data.action == "pause":
        if not active or active["status"] != "running":
            raise HTTPException(400, "Nessun timer attivo da mettere in pausa")
        await db[TIMER_COLL].update_one(
            {"timer_id": active["timer_id"]},
            {"$set": {"status": "paused"}, "$push": {"pauses": {"paused_at": now.isoformat(), "resumed_at": None}}}
        )
        updated = await db[TIMER_COLL].find_one({"timer_id": active["timer_id"]}, {"_id": 0})
        return updated

    if data.action == "resume":
        if not active or active["status"] != "paused":
            raise HTTPException(400, "Timer non in pausa")
        pauses = active.get("pauses", [])
        total_paused = active.get("total_paused_seconds", 0)
        if pauses and pauses[-1].get("resumed_at") is None:
            paused_at = datetime.fromisoformat(pauses[-1]["paused_at"])
            total_paused += (now - paused_at).total_seconds()
            pauses[-1]["resumed_at"] = now.isoformat()
        await db[TIMER_COLL].update_one(
            {"timer_id": active["timer_id"]},
            {"$set": {"status": "running", "pauses": pauses, "total_paused_seconds": total_paused}}
        )
        updated = await db[TIMER_COLL].find_one({"timer_id": active["timer_id"]}, {"_id": 0})
        return updated

    if data.action == "stop":
        if not active:
            raise HTTPException(400, "Nessun timer attivo")
        # Calculate total minutes
        started = datetime.fromisoformat(active["started_at"])
        total_paused = active.get("total_paused_seconds", 0)
        # If currently paused, add the current pause duration
        if active["status"] == "paused":
            pauses = active.get("pauses", [])
            if pauses and pauses[-1].get("resumed_at") is None:
                paused_at = datetime.fromisoformat(pauses[-1]["paused_at"])
                total_paused += (now - paused_at).total_seconds()

        elapsed = (now - started).total_seconds() - total_paused
        total_minutes = max(0, round(elapsed / 60, 1))

        await db[TIMER_COLL].update_one(
            {"timer_id": active["timer_id"]},
            {"$set": {
                "status": "stopped",
                "stopped_at": now.isoformat(),
                "total_paused_seconds": total_paused,
                "total_minutes": total_minutes,
            }}
        )

        # ── CABLAGGIO: save to diario_produzione automatically ──
        entry_id = f"dp_{uuid.uuid4().hex[:10]}"
        ore = round(total_minutes / 60, 2)
        diario_doc = {
            "entry_id": entry_id,
            "commessa_id": commessa_id,
            "admin_id": commessa["user_id"],
            "data": now.strftime("%Y-%m-%d"),
            "fase": "produzione",
            "ore": ore,
            "operatori": [{"id": data.operatore_id, "nome": data.operatore_nome}],
            "ore_totali": ore,
            "note": f"Timer officina — {voce_desc}" if voce_desc else "Timer officina",
            "voce_id": voce_key,
            "numero_colata": "",
            "wps_usata": "",
            "note_collaudo": "",
            "created_by": data.operatore_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "source": "officina_timer",
        }
        await db[DIARIO_COLL].insert_one(diario_doc)
        diario_doc.pop("_id", None)

        logger.info(f"[OFFICINA] Timer stopped: {total_minutes}min → diario {entry_id} ({ore}h)")

        return {
            "timer_id": active["timer_id"],
            "status": "stopped",
            "total_minutes": total_minutes,
            "ore_registrate": ore,
            "diario_entry_id": entry_id,
        }

    raise HTTPException(400, f"Azione non valida: {data.action}")


# ── PONTE 2: FOTO (Smart Routing) ───────────────────────────────

@router.post("/foto/{commessa_id}")
async def upload_foto_smart(
    commessa_id: str,
    file: UploadFile = File(...),
    voce_id: str = Form(""),
    operatore_id: str = Form(""),
    operatore_nome: str = Form(""),
):
    """Upload a photo from the workshop. Auto-routes based on voce normativa."""
    commessa, voce, normativa, voce_desc = await _get_officina_context(commessa_id, voce_id)
    now = datetime.now(timezone.utc)

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    # Smart routing: determine doc type based on normativa
    if normativa == "EN_1090":
        tipo = "certificato_31"
        prefix = "FOTO_1090"
    elif normativa == "EN_13241":
        tipo = "foto"
        prefix = "FOTO_13241"
    else:
        tipo = "foto"
        prefix = "FOTO_GEN"

    # Build clear filename
    numero = commessa.get("numero", commessa_id)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    clean_name = f"{prefix}_{numero}_{timestamp}.jpg"

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    doc = {
        "doc_id": doc_id,
        "commessa_id": commessa_id,
        "user_id": commessa["user_id"],
        "nome_file": clean_name,
        "tipo": tipo,
        "content_type": file.content_type or "image/jpeg",
        "file_base64": base64.b64encode(content).decode("utf-8"),
        "size_bytes": len(content),
        "metadata_estratti": {
            "source": "officina",
            "normativa": normativa,
            "voce_id": voce_id or "__principale__",
            "voce_desc": voce_desc,
            "operatore_id": operatore_id,
            "operatore_nome": operatore_nome,
        },
        "note": f"Foto officina — {voce_desc}" if voce_desc else "Foto officina",
        "uploaded_at": now.isoformat(),
        "uploaded_by": operatore_nome or operatore_id,
    }

    await db[DOC_COLL].insert_one(doc)
    doc.pop("_id", None)
    doc.pop("file_base64", None)  # Don't return the base64 in response

    logger.info(f"[OFFICINA] Foto uploaded: {clean_name} → tipo={tipo} voce={voce_id}")

    return {
        "doc_id": doc_id,
        "nome_file": clean_name,
        "tipo": tipo,
        "normativa": normativa,
        "message": f"Foto salvata come {tipo}",
    }


# ── PONTE 3: QUALITÀ (Checklist) ────────────────────────────────

@router.post("/checklist/{commessa_id}")
async def submit_checklist(commessa_id: str, data: ChecklistSubmit, voce_id: str = ""):
    """Submit a quality checklist. Thumbs-down items create admin alerts."""
    commessa, voce, normativa, voce_desc = await _get_officina_context(commessa_id, voce_id)
    now = datetime.now(timezone.utc)

    checklist_id = f"chk_{uuid.uuid4().hex[:10]}"
    doc = {
        "checklist_id": checklist_id,
        "commessa_id": commessa_id,
        "voce_id": voce_id or "",
        "normativa_tipo": normativa,
        "admin_id": commessa["user_id"],
        "operatore_id": data.operatore_id,
        "operatore_nome": data.operatore_nome,
        "items": [item.model_dump() for item in data.items],
        "all_ok": all(item.esito for item in data.items),
        "submitted_at": now.isoformat(),
    }
    await db[CHECKLIST_COLL].insert_one(doc)
    doc.pop("_id", None)

    # ── CABLAGGIO: create alerts + NC entries for failed items (👎) ──
    failed = [item for item in data.items if not item.esito]
    if failed:
        config_map = {c["codice"]: c for c in CHECKLIST_CONFIG.get(normativa, [])}
        nc_coll = "registro_nc"
        for item in failed:
            label = config_map.get(item.codice, {}).get("label_admin", item.codice)

            # Create alert
            alert = {
                "alert_id": f"alert_{uuid.uuid4().hex[:10]}",
                "admin_id": commessa["user_id"],
                "commessa_id": commessa_id,
                "commessa_numero": commessa.get("numero", ""),
                "voce_id": voce_id or "",
                "voce_desc": voce_desc,
                "tipo": "non_conformita",
                "messaggio": f"NC: Controllo '{label}' NON superato",
                "operatore_nome": data.operatore_nome,
                "normativa": normativa,
                "checklist_id": checklist_id,
                "letto": False,
                "created_at": now.isoformat(),
            }
            await db[ALERT_COLL].insert_one(alert)
            alert.pop("_id", None)

            # Create NC entry in Registro Non Conformità
            nc_id = f"nc_{uuid.uuid4().hex[:10]}"
            nc_doc = {
                "nc_id": nc_id,
                "commessa_id": commessa_id,
                "commessa_numero": commessa.get("numero", ""),
                "admin_id": commessa["user_id"],
                "voce_id": voce_id or "",
                "tipo": "checklist_nok",
                "descrizione": f"Controllo '{label}' NON superato",
                "operatore_nome": data.operatore_nome,
                "normativa": normativa,
                "source_id": checklist_id,
                "stato": "aperta",
                "azione_correttiva": "",
                "chiusa_da": "",
                "note_chiusura": "",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            await db[nc_coll].insert_one(nc_doc)
            nc_doc.pop("_id", None)

            logger.warning(f"[OFFICINA] NC + Alert: {label} NOK — commessa {commessa.get('numero', commessa_id)}")

    return {
        "checklist_id": checklist_id,
        "all_ok": doc["all_ok"],
        "problemi": len(failed),
        "message": "Controllo salvato" if doc["all_ok"] else f"{len(failed)} problema/i segnalato/i all'admin",
    }


# ── ADMIN: Alert Badge ──────────────────────────────────────────

@router.get("/alerts/count")
async def get_alerts_count(admin_id: str):
    """Get count of unread quality alerts for admin badge."""
    count = await db[ALERT_COLL].count_documents({"admin_id": admin_id, "letto": False})
    return {"count": count}


@router.get("/alerts")
async def list_alerts(admin_id: str, limit: int = 50):
    """List quality alerts for admin."""
    alerts = await db[ALERT_COLL].find(
        {"admin_id": admin_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    return {"alerts": alerts}


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    await db[ALERT_COLL].update_one(
        {"alert_id": alert_id},
        {"$set": {"letto": True}}
    )
    return {"message": "Alert letto"}


# ── QR CODE for Officina ─────────────────────────────────────────

@router.get("/qr-url/{commessa_id}")
async def get_officina_qr_url(commessa_id: str, voce_id: str = None):
    """Get the URL for the officina QR code (includes voce_id)."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id},
        {"_id": 0, "numero": 1, "title": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    voce_param = f"/{voce_id}" if voce_id else ""
    url = f"{settings.domain_url}/officina/{commessa_id}{voce_param}"

    return {
        "url": url,
        "commessa_numero": commessa.get("numero", ""),
        "commessa_title": commessa.get("title", ""),
    }
