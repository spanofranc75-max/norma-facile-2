"""
Istruttoria Automatica — API Routes
=====================================
Motore di istruttoria tecnica automatica da preventivo.
Fase 1: Analisi AI + Classificazione + Regole deterministiche.
"""

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from core.database import db
from services.ai_compliance_engine import analizza_preventivo_completo
from services.applicabilita_engine import calcola_applicabilita

router = APIRouter(prefix="/istruttoria", tags=["istruttoria"])
logger = logging.getLogger(__name__)


@router.post("/analizza-preventivo/{preventivo_id}")
async def analizza_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Fase 1 — Analisi completa del preventivo:
    1A: Estrazione tecnica strutturata (GPT)
    1B: Classificazione normativa + proposta istruttoria (GPT + Rules)

    Salva il risultato in DB e lo restituisce.
    """
    uid = user["user_id"]

    # Load preventivo
    preventivo = await db.preventivi.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not preventivo:
        raise HTTPException(404, "Preventivo non trovato")

    # Check if analysis already exists (allow re-analysis)
    existing = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0, "istruttoria_id": 1, "created_at": 1}
    )

    # Run full analysis
    logger.info(f"[ISTRUTTORIA] Avvio analisi per preventivo {preventivo_id}")
    result = await analizza_preventivo_completo(preventivo)

    if result.get("stato") == "errore":
        logger.error(f"[ISTRUTTORIA] Analisi fallita: {result.get('errore')}")
        raise HTTPException(500, f"Errore analisi: {result.get('errore')}")

    # Save to DB
    istr_id = existing.get("istruttoria_id") if existing else f"istr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc = {
        **result,
        "istruttoria_id": istr_id,
        "preventivo_id": preventivo_id,
        "user_id": uid,
        "versione": (existing.get("versione", 0) + 1) if existing else 1,
        "updated_at": now,
    }

    if existing:
        await db.istruttorie.update_one(
            {"istruttoria_id": istr_id},
            {"$set": doc}
        )
        logger.info(f"[ISTRUTTORIA] Aggiornata {istr_id} (v{doc['versione']})")
    else:
        doc["created_at"] = now
        await db.istruttorie.insert_one(doc)
        logger.info(f"[ISTRUTTORIA] Creata {istr_id}")

    # Clean response
    doc.pop("_id", None)
    return doc


@router.get("/preventivo/{preventivo_id}")
async def get_istruttoria_by_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Recupera l'istruttoria salvata per un preventivo (se esiste)."""
    doc = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Nessuna istruttoria trovata per questo preventivo")
    return doc


