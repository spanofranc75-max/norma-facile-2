"""
Preventivatore Predittivo — Servizio core per stime AI-driven.

Funzionalita:
1. Analisi AI Disegno → Estrazione materiali (profili, piastre, bulloneria)
2. Motore Prezzi Storici → Incrocio con DDT/fatture acquisto
3. Stima Ore → Tabella parametrica + Machine Learning da commesse chiuse
4. Calcolo Preventivo con margini differenziati
"""
import os
import uuid
import json
import logging

logger = logging.getLogger(__name__)

# ── AI imports (safe) ──
AI_AVAILABLE = False
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    AI_AVAILABLE = True
except ImportError:
    logger.warning("emergentintegrations not available — AI features disabled")


# ══════════════════════════════════════════════════════════════
#  1. TABELLA PARAMETRICA ORE / KG
# ══════════════════════════════════════════════════════════════

# ore_per_ton = ore necessarie per 1 tonnellata di materiale lavorato
TABELLA_ORE_KG = {
    "leggera": {
        "label": "Struttura Leggera",
        "desc": "Ringhiere, parapetti, pensiline leggere, piccola carpenteria",
        "ore_per_ton": 18,
        "range": (15, 22),
    },
    "media": {
        "label": "Struttura Media",
        "desc": "Tettoie, scale, soppalchi, portoni, cancelli industriali",
        "ore_per_ton": 28,
        "range": (24, 35),
    },
    "complessa": {
        "label": "Struttura Complessa",
        "desc": "Capannoni, ponti, strutture multi-piano, travi reticolari",
        "ore_per_ton": 40,
        "range": (35, 50),
    },
    "speciale": {
        "label": "Struttura Speciale",
        "desc": "EXC3/EXC4, strutture antisismiche, offshore, ad alta precisione",
        "ore_per_ton": 30,
        "range": (25, 40),
    },
}


# ══════════════════════════════════════════════════════════════
#  2. PESO MATERIALI — Tabella profili standard
# ══════════════════════════════════════════════════════════════

# Peso in kg/metro per profili comuni
PESO_PROFILI_KG_M = {
    "IPE 100": 8.1, "IPE 120": 10.4, "IPE 140": 12.9, "IPE 160": 15.8,
    "IPE 180": 18.8, "IPE 200": 22.4, "IPE 220": 26.2, "IPE 240": 30.7,
    "IPE 270": 36.1, "IPE 300": 42.2, "IPE 330": 49.1, "IPE 360": 57.1,
    "IPE 400": 66.3, "IPE 450": 77.6, "IPE 500": 90.7, "IPE 550": 106.0,
    "IPE 600": 122.0,
    "HEA 100": 16.7, "HEA 120": 19.9, "HEA 140": 24.7, "HEA 160": 30.4,
    "HEA 180": 35.5, "HEA 200": 42.3, "HEA 220": 50.5, "HEA 240": 60.3,
    "HEA 260": 68.2, "HEA 280": 76.4, "HEA 300": 88.3, "HEA 320": 97.6,
    "HEA 340": 105.0, "HEA 360": 112.0, "HEA 400": 125.0,
    "HEB 100": 20.4, "HEB 120": 26.7, "HEB 140": 33.7, "HEB 160": 42.6,
    "HEB 180": 51.2, "HEB 200": 61.3, "HEB 220": 71.5, "HEB 240": 83.2,
    "HEB 260": 93.0, "HEB 280": 103.0, "HEB 300": 117.0,
    "UPN 80": 8.64, "UPN 100": 10.6, "UPN 120": 13.4, "UPN 140": 16.0,
    "UPN 160": 18.8, "UPN 180": 22.0, "UPN 200": 25.3, "UPN 220": 29.4,
    "UPN 240": 33.2, "UPN 260": 37.9, "UPN 280": 41.8, "UPN 300": 46.2,
    "L 50x5": 3.77, "L 60x6": 5.42, "L 70x7": 7.38, "L 80x8": 9.63,
    "L 100x10": 15.0, "L 120x12": 21.6, "L 150x15": 33.8,
    "TUBO 40x40x3": 3.45, "TUBO 50x50x3": 4.39, "TUBO 60x60x3": 5.33,
    "TUBO 80x80x4": 9.22, "TUBO 100x100x4": 11.7, "TUBO 100x100x5": 14.4,
    "TUBO 120x120x5": 17.5, "TUBO 150x150x5": 22.3, "TUBO 200x200x6": 34.6,
    "TUBO D60.3x3": 4.24, "TUBO D76.1x3.2": 5.74, "TUBO D88.9x3.2": 6.76,
    "TUBO D114.3x4": 10.9, "TUBO D139.7x5": 16.6, "TUBO D168.3x5": 20.1,
}


