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
from services.applicabilita_engine import calcola_applicabilita, genera_domande_contestuali
from services.segmentation_engine import segmenta_preventivo
from services.phase2_engine import check_eligibility, generate_preistruita

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

    # Genera domande contestuali (preserva risposte esistenti, marca stale)
    ctx_esistenti = doc.get("domande_contestuali", [])
    domande_ctx = genera_domande_contestuali(domande, risposte_esistenti, ctx_esistenti)

    await db.istruttorie.update_one(
        {"istruttoria_id": istruttoria_id},
        {"$set": {
            "risposte_utente": risposte_esistenti,
            "n_risposte": n_risposte,
            "n_domande_totali": n_domande,
            "applicabilita": applicabilita,
            "domande_contestuali": domande_ctx,
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
        "domande_contestuali": domande_ctx,
    }


@router.post("/{istruttoria_id}/rispondi-contestuale")
async def rispondi_domande_contestuali(
    istruttoria_id: str, body: dict, user: dict = Depends(get_current_user)
):
    """Salva risposte alle domande contestuali (figlie delle domande base).

    Body: { "risposte": [{"id": "ctx_zinc_01", "risposta": "Testo"}, ...] }
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
    domande_ctx = doc.get("domande_contestuali", [])
    ctx_map = {q["id"]: i for i, q in enumerate(domande_ctx)}

    updated_count = 0
    for r in risposte_input:
        qid = r.get("id")
        risposta_text = r.get("risposta", "").strip()
        if not qid or qid not in ctx_map:
            continue
        if not risposta_text:
            continue

        idx = ctx_map[qid]
        domande_ctx[idx]["risposta"] = risposta_text
        domande_ctx[idx]["risposto_da"] = uid
        domande_ctx[idx]["risposto_da_nome"] = user.get("name", user.get("email", uid))
        domande_ctx[idx]["risposto_il"] = now.isoformat()
        domande_ctx[idx]["stale"] = False
        updated_count += 1

    await db.istruttorie.update_one(
        {"istruttoria_id": istruttoria_id},
        {"$set": {
            "domande_contestuali": domande_ctx,
            "updated_at": now,
        }}
    )

    logger.info(
        f"[ISTRUTTORIA] Risposte contestuali salvate: {updated_count} per {istruttoria_id}"
    )

    return {
        "message": f"Risposte contestuali salvate: {updated_count}",
        "domande_contestuali": domande_ctx,
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


# ═══════════════════════════════════════════════════════════════
#  SEGMENTAZIONE — P1.1
# ═══════════════════════════════════════════════════════════════

@router.post("/segmenta/{preventivo_id}")
async def run_segmentazione(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Esegue la segmentazione per riga del preventivo.
    Analizza ogni riga e propone la normativa applicabile."""
    uid = user["user_id"]

    preventivo = await db.preventivi.find_one(
        {"preventivo_id": preventivo_id},
        {"_id": 0}
    )
    if not preventivo:
        raise HTTPException(404, "Preventivo non trovato")

    logger.info(f"[SEGM] Avvio segmentazione per {preventivo_id}")

    segmentazione = await segmenta_preventivo(preventivo)

    if not segmentazione.get("enabled"):
        return {"segmentazione": segmentazione}

    # Save to istruttoria if exists, otherwise create a minimal record
    istr = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0, "istruttoria_id": 1}
    )

    if istr:
        await db.istruttorie.update_one(
            {"istruttoria_id": istr["istruttoria_id"]},
            {"$set": {
                "segmentazione_proposta": segmentazione,
                "updated_at": datetime.now(timezone.utc),
            }}
        )
    else:
        istr_id = f"istr_{uuid.uuid4().hex[:12]}"
        await db.istruttorie.insert_one({
            "istruttoria_id": istr_id,
            "preventivo_id": preventivo_id,
            "preventivo_number": preventivo.get("number", ""),
            "user_id": uid,
            "stato": "segmentazione",
            "segmentazione_proposta": segmentazione,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

    return {"segmentazione": segmentazione}


@router.post("/segmenta/{preventivo_id}/review")
async def review_segmentazione(preventivo_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Utente conferma/corregge la segmentazione.
    Body: {
        "line_reviews": [
            {"line_id": "ln_xxx", "final_normativa": "EN_1090", "decision": "accepted|corrected"},
            ...
        ],
        "action": "confirm" | "save_draft"
    }
    """
    uid = user["user_id"]

    istr = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0, "istruttoria_id": 1, "segmentazione_proposta": 1}
    )
    if not istr:
        raise HTTPException(404, "Istruttoria non trovata")

    seg = istr.get("segmentazione_proposta")
    if not seg:
        raise HTTPException(400, "Nessuna segmentazione proposta presente")

    line_reviews = body.get("line_reviews", [])
    action = body.get("action", "save_draft")

    # Apply reviews to line_classification
    review_map = {r["line_id"]: r for r in line_reviews}
    for lc in seg.get("line_classification", []):
        lid = lc.get("line_id")
        if lid in review_map:
            rev = review_map[lid]
            lc["review"] = {
                "final_normativa": rev.get("final_normativa"),
                "decision": rev.get("decision", "accepted"),
                "reviewed_by": uid,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    if action == "confirm":
        # Build official segmentation
        line_assignments = []
        has_uncertain = False
        for lc in seg.get("line_classification", []):
            rev = lc.get("review", {})
            final = rev.get("final_normativa") or lc.get("proposed_normativa")
            if final == "INCERTA":
                has_uncertain = True
            line_assignments.append({
                "line_id": lc["line_id"],
                "normativa": final,
            })

        if has_uncertain:
            raise HTTPException(400, "Non puoi confermare con righe ancora INCERTE. Classifica tutte le righe prima.")

        official = {
            "confirmed": True,
            "confirmed_by": uid,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "line_assignments": line_assignments,
        }

        seg["status"] = "confirmed"
        await db.istruttorie.update_one(
            {"istruttoria_id": istr["istruttoria_id"]},
            {"$set": {
                "segmentazione_proposta": seg,
                "official_segmentation": official,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

        return {"status": "confirmed", "official_segmentation": official}
    else:
        seg["status"] = "in_review"
        await db.istruttorie.update_one(
            {"istruttoria_id": istr["istruttoria_id"]},
            {"$set": {
                "segmentazione_proposta": seg,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

        return {"status": "in_review", "segmentazione": seg}



# ═══════════════════════════════════════════════════════════════
#  PHASE 2 — COMMESSA PRE-ISTRUITA REVISIONATA
# ═══════════════════════════════════════════════════════════════

@router.get("/phase2/eligibility/{preventivo_id}")
async def check_phase2_eligibility(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Verifica se l'istruttoria e' eleggibile per la Phase 2.
    Restituisce allowed=true/false con lista motivi di blocco."""
    uid = user["user_id"]

    istr = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not istr:
        raise HTTPException(404, "Istruttoria non trovata")

    result = check_eligibility(istr)
    return result


@router.post("/phase2/genera/{preventivo_id}")
async def genera_commessa_preistruita(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Genera la commessa pre-istruita revisionata.
    Bloccata se non tutti i criteri di eleggibilita' sono soddisfatti."""
    uid = user["user_id"]

    istr = await db.istruttorie.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not istr:
        raise HTTPException(404, "Istruttoria non trovata")

    # Check eligibility
    elig = check_eligibility(istr)
    if not elig["allowed"]:
        raise HTTPException(409, {
            "message": "Commessa pre-istruita non generabile",
            "reasons": elig["reasons"],
            "checks": elig["checks"],
        })

    # Generate
    commessa = generate_preistruita(istr)

    # Save to DB
    await db.commesse_preistruite.update_one(
        {"preventivo_id": preventivo_id, "created_by": uid},
        {"$set": {
            **commessa,
            "user_id": uid,
        }},
        upsert=True
    )

    # Update istruttoria
    await db.istruttorie.update_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"$set": {
            "phase2_generata": True,
            "phase2_commessa_id": commessa["commessa_id"],
            "phase2_generata_il": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    logger.info(f"[PHASE2] Commessa pre-istruita generata: {commessa['commessa_id']} per {preventivo_id}")
    return {"commessa": commessa, "warnings": elig.get("warnings", [])}


@router.get("/phase2/commessa/{preventivo_id}")
async def get_commessa_preistruita(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Recupera la commessa pre-istruita per un preventivo."""
    uid = user["user_id"]

    doc = await db.commesse_preistruite.find_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Commessa pre-istruita non trovata")

    return {"commessa": doc}

