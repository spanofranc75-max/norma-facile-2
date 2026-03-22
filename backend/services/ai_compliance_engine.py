"""
Motore di Istruttoria Automatica da Preventivo — Fase 1
========================================================

Livello 1A: Estrazione Tecnica Strutturata (GPT)
  - Legge il preventivo
  - Estrae: elementi, materiali, profili, spessori, lavorazioni, giunti, trattamenti, montaggio
  - Ogni dato ha: valore, stato (dedotto/confermato/mancante/incerto), fonte, confidenza

Livello 1B: Classificazione Normativa + Proposta Istruttoria (Rules Engine)
  - Classifica: EN 1090 / EN 13241 / Generica / Mista
  - Propone EXC, controlli, documenti richiesti
  - Genera 3-7 domande residue ad alto impatto
"""

import os
import json
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("emergentintegrations not available — AI compliance engine disabled")


# ═══════════════════════════════════════════════════════════════════
#  LIVELLO 1A — Prompt per estrazione tecnica strutturata
# ═══════════════════════════════════════════════════════════════════

EXTRACTION_SYSTEM_PROMPT = """Sei un tecnico esperto di carpenteria metallica e un responsabile qualita con 20 anni di esperienza in officine certificate EN 1090.

Il tuo compito e leggere un preventivo / descrizione lavori e ESTRARRE in modo strutturato tutti i dati tecnici rilevanti.

REGOLE FONDAMENTALI:
1. Distingui SEMPRE tra:
   - "dedotto": hai interpretato dal testo (es. "struttura in acciaio" -> materiale S275JR dedotto)
   - "confermato": il testo lo dice esplicitamente (es. "S275JR" scritto nel preventivo)
   - "mancante": il dato serve ma non c'e nel testo
   - "incerto": il testo e ambiguo, potresti interpretarlo in piu modi

2. Per ogni deduzione importante, indica DOVE nel testo hai trovato l'indizio (citazione breve).

3. NON inventare dati. Se non c'e, scrivi "mancante".

4. Ragiona come un fabbro esperto: cosa vedi, cosa capisci, cosa ti manca.

5. SALDATURA: se il preventivo descrive manufatti in acciaio assemblati (cancelli, ringhiere, recinzioni, parapetti, strutture), la saldatura e QUASI SEMPRE necessaria anche se non menzionata esplicitamente. In quel caso segna presenti=true con stato="dedotto".

6. MATERIALI E PROFILI: riporta TUTTI i profili/sezioni citati nelle righe (tubolari, IPE, HEB, piatti, lamiere) includendo dimensioni. Non omettere nulla.

Rispondi SOLO con JSON valido, senza commenti. Schema:
{
  "elementi_strutturali": [
    {
      "descrizione": "string",
      "profilo": "string o null",
      "materiale_base": "string o null",
      "spessore_mm": "number o null",
      "lunghezza_stimata_m": "number o null",
      "peso_stimato_kg": "number o null",
      "quantita": "number",
      "stato": "dedotto|confermato|mancante|incerto",
      "fonte_nel_testo": "string (citazione breve)"
    }
  ],
  "lavorazioni_rilevate": [
    {
      "tipo": "taglio|foratura|saldatura|piegatura|calandratura|assemblaggio|verniciatura|zincatura|trattamento_termico|altro",
      "dettaglio": "string",
      "stato": "dedotto|confermato|incerto",
      "fonte_nel_testo": "string"
    }
  ],
  "saldature": {
    "presenti": true/false,
    "stato": "dedotto|confermato|incerto|mancante",
    "processi_ipotizzati": ["135_MAG", "141_TIG", "111_MMA"],
    "giunti_attesi": [
      {
        "descrizione": "string",
        "tipo_giunto": "testa_a_testa|angolo|a_T|sovrapposto|altro",
        "spessore_mm": "number o null",
        "stato": "dedotto|confermato|incerto"
      }
    ],
    "fonte_nel_testo": "string"
  },
  "trattamenti_superficiali": {
    "tipo": "zincatura_caldo|verniciatura|sabbiatura|nessuno|incerto",
    "dettaglio": "string",
    "esecuzione": "interna|esterna_subfornitore|incerto|mancante",
    "stato": "dedotto|confermato|incerto|mancante",
    "fonte_nel_testo": "string"
  },
  "montaggio_posa": {
    "previsto": true/false,
    "tipo": "cantiere|stabilimento|misto|incerto",
    "dettaglio": "string",
    "stato": "dedotto|confermato|mancante",
    "fonte_nel_testo": "string"
  },
  "destinazione_uso": {
    "descrizione": "string",
    "ambiente": "interno|esterno|aggressivo|incerto",
    "stato": "dedotto|confermato|incerto|mancante",
    "fonte_nel_testo": "string"
  },
  "ambiguita_rilevate": [
    {
      "punto": "string",
      "possibili_interpretazioni": ["string"],
      "impatto": "alto|medio|basso"
    }
  ],
  "parole_chiave_rischio": ["string"],
  "note_tecnico": "string (commento libero del tecnico)"
}"""


