"""
Validation Engine — P1 Real-World Validation
==============================================
Runs the AI compliance engine on selected preventivi and scores the results
against expected outcomes. Produces a structured scorecard.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─── Ground Truth for validation ───
# Each entry defines the expected outcome for a preventivo.
# normativa_attesa: the correct classification
# profilo_atteso: the expected technical profile (EXC class, categories, etc.)
# note: why this is the expected result
VALIDATION_SET = {
    "prev_04a9a9d21bfa": {
        "number": "PRV-2026-0028",
        "subject": "Via Cadriano 22-5 — Carpenteria in acciaio",
        "normativa_attesa": "EN_1090",
        "profilo_atteso": {"tipo": "exc", "valore_range": ["EXC1", "EXC2"]},
        "elementi_attesi": ["profilati IPE/HEA/HEB/UPN", "angolari", "piatti"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Carpenteria strutturale classica con profilati laminati a caldo"
    },
    "prev_35c6b96a9e75": {
        "number": "PRV-2026-0033",
        "subject": "Cerchiatura HEB 120 — Via Bergonzoni 2",
        "normativa_attesa": "EN_1090",
        "profilo_atteso": {"tipo": "exc", "valore_range": ["EXC1", "EXC2"]},
        "elementi_attesi": ["HEB 120", "S275JR", "piastre"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Cerchiatura strutturale con disegno ingegnere, acciaio S275JR"
    },
    "prev_62e2e4b9c088": {
        "number": "PRV-2026-0030",
        "subject": "Cancello Carraio nuova lottizzazione Meridiana",
        "normativa_attesa": "EN_13241",
        "profilo_atteso": {"tipo": "categorie_prestazione"},
        "elementi_attesi": ["cancello", "motorizzazione", "tubolari"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Cancello carraio motorizzato a due ante"
    },
    "prev_7c71048368": {
        "number": "PRV-2026-0037",
        "subject": "Cancello scorrevole — Celesti Figlia Bazzano",
        "normativa_attesa": "EN_13241",
        "profilo_atteso": {"tipo": "categorie_prestazione"},
        "elementi_attesi": ["cancello scorrevole", "tubolari 50x50", "motorizzazione"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Cancello scorrevole doppia anta con motorizzazione"
    },
    "prev_1d4a5ec4c687": {
        "number": "PRV-2026-0008",
        "subject": "Lastra in ferro — Casteldebole",
        "normativa_attesa": "GENERICA",
        "profilo_atteso": {"tipo": "complessita", "valore_range": ["bassa", "media"]},
        "elementi_attesi": ["lamiera nera", "spessore 40mm"],
        "saldatura_attesa": False,
        "montaggio_atteso": False,
        "note": "Semplice fornitura lamiera senza lavorazione strutturale ne installazione"
    },
    "prev_eb87b5c85253": {
        "number": "PRV-2026-0002",
        "subject": "Recinzione + cancelli",
        "normativa_attesa": "MISTA",
        "profilo_atteso": {"tipo": "exc,categorie_prestazione"},
        "elementi_attesi": ["recinzione", "cancello", "tubolari", "porta"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Recinzione + porta + cancellino pedonale — effettivamente MISTA (EN 13241 per cancelli, GENERICA per recinzione)"
    },
    "prev_73cdb12e4ef7": {
        "number": "PRV-2026-0035",
        "subject": "Sostituzione motorizzazione dopo sinistro",
        "normativa_attesa": "EN_13241",
        "profilo_atteso": {"tipo": "categorie_prestazione"},
        "elementi_attesi": ["motorizzazione", "cancello scorrevole"],
        "saldatura_attesa": False,
        "montaggio_atteso": True,
        "note": "Sostituzione motorizzazione cancelli — EN 13241 specifico"
    },
    "prev_8e8311d22a3c": {
        "number": "PRV-2026-0021",
        "subject": "Parapetti — Roma Srl",
        "normativa_attesa": "MISTA",
        "profilo_atteso": {"tipo": "exc,categorie_prestazione"},
        "elementi_attesi": ["parapetto", "ringhiera", "cancello", "motorizzazione", "recinzione"],
        "saldatura_attesa": True,
        "montaggio_atteso": True,
        "note": "Parapetti (EN 1090) + cancello carraio + motorizzazione (EN 13241) + recinzione — effettivamente MISTA"
    },
}


def score_classificazione(ai_result: dict, ground_truth: dict) -> dict:
    """Score the normativa classification."""
    ai_norm = ai_result.get("classificazione", {}).get("normativa_proposta", "")
    expected = ground_truth["normativa_attesa"]
    ai_conf = ai_result.get("classificazione", {}).get("confidenza", "")
    ai_motiv = ai_result.get("classificazione", {}).get("motivazione", "")

    if ai_norm == expected:
        match = True
        score = 1.0
    elif expected == "MISTA" and ai_norm in ("EN_1090", "EN_13241", "GENERICA"):
        # Partial credit: AI identified one component of the mix
        match = False
        score = 0.5
    elif ai_norm == "MISTA" and expected in ("EN_1090", "EN_13241", "GENERICA"):
        # AI over-segments: says MISTA when case is actually pure
        match = False
        score = 0.3
    else:
        match = False
        score = 0.0

    return {
        "metrica": "Classificazione normativa",
        "atteso": expected,
        "ottenuto": ai_norm,
        "corretto": match,
        "confidenza_ai": ai_conf,
        "motivazione_ai": ai_motiv[:200] if ai_motiv else "",
        "punteggio": score,
    }


def score_profilo(ai_result: dict, ground_truth: dict) -> dict:
    """Score the technical profile."""
    ai_prof = ai_result.get("profilo_tecnico", {})
    expected = ground_truth.get("profilo_atteso", {})

    tipo_match = ai_prof.get("tipo", "") == expected.get("tipo", "")
    valore_range = expected.get("valore_range", [])
    valore_match = ai_prof.get("valore", "") in valore_range if valore_range else True

    score = 0.0
    if tipo_match:
        score += 0.5
    if valore_match:
        score += 0.5

    return {
        "metrica": "Profilo tecnico",
        "atteso_tipo": expected.get("tipo", ""),
        "atteso_valore_range": valore_range,
        "ottenuto_tipo": ai_prof.get("tipo", ""),
        "ottenuto_valore": ai_prof.get("valore", ""),
        "tipo_corretto": tipo_match,
        "valore_corretto": valore_match,
        "punteggio": score,
    }


def score_estrazione(ai_result: dict, ground_truth: dict) -> dict:
    """Score the technical data extraction quality."""
    est = ai_result.get("estrazione_tecnica", {})
    elementi = est.get("elementi_strutturali", [])
    lavorazioni = est.get("lavorazioni_rilevate", [])

    n_elementi = len(elementi)
    n_lavorazioni = len(lavorazioni)
    n_confermati = sum(1 for e in elementi if e.get("stato") in ("confermato", "dedotto"))

    # Build searchable text from ALL AI extraction fields
    search_parts = []
    for e in elementi:
        search_parts.append((e.get("descrizione", "") or "").lower())
        search_parts.append((e.get("tipo", "") or "").lower())
        search_parts.append((e.get("materiale", "") or "").lower())
    for l in lavorazioni:
        search_parts.append((l.get("dettaglio", "") or "").lower())
        search_parts.append((l.get("tipo", "") or "").lower())
        search_parts.append((l.get("descrizione", "") or "").lower())
    # Also search in trattamenti, montaggio, saldature text
    tratt = est.get("trattamenti_superficiali", {})
    if isinstance(tratt, dict):
        search_parts.append((tratt.get("tipo", "") or "").lower())
        search_parts.append((tratt.get("dettaglio", "") or "").lower())
    mont = est.get("montaggio_posa", {})
    if isinstance(mont, dict):
        search_parts.append((mont.get("tipo", "") or "").lower())
        search_parts.append((mont.get("dettaglio", "") or "").lower())
    sald_data = est.get("saldature", {})
    if isinstance(sald_data, dict):
        search_parts.append((sald_data.get("tipo", "") or "").lower())
        search_parts.append((sald_data.get("dettaglio", "") or "").lower())

    all_descs = " ".join(search_parts)

    # Synonym map for flexible matching
    SYNONYMS = {
        "tubolar": ["tubolare", "tubolari", "tubolar", "tubo", "tubi"],
        "cancello": ["cancello", "cancelli", "cancellino", "cancelletto"],
        "motorizzazione": ["motorizzazione", "motorizzaz", "motore", "motoriduttore", "automazione"],
        "parapetto": ["parapetto", "parapetti", "balaustra", "balaustre"],
        "ringhiera": ["ringhiera", "ringhiere", "corrimano"],
        "lamiera": ["lamiera", "lastra", "lamiere", "lastre", "piastra"],
        "piastra": ["piastra", "piastre", "piatto", "piatti", "flangia"],
        "recinzione": ["recinzione", "recinzioni", "recinto"],
        "profilat": ["profilat", "profilo", "profili", "ipe", "hea", "heb", "upn"],
        "angolar": ["angolar", "angolare", "angolari", "cantonale"],
        "scorrevole": ["scorrevole", "scorrimento"],
        "spessore": ["spessore", "sp.", "sp ", "mm"],
    }

    # Check if expected elements are found (flexible)
    expected_elements = ground_truth.get("elementi_attesi", [])
    found = 0
    for exp in expected_elements:
        exp_lower = exp.lower()
        # Direct substring match
        if any(kw in all_descs for kw in exp_lower.split("/")):
            found += 1
            continue
        # Try each word in the expected element
        exp_words = exp_lower.replace("/", " ").split()
        word_found = False
        for word in exp_words:
            if word in all_descs:
                word_found = True
                break
            # Check synonyms
            for base, syns in SYNONYMS.items():
                if word.startswith(base) or word in syns:
                    if any(s in all_descs for s in syns):
                        word_found = True
                        break
            if word_found:
                break
        if word_found:
            found += 1

    coverage = found / len(expected_elements) if expected_elements else 1.0

    # Check welding detection (more flexible)
    sald = est.get("saldature", {})
    sald_expected = ground_truth.get("saldatura_attesa", None)
    sald_detected = sald.get("presenti", False)
    # Also check if welding mentioned anywhere in extraction text
    if not sald_detected and sald_expected:
        welding_keywords = ["saldatura", "saldature", "saldato", "saldata", "saldare", "mig", "mag", "tig", "wps"]
        if any(kw in all_descs for kw in welding_keywords):
            sald_detected = True
    sald_match = (sald_detected == sald_expected) if sald_expected is not None else True

    return {
        "metrica": "Estrazione tecnica",
        "n_elementi": n_elementi,
        "n_lavorazioni": n_lavorazioni,
        "n_confermati": n_confermati,
        "elementi_attesi": expected_elements,
        "copertura_elementi": round(coverage, 2),
        "saldatura_attesa": sald_expected,
        "saldatura_rilevata": sald_detected,
        "saldatura_corretta": sald_match,
        "punteggio": round((coverage * 0.6 + (0.4 if sald_match else 0.0)), 2),
    }


def score_domande(ai_result: dict, ground_truth: dict) -> dict:
    """Score the quality and relevance of generated questions."""
    domande = ai_result.get("domande_residue", [])
    n_domande = len(domande)

    # Questions should exist for ambiguous cases
    alto = sum(1 for q in domande if q.get("impatto") == "alto")
    medio = sum(1 for q in domande if q.get("impatto") == "medio")

    # Check if questions are relevant (not nonsensical)
    has_perche = sum(1 for q in domande if q.get("perche_serve"))

    return {
        "metrica": "Qualita domande",
        "n_domande": n_domande,
        "n_impatto_alto": alto,
        "n_impatto_medio": medio,
        "n_con_motivazione": has_perche,
        "punteggio": min(1.0, round(has_perche / max(n_domande, 1), 2)),
    }


def score_singolo_preventivo(ai_result: dict, ground_truth: dict) -> dict:
    """Full scorecard for a single preventivo."""
    s_class = score_classificazione(ai_result, ground_truth)
    s_prof = score_profilo(ai_result, ground_truth)
    s_estr = score_estrazione(ai_result, ground_truth)
    s_dom = score_domande(ai_result, ground_truth)

    punteggio_globale = round(
        s_class["punteggio"] * 0.35 +
        s_prof["punteggio"] * 0.20 +
        s_estr["punteggio"] * 0.30 +
        s_dom["punteggio"] * 0.15
    , 2)

    return {
        "preventivo_id": ground_truth.get("preventivo_id", ""),
        "number": ground_truth.get("number", ""),
        "subject": ground_truth.get("subject", ""),
        "note_ground_truth": ground_truth.get("note", ""),
        "classificazione": s_class,
        "profilo": s_prof,
        "estrazione": s_estr,
        "domande": s_dom,
        "punteggio_globale": punteggio_globale,
        "valutato_il": datetime.now(timezone.utc).isoformat(),
    }


def score_batch(results: list) -> dict:
    """Aggregate scores across all validated preventivi."""
    if not results:
        return {"errore": "Nessun risultato"}

    n = len(results)
    avg_globale = round(sum(r["punteggio_globale"] for r in results) / n, 2)
    avg_class = round(sum(r["classificazione"]["punteggio"] for r in results) / n, 2)
    avg_prof = round(sum(r["profilo"]["punteggio"] for r in results) / n, 2)
    avg_estr = round(sum(r["estrazione"]["punteggio"] for r in results) / n, 2)
    avg_dom = round(sum(r["domande"]["punteggio"] for r in results) / n, 2)

    class_correct = sum(1 for r in results if r["classificazione"]["corretto"])
    class_partial = sum(1 for r in results if not r["classificazione"]["corretto"] and r["classificazione"]["punteggio"] > 0)

    return {
        "n_preventivi": n,
        "punteggio_medio_globale": avg_globale,
        "classificazione_corretta": f"{class_correct}/{n}",
        "classificazione_parziale": f"{class_partial}/{n}",
        "media_classificazione": avg_class,
        "media_profilo": avg_prof,
        "media_estrazione": avg_estr,
        "media_domande": avg_dom,
        "soglie": {
            "classificazione": ">=0.80 per produzione",
            "profilo": ">=0.70 per produzione",
            "estrazione": ">=0.60 per produzione",
            "domande": ">=0.50 per produzione",
            "globale": ">=0.70 per produzione",
        }
    }
