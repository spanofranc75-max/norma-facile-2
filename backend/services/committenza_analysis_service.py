"""
Verifica Committenza — Service (C1)
====================================
Analisi AI dei documenti ricevuti dalla committenza.
Estrae obblighi, anomalie, mismatch e domande residue.
Non duplica documenti: lavora sopra documenti_archivio esistenti.

Collections:
  - pacchetti_committenza: package analisi (riferimenti a doc_id esistenti)
  - analisi_committenza: risultato AI strutturato + review umana + snapshot
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None
    logger.warning("emergentintegrations not available — committenza analysis disabled")


# ═══════════════════════════════════════════════════════════════
#  CATEGORIE DOCUMENTI COMMITTENZA
# ═══════════════════════════════════════════════════════════════

DOC_CATEGORIES = [
    {"code": "contratto", "label": "Contratto"},
    {"code": "ordine", "label": "Ordine Cliente"},
    {"code": "capitolato", "label": "Capitolato Tecnico"},
    {"code": "condizioni_generali", "label": "Condizioni Generali"},
    {"code": "allegato_tecnico", "label": "Allegato Tecnico"},
    {"code": "allegato_sicurezza", "label": "Allegato Sicurezza"},
    {"code": "psc_duvri", "label": "PSC / DUVRI"},
    {"code": "mail_richiesta", "label": "Mail con Richieste"},
    {"code": "disciplinare", "label": "Disciplinare Fornitore"},
    {"code": "modulistica", "label": "Modulistica Onboarding"},
    {"code": "richiesta_documentale", "label": "Richiesta Documentale"},
    {"code": "altro", "label": "Altro"},
]


# ═══════════════════════════════════════════════════════════════
#  C1.1 — PACKAGE ANALISI COMMITTENZA
# ═══════════════════════════════════════════════════════════════

async def crea_package(user_id: str, commessa_id: str, title: str = "",
                       document_refs: list = None, tenant_id: str = None) -> dict:
    """Create an analysis package referencing existing docs from the archive."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0, "commessa_id": 1, "title": 1}
    )
    if not commessa:
        return {"error": "Commessa non trovata"}

    package_id = f"pc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    # document_refs: [{doc_id, category}]
    refs = []
    if document_refs:
        for ref in document_refs:
            doc_id = ref.get("doc_id", "")
            cat = ref.get("category", "altro")
            doc = await db.documenti_archivio.find_one(
                {"doc_id": doc_id, "user_id": user_id}, {"_id": 0, "doc_id": 1, "title": 1, "file_id": 1, "file_name": 1}
            )
            if doc:
                refs.append({
                    "doc_id": doc_id,
                    "category": cat,
                    "title": doc.get("title", doc.get("file_name", "")),
                    "file_id": doc.get("file_id", ""),
                    "file_name": doc.get("file_name", ""),
                })

    package = {
        "package_id": package_id,
        "user_id": user_id,
        "tenant_id": None,
        "commessa_id": commessa_id,
        "title": title or f"Verifica committenza - {commessa.get('title', commessa_id)}",
        "status": "uploaded",
        "document_refs": refs,
        "analysis_id": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.pacchetti_committenza.insert_one(package)
    package.pop("_id", None)
    return package


async def get_package(package_id: str, user_id: str, tenant_id: str = None) -> Optional[dict]:
    return await db.pacchetti_committenza.find_one(
        {"package_id": package_id, "user_id": user_id}, {"_id": 0}
    )


async def list_packages(user_id: str, commessa_id: str = None, tenant_id: str = None) -> list:
    query = {"user_id": user_id}
    if commessa_id:
        query["commessa_id"] = commessa_id
    return await db.pacchetti_committenza.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)