# ══════════════════════════════════════════════════════════════
#  3. ANALISI AI DISEGNO → MATERIALI
# ══════════════════════════════════════════════════════════════

DRAWING_MATERIALS_PROMPT = """Sei un ingegnere strutturale esperto in carpenteria metallica.

Analizza questo disegno tecnico e ESTRAI TUTTI i materiali strutturali presenti.

REGOLE IMPORTANTI:
- LEGGI LE QUOTE REALI dal disegno (scala indicata nel cartiglio). NON assumere lunghezze fisse.
- Distingui tra TRAVI (orizzontali, luci campata) e PILASTRI (verticali, altezza interpiano ~3-4m).
- Per i BULLONI, stima sempre il peso: M16 cl.8.8 ~0.5 kg/cad, M20 cl.8.8 ~0.8 kg/cad, M24 cl.8.8 ~1.3 kg/cad.
- Per le PIASTRE, calcola il peso dal volume: peso = lung_m * larg_m * spessore_m * 7850 kg/m3.

Per OGNI elemento trovato, riporta:
1. tipo: "profilo", "piastra", "lamiera", "tubo", "angolare", "bullone", "tirafondi", "altro"
2. profilo: Nome profilo esatto se applicabile (es. "IPE 200", "HEA 160", "UPN 120", "TUBO 100x100x4")
3. materiale: Tipo acciaio (es. "S275JR", "S355JR"). Se non leggibile: "S275JR"
4. lunghezza_mm: Lunghezza REALE dal disegno in mm (NON assumere 12000mm per tutti)
5. quantita: Numero pezzi
6. spessore_mm: Per piastre/lamiere, spessore in mm
7. larghezza_mm: Per piastre/lamiere, larghezza in mm
8. descrizione: Descrizione testuale (specificare se trave o pilastro)
9. peso_stimato_kg: Peso calcolato in kg (per bulloni: peso totale = peso_unitario * quantita)
10. diametro: Per bulloneria, diametro (es. "M16", "M20")
11. classe: Per bulloneria, classe resistenza (es. "8.8", "10.9")

RISPONDI SOLO con JSON valido:
{
    "titolo_disegno": "...",
    "tipologia_struttura": "leggera|media|complessa|speciale",
    "peso_totale_stimato_kg": 1234.5,
    "materiali": [
        {
            "tipo": "profilo",
            "profilo": "IPE 200",
            "materiale": "S275JR",
            "lunghezza_mm": 6000,
            "quantita": 4,
            "spessore_mm": null,
            "larghezza_mm": null,
            "descrizione": "Trave principale IPE 200 L=6m",
            "peso_stimato_kg": 537.6,
            "diametro": null,
            "classe": null
        }
    ],
    "note": "..."
}"""


