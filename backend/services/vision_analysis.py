"""GPT-4o Vision analysis for safety compliance."""
import os
import json
import logging
from typing import List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_JSON_SCHEMA = """{"tipo_chiusura":"<tipo>","descrizione_generale":"...","rischi":[{"zona":"...","tipo_rischio":"...","gravita":"alta|media|bassa","problema":"...","norma_riferimento":"...","soluzione":"..."}],"dispositivi_presenti":[],"dispositivi_mancanti":[],"materiali_suggeriti":[{"keyword":"...","descrizione":"...","quantita":1,"priorita":"obbligatorio|consigliato"}],"varianti":{"A":{"titolo":"Intervento Minimo","descrizione":"...","interventi":[],"stima_manodopera":"...","costo_stimato":0},"B":{"titolo":"Intervento Completo","descrizione":"...","interventi":[],"stima_manodopera":"...","costo_stimato":0},"C":{"titolo":"Rifacimento Totale","descrizione":"...","interventi":[],"stima_manodopera":"...","costo_stimato":0}},"rischi_residui":[],"testo_sintetico_fattura":"...","note_tecniche":"...","conformita_percentuale":0}"""

_COMMON_RULES = (
    "REGOLE:\n"
    "- Elemento non visibile = presumilo assente\n"
    "- conformita_percentuale: stima 0-100\n"
    "- Costi realistici per mercato italiano\n"
    "- Variante A ~30-50% di C, Variante B ~50-70% di C\n"
    "- Ogni variante elenca TUTTI gli interventi esplicitamente\n"
    "- OGNI elemento in dispositivi_mancanti deve avere scheda in rischi\n"
    "- Registro tecnico-professionale da perizia ingegneristica\n"
)

PROMPT_CANCELLI = (
    "Sei un Ingegnere esperto in Direttiva Macchine 2006/42/CE e Normativa Cancelli EN 12453 / EN 13241.\n\n"
    "Analizza le foto del cancello/chiusura automatica e:\n"
    "1. Identifica tipo di chiusura\n"
    "2. Individua rischi (schiacciamento EN 12453 par.5.1.1, cesoiamento EN 13241 par.4.3, impatto, intrappolamento)\n"
    "3. Verifica dispositivi: costa sensibile, fotocellule, lampeggiante, finecorsa, encoder\n"
    "4. Proponi 3 varianti di intervento con stima costi\n\n"
    "Rispondi ESCLUSIVAMENTE con JSON valido:\n"
    + _JSON_SCHEMA + "\n\n"
    + _COMMON_RULES
)

PROMPT_BARRIERE = (
    "Sei un esperto di accessibilita e barriere architettoniche (D.M. 236/1989, Legge 13/1989).\n\n"
    "Analizza le foto e individua non conformita su: rampe, corrimano, larghezze, soglie, pavimentazione.\n\n"
    "Rispondi ESCLUSIVAMENTE con JSON valido:\n"
    + _JSON_SCHEMA + "\n\n"
    + _COMMON_RULES
    + "- tipo_chiusura: indicare tipo accesso (scala, rampa, ingresso)\n"
)

PROMPT_STRUTTURE = (
    "Sei un ingegnere strutturista esperto in NTC 2018 ed EN 1090.\n\n"
    "Analizza le foto della struttura metallica e individua: corrosione, bulloneria, saldature, deformazioni.\n\n"
    "Rispondi ESCLUSIVAMENTE con JSON valido:\n"
    + _JSON_SCHEMA + "\n\n"
    + _COMMON_RULES
    + "- tipo_chiusura: indicare tipo struttura (tettoia, scala, soppalco)\n"
)

PROMPT_PARAPETTI = (
    "Sei un ingegnere strutturista specializzato in parapetti e ringhiere (NTC 2018, UNI 11678:2017, UNI 7697:2015).\n\n"
    "ATTENZIONE: NON applicare norme per cancelli motorizzati (EN 12453).\n\n"
    "Analizza le foto e individua: schema statico, fissaggi, stratigrafia vetro, altezza, scalabilita.\n\n"
    "Rispondi ESCLUSIVAMENTE con JSON valido:\n"
    + _JSON_SCHEMA + "\n\n"
    + _COMMON_RULES
    + "- tipo_chiusura: indicare tipo sistema (parapetto vetro, ringhiera metallica, balaustra)\n"
)

PROMPTS = {
    "cancelli": PROMPT_CANCELLI,
    "barriere": PROMPT_BARRIERE,
    "strutture": PROMPT_STRUTTURE,
    "parapetti": PROMPT_PARAPETTI,
}

SYSTEM_PROMPT = PROMPT_CANCELLI


async def analyze_photos(photo_data_list: List[dict], user_description: str = "", tipo_perizia: str = "cancelli") -> dict:
    """Analyze photos using GPT-4o Vision."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    system_prompt = PROMPTS.get(tipo_perizia, PROMPT_CANCELLI)

    content = []
    for photo in photo_data_list:
        content.append({
            "type": "image_url",
            "image_url": {"url": "data:" + photo["mime_type"] + ";base64," + photo["base64"]}
        })

    prompt_parts = []
    if user_description:
        prompt_parts.append("Descrizione del tecnico: " + user_description)
    labels = [p.get("label", "Foto " + str(i + 1)) for i, p in enumerate(photo_data_list)]
    prompt_parts.append("Foto allegate (" + str(len(photo_data_list)) + "): " + ", ".join(labels))
    prompt_parts.append("Analizza le foto e restituisci il JSON completo.")
    content.append({"type": "text", "text": "\n".join(prompt_parts)})

    client_ai = AsyncOpenAI(api_key=api_key)
    logger.info("Sending " + str(len(photo_data_list)) + " photos to GPT-4o Vision...")

    completion = await client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
    )
    response_text = completion.choices[0].message.content
    logger.info("GPT-4o Vision response received (" + str(len(response_text)) + " chars)")

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
        logger.error("Failed to parse AI response as JSON: " + str(e))
        result = {
            "tipo_chiusura": "non_determinato",
            "descrizione_generale": response_text[:500],
            "rischi": [],
            "dispositivi_presenti": [],
            "dispositivi_mancanti": [],
            "materiali_suggeriti": [],
            "varianti": _default_varianti(),
            "testo_sintetico_fattura": "",
            "note_tecniche": "Errore nel parsing della risposta AI.",
            "conformita_percentuale": 0,
            "_raw_response": response_text,
        }

    if "varianti" not in result:
        result["varianti"] = _default_varianti()
    if "testo_sintetico_fattura" not in result:
        result["testo_sintetico_fattura"] = ""

    return result


def _default_varianti() -> dict:
    return {
        "A": {"titolo": "Adeguamento Minimo", "descrizione": "", "interventi": [], "stima_manodopera": "", "costo_stimato": 0},
        "B": {"titolo": "Adeguamento Completo", "descrizione": "", "interventi": [], "stima_manodopera": "", "costo_stimato": 0},
        "C": {"titolo": "Sostituzione Totale", "descrizione": "", "interventi": [], "stima_manodopera": "", "costo_stimato": 0},
    }
