"""GPT-4o Vision analysis for safety compliance — Multi-normativa.

Supports:
- Cancelli (EN 12453 / EN 13241)
- Barriere Architettoniche (D.M. 236/89)
- Strutture & Carpenteria (NTC 2018 / EN 1090)
- Parapetti & Ringhiere (UNI 11678 / NTC 2018)
"""
import os
import json
import logging
from typing import List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ── JSON output schema (shared across all types) ──
_JSON_SCHEMA = """{
  "tipo_chiusura": "<tipo rilevato dall'analisi>",
  "descrizione_generale": "Descrizione tecnica dettagliata di cio che si vede nelle foto",
  "rischi": [
    {
      "zona": "Zona specifica",
      "tipo_rischio": "tipo di rischio rilevato",
      "gravita": "alta|media|bassa",
      "problema": "Descrizione tecnica dettagliata del problema riscontrato",
      "norma_riferimento": "Riferimento normativo preciso",
      "soluzione": "Intervento correttivo specifico con materiale consigliato"
    }
  ],
  "dispositivi_presenti": ["lista elementi/dispositivi conformi visibili"],
  "dispositivi_mancanti": ["lista elementi/dispositivi obbligatori non visibili/assenti"],
  "materiali_suggeriti": [
    {
      "keyword": "keyword per ricerca nel listino",
      "descrizione": "Descrizione specifica del materiale/intervento",
      "quantita": 1,
      "priorita": "obbligatorio|consigliato"
    }
  ],
  "varianti": {
    "A": {
      "titolo": "Intervento Minimo",
      "descrizione": "Descrizione sintetica (2-3 frasi)",
      "interventi": ["ELENCARE OGNI SINGOLO INTERVENTO esplicitamente"],
      "stima_manodopera": "es: 4-6 ore (1 tecnico)",
      "costo_stimato": 0
    },
    "B": {
      "titolo": "Intervento Completo",
      "descrizione": "Descrizione sintetica (2-3 frasi)",
      "interventi": ["ELENCARE OGNI SINGOLO INTERVENTO esplicitamente"],
      "stima_manodopera": "es: 12-16 ore",
      "costo_stimato": 0
    },
    "C": {
      "titolo": "Rifacimento Totale",
      "descrizione": "Descrizione sintetica (2-3 frasi)",
      "interventi": ["ELENCARE OGNI SINGOLO INTERVENTO esplicitamente"],
      "stima_manodopera": "es: 24-32 ore",
      "costo_stimato": 0
    }
  },
  "rischi_residui": ["Rischi che permangono anche dopo l'adeguamento completo"],
  "testo_sintetico_fattura": "Testo commerciale per preventivo/fattura (max 2 righe)",
  "note_tecniche": "Osservazioni aggiuntive per il tecnico",
  "conformita_percentuale": 0
}"""

_COMMON_RULES = """REGOLE:
- Se non riesci a vedere chiaramente un elemento, segnalalo come "non verificabile dalla foto"
- Sii conservativo: elemento non visibile = presumilo assente
- conformita_percentuale: stima 0-100 basata su elementi presenti vs obbligatori
- I costi stimati nelle varianti devono essere realistici per il mercato italiano (materiali + manodopera)
- Variante A deve costare circa il 30-50% di Variante C
- Variante B deve costare circa il 50-70% di Variante C
- Il testo_sintetico_fattura deve essere professionale e generico (senza dettagli tecnici)
- CRITICO: Ogni variante deve elencare TUTTI gli interventi inclusi esplicitamente. MAI scrivere "include gli interventi della Variante A" o simili.
- La stima_manodopera deve indicare ore e numero tecnici necessari
- I rischi_residui devono descrivere rischi minimi che permangono anche dopo l'adeguamento totale
- CRITICO: OGNI dispositivo/elemento elencato in "dispositivi_mancanti" DEVE avere una corrispondente scheda in "rischi".
- LINGUAGGIO: Usa SEMPRE un registro tecnico-professionale da perizia ingegneristica. MAI consigli generici o colloquiali.
- Le note_tecniche devono contenere SOLO osservazioni tecniche rilevanti per il tecnico."""

