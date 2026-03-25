"""
Preventivatore Predittivo — Route API.

POST /api/preventivatore/analyze-drawing          — Analizza disegno e estrae materiali
POST /api/preventivatore/calcola                   — Calcola preventivo predittivo
POST /api/preventivatore/genera-preventivo          — Genera preventivo ufficiale
POST /api/preventivatore/accetta/{preventivo_id}    — Accetta e genera commessa
GET  /api/preventivatore/prezzi-storici             — Prezzi medi storici
GET  /api/preventivatore/tabella-ore                — Tabella parametrica ore/kg
"""
import os
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user, tenant_match
from core.rate_limiter import limiter
from services.preventivatore_predittivo import (
    analyze_drawing_materials,
    calcola_peso_materiale,
    calcola_prezzi_storici,
    ml_stima_ore,
    calcola_preventivo_predittivo,
    TABELLA_ORE_KG,
)

router = APIRouter(prefix="/preventivatore", tags=["preventivatore"])
logger = logging.getLogger(__name__)


# ── Models ──

class CalcolaRequest(BaseModel):
    materiali: list = []
    tipologia_struttura: str = "media"
    margine_materiali: float = 25
    margine_manodopera: float = 30
    margine_conto_lavoro: float = 20
    ore_override: Optional[float] = None
    costo_cl_override: Optional[float] = None
    applica_calibrazione: bool = False
    peso_kg_target: Optional[float] = None
    classe_antisismica_target: Optional[int] = None
    nodi_target: Optional[int] = None


class GeneraPreventivoRequest(BaseModel):
    client_id: Optional[str] = None
    subject: str = ""
    calcolo: dict = {}
    stima_ore: dict = {}
    normativa: str = "EN_1090"
    classe_esecuzione: str = "EXC2"
    giorni_consegna: Optional[int] = 30
    note: Optional[str] = ""
    numero_disegno: Optional[str] = ""
    doc_id: Optional[str] = None


class AnalizzaRigheRequest(BaseModel):
    lines: list = []


# ── Endpoints ──