CLASSIFICATION_SYSTEM_PROMPT = """Sei un normatore esperto di prodotti da costruzione e chiusure industriali.

Dati i seguenti dati tecnici estratti da un preventivo, devi:

1. CLASSIFICARE la commessa:
   - "EN_1090": carpenteria metallica strutturale (Reg. UE 305/2011)
   - "EN_13241": porte, cancelli, chiusure industriali
   - "GENERICA": lavorazione metallica senza marcatura CE
   - "MISTA": parti strutturali + parti non strutturali

2. PROPORRE il PROFILO TECNICO specifico per la normativa:
   - Se EN_1090: proponi la Classe di Esecuzione (EXC1, EXC2, EXC3, EXC4) con motivazione
   - Se EN_13241: proponi le categorie di prestazione pertinenti (resistenza vento, permeabilita aria, tenuta acqua, sicurezza uso) — NON usare EXC che e esclusivo di EN 1090
   - Se GENERICA: indica il livello di complessita (bassa/media/alta)
   - Se MISTA: separa le parti EN 1090 (con EXC) dalle parti EN 13241 (con categorie)

3. ELENCARE i documenti e controlli richiesti

4. GENERARE 3-7 domande residue PER L'OFFICINA (linguaggio pratico, non da consulente)

REGOLE:
- Ogni conclusione DEVE avere una motivazione chiara
- NON dichiarare conformita. Proponi istruttoria.
- NON assegnare EXC a prodotti EN 13241 o GENERICA — EXC e SOLO per EN 1090
- Le domande devono essere specifiche e ad alto impatto operativo
- Se i dati sono insufficienti per classificare, dillo chiaramente

Rispondi SOLO con JSON valido:
{
  "classificazione": {
    "normativa_proposta": "EN_1090|EN_13241|GENERICA|MISTA",
    "confidenza": "alta|media|bassa",
    "motivazione": "string (2-3 frasi che spiegano PERCHE questa classificazione)"
  },
  "profilo_tecnico": {
    "tipo": "exc|categorie_prestazione|complessita",
    "valore": "string (es: EXC2, oppure 'Classe 2 resistenza vento, Classe 3 permeabilita aria', oppure 'media')",
    "applicabile_a": "EN_1090|EN_13241|GENERICA|MISTA",
    "motivazione": "string"
  },
  "fasi_produttive_attese": [
    {
      "fase": "string",
      "ordine": "number",
      "obbligatoria": true/false,
      "controlli_associati": ["string"]
    }
  ],
  "documenti_richiesti": [
    {
      "documento": "string",
      "obbligatorio": true/false,
      "motivazione": "string breve",
      "stato_attuale": "mancante"
    }
  ],
  "controlli_richiesti": [
    {
      "tipo": "VT|dimensionale|CND_UT|CND_MT|CND_PT|prova_carico|collaudo_funzionale|altro",
      "descrizione": "string",
      "fase": "string (in quale fase produttiva)",
      "motivazione": "string"
    }
  ],
  "prerequisiti_saldatura": {
    "richiesti": true/false,
    "wps_necessarie": true/false,
    "wpqr_necessarie": true/false,
    "qualifica_saldatori": true/false,
    "motivazione": "string"
  },
  "prerequisiti_tracciabilita": {
    "certificati_31_richiesti": true/false,
    "tracciabilita_colata": true/false,
    "ddt_obbligatori": true/false,
    "motivazione": "string"
  },
  "domande_residue": [
    {
      "domanda": "string (linguaggio da officina, chiaro e diretto)",
      "impatto": "alto|medio|basso",
      "perche_serve": "string (1 frase: cosa sblocca questa risposta)"
    }
  ]
}"""