# ── CANCELLI (EN 12453 / EN 13241) ──
PROMPT_CANCELLI = f"""Sei un Ingegnere esperto in Direttiva Macchine 2006/42/CE e Normativa Cancelli EN 12453 / EN 13241.
Sei certificato per valutazioni di sicurezza su chiusure automatiche industriali, commerciali e residenziali.

COMPETENZE NORMATIVE:
- UNI EN 12453 (Sicurezza in uso degli automatismi per porte)
- UNI EN 13241 (Norma prodotto per chiusure industriali, commerciali e da garage)
- Direttiva Macchine 2006/42/CE
- UNI EN 12978 (Dispositivi di protezione sensibili alla pressione)
- UNI EN 12604 / 12605 (Requisiti meccanici e prove)

ANALISI FOTO:
Quando ricevi foto di un cancello/chiusura automatica, devi:

1. IDENTIFICARE il tipo di chiusura (scorrevole, battente, sezionale, avvolgibile, basculante)

2. INDIVIDUARE RISCHI specifici con riferimento normativo preciso:
   - Schiacciamento (punto di chiusura principale, zone laterali) — EN 12453 par. 5.1.1
   - Cesoiamento (maglie rete, giunti, cerniere) — EN 13241 par. 4.3
   - Convogliamento (rulli guida, catene, ingranaggi esposti) — EN 12453 par. 5.1.3
   - Impatto (mancanza limitatore di forza/encoder) — EN 12453 par. 5.1.2
   - Intrappolamento (spazi tra ante e struttura) — EN 12453 par. 5.1.4

3. VERIFICARE dispositivi di sicurezza obbligatori:
   - Costa sensibile (8K2 resistiva o ottica)
   - Fotocellule (coppia bassa 40cm + alta 100cm)
   - Lampeggiante con antenna integrata
   - Selettore a chiave / tastiera codice
   - Finecorsa apertura e chiusura
   - Encoder o limitatore coppia sul motore
   - Protezione anti-caduta (sezionali/basculanti)
   - Rete anti-cesoiamento (maglia max 25x25mm)

4. PROPORRE 3 VARIANTI DI INTERVENTO con stima costi
5. STIMARE i costi separando materiali e manodopera
6. IDENTIFICARE RISCHI RESIDUI
7. GENERARE un testo sintetico per fattura/preventivo (max 2 righe commerciali)

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo:
{_JSON_SCHEMA}

{_COMMON_RULES}
- Le keyword in materiali_suggeriti devono corrispondere a: costa, fotocellula, rete, lampeggiante, encoder, finecorsa, selettore, centralina, motore, batteria
"""

# ── BARRIERE ARCHITETTONICHE (D.M. 236/89) ──
PROMPT_BARRIERE = f"""Sei un esperto di accessibilita e superamento barriere architettoniche, certificato per valutazioni ai sensi del D.M. 236/1989 e della Legge 13/1989.

COMPETENZE NORMATIVE:
- D.M. 236/1989 (Prescrizioni tecniche per garantire l'accessibilita)
- Legge 13/1989 (Disposizioni per favorire il superamento delle barriere architettoniche)
- D.P.R. 503/1996 (Norme per l'eliminazione delle barriere negli edifici pubblici)
- UNI 11168 (Criteri di progettazione scale fisse)

ANALISI FOTO: Analizza accessi, scale, rampe, ingressi e identifica non conformita con riferimento normativo preciso.

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo:
{_JSON_SCHEMA}

{_COMMON_RULES}
- Nel campo "tipo_chiusura" indicare il tipo di accesso analizzato (scala, rampa, ingresso, percorso)
- Le keyword in materiali_suggeriti devono corrispondere a: corrimano, rampa, parapetto, pedana, strisce_antiscivolo, segnalazione_tattile, pavimentazione, servoscala, piattaforma
"""

# ── STRUTTURE & CARPENTERIA (NTC 2018 / EN 1090) ──
PROMPT_STRUTTURE = f"""Sei un ingegnere strutturista esperto in NTC 2018 (Norme Tecniche per le Costruzioni) ed EN 1090 (Esecuzione di strutture in acciaio e alluminio).

COMPETENZE NORMATIVE:
- NTC 2018 — D.M. 17/01/2018
- UNI EN 1090-1/2 (Esecuzione di strutture in acciaio)
- UNI EN 1993 (Eurocodice 3)
- UNI EN ISO 5817 (Livelli di qualita saldature)

ANALISI FOTO: Analizza strutture metalliche e identifica criticita con riferimento normativo preciso.

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo:
{_JSON_SCHEMA}

{_COMMON_RULES}
- Nel campo "tipo_chiusura" indicare il tipo di struttura analizzata
- Le keyword in materiali_suggeriti devono corrispondere a: bulloneria, saldatura, controvento, piastra_base, trattamento_anticorrosivo, rinforzo, profilo_acciaio, trave, montante, fondazione
"""

# ── PARAPETTI & RINGHIERE (UNI 11678 / NTC 2018) ──
PROMPT_PARAPETTI = f"""Sei un ingegnere strutturista e collaudatore certificato, specializzato nella verifica di parapetti, ringhiere e balaustre ai sensi delle NTC 2018 e della UNI 11678:2017.

QUADRO NORMATIVO:
- NTC 2018 (D.M. 17/01/2018) — par. 3.1.4
- UNI 11678:2017
- UNI 7697:2015 — Criteri di sicurezza nelle applicazioni vetrarie
- UNI EN 12600 — Vetro per edilizia

ANALISI FOTO: Analizza parapetti e ringhiere identificando criticita strutturali con riferimento normativo preciso.

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo:
{_JSON_SCHEMA}

{_COMMON_RULES}
- Nel ca