async def add_doc_to_package(package_id: str, user_id: str, doc_id: str, category: str = "altro", tenant_id: str = None) -> dict:
    """Add an existing archive document to a package."""
    package = await get_package(package_id, user_id)
    if not package:
        return {"error": "Package non trovato"}

    doc = await db.documenti_archivio.find_one(
        {"doc_id": doc_id, "user_id": user_id}, {"_id": 0, "doc_id": 1, "title": 1, "file_id": 1, "file_name": 1}
    )
    if not doc:
        return {"error": "Documento non trovato nell'archivio"}

    # Check if already in package
    existing_ids = {r["doc_id"] for r in package.get("document_refs", [])}
    if doc_id in existing_ids:
        return {"error": "Documento gia presente nel package"}

    ref = {
        "doc_id": doc_id,
        "category": category,
        "title": doc.get("title", doc.get("file_name", "")),
        "file_id": doc.get("file_id", ""),
        "file_name": doc.get("file_name", ""),
    }

    await db.pacchetti_committenza.update_one(
        {"package_id": package_id, "user_id": user_id},
        {"$push": {"document_refs": ref}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return await get_package(package_id, user_id)


async def remove_doc_from_package(package_id: str, user_id: str, doc_id: str, tenant_id: str = None) -> dict:
    """Remove a document reference from a package."""
    await db.pacchetti_committenza.update_one(
        {"package_id": package_id, "user_id": user_id},
        {"$pull": {"document_refs": {"doc_id": doc_id}},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return await get_package(package_id, user_id)


# ═══════════════════════════════════════════════════════════════
#  C1.2 — MOTORE AI ANALISI COMMITTENZA
# ═══════════════════════════════════════════════════════════════

COMMITTENZA_SYSTEM_PROMPT = """Sei un esperto di contrattualistica e compliance per aziende di carpenteria metallica e costruzioni metalliche (EN 1090, EN 13241, DM 2018, ecc.).

Il tuo compito e analizzare documenti ricevuti dalla committenza (contratti, ordini, capitolati, PSC, allegati) ed estrarre in modo strutturato:

1. OBBLIGHI: ogni requisito/obbligo imposto dal committente
2. ANOMALIE: clausole squilibrate, penali eccessive, richieste inusuali
3. MISMATCH: richieste non coperte dal preventivo/offerta dell'azienda
4. DOMANDE: punti ambigui che richiedono chiarimento

CATEGORIE OBBLIGHI:
- contrattuale: penali, garanzie, pagamenti, assicurazioni, foro
- tecnico: materiali, prove, tolleranze, certificazioni, classi EXC
- documentale: manuali, dichiarazioni, certificati, as-built, schede
- sicurezza: POS, PSC/DUVRI, attestati, accessi, procedure cantiere
- logistico_temporale: date, milestone, consegne, finestre operative

REGOLE IMPORTANTI:
- NON dichiarare che il contratto e "legalmente sicuro"
- NON sostituire il consulente legale
- Segnala, evidenzia, classifica, suggerisci revisione
- Ogni item deve avere un codice univoco (es. CLIENT_POS_REQUIRED)
- I codici devono essere in UPPER_SNAKE_CASE
- La confidence va da 0.0 a 1.0
- severity: alta, media, bassa
- blocking_level: hard_block, warning, none

Rispondi ESCLUSIVAMENTE in JSON valido, senza markdown o commenti."""


COMMITTENZA_USER_TEMPLATE = """## Documenti Committenza
{documents_text}

## Dati Commessa/Preventivo Esistenti
{system_context}

## Rispondi con questo schema JSON esatto:
{{
  "summary": {{
    "contract_present": true/false,
    "technical_specs_present": true/false,
    "safety_docs_present": true/false,
    "document_request_present": true/false,
    "overall_risk_level": "basso|medio|alto"
  }},
  "extracted_obligations": [
    {{
      "code": "CODICE_UNIVOCO",
      "category": "contrattuale|tecnico|documentale|sicurezza|logistico_temporale",
      "title": "Titolo breve",
      "description": "Descrizione dettagliata",
      "severity": "alta|media|bassa",
      "blocking_level": "hard_block|warning|none",
      "source_excerpt": "Testo originale citato dal documento",
      "confidence": 0.85,
      "suggested_module": "sicurezza|documentale|emissione|commessa|null"
    }}
  ],
  "anomalies": [
    {{
      "code": "CODICE_ANOMALIA",
      "title": "Titolo anomalia",
      "description": "Descrizione",
      "severity": "alta|media|bassa",
      "source_excerpt": "Testo citato",
      "recommended_action": "revisione_legale|revisione_amministrativa|revisione_tecnica|accettare",
      "confidence": 0.80
    }}
  ],
  "mismatches": [
    {{
      "code": "CODICE_MISMATCH",
      "title": "Titolo mismatch",
      "description": "Descrizione della discrepanza",
      "severity": "alta|media|bassa",
      "blocking_level": "warning|hard_block|none",
      "compared_against": ["preventivo", "istruttoria", "commessa"],
      "recommended_action": "valutare_variante|integrare_offerta|chiarire_cliente|accettare",
      "confidence": 0.82
    }}
  ],
  "open_questions": [
    {{
      "qid": "q1",
      "question": "Domanda da chiarire col cliente",
      "impact": "alto|medio|basso",
      "depends_on": "obligation|mismatch|anomaly"
    }}
  ]
}}"""


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])
    return json.loads(cleaned)


async def _gather_system_context(commessa_id: str, user_id: str, tenant_id: str = None) -> str:
    """Gather preventivo/istruttoria/commessa context for comparison."""
    parts = []

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    if commessa:
        parts.append(f"Commessa: {commessa.get('title', '')} - {commessa.get('description', '')}")
        parts.append(f"Cliente: {commessa.get('client_name', '')}")
        parts.append(f"Normativa: {commessa.get('normativa_tipo', '')}")
        parts.append(f"Classe EXC: {commessa.get('classe_exc', '')}")
        parts.append(f"Valore: {commessa.get('value', '')}")

        moduli = commessa.get("moduli", {})
        prev_id = moduli.get("preventivo_id") or commessa.get("linked_preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one(
                {"preventivo_id": prev_id, "user_id": user_id}, {"_id": 0}
            )
            if prev:
                parts.append(f"\nPreventivo: {prev.get('subject', '')}")
                parts.append(f"Totale: {prev.get('total', '')}")
                for line in prev.get("lines", [])[:15]:
                    desc = line.get("description", "")
                    if desc:
                        parts.append(f"  - {desc} (Qt: {line.get('quantity', '')} {line.get('unit', '')})")

            istr = await db.istruttorie.find_one(
                {"preventivo_id": prev_id, "user_id": user_id}, {"_id": 0}
            )
            if istr:
                parts.append(f"\nIstruttoria classificazione: {istr.get('classificazione', {}).get('normativa', '')}")
                seg = istr.get("official_segmentation", {})
                if seg:
                    for la in seg.get("line_assignments", []):
                        parts.append(f"  Segmento: {la.get('line_id', '')} → {la.get('normativa', '')}")

    # Cantiere sicurezza
    cantiere = await db.cantieri_sicurezza.find_one(
        {"$or": [{"commessa_id": commessa_id}, {"parent_commessa_id": commessa_id}],
         "user_id": user_id}, {"_id": 0}
    )
    if cantiere:
        dati = cantiere.get("dati_cantiere", {})
        if dati:
            parts.append(f"\nCantiere: {dati.get('indirizzo', '')} {dati.get('citta', '')}")
            parts.append(f"Tipo cantiere: {dati.get('contesto_operativo', '')}")
        soggetti = cantiere.get("soggetti", [])
        for s in soggetti:
            if s.get("nome"):
                parts.append(f"  Soggetto: {s.get('ruolo', '')} = {s.get('nome', '')}")

    return "\n".join(parts) if parts else "Nessun dato di sistema disponibile."


async def _gather_documents_text(package: dict, user_id: str, tenant_id: str = None) -> str:
    """Extract text content from documents in the package."""
    parts = []
    for ref in package.get("document_refs", []):
        file_id = ref.get("file_id", "")
        title = ref.get("title", ref.get("file_name", ""))
        category = ref.get("category", "")
        doc_id = ref.get("doc_id", "")

        parts.append(f"\n--- DOCUMENTO: {title} (categoria: {category}) ---")

        # Try to get text from stored document metadata
        doc = await db.documenti_archivio.find_one(
            {"doc_id": doc_id, "user_id": user_id}, {"_id": 0}
        )
        if doc and doc.get("extracted_text"):
            parts.append(doc["extracted_text"][:8000])
        elif file_id:
            # Try to read from object storage
            try:
                from services.object_storage import get_object
                file_bytes, content_type = get_object(file_id)
                if file_bytes and content_type and "text" in content_type:
                    parts.append(file_bytes.decode("utf-8", errors="replace")[:8000])
                elif file_bytes:
                    parts.append(f"[File binario: {ref.get('file_name', '')} - {len(file_bytes)} bytes - contenuto non estraibile come testo]")
            except Exception as e:
                parts.append(f"[Errore lettura file: {e}]")
        else:
            parts.append(f"[Documento senza file allegato: {title}]")

        # Add any notes/metadata
        if doc and doc.get("notes"):
            parts.append(f"Note: {doc['notes']}")

    return "\n".join(parts) if parts else "Nessun documento disponibile."


async def analizza_committenza(package_id: str, user_id: str, tenant_id: str = None) -> dict:
    """C1.2: Run AI analysis on a committenza package."""
    package = await get_package(package_id, user_id)
    if not package:
        return {"error": "Package non trovato"}

    if not package.get("document_refs"):
        return {"error": "Nessun documento nel package. Aggiungi documenti dall'archivio."}

    if not LlmChat or not UserMessage:
        return {"error": "Motore AI non disponibile (emergentintegrations non installato)"}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY non configurata"}

    commessa_id = package["commessa_id"]

    # Gather context
    documents_text = await _gather_documents_text(package, user_id)
    system_context = await _gather_system_context(commessa_id, user_id)

    user_prompt = COMMITTENZA_USER_TEMPLATE.format(
        documents_text=documents_text,
        system_context=system_context,
    )

    # Call LLM
    try:
        chat = LlmChat(api_key=api_key, model="gpt-4o")
        chat.add_message(UserMessage(message=COMMITTENZA_SYSTEM_PROMPT))
        response = chat.send_message(UserMessage(message=user_prompt))

        ai_result = _parse_json_response(response.message)
    except json.JSONDecodeError as e:
        logger.error(f"[COMMITTENZA AI] JSON parse error: {e}")
        return {"error": f"Errore parsing risposta AI: {e}"}
    except Exception as e:
        logger.error(f"[COMMITTENZA AI] LLM call error: {e}")
        return {"error": f"Errore chiamata AI: {e}"}

    # Build analysis record
    analysis_id = f"ac_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    # Add doc_id references to extracted items
    first_doc_id = package["document_refs"][0]["doc_id"] if package["document_refs"] else ""

    for obl in ai_result.get("extracted_obligations", []):
        obl["source_doc_id"] = obl.get("source_doc_id", first_doc_id)
        obl["status"] = "dedotto"
        obl["confirmed"] = False

    for anom in ai_result.get("anomalies", []):
        anom["source_doc_id"] = anom.get("source_doc_id", first_doc_id)
        anom["confirmed"] = False

    for mm in ai_result.get("mismatches", []):
        mm["confirmed"] = False

    for q in ai_result.get("open_questions", []):
        q["answer"] = None

    analysis = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "tenant_id": None,
        "commessa_id": commessa_id,
        "package_id": package_id,
        "status": "analysis_ready",
        "engine_version": "committenza_v1",
        "llm_model": "gpt-4o",
        "overall_confidence": _calc_overall_confidence(ai_result),
        "summary": ai_result.get("summary", {}),
        "extracted_obligations": ai_result.get("extracted_obligations", []),
        "anomalies": ai_result.get("anomalies", []),
        "mismatches": ai_result.get("mismatches", []),
        "open_questions": ai_result.get("open_questions", []),
        "human_review": {"review_status": "pending"},
        "official_snapshot": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.analisi_committenza.insert_one(analysis)
    analysis.pop("_id", None)

    # Update package status
    await db.pacchetti_committenza.update_one(
        {"package_id": package_id, "user_id": user_id},
        {"$set": {"status": "analyzed", "analysis_id": analysis_id, "updated_at": now}}
    )

    logger.info(f"[COMMITTENZA AI] Analysis complete: {analysis_id} for {commessa_id} "
                f"({len(analysis['extracted_obligations'])} obligations, "
                f"{len(analysis['anomalies'])} anomalies, "
                f"{len(analysis['mismatches'])} mismatches)")

    return analysis


def _calc_overall_confidence(ai_result: dict) -> float:
    """Calculate average confidence across all extracted items."""
    confs = []
    for obl in ai_result.get("extracted_obligations", []):
        if isinstance(obl.get("confidence"), (int, float)):
            confs.append(obl["confidence"])
    for anom in ai_result.get("anomalies", []):
        if isinstance(anom.get("confidence"), (int, float)):
            confs.append(anom["confidence"])
    for mm in ai_result.get("mismatches", []):
        if isinstance(mm.get("confidence"), (int, float)):
            confs.append(mm["confidence"])
    return round(sum(confs) / len(confs), 2) if confs else 0.0


# ═══════════════════════════════════════════════════════════════
#  C1.3 — REVIEW UMANA
# ═══════════════════════════════════════════════════════════════

async def get_analysis(analysis_id: str, user_id: str, tenant_id: str = None) -> Optional[dict]:
    return await db.analisi_committenza.find_one(
        {"analysis_id": analysis_id, "user_id": user_id}, {"_id": 0}
    )


async def list_analyses(user_id: str, commessa_id: str = None, tenant_id: str = None) -> list:
    query = {"user_id": user_id}
    if commessa_id:
        query["commessa_id"] = commessa_id
    return await db.analisi_committenza.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)


async def review_analysis(analysis_id: str, user_id: str, review_data: dict, tenant_id: str = None) -> dict:
    """Apply human review to an analysis.
    review_data: {
        obligations_review: [{code, confirmed, note}],
        anomalies_review: [{code, confirmed, note}],
        mismatches_review: [{code, confirmed, note}],
        questions_answers: [{qid, answer}],
    }
    """
    analysis = await get_analysis(analysis_id, user_id)
    if not analysis:
        return {"error": "Analisi non trovata"}

    now = datetime.now(timezone.utc).isoformat()

    # Apply obligation reviews
    obl_map = {r.get("code"): r for r in review_data.get("obligations_review", [])}
    for obl in analysis.get("extracted_obligations", []):
        rev = obl_map.get(obl.get("code"))
        if rev:
            obl["confirmed"] = rev.get("confirmed", False)
            obl["review_note"] = rev.get("note", "")
            obl["status"] = "confermato" if rev.get("confirmed") else "rifiutato"

    # Apply anomaly reviews
    anom_map = {r.get("code"): r for r in review_data.get("anomalies_review", [])}
    for anom in analysis.get("anomalies", []):
        rev = anom_map.get(anom.get("code"))
        if rev:
            anom["confirmed"] = rev.get("confirmed", False)
            anom["review_note"] = rev.get("note", "")

    # Apply mismatch reviews
    mm_map = {r.get("code"): r for r in review_data.get("mismatches_review", [])}
    for mm in analysis.get("mismatches", []):
        rev = mm_map.get(mm.get("code"))
        if rev:
            mm["confirmed"] = rev.get("confirmed", False)
            mm["review_note"] = rev.get("note", "")

    # Apply question answers
    qa_map = {r.get("qid"): r for r in review_data.get("questions_answers", [])}
    for q in analysis.get("open_questions", []):
        ans = qa_map.get(q.get("qid"))
        if ans:
            q["answer"] = ans.get("answer", "")

    analysis["human_review"] = {
        "review_status": "reviewed",
        "reviewed_by": user_id,
        "reviewed_at": now,
    }
    analysis["status"] = "in_review"
    analysis["updated_at"] = now

    await db.analisi_committenza.update_one(
        {"analysis_id": analysis_id, "user_id": user_id},
        {"$set": {
            "extracted_obligations": analysis["extracted_obligations"],
            "anomalies": analysis["anomalies"],
            "mismatches": analysis["mismatches"],
            "open_questions": analysis["open_questions"],
            "human_review": analysis["human_review"],
            "status": analysis["status"],
            "updated_at": now,
        }}
    )
    return await get_analysis(analysis_id, user_id)


async def approve_analysis(analysis_id: str, user_id: str, tenant_id: str = None) -> dict:
    """Approve analysis and generate official_snapshot from confirmed items."""
    analysis = await get_analysis(analysis_id, user_id)
    if not analysis:
        return {"error": "Analisi non trovata"}

    now = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "approved_by": user_id,
        "approved_at": now,
        "obligations": [o for o in analysis.get("extracted_obligations", []) if o.get("confirmed")],
        "anomalies": [a for a in analysis.get("anomalies", []) if a.get("confirmed")],
        "mismatches": [m for m in analysis.get("mismatches", []) if m.get("confirmed")],
        "questions": [q for q in analysis.get("open_questions", []) if q.get("answer")],
    }

    await db.analisi_committenza.update_one(
        {"analysis_id": analysis_id, "user_id": user_id},
        {"$set": {
            "official_snapshot": snapshot,
            "status": "approved",
            "human_review.review_status": "approved",
            "updated_at": now,
        }}
    )

    logger.info(f"[COMMITTENZA] Analysis approved: {analysis_id} "
                f"({len(snapshot['obligations'])} obligations, "
                f"{len(snapshot['anomalies'])} anomalies, "
                f"{len(snapshot['mismatches'])} mismatches)")

    return await get_analysis(analysis_id, user_id)