# ═══════════════════════════════════════════════════════════════════
#  LIVELLO 1A — Estrazione Tecnica dal Preventivo
# ═══════════════════════════════════════════════════════════════════

def _build_preventivo_text(preventivo: dict) -> str:
    """Converte un preventivo in testo leggibile per l'AI."""
    parts = []
    parts.append(f"PREVENTIVO: {preventivo.get('number', 'N/D')}")
    parts.append(f"OGGETTO: {preventivo.get('subject', 'N/D')}")
    parts.append(f"CLIENTE: {preventivo.get('client_name', 'N/D')}")

    if preventivo.get("notes"):
        parts.append(f"NOTE: {preventivo['notes']}")

    if preventivo.get("normativa"):
        parts.append(f"NORMATIVA INDICATA: {preventivo['normativa']}")

    if preventivo.get("classe_esecuzione"):
        parts.append(f"CLASSE ESECUZIONE INDICATA: {preventivo['classe_esecuzione']}")

    lines = preventivo.get("lines", [])
    if lines:
        parts.append("\nRIGHE DEL PREVENTIVO:")
        for i, ln in enumerate(lines, 1):
            desc = ln.get("description", "")
            qty = ln.get("quantity", 1)
            unit = ln.get("unit", "")
            price = ln.get("unit_price", 0)
            total = ln.get("line_total", 0)
            parts.append(f"  {i}. {desc} | Qt: {qty} {unit} | Prezzo unit: {price} EUR | Tot: {total} EUR")

    # Add any perizia source info
    ps = preventivo.get("perizia_source", {})
    if ps:
        parts.append(f"\nORIGINE: Perizia {ps.get('perizia_number', '')}")
        parts.append(f"TIPO DANNO: {ps.get('tipo_danno', '')}")

    return "\n".join(parts)