@router.post("/analizza-righe")
@limiter.limit("10/minute")
async def analizza_righe_preventivo(
    request: Request,
    data: AnalizzaRigheRequest,
    user: dict = Depends(get_current_user),
):
    """Analizza le righe di un preventivo usando AI per estrarre profili, pesi e struttura.
    
    Prende le descrizioni testuali e usa GPT-4o per estrarre materiali strutturati
    con pesi calcolati usando la tabella profili standard.
    """
    if not data.lines:
        raise HTTPException(400, "Nessuna riga da analizzare")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(500, "EMERGENT_LLM_KEY non configurata")

    from services.preventivatore_predittivo import AI_AVAILABLE, PESO_PROFILI_KG_M
    if not AI_AVAILABLE:
        raise HTTPException(500, "AI non disponibile")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import json as _json

    # Build prompt with line data (include ore_stimate if user provided them)
    lines_text = "\n".join(
        f"- Riga {i+1}: \"{ln.get('description', '')}\", qty={ln.get('quantity', 1)}, prezzo_unitario={ln.get('unit_price', 0)} EUR, ore_stimate_utente={ln.get('ore_stimate', 0)}"
        for i, ln in enumerate(data.lines)
    )

    system = """Sei un ingegnere strutturista esperto in carpenteria metallica italiana.
Analizzi le righe di un preventivo e per ciascuna estrai dati strutturati.

CAMPI DA ESTRARRE per ogni riga:
- tipo: "profilo"|"piastra"|"grigliato"|"bulloneria"|"manodopera"|"zincatura"|"conto_lavoro"|"accessori"|"trasporto"|"altro"
- profilo: profilo standard (es. "IPE 200", "HEA 160", "TUBO 100x100x4") o maglia grigliato (es. "63x132/25x2"). Null se non applicabile.
- materiale: tipo acciaio ("S275JR", "S355JR"). Default "S275JR".
- lunghezza_mm: lunghezza in millimetri. Per grigliato = dimensione L.
- larghezza_mm: per piastre/grigliato = dimensione H o W.
- quantita: numero pezzi dalla riga.
- peso_stimato_kg: peso TOTALE per questa riga. Per grigliato usa kg/m2, NON densita acciaio pieno.
- spessore_mm: per piastre/lamiere. Null altrimenti.
- conto_lavoro: true se materiale fornito dal cliente, false altrimenti.
- ore_stimate: solo per manodopera — ore di lavoro stimate.
- tipologia_struttura: "leggera"|"media"|"complessa"|"speciale" (valutazione globale)

REGOLE CRITICHE:

1. GRIGLIATO/GRATE/GRIGLIA:
   - Tipo = "grigliato" per grate, grigliato elettrosaldato, pannelli grigliato, specchiature in grigliato
   - Dimensioni in formato "LxxxxHxxxx", "L xxxx H xxxx", "Lxxxx×Hxxxx", "xxxxmm × xxxxmm", "xxxx x xxxx": estrarre come lunghezza_mm e larghezza_mm
   - Se ci sono PIU specchiature/pannelli con dimensioni diverse nella stessa riga (es. "L2230xH2150, L4600xH2150, L5500xH2150"), crea UNA SOLA entry dove lunghezza_mm e larghezza_mm rappresentano la SOMMA delle aree. Calcola area_totale_m2 e peso = area * kg_m2.
   - Pesi per m2: maglia 63x132/25x2 = 15.3 kg/m2, maglia 34x38/25x2 = 19.8 kg/m2, maglia 30x100/20x2 = 12.5 kg/m2, default = 16 kg/m2
   - NON usare la densita dell'acciaio pieno (7850 kg/m3) per il grigliato!
   - Formula: peso = somma(L_mm/1000 * H_mm/1000) * quantita * peso_kg_m2

2. CONTO LAVORO:
   - Se la descrizione contiene "conto lavoro", "fornito dal cliente", "a cura di", "fornitura cliente", "fornite in conto lavoro":
   - Tipo = "conto_lavoro", peso_stimato_kg = 0, conto_lavoro = true
   - Questi materiali NON hanno costo di acquisto (sono forniti dal cliente)

3. MANODOPERA:
   - Se la riga contiene "manodopera", "lavorazione", "montaggio", "posa in opera":
   - Tipo = "manodopera", peso_stimato_kg = 0
   - ore_stimate = quantita se l'unita di misura e ore, altrimenti stima ore = importo_totale / 35 (tariffa media)

4. PESI GENERALI:
   - Per profili standard (IPE, HEA, HEB, UPN): usa peso_lineare_kg_m * lunghezza_m * quantita
   - Per acciaio lavorato generico: stima ~2.50-4.00 EUR/kg
   - Per zincatura/trasporto: peso_stimato_kg = 0

Rispondi SOLO con JSON valido:
{
  "tipologia_struttura": "media",
  "materiali": [
    {
      "riga_originale": 1,
      "tipo": "grigliato",
      "profilo": "63x132/25x2",
      "materiale": "S275JR",
      "lunghezza_mm": 1892,
      "larghezza_mm": 6100,
      "quantita": 5,
      "spessore_mm": null,
      "peso_stimato_kg": 883.5,
      "conto_lavoro": false,
      "ore_stimate": null,
      "descrizione": "Pannelli grigliato 63x132/25x2"
    }
  ],
  "peso_totale_stimato_kg": 883.5,
  "note_analisi": "..."
}"""

    chat = LlmChat(
        api_key=api_key,
        session_id=f"analisi-righe-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("openai", "gpt-4o")

    user_msg = UserMessage(
        text=f"Analizza queste righe di preventivo ed estrai materiali con pesi stimati:\n\n{lines_text}\n\nRestituisci JSON.",
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
        result = _json.loads(cleaned)
    except Exception as e:
        logger.error(f"AI righe analysis failed: {e}")
        raise HTTPException(500, f"Errore analisi AI: {str(e)}")

    # Refine weights using the profile table
    materiali = result.get("materiali", [])
    peso_totale = 0
    _CL_KEYWORDS = ("conto lavoro", "fornito dal cliente", "a cura di", "fornitura cliente",
                     "fornite in conto lavoro")

    for m in materiali:
        desc_lower = (m.get("descrizione") or m.get("description") or "").lower()

        # Server-side conto lavoro detection (non dipendere solo dall'AI)
        if not m.get("conto_lavoro") and m.get("tipo") != "conto_lavoro":
            if any(kw in desc_lower for kw in _CL_KEYWORDS):
                m["conto_lavoro"] = True
                m["tipo"] = "conto_lavoro"

        # Conto lavoro: always 0 weight and 0 cost
        if m.get("conto_lavoro") or m.get("tipo") == "conto_lavoro":
            m["peso_calcolato_kg"] = 0
            m["conto_lavoro"] = True
            continue

        peso = calcola_peso_materiale(m)
        if peso > 0:
            m["peso_calcolato_kg"] = peso
        else:
            m["peso_calcolato_kg"] = m.get("peso_stimato_kg", 0) or 0
        peso_totale += m["peso_calcolato_kg"]

    result["peso_totale_calcolato_kg"] = round(peso_totale, 1)
    result["materiali"] = materiali

    # Sum user-provided ore_stimate from original lines
    ore_utente = sum(float(ln.get("ore_stimate", 0) or 0) for ln in data.lines)
    # Sum AI-extracted ore_stimate from materials
    ore_ai = sum(float(m.get("ore_stimate", 0) or 0) for m in materiali)
    result["ore_stimate_utente"] = round(ore_utente, 1)
    result["ore_stimate_ai"] = round(ore_ai, 1)
    result["ore_stimate_totali"] = round(max(ore_utente, ore_ai), 1)

    return result


@router.get("/tabella-ore")
async def get_tabella_ore(user: dict = Depends(get_current_user)):
    """Tabella parametrica ore/kg per tipologia struttura."""
    return {"tabella": TABELLA_ORE_KG}


@router.get("/prezzi-storici")
async def get_prezzi_storici(user: dict = Depends(get_current_user)):
    """Prezzi medi storici da DDT e fatture acquisto."""
    prezzi = await calcola_prezzi_storici(user["user_id"], db)
    return {"prezzi": prezzi}


@router.post("/analyze-drawing")
@limiter.limit("10/minute")
async def analyze_drawing(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Analizza un disegno tecnico caricato e estrae tutti i materiali."""
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "File troppo grande (max 20MB)")

    content_type = file.content_type or ""
    filename = file.filename or ""
    is_pdf = "pdf" in content_type or filename.lower().endswith(".pdf")
    is_image = any(x in content_type for x in ["image/png", "image/jpeg", "image/jpg", "image/webp"])

    if not is_pdf and not is_image:
        raise HTTPException(400, "Solo PDF o immagini supportate")

    if is_image:
        image_b64 = base64.b64encode(content).decode("utf-8")
        analysis = await analyze_drawing_materials(image_b64)
    else:
        # PDF — convert first page to image
        from services.smistatore_intelligente import split_pdf_to_pages, pdf_page_to_image_b64
        pages = split_pdf_to_pages(content)
        if not pages:
            raise HTTPException(400, "PDF vuoto o non leggibile")

        # Analyze first 3 pages
        all_materials = []
        titolo = ""
        tipologia = "media"
        peso_totale = 0

        for page_pdf in pages[:3]:
            page_b64 = pdf_page_to_image_b64(page_pdf, dpi=200)
            if not page_b64:
                continue
            page_analysis = await analyze_drawing_materials(page_b64)
            if page_analysis.get("errore"):
                continue
            if not titolo and page_analysis.get("titolo_disegno"):
                titolo = page_analysis["titolo_disegno"]
            if page_analysis.get("tipologia_struttura"):
                tipologia = page_analysis["tipologia_struttura"]
            peso_totale += page_analysis.get("peso_totale_stimato_kg", 0)
            all_materials.extend(page_analysis.get("materiali", []))

        analysis = {
            "titolo_disegno": titolo,
            "tipologia_struttura": tipologia,
            "peso_totale_stimato_kg": peso_totale,
            "materiali": all_materials,
        }

    if analysis.get("errore"):
        raise HTTPException(400, f"Errore analisi: {analysis.get('note', 'Non leggibile')}")

    # Calcola pesi precisi
    materiali = analysis.get("materiali", [])
    peso_totale = 0
    for m in materiali:
        peso = calcola_peso_materiale(m)
        m["peso_calcolato_kg"] = peso
        peso_totale += peso

    analysis["peso_totale_calcolato_kg"] = round(peso_totale, 1)
    analysis["materiali"] = materiali

    # Save analysis temporarily
    doc_id = f"pred_{uuid.uuid4().hex[:10]}"
    await db.preventivatore_analyses.insert_one({
        "doc_id": doc_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "filename": filename,
        "analysis": analysis,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    analysis["doc_id"] = doc_id
    return analysis


@router.post("/calcola")
async def calcola(data: CalcolaRequest, user: dict = Depends(get_current_user)):
    """Calcola il preventivo predittivo con margini differenziati."""
    # Calculate total weight — from materials or from manual peso_kg_target
    peso_totale = sum(calcola_peso_materiale(m) for m in data.materiali)

    # Se nessun materiale ma peso target fornito, crea materiale sintetico
    materiali_calc = list(data.materiali)
    if peso_totale <= 0 and data.peso_kg_target and data.peso_kg_target > 0:
        peso_totale = data.peso_kg_target
        materiali_calc = [{
            "tipo": "profilo",
            "profilo": f"Carpenteria {data.tipologia_struttura}",
            "descrizione": f"Stima manuale — {data.peso_kg_target} kg",
            "materiale": "S275JR",
            "quantita": 1,
            "peso_stimato_kg": data.peso_kg_target,
            "peso_calcolato_kg": data.peso_kg_target,
        }]

    # Get historical prices
    prezzi = await calcola_prezzi_storici(user["user_id"], db)

    # Get hour estimation (ML + parametric)
    stima_ore = await ml_stima_ore(user["user_id"], peso_totale, data.tipologia_struttura, db)

    ore_da_usare = data.ore_override if data.ore_override else stima_ore["ore_suggerite"]

    # Get company hourly cost
    cost_doc = await db.company_costs.find_one({"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    costo_orario = (cost_doc or {}).get("costo_orario_pieno", 35)

    # Calculate full quote
    calcolo = calcola_preventivo_predittivo(
        materiali=materiali_calc,
        prezzi_storici=prezzi,
        ore_stimate=ore_da_usare,
        costo_orario=costo_orario,
        margine_materiali=data.margine_materiali,
        margine_manodopera=data.margine_manodopera,
        margine_conto_lavoro=data.margine_conto_lavoro,
        costo_cl_stimato=data.costo_cl_override or 0,
    )

    # Apply ML calibration if requested
    calibrazione = None
    if data.applica_calibrazione:
        from services.ml_calibrazione import applica_calibrazione as ml_calibra
        target_params = {
            "peso_kg": data.peso_kg_target or peso_totale,
            "classe_antisismica": data.classe_antisismica_target or 0,
            "nodi_strutturali": data.nodi_target or 0,
            "tipologia": data.tipologia_struttura,
        }
        riepilogo = calcolo.get("riepilogo", {})
        stima_raw = {
            "ore_totali": ore_da_usare,
            "costo_materiali": riepilogo.get("costo_materiali", 0),
            "costo_manodopera": riepilogo.get("costo_manodopera", 0),
            "costo_cl": riepilogo.get("costo_cl", 0),
        }
        calibrazione = await ml_calibra(db, user["user_id"], stima_raw, target_params)

    return {
        "peso_totale_kg": round(peso_totale, 1),
        "tipologia": data.tipologia_struttura,
        "prezzi_storici": prezzi,
        "stima_ore": stima_ore,
        "ore_utilizzate": ore_da_usare,
        "costo_orario": costo_orario,
        "calcolo": calcolo,
        "calibrazione": calibrazione,
    }


@router.post("/genera-preventivo")
async def genera_preventivo(data: GeneraPreventivoRequest, user: dict = Depends(get_current_user)):
    """Genera un preventivo ufficiale dal calcolo predittivo."""
    calcolo = data.calcolo
    riepilogo = calcolo.get("riepilogo", {})
    righe_materiali = calcolo.get("righe_materiali", [])

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.preventivi.count_documents({"user_id": user["user_id"], "tenant_id": tenant_match(user)})
    prev_id = f"prev_{uuid.uuid4().hex[:12]}"
    prev_number = f"PV-{year}-{count + 1:04d}"

    # Build preventivo lines
    lines = []

    # Materiali
    for r in righe_materiali:
        desc = r.get("descrizione") or f"{r.get('profilo', '')} {r.get('tipo', '')}"
        peso = r.get("peso_calcolato_kg", 0)
        costo = r.get("costo_con_margine", 0)
        lines.append({
            "line_id": f"l_{uuid.uuid4().hex[:8]}",
            "description": f"{desc} ({peso} kg)",
            "quantity": r.get("quantita", 1),
            "unit": "pz",
            "unit_price": round(costo / max(r.get("quantita", 1), 1), 2),
            "sconto_1": 0,
            "sconto_2": 0,
            "vat_rate": "22",
            "line_total": costo,
            "prezzo_netto": round(costo / max(r.get("quantita", 1), 1), 2),
        })

    # Manodopera
    ore = riepilogo.get("ore_stimate", 0)
    mano_vendita = riepilogo.get("manodopera_vendita", 0)
    if ore > 0:
        lines.append({
            "line_id": f"l_{uuid.uuid4().hex[:8]}",
            "description": f"Manodopera specializzata ({ore}h)",
            "quantity": ore,
            "unit": "ore",
            "unit_price": round(mano_vendita / max(ore, 1), 2),
            "sconto_1": 0,
            "sconto_2": 0,
            "vat_rate": "22",
            "line_total": mano_vendita,
            "prezzo_netto": round(mano_vendita / max(ore, 1), 2),
        })

    # Conto Lavoro
    cl_vendita = riepilogo.get("cl_vendita", 0)
    if cl_vendita > 0:
        lines.append({
            "line_id": f"l_{uuid.uuid4().hex[:8]}",
            "description": "Trattamenti superficiali (zincatura/verniciatura)",
            "quantity": 1,
            "unit": "a corpo",
            "unit_price": cl_vendita,
            "sconto_1": 0,
            "sconto_2": 0,
            "vat_rate": "22",
            "line_total": cl_vendita,
            "prezzo_netto": cl_vendita,
        })

    subtotal = sum(ln.get("line_total", 0) for ln in lines)
    vat = round(subtotal * 0.22, 2)

    # Get client info
    client_name = ""
    if data.client_id:
        cl = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0, "business_name": 1, "name": 1})
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")

    preventivo = {
        "preventivo_id": prev_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "number": prev_number,
        "client_id": data.client_id or "",
        "client_name": client_name,
        "subject": data.subject or "Preventivo Predittivo AI",
        "status": "bozza",
        "lines": lines,
        "totals": {
            "subtotal": round(subtotal, 2),
            "sconto_globale_pct": 0,
            "sconto_val": 0,
            "imponibile": round(subtotal, 2),
            "total_vat": vat,
            "total": round(subtotal + vat, 2),
            "total_document": round(subtotal + vat, 2),
            "acconto": 0,
            "da_pagare": round(subtotal + vat, 2),
            "line_count": len(lines),
        },
        "notes": data.note or "",
        "normativa": data.normativa,
        "classe_esecuzione": data.classe_esecuzione,
        "numero_disegno": data.numero_disegno or "",
        "giorni_consegna": data.giorni_consegna,
        "validity_days": 30,
        # Predictive metadata
        "predittivo": True,
        "predittivo_data": {
            "riepilogo": riepilogo,
            "stima_ore": data.stima_ore,
            "doc_id": data.doc_id,
        },
        "ore_stimate": data.stima_ore.get("ore_suggerite", ore),
        "created_at": now,
        "updated_at": now,
    }

    await db.preventivi.insert_one(preventivo)
    preventivo.pop("_id", None)

    return {
        "message": f"Preventivo {prev_number} generato con {len(lines)} righe",
        "preventivo_id": prev_id,
        "number": prev_number,
        "totale": round(subtotal + vat, 2),
    }


@router.post("/accetta/{preventivo_id}")
async def accetta_e_genera_commessa(preventivo_id: str, user: dict = Depends(get_current_user)):
    """
    Accetta un preventivo predittivo e genera automaticamente la Commessa
    con materiali, ore stimate e budget pre-compilati.
    """
    prev = await db.preventivi.find_one(
        {"preventivo_id": preventivo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    if prev.get("status") == "accettato":
        raise HTTPException(400, "Preventivo gia accettato")

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.commesse.count_documents({"user_id": user["user_id"], "tenant_id": tenant_match(user)})
    commessa_id = f"comm_{uuid.uuid4().hex[:12]}"
    commessa_number = f"C-{year}-{count + 1:04d}"

    pred_data = prev.get("predittivo_data", {})
    riepilogo = pred_data.get("riepilogo", {})
    stima_ore = pred_data.get("stima_ore", {})
    righe = riepilogo.get("righe_materiali", []) if riepilogo else []

    # Build voci di lavoro (material list / RdP)
    approvvigionamento_richieste = []
    if righe or prev.get("lines"):
        rdp_id = f"rdp_{uuid.uuid4().hex[:10]}"
        rdp_righe = []
        for line in prev.get("lines", []):
            if "Manodopera" in (line.get("description") or ""):
                continue
            if "Trattamenti" in (line.get("description") or ""):
                continue
            rdp_righe.append({
                "descrizione": line.get("description", ""),
                "quantita": line.get("quantity", 1),
                "unita_misura": line.get("unit", "pz"),
                "richiede_cert_31": True,
                "note": "",
            })

        if rdp_righe:
            approvvigionamento_richieste.append({
                "rdp_id": rdp_id,
                "fornitore_nome": "Da assegnare",
                "fornitore_id": "",
                "righe": rdp_righe,
                "importo_totale": riepilogo.get("materiali_vendita", 0),
                "note": f"Generata automaticamente da Preventivo Predittivo {prev.get('number', '')}",
                "stato": "bozza",
                "data_creazione": now.isoformat(),
            })

    commessa = {
        "commessa_id": commessa_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "numero": commessa_number,
        "title": prev.get("subject", "Commessa da Preventivo AI"),
        "client_id": prev.get("client_id", ""),
        "client_name": prev.get("client_name", ""),
        "description": f"Commessa generata automaticamente da Preventivo Predittivo {prev.get('number', '')}",
        "riferimento": prev.get("number", ""),
        "value": (prev.get("totals") or {}).get("total_document", 0),
        "importo_totale": (prev.get("totals") or {}).get("total_document", 0),
        "priority": "media",
        "status": "lavorazione",
        "stato": "firmato",
        "normativa_tipo": prev.get("normativa", "EN_1090"),
        "classe_exc": prev.get("classe_esecuzione", "EXC2"),
        "cantiere": {},
        "notes": prev.get("notes", ""),
        # Pre-compiled data
        "ore_preventivate": stima_ore.get("ore_suggerite", prev.get("ore_stimate", 0)),
        "peso_totale_kg": sum(calcola_peso_materiale(m) for m in (righe or [])) if righe else 0,
        "budget": {
            "materiali": riepilogo.get("materiali_vendita", 0),
            "manodopera": riepilogo.get("manodopera_vendita", 0),
            "conto_lavoro": riepilogo.get("cl_vendita", 0),
            "totale": riepilogo.get("totale_vendita", 0),
        },
        # Modules
        "moduli": {
            "rilievo_id": None,
            "distinta_id": None,
            "preventivo_id": preventivo_id,
            "perizia_id": None,
            "fatture_ids": [],
            "ddt_ids": [],
            "fpc_project_id": None,
            "certificazione_id": None,
        },
        "approvvigionamento": {
            "richieste": approvvigionamento_richieste,
            "ordini": [],
            "arrivi": [],
        },
        "fasi_produzione": [],
        "conto_lavoro": [],
        "eventi": [
            {
                "tipo": "COMMESSA_CREATA",
                "data": now.isoformat(),
                "operatore_id": user["user_id"],
                "operatore_nome": user.get("name", user.get("email", "")),
                "note": f"Generata automaticamente da Preventivo Predittivo {prev.get('number', '')}",
                "payload": {"source": "preventivatore_predittivo", "preventivo_id": preventivo_id},
            },
            {
                "tipo": "PREVENTIVO_ACCETTATO",
                "data": now.isoformat(),
                "operatore_id": user["user_id"],
                "operatore_nome": user.get("name", user.get("email", "")),
                "note": f"Preventivo {prev.get('number', '')} accettato — generazione automatica commessa",
            },
        ],
        "created_at": now,
        "updated_at": now,
    }

    await db.commesse.insert_one(commessa)

    # Update preventivo status
    await db.preventivi.update_one(
        {"preventivo_id": preventivo_id},
        {"$set": {
            "status": "accettato",
            "commessa_id": commessa_id,
            "commessa_number": commessa_number,
            "updated_at": now,
        }}
    )

    return {
        "message": f"Commessa {commessa_number} generata automaticamente con budget, ore e distinta materiali",
        "commessa_id": commessa_id,
        "commessa_number": commessa_number,
        "ore_preventivate": commessa["ore_preventivate"],
        "budget": commessa["budget"],
        "rdp_create": len(approvvigionamento_richieste),
    }



# ── Confronto AI vs Manuale ──

class ConfrontaRequest(BaseModel):
    preventivo_ai_id: str
    preventivo_manuale_id: str


@router.post("/confronta")
async def confronta_preventivi(data: ConfrontaRequest, user: dict = Depends(get_current_user)):
    """
    Confronta un preventivo generato dall'AI con uno manuale.
    Calcola delta per voce, scostamento percentuale, e confidence score.
    """
    prev_ai = await db.preventivi.find_one(
        {"preventivo_id": data.preventivo_ai_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not prev_ai:
        raise HTTPException(404, "Preventivo AI non trovato")

    prev_man = await db.preventivi.find_one(
        {"preventivo_id": data.preventivo_manuale_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not prev_man:
        raise HTTPException(404, "Preventivo manuale non trovato")

    # Extract totals
    ai_totals = prev_ai.get("totals", {})
    man_totals = prev_man.get("totals", {})
    ai_sub = ai_totals.get("subtotal", 0) or ai_totals.get("total", 0)
    man_sub = man_totals.get("subtotal", 0) or man_totals.get("total", 0)

    # Extract predittivo data if available
    ai_pred = prev_ai.get("predittivo_data", {})
    ai_riepilogo = ai_pred.get("riepilogo", {})
    ai_stima_ore = ai_pred.get("stima_ore", {})

    man_dettaglio = prev_man.get("dettaglio_costi", {})

    # Category comparison
    ai_mat = ai_riepilogo.get("materiali_vendita", 0)
    ai_mano = ai_riepilogo.get("manodopera_vendita", 0)
    ai_cl = ai_riepilogo.get("cl_vendita", 0)
    ai_ore = ai_riepilogo.get("ore_stimate", 0) or prev_ai.get("ore_stimate", 0)

    man_mat = man_dettaglio.get("materiali_vendita", 0)
    man_mano = man_dettaglio.get("manodopera_vendita", 0)
    man_cl = man_dettaglio.get("cl_vendita", 0)
    man_ore = prev_man.get("ore_stimate", 0)

    # Helper: delta and pct
    def delta_pct(ai_val, man_val):
        d = round(ai_val - man_val, 2)
        pct = round((d / man_val * 100), 1) if man_val else 0
        return {"ai": round(ai_val, 2), "manuale": round(man_val, 2), "delta": d, "delta_pct": pct}

    confronto_categorie = {
        "materiali": delta_pct(ai_mat, man_mat),
        "manodopera": delta_pct(ai_mano, man_mano),
        "conto_lavoro": delta_pct(ai_cl, man_cl),
        "subtotale": delta_pct(ai_sub, man_sub),
    }

    # Ore comparison
    confronto_ore = delta_pct(ai_ore, man_ore)

    # Peso comparison
    ai_peso = prev_ai.get("predittivo_data", {}).get("riepilogo", {}).get("peso_totale_calcolato_kg", 0)
    if not ai_peso:
        ai_peso = sum(
            line.get("peso_calcolato_kg", 0)
            for line in ai_riepilogo.get("righe_materiali", [])
        ) if ai_riepilogo.get("righe_materiali") else 0
    man_peso = prev_man.get("peso_totale_kg", 0)
    confronto_peso = delta_pct(ai_peso, man_peso)

    # Line-by-line comparison (category-based matching)
    ai_lines = prev_ai.get("lines", [])
    man_lines = prev_man.get("lines", [])

    def categorize_line(desc):
        d = (desc or "").upper()
        if "IPE" in d: return "IPE"
        if "HEA" in d or "HEB" in d: return "HEA"
        if "PIASTR" in d or "PIASTRA" in d or "LAMIER" in d: return "PIASTRA"
        if "BULLON" in d or "M16" in d or "M20" in d or "DADO" in d: return "BULLONI"
        if "MANODOPERA" in d or "ORE" in d: return "MANODOPERA"
        if "ZINCAT" in d or "VERNICIT" in d or "TRATTAMENT" in d: return "TRATTAMENTI"
        if "TRASPORT" in d: return "TRASPORTO"
        return "ALTRO"

    confronto_righe = []
    used_man_ids = set()

    for ai_l in ai_lines:
        ai_desc = ai_l.get("description", "")
        ai_cat = categorize_line(ai_desc)
        best_match = None
        best_score = 0

        for idx, man_l in enumerate(man_lines):
            if idx in used_man_ids:
                continue
            man_desc = man_l.get("description", "")
            man_cat = categorize_line(man_desc)
            score = 0
            if ai_cat == man_cat:
                score = 10
            # Additional keyword overlap
            ai_words = set(ai_desc.upper().replace("(", " ").replace(")", " ").split())
            man_words = set(man_desc.upper().replace("(", " ").replace(")", " ").split())
            score += len(ai_words & man_words)
            if score > best_score:
                best_score = score
                best_match = (idx, man_l)

        if best_match and best_score >= 3:
            used_man_ids.add(best_match[0])
            man_l = best_match[1]
        else:
            man_l = None

        ai_tot = ai_l.get("line_total", 0)
        man_tot = man_l.get("line_total", 0) if man_l else 0
        delta = round(ai_tot - man_tot, 2)
        delta_p = round((delta / man_tot * 100), 1) if man_tot else 0

        confronto_righe.append({
            "voce_ai": ai_desc,
            "voce_manuale": man_l.get("description", "-") if man_l else "-",
            "importo_ai": round(ai_tot, 2),
            "importo_manuale": round(man_tot, 2),
            "delta": delta,
            "delta_pct": delta_p,
        })

    # Append unmatched manual lines
    for idx, man_l in enumerate(man_lines):
        if idx not in used_man_ids:
            confronto_righe.append({
                "voce_ai": "- (non rilevata dall'AI)",
                "voce_manuale": man_l.get("description", ""),
                "importo_ai": 0,
                "importo_manuale": round(man_l.get("line_total", 0), 2),
                "delta": round(-man_l.get("line_total", 0), 2),
                "delta_pct": -100.0,
            })

    # Confidence score (0-100)
    scostamento_sub = abs(ai_sub - man_sub) / man_sub * 100 if man_sub else 100
    if scostamento_sub < 5:
        confidence = 95
        giudizio = "Eccellente"
    elif scostamento_sub < 10:
        confidence = 85
        giudizio = "Buono"
    elif scostamento_sub < 20:
        confidence = 70
        giudizio = "Accettabile"
    elif scostamento_sub < 30:
        confidence = 55
        giudizio = "Da verificare"
    else:
        confidence = max(100 - scostamento_sub, 10)
        giudizio = "Significativo scostamento"

    # Insight generation
    insights = []
    if confronto_peso["delta"] > 0:
        insights.append(f"L'AI ha stimato {confronto_peso['delta']:.0f} kg in piu ({confronto_peso['delta_pct']:+.1f}%). Possibile che il preventivo manuale abbia sottostimato alcuni elementi.")
    elif confronto_peso["delta"] < 0:
        insights.append(f"L'AI ha stimato {abs(confronto_peso['delta']):.0f} kg in meno ({confronto_peso['delta_pct']:+.1f}%). Verificare se ci sono elementi non visibili nel disegno.")

    if confronto_ore["delta"] > 0:
        insights.append(f"L'AI stima {confronto_ore['delta']:.0f} ore in piu. Per una struttura Classe Antisismica 3 con 5 nodi, potrebbe essere piu realistico.")
    elif confronto_ore["delta"] < 0:
        insights.append(f"Il preventivo manuale prevede {abs(confronto_ore['delta']):.0f} ore in piu. L'esperienza dell'operatore potrebbe includere fattori non rilevabili dal disegno.")

    for cat_name, cat_data in confronto_categorie.items():
        if cat_name == "subtotale":
            continue
        if abs(cat_data["delta_pct"]) > 15:
            insights.append(f"Scostamento significativo su '{cat_name}': {cat_data['delta_pct']:+.1f}%")

    return {
        "titolo": f"Confronto: {prev_ai.get('number', '?')} (AI) vs {prev_man.get('number', '?')} (Manuale)",
        "progetto": prev_man.get("subject") or prev_ai.get("subject", ""),
        "confidence_score": confidence,
        "giudizio": giudizio,
        "scostamento_totale_pct": round(confronto_categorie["subtotale"]["delta_pct"], 1),
        "confronto_categorie": confronto_categorie,
        "confronto_ore": confronto_ore,
        "confronto_peso": confronto_peso,
        "confronto_righe": confronto_righe,
        "insights": insights,
        "preventivo_ai": {
            "id": prev_ai["preventivo_id"],
            "number": prev_ai.get("number", ""),
            "totale": ai_sub,
        },
        "preventivo_manuale": {
            "id": prev_man["preventivo_id"],
            "number": prev_man.get("number", ""),
            "totale": man_sub,
        },
    }
