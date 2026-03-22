"""
Segmentazione Engine — P1.1
=============================
Analizza le righe di un preventivo e propone una segmentazione normativa per riga.
Due livelli: regole deterministiche (keyword) + AI (GPT-4o) per i casi incerti.
"""

import os
import uuid
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from emergentintegrations.llm import LlmChat, UserMessage
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# ─── Keyword rules for deterministic per-line classification ───

KEYWORDS_EN_13241 = [
    "cancello", "cancellino", "portone", "chiusura", "scorrevole",
    "battente", "automazione", "motorizzazione", "motore", "motoriduttore",
    "fotocellul", "bordo sensibile", "lampeggiante", "selettore",
    "elettroserratura", "elettro serratura", "serratura elettrica",
    "cancello carraio", "cancello pedonale", "cancellino pedonale",
    "porta sezionale", "porta in ferro", "porta industriale",
    "basculante", "avvolgibile", "saracinesca",
    "serratura", "cardini",
]

KEYWORDS_EN_1090 = [
    "struttura", "trave", "pilastro", "piastra", "profil",
    "carpenteria strutturale", "cerchiatura", "HEB", "HEA", "IPE", "UPN",
    "S235", "S275", "S355", "acciaio strutturale",
    "portante", "telaio strutturale", "solaio",
    "controvento", "ancoraggio", "fondazione",
]

KEYWORDS_GENERICA = [
    "parapetto", "ringhiera",
    "manutenzione", "riparazione", "smontaggio", "smaltimento",
    "verniciatura", "zincatura", "sovrapprezzo", "supplemento",
    "logo", "targhetta", "accessori", "lavorazioni generiche",
]

# Patterns that increase EN_1090 confidence when combined
STRUCTURAL_BOOST = ["saldatura", "S275JR", "S355JR", "lamiera", "angolare", "piatto"]


def _keyword_classify_line(description: str) -> dict:
    """Classify a single line using keyword rules. Returns proposed normativa + confidence."""
    desc_lower = (description or "").lower()

    if len(desc_lower.strip()) < 10:
        return {"normativa": "INCERTA", "confidence": 0.2, "method": "keyword", "reason": "Descrizione troppo breve"}

    score_13241 = sum(1 for kw in KEYWORDS_EN_13241 if kw.lower() in desc_lower)
    score_1090 = sum(1 for kw in KEYWORDS_EN_1090 if kw.lower() in desc_lower)
    score_gen = sum(1 for kw in KEYWORDS_GENERICA if kw.lower() in desc_lower)
    boost = sum(1 for kw in STRUCTURAL_BOOST if kw.lower() in desc_lower)

    score_1090 += boost * 0.5

    total = score_13241 + score_1090 + score_gen
    if total == 0:
        return {"normativa": "INCERTA", "confidence": 0.3, "method": "keyword", "reason": "Nessuna keyword normativa riconosciuta"}

    scores = {"EN_13241": score_13241, "EN_1090": score_1090, "GENERICA": score_gen}
    best = max(scores, key=scores.get)
    best_score = scores[best]
    second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0

    # If too close, mark as uncertain
    if best_score > 0 and (best_score - second_score) < 0.5:
        return {
            "normativa": "INCERTA",
            "confidence": 0.4,
            "method": "keyword",
            "reason": f"Segnali misti: {best}={best_score:.1f} vs altro={second_score:.1f}",
            "alternative": best,
        }

    confidence = min(0.85, 0.5 + (best_score / max(total, 1)) * 0.4)
    return {"normativa": best, "confidence": round(confidence, 2), "method": "keyword", "reason": f"Keyword match: {best_score:.1f}/{total:.1f}"}


SEGMENTATION_PROMPT = """Sei un tecnico di carpenteria metallica esperto in normativa CE.

Ti viene passata una lista di righe di un preventivo. Per OGNI riga, devi classificare la normativa applicabile.

## Normative possibili
- **EN_1090**: Strutture in acciaio portanti (carpenteria strutturale, travi, pilastri, piastre, telai, cerchiature, controventi)
- **EN_13241**: Chiusure industriali e cancelli (cancelli, portoni, porte sezionali, motorizzazioni, automazioni)
- **GENERICA**: Lavorazioni senza obbligo CE specifico (parapetti, ringhiere semplici, recinzioni non strutturali, accessori, manutenzione, servizi)
- **INCERTA**: Quando la descrizione e troppo ambigua per decidere

## Regole
- I parapetti e ringhiere semplici sono GENERICA, non EN 1090 (salvo esplicita indicazione strutturale)
- Le recinzioni semplici sono GENERICA
- "Sovrapprezzo", "supplemento", "logo" sono GENERICA
- "Smontaggio", "smaltimento" sono GENERICA (servizio)
- Se una riga menziona cancello/portone/automazione, e EN_13241
- Se una riga menziona struttura/telaio/cerchiatura con acciaio S275/S355, e EN_1090

## Output JSON
Rispondi SOLO con un JSON valido, nessun testo prima o dopo:
```json
{
  "line_classifications": [
    {
      "line_index": 0,
      "proposed_normativa": "EN_1090|EN_13241|GENERICA|INCERTA",
      "confidence": 0.0-1.0,
      "reasoning": "1 frase: perche questa classificazione",
      "keywords_found": ["keyword1", "keyword2"]
    }
  ]
}
```"""