@router.get("/{istruttoria_id}")
async def get_istruttoria(istruttoria_id: str, user: dict = Depends(get_current_user)):
    """Recupera un'istruttoria per ID."""
    doc = await db.istruttorie.find_one(
        {"istruttoria_id": istruttoria_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Istruttoria non trovata")
    return doc


@router.post("/{istruttoria_id}/revisione")
async def revisione_umana(istruttoria_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Override umano tracciato. L'utente corregge/conferma i dati proposti dall'AI.
    Salva sia il valore AI originale sia la correzione umana con chi/quando.

    Body: {
        "campo": "classificazione.normativa_proposta" | "profilo_tecnico.valore" | ...,
        "valore_corretto": "EN_1090",
        "motivazione": "Il preventivo include anche parti strutturali" (opzionale)
    }
    """
    uid = user["user_id"]
    doc = await db.istruttorie.find_one(
        {"istruttoria_id": istruttoria_id, "user_id": uid},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Istruttoria non trovata")

    campo = body.get("campo", "")
    valore_corretto = body.get("valore_corretto")
    motivazione = body.get("motivazione", "")

    if not campo or valore_corretto is None:
        raise HTTPException(400, "Specificare 'campo' e 'valore_corretto'")

    now = datetime.now(timezone.utc)

    # Navigate to the field to get the AI value
    parts = campo.split(".")
    ai_value = doc
    for p in parts:
        if isinstance(ai_value, dict):
            ai_value = ai_value.get(p)
        else:
            ai_value = None
            break

    override_entry = {
        "campo": campo,
        "valore_ai": ai_value,
        "valore_umano": valore_corretto,
        "motivazione_correzione": motivazione,
        "corretto_da": uid,
        "corretto_da_nome": user.get("name", user.get("email", uid)),
        "corretto_il": now.isoformat(),
    }

    # Apply the correction to the document
    update_ops = {
        "$push": {"revisioni_umane": override_entry},
        "$set": {"updated_at": now, "stato_revisione": "revisionato"},
    }

    # Also set the corrected value in the actual field
    if len(parts) >= 1:
        update_ops["$set"][campo] = valore_corretto

    await db.istruttorie.update_one(
        {"istruttoria_id": istruttoria_id},
        update_ops
    )

    logger.info(f"[ISTRUTTORIA] Revisione umana: {campo} = {valore_corretto} (era: {ai_value})")

    return {
        "message": f"Revisione salvata: {campo}",
        "override": override_entry,
    }


@router.post("/{istruttoria_id}/conferma")
async def conferma_istruttoria(istruttoria_id: str, user: dict = Depends(get_current_user)):
    """L'utente conferma l'istruttoria come base per la Fase 2 (generazione commessa).
    Questo checkpoint e obbligatorio prima di generare la commessa pre-istruita.
    Blocca conferma se ci sono blocchi strutturali (es. commessa mista non segmentata)."""
    uid = user["user_id"]
    doc = await db.istruttorie.find_one(
        {"istruttoria_id": istruttoria_id, "user_id": uid},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Istruttoria non trovata")

    # Check for blocking conditions
    applicabilita = doc.get("applicabilita", {})
    blocchi = applicabilita.get("blocchi_conferma", [])
    blocchi_bloccanti = [b for b in blocchi if b.get("bloccante")]
    if blocchi_bloccanti:
        raise HTTPException(
            409,
            f"Conferma bloccata: {blocchi_bloccanti[0]['messaggio']}"
        )

    now = datetime.now(timezone.utc)
    await db.istruttorie.update_one(
        {"istruttoria_id": istruttoria_id},
        {"$set": {
            "confermata": True,
            "confermata_da": uid,
            "confermata_da_nome": user.get("name", user.get("email", uid)),
            "confermata_il": now.isoformat(),
            "updated_at": now,
        }}
    )

    logger.info(f"[ISTRUTTORIA] Confermata {istruttoria_id} da {uid}")
    return {"message": "Istruttoria confermata. Pronta per la Fase 2.", "istruttoria_id": istruttoria_id}



@router.post("/{istruttoria_id}/rispondi")
async def rispondi_domande(istruttoria_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Salva le risposte dell'utente alle domande residue generate dall'AI.

    Body: {
        "risposte": [
            {"domanda_idx": 0, "risposta": "Testo risposta utente"},
            {"domanda_idx": 1, "risposta": "Altra risposta"},
            ...
        ]
    }
    """
    uid = user["user_id"]
    doc = await db.istruttorie.find_one(
        {"istruttoria_id": istruttoria_id, "user_id": uid},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Istruttoria non trovata")

    risposte_input = body.get("risposte", [])
    if not risposte_input:
        raise HTTPException(400, "Nessuna risposta fornita")

    now = datetime.now(timezone.utc)
    domande = doc.get("domande_residue", [])

    # Build the risposte map: merge with any existing answers
    risposte_esistenti = doc.get("risposte_utente", {})

    for r in risposte_input:
        idx = r.get("domanda_idx")
        risposta_text = r.get("risposta", "").strip()
        if idx is None or idx < 0 or idx >= len(domande):
            continue
        if not risposta_text:
            continue

        risposte_esistenti[str(idx)] = {
            "risposta": risposta_text,
            "domanda": domande[idx].get("domanda", ""),
            "risposto_da": uid,
            "risposto_da_nome": user.get("name", user.get("email", uid)),
            "risposto_il": now.isoformat(),
        }

    n_risposte = len(risposte_esistenti)
    n_domande = len(domande)

    # Calcola applicabilita condizionale
    applicabilita = calcola_applicabilita(domande, risposte_esistenti)

    await db.istruttorie.update_one(
        {"istruttoria_id": istruttoria_id},
        {"$set": {
            "risposte_utente": risposte_esistenti,
            "n_risposte": n_risposte,
            "n_domande_totali": n_domande,
            "applicabilita": applicabilita,
            "updated_at": now,
        }}
    )

    logger.info(f"[ISTRUTTORIA] Risposte salvate: {n_risposte}/{n_domande} per {istruttoria_id}")

    return {
        "message": f"Risposte salvate: {n_risposte}/{n_domande}",
        "risposte_utente": risposte_esistenti,
        "n_risposte": n_risposte,
        "n_domande_totali": n_domande,
        "applicabilita": applicabilita,
    }


@router.get("")
async def list_istruttorie(user: dict = Depends(get_current_user)):
    """Lista tutte le istruttorie dell'utente."""
    docs = await db.istruttorie.find(
        {"user_id": user["user_id"]},
        {"_id": 0, "istruttoria_id": 1, "preventivo_id": 1, "preventivo_number": 1,
         "classificazione": 1, "exc_proposta": 1, "stato_conoscenza": 1,
         "stato": 1, "created_at": 1, "updated_at": 1, "versione": 1}
    ).sort("updated_at", -1).to_list(100)
    return {"istruttorie": docs, "total": len(docs)}
