"""GPT-4o Vision analysis for gate safety compliance (EN 12453/EN 13241)."""
import os
import base64
import json
import logging
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sei un esperto certificato di sicurezza cancelli automatici e chiusure industriali.
Le tue competenze coprono le seguenti normative:
- UNI EN 12453 (Sicurezza in uso degli automatismi)
- UNI EN 13241 (Norma prodotto per chiusure industriali, commerciali e da garage)
- Direttiva Macchine 2006/42/CE
- UNI EN 12978 (Dispositivi di protezione sensibili alla pressione - coste)

ANALISI FOTO:
Quando ricevi foto di un cancello/chiusura automatica, devi:
1. IDENTIFICARE il tipo di chiusura (scorrevole, battente, sezionale, avvolgibile, basculante)
2. INDIVIDUARE RISCHI specifici:
   - Schiacciamento (punto di chiusura principale, zone laterali)
   - Cesoiamento (maglie rete, giunti, cerniere)
   - Convogliamento (rulli guida, catene, ingranaggi esposti)
   - Impatto (mancanza limitatore di forza/encoder)
   - Intrappolamento (spazi tra ante e struttura)
3. VERIFICARE la presenza dei dispositivi di sicurezza obbligatori:
   - Costa sensibile di sicurezza (8K2 o ottica)
   - Fotocellule (coppia bassa + coppia alta se necessario)
   - Lampeggiante con antenna
   - Selettore a chiave/tastiera
   - Finecorsa di apertura e chiusura
   - Encoder o limitatore di coppia sul motore
   - Protezione anti-caduta (per sezionali/basculanti)
   - Rete anti-cesoiamento (maglia max 25x25mm per EN 13241)

FORMATO RISPOSTA (JSON RIGOROSO):
Rispondi ESCLUSIVAMENTE con un JSON valido, senza testo aggiuntivo, con questa struttura:
{
  "tipo_chiusura": "scorrevole|battente|sezionale|avvolgibile|basculante|altro",
  "descrizione_generale": "Breve descrizione di ciò che si vede nella foto",
  "rischi": [
    {
      "zona": "Zona specifica (es: 'Bordo chiusura lato muro')",
      "tipo_rischio": "schiacciamento|cesoiamento|convogliamento|impatto|intrappolamento",
      "gravita": "alta|media|bassa",
      "problema": "Descrizione tecnica del problema",
      "norma_riferimento": "EN 12453 par. X.X",
      "soluzione": "Intervento correttivo specifico"
    }
  ],
  "dispositivi_presenti": ["lista dispositivi di sicurezza visibili"],
  "dispositivi_mancanti": ["lista dispositivi obbligatori non visibili"],
  "materiali_suggeriti": [
    {
      "keyword": "keyword per ricerca nel listino (es: costa, fotocellula, rete, lampeggiante, encoder, finecorsa, selettore)",
      "descrizione": "Descrizione specifica del materiale necessario",
      "quantita": 1,
      "priorita": "obbligatorio|consigliato"
    }
  ],
  "note_tecniche": "Eventuali osservazioni aggiuntive per il tecnico",
  "conformita_percentuale": 0
}

REGOLE IMPORTANTI:
- Se non riesci a vedere chiaramente un elemento, segnalalo come "non verificabile dalla foto"
- Sii conservativo: se non vedi un dispositivo, presumilo assente
- Le keyword in materiali_suggeriti devono corrispondere a termini generici del listino
- La conformita_percentuale è una stima 0-100 basata sui dispositivi presenti vs obbligatori
"""


async def analyze_photos(photo_data_list: List[dict], user_description: str = "") -> dict:
    """Analyze gate photos using GPT-4o Vision.
    
    Args:
        photo_data_list: List of {"base64": str, "mime_type": str, "label": str}
        user_description: Optional user description of the situation
    
    Returns:
        Structured analysis result dict
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
    prompt_parts.append("Analizza le foto e restituisci il JSON con l'analisi di sicurezza completa.")

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
            "note_tecniche": "Errore nel parsing della risposta AI. Analisi testuale disponibile sopra.",
            "conformita_percentuale": 0,
            "_raw_response": response_text,
        }

    return result
