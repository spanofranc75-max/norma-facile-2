"""
Servizio Montaggio — Analisi DDT Bulloneria + Tabella Coppie di Serraggio ISO 898-1.

Funzionalità:
1. AI Vision (GPT-4o) analizza foto DDT fornitori bulloni/dadi/rondelle
2. Estrae: Diametro, Classe, Lotto, Quantità
3. Tabella ISO 898-1 per coppie di serraggio (Nm) dato Diametro × Classe
"""
import os
import json
import uuid
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("emergentintegrations not available — AI analysis disabled")


# ══════════════════════════════════════════════════════════════
#  TABELLA COPPIE DI SERRAGGIO ISO 898-1 (Nm)
#  Fonte: EN 14399, ISO 898-1, VDI 2230
#  Valori per bulloni a gambo pieno, coefficiente attrito μ = 0.12-0.14
# ══════════════════════════════════════════════════════════════

TORQUE_TABLE = {
    # Classe 4.6
    ("M6", "4.6"): 4.1,
    ("M8", "4.6"): 10,
    ("M10", "4.6"): 20,
    ("M12", "4.6"): 34,
    ("M14", "4.6"): 55,
    ("M16", "4.6"): 85,
    ("M18", "4.6"): 115,
    ("M20", "4.6"): 165,
    ("M22", "4.6"): 225,
    ("M24", "4.6"): 280,
    ("M27", "4.6"): 415,
    ("M30", "4.6"): 555,

    # Classe 5.6
    ("M6", "5.6"): 5.1,
    ("M8", "5.6"): 12,
    ("M10", "5.6"): 25,
    ("M12", "5.6"): 43,
    ("M14", "5.6"): 69,
    ("M16", "5.6"): 106,
    ("M18", "5.6"): 145,
    ("M20", "5.6"): 206,
    ("M22", "5.6"): 280,
    ("M24", "5.6"): 350,
    ("M27", "5.6"): 520,
    ("M30", "5.6"): 695,

    # Classe 8.8
    ("M6", "8.8"): 8.5,
    ("M8", "8.8"): 21,
    ("M10", "8.8"): 42,
    ("M12", "8.8"): 72,
    ("M14", "8.8"): 115,
    ("M16", "8.8"): 175,
    ("M18", "8.8"): 245,
    ("M20", "8.8"): 345,
    ("M22", "8.8"): 470,
    ("M24", "8.8"): 590,
    ("M27", "8.8"): 870,
    ("M30", "8.8"): 1150,

    # Classe 10.9
    ("M6", "10.9"): 12,
    ("M8", "10.9"): 30,
    ("M10", "10.9"): 59,
    ("M12", "10.9"): 101,
    ("M14", "10.9"): 162,
    ("M16", "10.9"): 245,
    ("M18", "10.9"): 345,
    ("M20", "10.9"): 485,
    ("M22", "10.9"): 660,
    ("M24", "10.9"): 830,
    ("M27", "10.9"): 1220,
    ("M30", "10.9"): 1630,

    # Classe 12.9
    ("M6", "12.9"): 14,
    ("M8", "12.9"): 35,
    ("M10", "12.9"): 70,
    ("M12", "12.9"): 121,
    ("M14", "12.9"): 195,
    ("M16", "12.9"): 295,
    ("M18", "12.9"): 410,
    ("M20", "12.9"): 580,
    ("M22", "12.9"): 790,
    ("M24", "12.9"): 990,
    ("M27", "12.9"): 1460,
    ("M30", "12.9"): 1950,
}

# Available diameters and classes for UI reference
AVAILABLE_DIAMETERS = ["M6", "M8", "M10", "M12", "M14", "M16", "M18", "M20", "M22", "M24", "M27", "M30"]
AVAILABLE_CLASSES = ["4.6", "5.6", "8.8", "10.9", "12.9"]


def get_torque_nm(diametro: str, classe: str) -> Optional[float]:
    """Get the tightening torque in Nm for a given diameter and class."""
    d = diametro.upper().strip()
    c = classe.strip()
    return TORQUE_TABLE.get((d, c))


def get_torque_table_full() -> List[Dict]:
    """Return the full torque table for frontend display."""
    rows = []
    for (d, c), nm in sorted(TORQUE_TABLE.items(), key=lambda x: (AVAILABLE_DIAMETERS.index(x[0][0]) if x[0][0] in AVAILABLE_DIAMETERS else 99, x[0][1])):
        rows.append({"diametro": d, "classe": c, "coppia_nm": nm})
    return rows


# ══════════════════════════════════════════════════════════════
#  AI VISION — Analisi DDT Bulloneria
# ══════════════════════════════════════════════════════════════

DDT_ANALYSIS_PROMPT = """Sei un analista documentale specializzato in DDT (Documenti di Trasporto) per bulloneria e carpenteria metallica.

Analizza questa foto/scansione di un DDT fornitore e estrai TUTTI i bulloni, dadi e rondelle elencati.

PER OGNI ARTICOLO ESTRATTO:
1. diametro: Il diametro metrico (es. "M12", "M16", "M20"). Se trovi "12x50" interpretalo come "M12"
2. classe: La classe di resistenza (es. "8.8", "10.9", "12.9"). Cercala vicino alla descrizione articolo
3. lotto: Il numero di lotto/batch (es. "LOT-2026-001", "B1234"). Cercalo in testa al DDT o nella riga articolo
4. quantita: Quantità indicata (es. "50 pz", "100", "2 scatole")
5. descrizione: Descrizione breve dell'articolo (es. "Bullone TE M16x60 cl.10.9", "Dado autobloccante M12")

Se non riesci a leggere un campo, metti null.
Se la foto NON è un DDT di bulloneria, restituisci un array vuoto.

RISPONDI SOLO con JSON valido:
{
    "fornitore": "Nome fornitore se visibile, altrimenti null",
    "numero_ddt": "Numero DDT se visibile, altrimenti null",
    "data_ddt": "Data DDT se visibile, altrimenti null",
    "lotto_generale": "Numero lotto generale del DDT se presente, altrimenti null",
    "articoli": [
        {
            "diametro": "M16",
            "classe": "10.9",
            "lotto": "LOT-2026-001",
            "quantita": "50 pz",
            "descrizione": "Bullone TE M16x60 cl.10.9"
        }
    ]
}"""


async def analyze_ddt_bulloneria(image_b64: str) -> Dict:
    """Analyze a DDT photo using GPT-4o Vision to extract bolt data."""
    if not AI_AVAILABLE:
        return {"error": "AI non disponibile", "articoli": []}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY mancante", "articoli": []}

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ddt-{uuid.uuid4().hex[:8]}",
        system_message=DDT_ANALYSIS_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text="Analizza questo DDT di bulloneria e restituisci il JSON con tutti gli articoli estratti.",
        file_contents=[ImageContent(image_base64=image_b64)],
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

        # Enrich with torque values
        for art in result.get("articoli", []):
            d = art.get("diametro")
            c = art.get("classe")
            if d and c:
                torque = get_torque_nm(d, c)
                art["coppia_nm"] = torque

        return result
    except Exception as e:
        logger.error(f"DDT AI analysis failed: {e}")
        return {"error": str(e), "articoli": []}