async def analyze_drawing_materials(page_image_b64: str) -> dict:
    """Analyze a technical drawing to extract all structural materials."""
    if not AI_AVAILABLE:
        return {"errore": True, "note": "AI non disponibile"}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"errore": True, "note": "EMERGENT_LLM_KEY mancante"}

    chat = LlmChat(
        api_key=api_key,
        session_id=f"pred-{uuid.uuid4().hex[:8]}",
        system_message=DRAWING_MATERIALS_PROMPT,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text="Analizza questo disegno tecnico. Estrai tutti i materiali strutturali con profili, dimensioni, quantita e pesi. Restituisci JSON.",
        file_contents=[ImageContent(image_base64=page_image_b64)],
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
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Drawing materials AI analysis failed: {e}")
        return {"errore": True, "note": str(e), "materiali": []}


def calcola_peso_materiale(materiale: dict) -> float:
    """Calculate weight of a material entry using profile tables."""
    tipo = materiale.get("tipo", "")

    # Conto lavoro: always 0
    if tipo == "conto_lavoro" or materiale.get("conto_lavoro"):
        return 0.0

    # If AI already estimated and type is not calculable, trust it (but DON'T multiply by qty again if AI already included it)
    lunghezza_mm = materiale.get("lunghezza_mm", 0) or 0
    quantita = materiale.get("quantita", 1) or 1
    spessore_mm = materiale.get("spessore_mm", 0) or 0
    larghezza_mm = materiale.get("larghezza_mm", 0) or 0
    profilo = (materiale.get("profilo") or "").upper().strip()

    # Profili standard (IPE, HEA, HEB, UPN, tubo, etc.)
    if tipo in ("profilo", "tubo") and profilo:
        kg_m = PESO_PROFILI_KG_M.get(profilo, 0)
        if kg_m > 0 and lunghezza_mm > 0:
            return round(kg_m * (lunghezza_mm / 1000) * quantita, 1)

    # Piastre e lamiere (volume × densità acciaio)
    if tipo in ("piastra", "lamiera") and spessore_mm > 0 and larghezza_mm > 0 and lunghezza_mm > 0:
        volume_cm3 = (lunghezza_mm / 10) * (larghezza_mm / 10) * (spessore_mm / 10)
        peso_kg = volume_cm3 * 7.85 / 1000  # densita acciaio
        return round(peso_kg * quantita, 1)

    # Grigliato, grate, griglie — calcolo per superficie (kg/m²)
    if tipo in ("grigliato", "grata", "griglia"):
        l_m = lunghezza_mm / 1000
        w_m = (larghezza_mm or spessore_mm) / 1000
        if l_m > 0 and w_m > 0:
            peso_m2 = _peso_grigliato_per_maglia(profilo or materiale.get("descrizione", ""))
            return round(l_m * w_m * quantita * peso_m2, 1)

    # Fallback from AI estimate
    return round((materiale.get("peso_stimato_kg", 0) or 0), 1)


# Tabella pesi grigliato elettrosaldato (kg/m²) per tipo maglia
PESO_GRIGLIATO_KG_M2 = {
    "30x100/20x2": 12.5,
    "34x38/25x2": 19.8,
    "63x132/25x2": 15.3,
    "34x38/30x3": 29.6,
    "34x100/25x2": 16.8,
}
PESO_GRIGLIATO_DEFAULT = 16.0


def _peso_grigliato_per_maglia(testo: str) -> float:
    """Trova il peso kg/m² corrispondente alla maglia nel testo."""
    if not testo:
        return PESO_GRIGLIATO_DEFAULT
    t = testo.lower().replace(" ", "")
    for key, val in PESO_GRIGLIATO_KG_M2.items():
        if key.replace(" ", "") in t:
            return val
    return PESO_GRIGLIATO_DEFAULT


# ══════════════════════════════════════════════════════════════
#  4. MOTORE PREZZI STORICI
# ══════════════════════════════════════════════════════════════

async def calcola_prezzi_storici(user_id: str, db_instance) -> dict:
    """
    Calcola i prezzi medi per kg basati sugli ultimi DDT e fatture acquisto.
    Returns: { "S275JR": 1.45, "S355JR": 1.62, "bulloneria": 3.50, "default": 1.50 }
    """
    prezzi = {}
    conteggi = {}

    # 1. From purchase invoices (fatture_ricevute)
    fatture = await db_instance.invoices.find(
        {"user_id": user_id, "document_type": "fattura_acquisto"},
        {"_id": 0, "lines": 1, "issue_date": 1}
    ).sort("issue_date", -1).limit(50).to_list(50)

    for f in fatture:
        for line in (f.get("lines") or []):
            desc = (line.get("description") or "").upper()
            price = float(line.get("unit_price", 0) or 0)
            qty = float(line.get("quantity", 0) or 0)
            if price <= 0 or qty <= 0:
                continue

            # Try to identify material type from description
            mat_type = "default"
            if "S355" in desc:
                mat_type = "S355JR"
            elif "S275" in desc or "S235" in desc:
                mat_type = "S275JR"
            elif "INOX" in desc or "AISI" in desc:
                mat_type = "INOX"
            elif "BULLON" in desc or "VITE" in desc or "DADO" in desc:
                mat_type = "bulloneria"
            elif "ZINC" in desc:
                mat_type = "zincatura_kg"
            elif "VERN" in desc:
                mat_type = "verniciatura_kg"

            prezzi.setdefault(mat_type, 0)
            conteggi.setdefault(mat_type, 0)
            prezzi[mat_type] += price
            conteggi[mat_type] += 1

    # 2. From DDT (if they have price info in lines)
    ddts = await db_instance.ddt_documents.find(
        {"user_id": user_id, "ddt_type": {"$in": ["acquisto", "rientro_conto_lavoro"]}},
        {"_id": 0, "lines": 1}
    ).sort("created_at", -1).limit(50).to_list(50)

    for d in ddts:
        for line in (d.get("lines") or []):
            desc = (line.get("description") or "").upper()
            price = float(line.get("unit_price", 0) or 0)
            if price <= 0:
                continue

            mat_type = "default"
            if "S355" in desc:
                mat_type = "S355JR"
            elif "S275" in desc:
                mat_type = "S275JR"

            prezzi.setdefault(mat_type, 0)
            conteggi.setdefault(mat_type, 0)
            prezzi[mat_type] += price
            conteggi[mat_type] += 1

    # Calculate averages
    result = {}
    for key in prezzi:
        if conteggi[key] > 0:
            result[key] = round(prezzi[key] / conteggi[key], 2)

    # Defaults if no historical data
    if "S275JR" not in result:
        result["S275JR"] = 1.35
    if "S355JR" not in result:
        result["S355JR"] = 1.55
    if "bulloneria" not in result:
        result["bulloneria"] = 3.50
    if "default" not in result:
        result["default"] = 1.45
    if "zincatura_kg" not in result:
        result["zincatura_kg"] = 0.80
    if "verniciatura_kg" not in result:
        result["verniciatura_kg"] = 0.60

    return result


# ══════════════════════════════════════════════════════════════
#  5. ML — STIMA ORE DA COMMESSE CHIUSE
# ══════════════════════════════════════════════════════════════

async def ml_stima_ore(user_id: str, peso_totale_kg: float, tipologia: str, db_instance) -> dict:
    """
    Machine Learning semplice: confronta con commesse chiuse per affinare la stima.
    Usa regressione lineare su peso → ore effettive.
    Include anche stima EUR/kg come metodo alternativo (es. 1.05 EUR/kg montaggio).
    Returns: { "ore_parametriche": X, "ore_ml": Y, "ore_suggerite": Z, "confidence": "alta|media|bassa", "campioni": N }
    """
    # 1. Stima parametrica (ore/tonnellata)
    params = TABELLA_ORE_KG.get(tipologia, TABELLA_ORE_KG["media"])
    peso_ton = peso_totale_kg / 1000
    ore_parametriche = round(peso_ton * params["ore_per_ton"], 1)

    # 1b. Stima alternativa EUR/kg (metodo diffuso in carpenteria)
    # Costo montaggio ~1.05 EUR/kg include officina+montaggio
    COSTO_MONTAGGIO_EUR_KG = {
        "semplice": 0.85,
        "media": 1.00,
        "complessa": 1.20,
        "speciale": 1.05,  # Antisismico: piu saldature ma pesi standardizzati
    }
    eur_kg = COSTO_MONTAGGIO_EUR_KG.get(tipologia, 1.05)
    costo_totale_montaggio = peso_totale_kg * eur_kg
    # Recupera costo orario company
    company = await db_instance.company_costs.find_one(
        {"user_id": user_id}, {"_id": 0, "costo_orario_pieno": 1}
    )
    costo_orario = (company or {}).get("costo_orario_pieno", 35.0)
    ore_eur_kg = round(costo_totale_montaggio / costo_orario, 1) if costo_orario else ore_parametriche

    # 2. Recupera dati storici dalle commesse chiuse
    commesse_chiuse = await db_instance.commesse.find(
        {"user_id": user_id, "stato": {"$in": ["chiuso", "fatturato"]}},
        {"_id": 0, "commessa_id": 1, "value": 1, "peso_totale_kg": 1, "ore_preventivate": 1}
    ).to_list(200)

    # Fetch actual hours from diario_produzione for each
    campioni = []
    for c in commesse_chiuse:
        cid = c.get("commessa_id")
        if not cid:
            continue

        # Get real hours
        entries = await db_instance.diario_produzione.find(
            {"commessa_id": cid},
            {"_id": 0, "ore_totali": 1}
        ).to_list(500)

        ore_reali = sum(e.get("ore_totali", 0) for e in entries)
        if ore_reali <= 0:
            continue

        peso = c.get("peso_totale_kg", 0)
        if peso <= 0:
            # Try to estimate from value
            continue

        campioni.append({
            "peso_kg": peso,
            "ore_reali": ore_reali,
            "ore_per_ton": round(ore_reali / (peso / 1000), 1) if peso > 0 else 0,
        })

    n_campioni = len(campioni)

    if n_campioni < 3:
        # Not enough data for ML, use EUR/kg as primary, parametric as fallback
        ore_suggerite = ore_eur_kg  # Metodo EUR/kg piu affidabile del parametrico puro
        return {
            "ore_parametriche": ore_parametriche,
            "ore_eur_kg": ore_eur_kg,
            "eur_kg_montaggio": eur_kg,
            "ore_ml": None,
            "ore_suggerite": ore_suggerite,
            "confidence": "bassa",
            "campioni": n_campioni,
            "metodo": "eur_kg",
            "nota": f"Solo {n_campioni} commesse chiuse con dati. Usato metodo EUR/kg ({eur_kg} EUR/kg).",
        }

    # 3. Regressione lineare semplice: peso_kg → ore
    sum_x = sum(c["peso_kg"] for c in campioni)
    sum_y = sum(c["ore_reali"] for c in campioni)
    sum_xy = sum(c["peso_kg"] * c["ore_reali"] for c in campioni)
    sum_x2 = sum(c["peso_kg"] ** 2 for c in campioni)
    n = n_campioni

    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-10:
        # Perfect correlation or no variance
        ore_ml = ore_parametriche
    else:
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        ore_ml = round(max(slope * peso_totale_kg + intercept, 0), 1)

    # 4. R-squared for confidence
    mean_y = sum_y / n
    ss_tot = sum((c["ore_reali"] - mean_y) ** 2 for c in campioni)
    if ss_tot > 0 and abs(denom) > 1e-10:
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        ss_res = sum((c["ore_reali"] - (slope * c["peso_kg"] + intercept)) ** 2 for c in campioni)
        r_squared = 1 - ss_res / ss_tot
    else:
        r_squared = 0

    if r_squared > 0.7 and n_campioni >= 10:
        confidence = "alta"
    elif r_squared > 0.4 and n_campioni >= 5:
        confidence = "media"
    else:
        confidence = "bassa"

    # 5. Blend: ML weighted by confidence
    if confidence == "alta":
        ore_suggerite = round(ore_ml * 0.7 + ore_parametriche * 0.3, 1)
    elif confidence == "media":
        ore_suggerite = round(ore_ml * 0.5 + ore_parametriche * 0.5, 1)
    else:
        ore_suggerite = round(ore_ml * 0.3 + ore_parametriche * 0.7, 1)

    # Media ore/ton storica
    media_ore_ton = round(sum(c["ore_per_ton"] for c in campioni) / n, 1) if n > 0 else 0

    return {
        "ore_parametriche": ore_parametriche,
        "ore_eur_kg": ore_eur_kg,
        "eur_kg_montaggio": eur_kg,
        "ore_ml": ore_ml,
        "ore_suggerite": ore_suggerite,
        "confidence": confidence,
        "r_squared": round(r_squared, 3),
        "campioni": n_campioni,
        "media_ore_ton_storica": media_ore_ton,
        "metodo": "ml_regressione" if confidence != "bassa" else "blend_parametrico_ml",
    }


# ══════════════════════════════════════════════════════════════
#  6. CALCOLO PREVENTIVO PREDITTIVO
# ══════════════════════════════════════════════════════════════

def calcola_preventivo_predittivo(
    materiali: list,
    prezzi_storici: dict,
    ore_stimate: float,
    costo_orario: float,
    margine_materiali: float = 25,
    margine_manodopera: float = 30,
    margine_conto_lavoro: float = 20,
    costo_cl_stimato: float = 0,
) -> dict:
    """
    Calcola il preventivo predittivo completo con margini differenziati.
    """
    # 1. Costo materiali
    costo_materiali = 0
    righe_materiali = []

    for m in materiali:
        peso_kg = calcola_peso_materiale(m)
        mat_type = (m.get("materiale") or "").upper()
        prezzo_kg = prezzi_storici.get(mat_type, prezzi_storici.get("default", 1.45))

        # For bulloneria, use bulloneria price
        if m.get("tipo") in ("bullone", "tirafondi", "dado", "rondella"):
            prezzo_kg = prezzi_storici.get("bulloneria", 3.50)

        costo = round(peso_kg * prezzo_kg, 2)
        costo_materiali += costo

        righe_materiali.append({
            **m,
            "peso_calcolato_kg": peso_kg,
            "prezzo_unitario_kg": prezzo_kg,
            "costo_base": costo,
            "costo_con_margine": round(costo * (1 + margine_materiali / 100), 2),
        })

    # 2. Costo manodopera
    costo_manodopera = round(ore_stimate * costo_orario, 2)

    # 3. Costo conto lavoro (zincatura/verniciatura)
    if costo_cl_stimato <= 0:
        # Stima: 15% del costo materiali per zincatura/verniciatura
        peso_tot = sum(r.get("peso_calcolato_kg", 0) for r in righe_materiali)
        prezzo_zinc = prezzi_storici.get("zincatura_kg", 0.80)
        costo_cl_stimato = round(peso_tot * prezzo_zinc, 2)

    # 4. Totali con margini
    materiali_vendita = round(costo_materiali * (1 + margine_materiali / 100), 2)
    manodopera_vendita = round(costo_manodopera * (1 + margine_manodopera / 100), 2)
    cl_vendita = round(costo_cl_stimato * (1 + margine_conto_lavoro / 100), 2)

    totale_costo = round(costo_materiali + costo_manodopera + costo_cl_stimato, 2)
    totale_vendita = round(materiali_vendita + manodopera_vendita + cl_vendita, 2)
    margine_globale_pct = round(((totale_vendita - totale_costo) / totale_costo * 100), 1) if totale_costo > 0 else 0
    utile = round(totale_vendita - totale_costo, 2)

    return {
        "righe_materiali": righe_materiali,
        "riepilogo": {
            "costo_materiali": costo_materiali,
            "margine_materiali_pct": margine_materiali,
            "materiali_vendita": materiali_vendita,
            "costo_manodopera": costo_manodopera,
            "ore_stimate": ore_stimate,
            "costo_orario": costo_orario,
            "margine_manodopera_pct": margine_manodopera,
            "manodopera_vendita": manodopera_vendita,
            "costo_cl": costo_cl_stimato,
            "margine_cl_pct": margine_conto_lavoro,
            "cl_vendita": cl_vendita,
            "totale_costo": totale_costo,
            "totale_vendita": totale_vendita,
            "margine_globale_pct": margine_globale_pct,
            "utile_lordo": utile,
        },
    }
