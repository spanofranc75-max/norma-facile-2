"""GPT-4o Vision analysis for gate safety compliance (EN 12453/EN 13241).

Enhanced with 3 intervention variants (A/B/C) and synthetic invoice text.
"""
import os
import json
import logging
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sei un Ingegnere esperto in Direttiva Macchine 2006/42/CE e Normativa Cancelli EN 12453 / EN 13241.
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

4. PROPORRE 3 VARIANTI DI INTERVENTO con stima costi:
   - Variante A "Adeguamento Minimo": Solo dispositivi di sicurezza obbligatori mancanti
   - Variante B "Adeguamento Completo": Sicurezze + nuova centralina + ottimizzazione impianto
   - Variante C "Sostituzione Totale": Nuovo impianto completo (motore, centralina, sicurezze, struttura se necessario)

5. GENERARE un testo sintetico per fattura/preventivo (max 2 righe commerciali)

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo:
{
  "tipo_chiusura": "scorrevole|battente|sezionale|avvolgibile|basculante|altro",
  "descrizione_generale": "Descrizione tecnica dettagliata di cio che si vede nelle foto",
  "rischi": [
    {
      "zona": "Zona specifica (es: 'Bordo chiusura lato muro')",
      "tipo_rischio": "schiacciamento|cesoiamento|convogliamento|impatto|intrappolamento",
      "gravita": "alta|media|bassa",
      "problema": "Descrizione tecnica dettagliata del problema riscontrato",
      "norma_riferimento": "EN 12453 par. X.X.X",
      "soluzione": "Intervento correttivo specifico con materiale consigliato"
    }
  ],
  "dispositivi_presenti": ["lista dispositivi di sicurezza visibili/verificati"],
  "dispositivi_mancanti": ["lista dispositivi obbligatori non visibili/assenti"],
  "materiali_suggeriti": [
    {
      "keyword": "keyword per ricerca nel listino (costa, fotocellula, rete, lampeggiante, encoder, finecorsa, selettore, centralina, motore, batteria)",
      "descrizione": "Descrizione specifica del materiale",
      "quantita": 1,
      "priorita": "obbligatorio|consigliato"
    }
  ],
  "varianti": {
    "A": {
      "titolo": "Adeguamento Minimo",
      "descrizione": "Descrizione sintetica dell'intervento (2-3 frasi)",
      "interventi": ["Lista puntata degli interventi inclusi"],
      "costo_stimato": 0,
      "tempo_stimato": "1 giorno"
    },
    "B": {
      "titolo": "Adeguamento Completo",
      "descrizione": "Descrizione sintetica dell'intervento (2-3 frasi)",
      "interventi": ["Lista puntata degli interventi inclusi"],
      "costo_stimato": 0,
      "tempo_stimato": "2-3 giorni"
    },
    "C": {
      "titolo": "Sostituzione Totale",
      "descrizione": "Descrizione sintetica dell'intervento (2-3 frasi)",
      "interventi": ["Lista puntata degli interventi inclusi"],
      "costo_stimato": 0,
      "tempo_stimato": "3-5 giorni"
    }
  },
  "testo_sintetico_fattura": "Testo commerciale per preventivo/fattura (max 2 righe). Es: 'Messa a norma cancello scorrevole automatico c/o [indirizzo] secondo normativa EN 12453/EN 13241 come da perizia tecnica allegata.'",
  "note_tecniche": "Osservazioni aggiuntive per il tecnico",
  "conformita_percentuale": 0
}

REGOLE:
- Se non riesci a vedere chiaramente un elemento, segnalalo come "non verificabile dalla foto"
- Sii conservativo: dispositivo non visibile = presumilo assente
- Le keyword in materiali_suggeriti devono corrispondere a termini generici del listino
- conformita_percentuale: stima 0-100 basata su dispositivi presenti vs obbligatori
- I costi stimati nelle varianti devono essere realistici per il mercato italiano (materiali + manodopera)
- Variante A deve costare circa il 30-50% di Variante C
- Variante B deve costare circa il 50-70% di Variante C
- Il testo_sintetico_fattura deve essere professionale e generico (senza dettagli tecnici)
"""


async def analyze_photos(photo_data_list: List[dict], user_description: str = "") -> dict:
    """Analyze gate photos using GPT-4o Vision.

    Args:
        photo_data_list: List of {"base64": str, "mime_type": str, "label": str}
        user_description: Optional user description of the situation

    Returns:
        Structured analysis result dict with risks, variants A/B/C, and synthetic text
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    chat = LlmChat(
        api_key=api_key,
        session_id=f"sopralluogo-{os.urandom(8).hex()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("openai", "gpt-4o")

    file_contents = []
    for photo in photo_data_list:
        file_contents.append(ImageContent(image_base64=photo["base64"]))

    prompt_parts = []
    if user_description:
        prompt_parts.append(f"Descrizione del tecnico: {user_description}")

    labels = [p.get("label", f"Foto {i+1}") for i, p in enumerate(photo_data_list)]
    prompt_parts.append(f"Foto allegate ({len(photo_data_list)}): {', '.join(labels)}")
    prompt_parts.append("Analizza le foto e restituisci il JSON completo con analisi di sicurezza, 3 varianti di intervento e testo sintetico per fattura.")

    user_msg = UserMessage(
        text="\n".join(prompt_parts),
        file_contents=file_contents,
    )

    logger.info(f"Sending {len(photo_data_list)} photos to GPT-4o Vision for analysis...")
    response_text = await chat.send_message(user_msg)
    logger.info(f"GPT-4o Vision response received ({len(response_text)} chars)")

    # Parse JSON from response (handle markdown code blocks)
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}\nRaw: {response_text[:500]}")
        result = {
            "tipo_chiusura": "non_determinato",
            "descrizione_generale": response_text[:500],
            "rischi": [],
            "dispositivi_presenti": [],
            "dispositivi_mancanti": [],
            "materiali_suggeriti": [],
            "varianti": _default_varianti(),
            "testo_sintetico_fattura": "",
            "note_tecniche": "Errore nel parsing della risposta AI. Analisi testuale disponibile sopra.",
            "conformita_percentuale": 0,
            "_raw_response": response_text,
        }

    # Ensure varianti and testo_sintetico exist (backward compat)
    if "varianti" not in result:
        result["varianti"] = _default_varianti()
    if "testo_sintetico_fattura" not in result:
        result["testo_sintetico_fattura"] = ""

    return result


def _default_varianti() -> dict:
    """Return empty variant structure as fallback."""
    return {
        "A": {"titolo": "Adeguamento Minimo", "descrizione": "", "interventi": [], "costo_stimato": 0, "tempo_stimato": ""},
        "B": {"titolo": "Adeguamento Completo", "descrizione": "", "interventi": [], "costo_stimato": 0, "tempo_stimato": ""},
        "C": {"titolo": "Sostituzione Totale", "descrizione": "", "interventi": [], "costo_stimato": 0, "tempo_stimato": ""},
    }