def _clean_json_response(text: str) -> dict:
    """Pulisce la risposta GPT ed estrae il JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


async def extract_technical_data(preventivo: dict) -> dict:
    """Livello 1A: Estrazione tecnica strutturata dal preventivo via GPT."""
    if not AI_AVAILABLE:
        return {"error": "AI non disponibile", "elementi_strutturali": []}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY mancante", "elementi_strutturali": []}

    preventivo_text = _build_preventivo_text(preventivo)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"istr-1a-{uuid.uuid4().hex[:8]}",
        system_message=EXTRACTION_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text=f"Analizza questo preventivo ed estrai tutti i dati tecnici strutturati:\n\n{preventivo_text}"
    )

    try:
        response_text = await chat.send_message(user_msg)
        result = _clean_json_response(response_text)
        result["_meta"] = {"livello": "1A", "modello": "gpt-4o", "stato": "completato"}
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[1A] JSON parse error: {e}")
        return {"error": f"Errore parsing risposta AI: {e}", "elementi_strutturali": [], "raw_response": response_text[:500]}
    except Exception as e:
        logger.error(f"[1A] AI extraction failed: {e}")
        return {"error": f"Errore AI: {e}", "elementi_strutturali": []}


# ═══════════════════════════════════════════════════════════════════
#  LIVELLO 1B — Classificazione Normativa + Proposta Istruttoria
# ═══════════════════════════════════════════════════════════════════

async def classify_and_propose(extracted_data: dict, preventivo: dict) -> dict:
    """Livello 1B: Classificazione normativa e proposta istruttoria.
    Usa i dati estratti dal Livello 1A + il preventivo originale."""
    if not AI_AVAILABLE:
        return {"error": "AI non disponibile"}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY mancante"}

    # Build context for classification
    context_parts = [
        "DATI TECNICI ESTRATTI DAL PREVENTIVO (Livello 1A):",
        json.dumps(extracted_data, indent=2, ensure_ascii=False),
        "",
        "INFORMAZIONI AGGIUNTIVE DAL PREVENTIVO:",
        f"- Normativa indicata dal commerciale: {preventivo.get('normativa', 'non specificata')}",
        f"- Classe esecuzione indicata: {preventivo.get('classe_esecuzione', 'non specificata')}",
        f"- Valore commessa: {preventivo.get('totals', {}).get('total', 0)} EUR",
        f"- Oggetto: {preventivo.get('subject', 'N/D')}",
    ]
    context = "\n".join(context_parts)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"istr-1b-{uuid.uuid4().hex[:8]}",
        system_message=CLASSIFICATION_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text=f"Classifica questa commessa e proponi l'istruttoria completa:\n\n{context}"
    )

    try:
        response_text = await chat.send_message(user_msg)
        result = _clean_json_response(response_text)
        result["_meta"] = {"livello": "1B", "modello": "gpt-4o", "stato": "completato"}
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[1B] JSON parse error: {e}")
        return {"error": f"Errore parsing classificazione: {e}", "raw_response": response_text[:500]}
    except Exception as e:
        logger.error(f"[1B] AI classification failed: {e}")
        return {"error": f"Errore AI classificazione: {e}"}


# ═══════════════════════════════════════════════════════════════════
#  REGOLE DETERMINISTICHE — Validazione e arricchimento
# ═══════════════════════════════════════════════════════════════════

# Matrice documenti obbligatori per normativa + EXC
DOCUMENT_MATRIX = {
    "EN_1090": {
        "EXC1": [
            "Certificato FPC (del fabbricante)",
            "Certificati materiale EN 10204 3.1",
            "Disegno esecutivo / di officina",
            "DDT materiali in ingresso",
        ],
        "EXC2": [
            "Certificato FPC (del fabbricante)",
            "Certificati materiale EN 10204 3.1",
            "WPS (Specifiche di procedura di saldatura)",
            "WPQR (Qualifica del procedimento di saldatura)",
            "Qualifiche saldatori EN ISO 9606-1",
            "Disegno esecutivo / di officina",
            "Piano di controllo qualita (PCQ)",
            "Rapporti VT (Controllo visivo)",
            "Rapporto controllo dimensionale",
            "DDT materiali in ingresso",
            "Registro saldature",
            "Dichiarazione di Prestazione (DoP)",
            "Etichetta CE",
        ],
        "EXC3": [
            "Certificato FPC (del fabbricante)",
            "Certificati materiale EN 10204 3.1",
            "WPS (Specifiche di procedura di saldatura)",
            "WPQR (Qualifica del procedimento di saldatura)",
            "Qualifiche saldatori EN ISO 9606-1",
            "Disegno esecutivo / di officina",
            "Piano di controllo qualita (PCQ)",
            "Rapporti VT (Controllo visivo)",
            "Rapporti CND (UT/MT/PT)",
            "Rapporto controllo dimensionale",
            "DDT materiali in ingresso",
            "Registro saldature",
            "Dichiarazione di Prestazione (DoP)",
            "Etichetta CE",
        ],
    },
    "EN_13241": {
        "default": [
            "Disegno tecnico",
            "Scheda prodotto",
            "Dichiarazione di Prestazione (DoP)",
            "Etichetta CE",
            "Manuale uso e manutenzione",
        ],
    },
    "GENERICA": {
        "default": [
            "Disegno / schema",
            "DDT materiali",
        ],
    },
}

# Controlli obbligatori per EXC
CONTROL_MATRIX = {
    "EXC1": ["VT", "dimensionale"],
    "EXC2": ["VT", "dimensionale"],
    "EXC3": ["VT", "dimensionale", "CND_UT", "CND_MT"],
    "EXC4": ["VT", "dimensionale", "CND_UT", "CND_MT", "CND_PT", "prova_carico"],
}


def apply_deterministic_rules(classification: dict, extraction: dict) -> dict:
    """Applica regole deterministiche per validare/arricchire la proposta AI.
    Questo livello NON usa LLM — e puro codice."""

    normativa = classification.get("classificazione", {}).get("normativa_proposta", "GENERICA")
    profilo = classification.get("profilo_tecnico", {})
    profilo_valore = profilo.get("valore", "")
    saldature = extraction.get("saldature", {})
    trattamenti = extraction.get("trattamenti_superficiali", {})

    warnings = []
    enrichments = []

    # Rule 0: EXC non deve apparire per EN 13241/GENERICA
    if normativa in ("EN_13241", "GENERICA"):
        if profilo.get("tipo") == "exc":
            warnings.append({
                "tipo": "semantica_normativa",
                "messaggio": f"Correzione: EXC non e applicabile a {normativa}. EXC e esclusiva di EN 1090-2. Riclassificato come profilo prestazionale.",
                "correzione_applicata": True,
            })
            classification["profilo_tecnico"]["tipo"] = "categorie_prestazione" if normativa == "EN_13241" else "complessita"

    # Rule 1: Se c'e saldatura strutturale EN 1090, servono WPS/WPQR/qualifica
    if saldature.get("presenti") and normativa in ("EN_1090", "MISTA"):
        prereq = classification.get("prerequisiti_saldatura", {})
        if not prereq.get("wps_necessarie"):
            warnings.append({
                "tipo": "incoerenza",
                "messaggio": "Saldature rilevate ma WPS non marcate come necessarie. Correzione: WPS obbligatorie per EN 1090 con saldatura.",
                "correzione_applicata": True,
            })
            classification.setdefault("prerequisiti_saldatura", {})["wps_necessarie"] = True
            classification["prerequisiti_saldatura"]["wpqr_necessarie"] = True
            classification["prerequisiti_saldatura"]["qualifica_saldatori"] = True

    # Rule 2: Se c'e zincatura esterna, serve gestione subfornitore
    if trattamenti.get("tipo") == "zincatura_caldo" and trattamenti.get("esecuzione") == "esterna_subfornitore":
        enrichments.append({
            "tipo": "subfornitore",
            "messaggio": "Zincatura a caldo esterna: richiedere DDT + certificato trattamento dal subfornitore.",
        })
        # Add document if not present
        docs = classification.get("documenti_richiesti", [])
        doc_names = [d["documento"] for d in docs]
        if "Certificato zincatura (subfornitore)" not in doc_names:
            docs.append({
                "documento": "Certificato zincatura (subfornitore)",
                "obbligatorio": True,
                "motivazione": "Trattamento superficiale affidato a terzi — richiede documentazione di conformita.",
                "stato_attuale": "mancante",
            })
            docs.append({
                "documento": "DDT invio/rientro zincatura",
                "obbligatorio": True,
                "motivazione": "Tracciabilita del trattamento esterno.",
                "stato_attuale": "mancante",
            })

    # Rule 3: Se EXC >= 3 (solo EN 1090), servono CND
    if normativa in ("EN_1090", "MISTA") and profilo.get("tipo") == "exc" and profilo_valore in ("EXC3", "EXC4"):
        controls = classification.get("controlli_richiesti", [])
        ctrl_types = [c["tipo"] for c in controls]
        for cnd in ["CND_UT", "CND_MT"]:
            if cnd not in ctrl_types:
                warnings.append({
                    "tipo": "controllo_mancante",
                    "messaggio": f"{cnd} obbligatorio per {profilo_valore} ma non proposto dall'AI. Aggiunto.",
                    "correzione_applicata": True,
                })
                controls.append({
                    "tipo": cnd,
                    "descrizione": f"Controllo non distruttivo {cnd} obbligatorio per classe {profilo_valore}",
                    "fase": "post_saldatura",
                    "motivazione": f"EN 1090-2 Tab. 24 richiede {cnd} per {profilo_valore}",
                })

    # Rule 4: Certificati 3.1 sempre obbligatori per EN 1090
    if normativa in ("EN_1090", "MISTA"):
        prereq_tracc = classification.get("prerequisiti_tracciabilita", {})
        if not prereq_tracc.get("certificati_31_richiesti"):
            classification.setdefault("prerequisiti_tracciabilita", {})["certificati_31_richiesti"] = True
            classification["prerequisiti_tracciabilita"]["tracciabilita_colata"] = True
            classification["prerequisiti_tracciabilita"]["ddt_obbligatori"] = True
            warnings.append({
                "tipo": "incoerenza",
                "messaggio": "Certificati 3.1 e tracciabilita colata sono SEMPRE obbligatori per EN 1090.",
                "correzione_applicata": True,
            })

    return {
        "warnings_regole": warnings,
        "enrichments_regole": enrichments,
        "classification_corretta": classification,
    }


# ═══════════════════════════════════════════════════════════════════
#  FUNZIONE PRINCIPALE — Analisi completa Fase 1
# ═══════════════════════════════════════════════════════════════════

async def analizza_preventivo_completo(preventivo: dict) -> dict:
    """Esegue l'analisi completa Fase 1: estrazione + classificazione + regole.
    Returns a full istruttoria object."""

    # ── Livello 1A: Estrazione tecnica ──
    logger.info(f"[ISTRUTTORIA] 1A — Estrazione tecnica per {preventivo.get('number', '?')}")
    extraction = await extract_technical_data(preventivo)

    if extraction.get("error"):
        return {
            "stato": "errore",
            "fase_fallita": "1A_estrazione",
            "errore": extraction["error"],
            "estrazione": extraction,
        }

    # ── Livello 1B: Classificazione normativa ──
    logger.info("[ISTRUTTORIA] 1B — Classificazione normativa")
    classification = await classify_and_propose(extraction, preventivo)

    if classification.get("error"):
        return {
            "stato": "errore",
            "fase_fallita": "1B_classificazione",
            "errore": classification["error"],
            "estrazione": extraction,
            "classificazione": classification,
        }

    # ── Regole deterministiche ──
    logger.info("[ISTRUTTORIA] Regole deterministiche")
    rules_result = apply_deterministic_rules(classification, extraction)

    # ── Componi risultato finale ──

    # Build knowledge state summary
    all_stati = []
    for el in extraction.get("elementi_strutturali", []):
        all_stati.append(el.get("stato", "mancante"))
    for lav in extraction.get("lavorazioni_rilevate", []):
        all_stati.append(lav.get("stato", "mancante"))
    if extraction.get("saldature"):
        all_stati.append(extraction["saldature"].get("stato", "mancante"))
    if extraction.get("trattamenti_superficiali"):
        all_stati.append(extraction["trattamenti_superficiali"].get("stato", "mancante"))

    n_confermato = all_stati.count("confermato")
    n_dedotto = all_stati.count("dedotto")
    n_mancante = all_stati.count("mancante")
    n_incerto = all_stati.count("incerto")

    return {
        "stato": "completato",
        "preventivo_number": preventivo.get("number", ""),
        "preventivo_id": preventivo.get("preventivo_id", ""),

        # Sezione A: Classificazione
        "classificazione": rules_result["classification_corretta"].get("classificazione", {}),
        "profilo_tecnico": rules_result["classification_corretta"].get("profilo_tecnico", {}),

        # Sezione B: Dati estratti
        "estrazione_tecnica": {
            "elementi_strutturali": extraction.get("elementi_strutturali", []),
            "lavorazioni_rilevate": extraction.get("lavorazioni_rilevate", []),
            "saldature": extraction.get("saldature", {}),
            "trattamenti_superficiali": extraction.get("trattamenti_superficiali", {}),
            "montaggio_posa": extraction.get("montaggio_posa", {}),
            "destinazione_uso": extraction.get("destinazione_uso", {}),
            "ambiguita_rilevate": extraction.get("ambiguita_rilevate", []),
            "parole_chiave_rischio": extraction.get("parole_chiave_rischio", []),
            "note_tecnico": extraction.get("note_tecnico", ""),
        },

        # Sezione C: Requisiti proposti
        "fasi_produttive_attese": rules_result["classification_corretta"].get("fasi_produttive_attese", []),
        "documenti_richiesti": rules_result["classification_corretta"].get("documenti_richiesti", []),
        "controlli_richiesti": rules_result["classification_corretta"].get("controlli_richiesti", []),
        "prerequisiti_saldatura": rules_result["classification_corretta"].get("prerequisiti_saldatura", {}),
        "prerequisiti_tracciabilita": rules_result["classification_corretta"].get("prerequisiti_tracciabilita", {}),

        # Sezione D: Stato conoscenza
        "stato_conoscenza": {
            "confermato": n_confermato,
            "dedotto": n_dedotto,
            "mancante": n_mancante,
            "incerto": n_incerto,
            "completezza_pct": round(
                (n_confermato + n_dedotto) / max(len(all_stati), 1) * 100, 1
            ),
        },

        # Sezione E: Domande residue
        "domande_residue": rules_result["classification_corretta"].get("domande_residue", []),

        # Meta
        "warnings_regole": rules_result["warnings_regole"],
        "enrichments_regole": rules_result["enrichments_regole"],
    }