# ═══════════════════════════════════════════════════════════════
#  C1.4 — GENERAZIONE OBBLIGHI NEL REGISTRO
# ═══════════════════════════════════════════════════════════════

async def genera_obblighi_da_analisi(analysis_id: str, user_id: str, tenant_id: str = None) -> dict:
    """Generate obligations in Registro Obblighi from approved analysis snapshot."""
    analysis = await get_analysis(analysis_id, user_id)
    if not analysis:
        return {"error": "Analisi non trovata"}

    snapshot = analysis.get("official_snapshot")
    if not snapshot:
        return {"error": "Analisi non ancora approvata. Approva prima di generare obblighi."}

    commessa_id = analysis["commessa_id"]
    now = datetime.now(timezone.utc).isoformat()

    created = 0
    updated = 0

    # Map obligations
    for obl in snapshot.get("obligations", []):
        code = obl.get("code", "UNKNOWN")
        dedupe_key = f"{commessa_id}|committenza|{analysis_id}|{code}"

        existing = await db.obblighi_commessa.find_one(
            {"dedupe_key": dedupe_key, "user_id": user_id}, {"_id": 0}
        )

        severity = obl.get("severity", "media")
        blocking = obl.get("blocking_level", "warning")
        severity_sort = {"alta": 1, "media": 2, "bassa": 3}.get(severity, 9)
        blocking_sort = {"hard_block": 1, "warning": 2, "none": 3}.get(blocking, 9)
        status = "bloccante" if blocking == "hard_block" else "nuovo"

        category_map = {
            "contrattuale": "commessa",
            "tecnico": "qualita",
            "documentale": "documentale",
            "sicurezza": "sicurezza",
            "logistico_temporale": "commessa",
        }

        if existing:
            await db.obblighi_commessa.update_one(
                {"dedupe_key": dedupe_key, "user_id": user_id},
                {"$set": {
                    "title": obl.get("title", ""),
                    "description": obl.get("description", ""),
                    "severity": severity,
                    "severity_sort": severity_sort,
                    "blocking_level": blocking,
                    "blocking_level_sort": blocking_sort,
                    "updated_at": now,
                }}
            )
            updated += 1
        else:
            obbligo = {
                "obbligo_id": f"obl_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "tenant_id": None,
                "commessa_id": commessa_id,
                "cantiere_id": "",
                "ramo_id": "",
                "emissione_id": "",
                "source_module": "committenza",
                "source_entity_type": "analisi_committenza",
                "source_entity_id": analysis_id,
                "code": code,
                "title": obl.get("title", ""),
                "description": obl.get("description", ""),
                "category": category_map.get(obl.get("category", ""), "commessa"),
                "severity": severity,
                "severity_sort": severity_sort,
                "blocking_level": blocking,
                "blocking_level_sort": blocking_sort,
                "status": status,
                "auto_generated": True,
                "owner_role": _suggest_owner(obl.get("category", "")),
                "owner_user_id": None,
                "due_date": None,
                "linked_route": f"/commesse/{commessa_id}",
                "linked_label": "Apri commessa",
                "context": {
                    "phase": "committenza",
                    "source_excerpt": obl.get("source_excerpt", "")[:200],
                    "suggested_module": obl.get("suggested_module", ""),
                },
                "dedupe_key": dedupe_key,
                "created_at": now,
                "updated_at": now,
                "resolved_at": None,
                "resolved_by": None,
                "resolution_note": None,
            }
            await db.obblighi_commessa.insert_one(obbligo)
            created += 1

    # Map anomalies as warning obligations
    for anom in snapshot.get("anomalies", []):
        code = f"ANOM_{anom.get('code', 'UNKNOWN')}"
        dedupe_key = f"{commessa_id}|committenza|{analysis_id}|{code}"

        existing = await db.obblighi_commessa.find_one(
            {"dedupe_key": dedupe_key, "user_id": user_id}, {"_id": 0}
        )
        if not existing:
            obbligo = {
                "obbligo_id": f"obl_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "tenant_id": None,
                "commessa_id": commessa_id,
                "cantiere_id": "", "ramo_id": "", "emissione_id": "",
                "source_module": "committenza",
                "source_entity_type": "analisi_committenza",
                "source_entity_id": analysis_id,
                "code": code,
                "title": f"Anomalia: {anom.get('title', '')}",
                "description": anom.get("description", ""),
                "category": "commessa",
                "severity": anom.get("severity", "media"),
                "severity_sort": {"alta": 1, "media": 2, "bassa": 3}.get(anom.get("severity", "media"), 9),
                "blocking_level": "warning",
                "blocking_level_sort": 2,
                "status": "da_verificare",
                "auto_generated": True,
                "owner_role": anom.get("recommended_action", "revisione_amministrativa"),
                "owner_user_id": None,
                "due_date": None,
                "linked_route": f"/commesse/{commessa_id}",
                "linked_label": "Apri commessa",
                "context": {
                    "phase": "committenza",
                    "source_excerpt": anom.get("source_excerpt", "")[:200],
                    "recommended_action": anom.get("recommended_action", ""),
                },
                "dedupe_key": dedupe_key,
                "created_at": now, "updated_at": now,
                "resolved_at": None, "resolved_by": None, "resolution_note": None,
            }
            await db.obblighi_commessa.insert_one(obbligo)
            created += 1

    # Map mismatches as warning obligations
    for mm in snapshot.get("mismatches", []):
        code = f"MISMATCH_{mm.get('code', 'UNKNOWN')}"
        dedupe_key = f"{commessa_id}|committenza|{analysis_id}|{code}"

        existing = await db.obblighi_commessa.find_one(
            {"dedupe_key": dedupe_key, "user_id": user_id}, {"_id": 0}
        )
        if not existing:
            obbligo = {
                "obbligo_id": f"obl_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "tenant_id": None,
                "commessa_id": commessa_id,
                "cantiere_id": "", "ramo_id": "", "emissione_id": "",
                "source_module": "committenza",
                "source_entity_type": "analisi_committenza",
                "source_entity_id": analysis_id,
                "code": code,
                "title": f"Mismatch: {mm.get('title', '')}",
                "description": mm.get("description", ""),
                "category": "commessa",
                "severity": mm.get("severity", "media"),
                "severity_sort": {"alta": 1, "media": 2, "bassa": 3}.get(mm.get("severity", "media"), 9),
                "blocking_level": mm.get("blocking_level", "warning"),
                "blocking_level_sort": {"hard_block": 1, "warning": 2, "none": 3}.get(mm.get("blocking_level", "warning"), 9),
                "status": "da_verificare",
                "auto_generated": True,
                "owner_role": "ufficio_tecnico",
                "owner_user_id": None,
                "due_date": None,
                "linked_route": f"/commesse/{commessa_id}",
                "linked_label": "Apri commessa",
                "context": {
                    "phase": "committenza",
                    "compared_against": mm.get("compared_against", []),
                    "recommended_action": mm.get("recommended_action", ""),
                },
                "dedupe_key": dedupe_key,
                "created_at": now, "updated_at": now,
                "resolved_at": None, "resolved_by": None, "resolution_note": None,
            }
            await db.obblighi_commessa.insert_one(obbligo)
            created += 1

    logger.info(f"[COMMITTENZA] Obligations generated from {analysis_id}: created={created}, updated={updated}")
    return {"created": created, "updated": updated, "analysis_id": analysis_id}


def _suggest_owner(category: str) -> str:
    return {
        "contrattuale": "amministrazione",
        "tecnico": "ufficio_tecnico",
        "documentale": "ufficio_tecnico",
        "sicurezza": "sicurezza",
        "logistico_temporale": "produzione",
    }.get(category, "ufficio_tecnico")


# Need os for env var
import os