async def _ai_classify_lines(lines: list) -> list:
    """Use GPT-4o to classify lines when keyword rules are uncertain."""
    if not AI_AVAILABLE:
        return []

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return []

    lines_text = "\n".join([
        f"[{i}] {(ln.get('description', '') or '')[:300]}"
        for i, ln in enumerate(lines) if isinstance(ln, dict)
    ])

    chat = LlmChat(
        api_key=api_key,
        session_id=f"seg-{uuid.uuid4().hex[:8]}",
        system_message=SEGMENTATION_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text=f"Classifica queste righe del preventivo:\n\n{lines_text}"
    )

    try:
        response_text = await chat.send_message(user_msg)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        result = json.loads(cleaned)
        return result.get("line_classifications", [])
    except Exception as e:
        logger.error(f"[SEGMENTATION] AI classification failed: {e}")
        return []


async def segmenta_preventivo(preventivo: dict) -> dict:
    """Main segmentation function. Analyzes each line and proposes normativa."""
    lines = preventivo.get("lines", [])
    if not lines:
        return {"enabled": False, "reason": "Nessuna riga nel preventivo"}

    # Phase 1: Keyword-based classification for all lines
    line_classifications = []
    uncertain_indices = []

    for i, ln in enumerate(lines):
        if not isinstance(ln, dict):
            continue
        desc = ln.get("description", "") or ""
        line_id = ln.get("line_id", f"r{i}")

        kw_result = _keyword_classify_line(desc)
        entry = {
            "line_id": line_id,
            "line_index": i,
            "descrizione": desc[:200],
            "proposed_normativa": kw_result["normativa"],
            "confidence": kw_result["confidence"],
            "status": "dedotto",
            "reasoning": kw_result["reason"],
            "keywords": [],
            "review": {
                "final_normativa": None,
                "decision": None,
                "reviewed_by": None,
            }
        }
        line_classifications.append(entry)

        if kw_result["normativa"] == "INCERTA" or kw_result["confidence"] < 0.5:
            uncertain_indices.append(i)

    # Phase 2: AI classification for uncertain lines (or all if many uncertain)
    if uncertain_indices or len(lines) <= 15:
        logger.info(f"[SEGMENTATION] Running AI classification on {len(lines)} lines")
        ai_results = await _ai_classify_lines(lines)

        for ai_item in ai_results:
            idx = ai_item.get("line_index", -1)
            if 0 <= idx < len(line_classifications):
                existing = line_classifications[idx]
                ai_norm = ai_item.get("proposed_normativa", "INCERTA")
                ai_conf = ai_item.get("confidence", 0.5)

                # AI overrides keyword only if higher confidence or keyword was uncertain
                if existing["proposed_normativa"] == "INCERTA" or ai_conf > existing["confidence"]:
                    existing["proposed_normativa"] = ai_norm
                    existing["confidence"] = round(ai_conf, 2)
                    existing["reasoning"] = ai_item.get("reasoning", existing["reasoning"])
                    existing["keywords"] = ai_item.get("keywords_found", [])

    # Phase 3: Aggregate into segments
    segments = {}
    for lc in line_classifications:
        norm = lc["proposed_normativa"]
        if norm not in segments:
            segments[norm] = {
                "segment_id": f"seg_{uuid.uuid4().hex[:6]}",
                "normativa": norm,
                "line_ids": [],
                "line_count": 0,
                "avg_confidence": 0,
                "total_confidence": 0,
            }
        segments[norm]["line_ids"].append(lc["line_id"])
        segments[norm]["line_count"] += 1
        segments[norm]["total_confidence"] += lc["confidence"]

    segment_list = []
    for seg in segments.values():
        seg["avg_confidence"] = round(seg["total_confidence"] / max(seg["line_count"], 1), 2)
        del seg["total_confidence"]

        labels = {
            "EN_1090": "Blocco EN 1090 — Carpenteria strutturale",
            "EN_13241": "Blocco EN 13241 — Cancelli e chiusure",
            "GENERICA": "Blocco Generico — Lavorazioni senza obbligo CE",
            "INCERTA": "Righe da classificare",
        }
        seg["label"] = labels.get(seg["normativa"], f"Blocco {seg['normativa']}")
        segment_list.append(seg)

    # Summary
    summary = {
        "righe_totali": len(line_classifications),
        "en_1090": sum(1 for lc in line_classifications if lc["proposed_normativa"] == "EN_1090"),
        "en_13241": sum(1 for lc in line_classifications if lc["proposed_normativa"] == "EN_13241"),
        "generiche": sum(1 for lc in line_classifications if lc["proposed_normativa"] == "GENERICA"),
        "incerte": sum(1 for lc in line_classifications if lc["proposed_normativa"] == "INCERTA"),
    }

    # Determine trigger reason
    norms_found = set(lc["proposed_normativa"] for lc in line_classifications if lc["proposed_normativa"] != "INCERTA")
    trigger_reason = "classificazione_mista" if len(norms_found) > 1 else "richiesta_utente"

    return {
        "enabled": True,
        "trigger_reason": trigger_reason,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "proposed",
        "summary": summary,
        "segments": segment_list,
        "line_classification": line_classifications,
    }
