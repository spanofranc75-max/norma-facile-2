"""
Preventivatore Predittivo — Route API.

POST /api/preventivatore/analyze-drawing          — Analizza disegno e estrae materiali
POST /api/preventivatore/calcola                   — Calcola preventivo predittivo
POST /api/preventivatore/genera-preventivo          — Genera preventivo ufficiale
POST /api/preventivatore/accetta/{preventivo_id}    — Accetta e genera commessa
GET  /api/preventivatore/prezzi-storici             — Prezzi medi storici
GET  /api/preventivatore/tabella-ore                — Tabella parametrica ore/kg
"""
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user
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


# ── Endpoints ──

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
async def analyze_drawing(
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
        "user_id": user["user_id"],
        "filename": filename,
        "analysis": analysis,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    analysis["doc_id"] = doc_id
    return analysis


@router.post("/calcola")
async def calcola(data: CalcolaRequest, user: dict = Depends(get_current_user)):
    """Calcola il preventivo predittivo con margini differenziati."""
    # Calculate total weight
    peso_totale = sum(calcola_peso_materiale(m) for m in data.materiali)

    # Get historical prices
    prezzi = await calcola_prezzi_storici(user["user_id"], db)

    # Get hour estimation (ML + parametric)
    stima_ore = await ml_stima_ore(user["user_id"], peso_totale, data.tipologia_struttura, db)

    ore_da_usare = data.ore_override if data.ore_override else stima_ore["ore_suggerite"]

    # Get company hourly cost
    cost_doc = await db.company_costs.find_one({"user_id": user["user_id"]}, {"_id": 0})
    costo_orario = (cost_doc or {}).get("costo_orario_pieno", 35)

    # Calculate full quote
    calcolo = calcola_preventivo_predittivo(
        materiali=data.materiali,
        prezzi_storici=prezzi,
        ore_stimate=ore_da_usare,
        costo_orario=costo_orario,
        margine_materiali=data.margine_materiali,
        margine_manodopera=data.margine_manodopera,
        margine_conto_lavoro=data.margine_conto_lavoro,
        costo_cl_stimato=data.costo_cl_override or 0,
    )

    return {
        "peso_totale_kg": round(peso_totale, 1),
        "tipologia": data.tipologia_struttura,
        "prezzi_storici": prezzi,
        "stima_ore": stima_ore,
        "ore_utilizzate": ore_da_usare,
        "costo_orario": costo_orario,
        "calcolo": calcolo,
    }


@router.post("/genera-preventivo")
async def genera_preventivo(data: GeneraPreventivoRequest, user: dict = Depends(get_current_user)):
    """Genera un preventivo ufficiale dal calcolo predittivo."""
    calcolo = data.calcolo
    riepilogo = calcolo.get("riepilogo", {})
    righe_materiali = calcolo.get("righe_materiali", [])

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.preventivi.count_documents({"user_id": user["user_id"]})
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
        "user_id": user["user_id"],
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
        {"preventivo_id": preventivo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    if prev.get("status") == "accettato":
        raise HTTPException(400, "Preventivo gia accettato")

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.commesse.count_documents({"user_id": user["user_id"]})
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
        "user_id": user["user_id"],
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
