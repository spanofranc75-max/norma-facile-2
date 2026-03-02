"""Cost Control — Mock Invoice Data & Cost Assignment.

Provides mock purchase invoices for UI development and real cost assignment to commesse.
When the Fatture in Cloud integration is live, the mock data can be replaced with real data.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/costs", tags=["costs"])
logger = logging.getLogger(__name__)

COST_ENTRIES = "project_costs"


# ── Models ───────────────────────────────────────────────────────

class CostAssignment(BaseModel):
    target_type: str  # "commessa" | "magazzino" | "generale"
    target_id: Optional[str] = None
    category: str = "materiali"  # materiali, lavorazioni_esterne, consumabili, trasporti
    amount: Optional[float] = None
    righe_selezionate: Optional[List[int]] = None
    note: Optional[str] = ""


# ── Mock Data Generator ─────────────────────────────────────────

def _generate_mock_invoices(user_id: str):
    """Generate realistic mock purchase invoices for UI development."""
    now = datetime.now(timezone.utc)
    return [
        {
            "invoice_id": "mock_inv_001",
            "fornitore": "Acciaierie Venete S.p.A.",
            "fornitore_piva": "IT01234567890",
            "numero": "FV-2026/0234",
            "data": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
            "totale": 4500.00,
            "imponibile": 3688.52,
            "iva": 811.48,
            "status": "da_processare",
            "linee": [
                {"idx": 0, "descrizione": "Travi HEA 200 S275JR — 6m (x4)", "quantita": 4, "unita": "pz", "prezzo_unitario": 520.00, "importo": 2080.00},
                {"idx": 1, "descrizione": "Piatti 200x10 S275JR — 6m (x6)", "quantita": 6, "unita": "pz", "prezzo_unitario": 145.00, "importo": 870.00},
                {"idx": 2, "descrizione": "Tubolari 100x100x4 — 6m (x3)", "quantita": 3, "unita": "pz", "prezzo_unitario": 246.17, "importo": 738.52},
            ],
            "is_mock": True,
        },
        {
            "invoice_id": "mock_inv_002",
            "fornitore": "Ferramenta Rossi Srl",
            "fornitore_piva": "IT09876543210",
            "numero": "FT-412/2026",
            "data": now.strftime("%Y-%m-%d"),
            "totale": 186.50,
            "imponibile": 152.87,
            "iva": 33.63,
            "status": "da_processare",
            "linee": [
                {"idx": 0, "descrizione": "Dischi taglio 230mm (x20)", "quantita": 20, "unita": "pz", "prezzo_unitario": 3.80, "importo": 76.00},
                {"idx": 1, "descrizione": "Guanti anticalore TIG (x5 paia)", "quantita": 5, "unita": "paia", "prezzo_unitario": 12.50, "importo": 62.50},
                {"idx": 2, "descrizione": "Occhiali protettivi EN166 (x3)", "quantita": 3, "unita": "pz", "prezzo_unitario": 4.79, "importo": 14.37},
            ],
            "is_mock": True,
        },
        {
            "invoice_id": "mock_inv_003",
            "fornitore": "Zincatura Nord Srl",
            "fornitore_piva": "IT11223344556",
            "numero": "26/0089",
            "data": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            "totale": 1220.00,
            "imponibile": 1000.00,
            "iva": 220.00,
            "status": "da_processare",
            "linee": [
                {"idx": 0, "descrizione": "Zincatura a caldo carpenteria — 850kg", "quantita": 850, "unita": "kg", "prezzo_unitario": 0.95, "importo": 807.50},
                {"idx": 1, "descrizione": "Sabbiatura SA 2.5 pre-zincatura", "quantita": 1, "unita": "corpo", "prezzo_unitario": 192.50, "importo": 192.50},
            ],
            "is_mock": True,
        },
        {
            "invoice_id": "mock_inv_004",
            "fornitore": "ServiceSaldatura Srl",
            "fornitore_piva": "IT55443322110",
            "numero": "FS-2026/078",
            "data": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            "totale": 312.00,
            "imponibile": 255.74,
            "iva": 56.26,
            "status": "da_processare",
            "linee": [
                {"idx": 0, "descrizione": "Filo SG2 1.0mm EN440 Bobina 15kg — Lotto B442", "quantita": 2, "unita": "bobina", "prezzo_unitario": 89.00, "importo": 178.00},
                {"idx": 1, "descrizione": "Gas Argon+CO2 82/18 bombola 50lt", "quantita": 1, "unita": "bombola", "prezzo_unitario": 77.74, "importo": 77.74},
            ],
            "is_mock": True,
        },
        {
            "invoice_id": "mock_inv_005",
            "fornitore": "Trasporti Bianchi Snc",
            "fornitore_piva": "IT66778899001",
            "numero": "TRS-2026-0156",
            "data": (now - timedelta(days=4)).strftime("%Y-%m-%d"),
            "totale": 280.00,
            "imponibile": 229.51,
            "iva": 50.49,
            "status": "da_processare",
            "linee": [
                {"idx": 0, "descrizione": "Trasporto cantiere Milano — andata", "quantita": 1, "unita": "viaggio", "prezzo_unitario": 120.00, "importo": 120.00},
                {"idx": 1, "descrizione": "Trasporto cantiere Milano — ritorno", "quantita": 1, "unita": "viaggio", "prezzo_unitario": 109.51, "importo": 109.51},
            ],
            "is_mock": True,
        },
    ]


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/invoices/pending")
async def get_pending_invoices(user: dict = Depends(get_current_user)):
    """Get pending (unprocessed) real invoices from fatture_ricevute."""
    uid = user["user_id"]

    # Real unprocessed invoices from fatture_ricevute
    real = await db.fatture_ricevute.find(
        {"user_id": uid, "imputazione": {"$exists": False}},
        {"_id": 0, "xml_raw": 0},
    ).sort("created_at", -1).to_list(200)

    real_invoices = []
    for fr in real:
        real_invoices.append({
            "invoice_id": fr.get("fr_id", ""),
            "fornitore": fr.get("fornitore_nome", ""),
            "fornitore_piva": fr.get("fornitore_piva", ""),
            "numero": fr.get("numero_documento", ""),
            "data": fr.get("data_documento", ""),
            "totale": fr.get("totale_documento", 0),
            "imponibile": fr.get("imponibile", 0),
            "iva": fr.get("imposta", 0),
            "status": "da_processare",
            "linee": [
                {"idx": i, "descrizione": l.get("descrizione", ""), "quantita": l.get("quantita", 0),
                 "unita": l.get("unita_misura", "pz"), "prezzo_unitario": l.get("prezzo_unitario", 0),
                 "importo": l.get("importo", 0)}
                for i, l in enumerate(fr.get("linee", []))
            ],
            "is_mock": False,
        })

    return {
        "invoices": real_invoices,
        "total": len(real_invoices),
        "real_count": len(real_invoices),
        "mock_count": 0,
    }


@router.get("/invoices/processed")
async def get_processed_invoices(user: dict = Depends(get_current_user)):
    """Get already processed (assigned) cost entries."""
    uid = user["user_id"]
    entries = await db[COST_ENTRIES].find(
        {"user_id": uid},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    return {"entries": entries, "total": len(entries)}


@router.post("/invoices/{invoice_id}/assign")
async def assign_invoice_cost(invoice_id: str, data: CostAssignment, user: dict = Depends(get_current_user)):
    """Assign costs from an invoice to a commessa, magazzino, or spese generali."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)

    # Find the invoice (real or mock)
    source_invoice = None
    is_mock = invoice_id.startswith("mock_inv_")

    if is_mock:
        mock_list = _generate_mock_invoices(uid)
        source_invoice = next((inv for inv in mock_list if inv["invoice_id"] == invoice_id), None)
    else:
        fr = await db.fatture_ricevute.find_one(
            {"fr_id": invoice_id, "user_id": uid}, {"_id": 0, "xml_raw": 0}
        )
        if fr:
            source_invoice = {
                "invoice_id": fr.get("fr_id", ""),
                "fornitore": fr.get("fornitore_nome", ""),
                "numero": fr.get("numero_documento", ""),
                "totale": fr.get("totale_documento", 0),
                "linee": [
                    {"idx": i, "descrizione": l.get("descrizione", ""), "quantita": l.get("quantita", 0),
                     "prezzo_unitario": l.get("prezzo_unitario", 0), "importo": l.get("importo", 0)}
                    for i, l in enumerate(fr.get("linee", []))
                ],
            }

    if not source_invoice:
        raise HTTPException(404, "Fattura non trovata")

    # Calculate amount from selected lines or use provided amount
    linee = source_invoice.get("linee", [])
    if data.righe_selezionate:
        selected = [linee[i] for i in data.righe_selezionate if i < len(linee)]
    else:
        selected = linee

    amount = data.amount or sum(abs(l.get("importo", 0)) for l in selected)

    # Build cost entry
    cost_entry = {
        "cost_id": f"cost_{uuid.uuid4().hex[:10]}",
        "user_id": uid,
        "source_invoice_id": invoice_id,
        "source_invoice_numero": source_invoice.get("numero", ""),
        "fornitore": source_invoice.get("fornitore", ""),
        "target_type": data.target_type,
        "target_id": data.target_id,
        "target_name": "",
        "category": data.category,
        "importo": round(amount, 2),
        "note": data.note or "",
        "righe": [{
            "descrizione": l.get("descrizione", ""),
            "quantita": l.get("quantita", 0),
            "prezzo_unitario": l.get("prezzo_unitario", 0),
            "importo": l.get("importo", 0),
        } for l in selected],
        "is_mock": is_mock,
        "created_at": now,
    }

    # If assigned to a commessa, update that commessa's costi_reali
    if data.target_type == "commessa" and data.target_id:
        commessa = await db.commesse.find_one(
            {"commessa_id": data.target_id, "user_id": uid},
            {"_id": 0, "commessa_id": 1, "numero": 1},
        )
        if not commessa:
            raise HTTPException(404, "Commessa non trovata")

        cost_entry["target_name"] = commessa.get("numero", "")

        # Push cost to commessa
        await db.commesse.update_one(
            {"commessa_id": data.target_id},
            {
                "$push": {"costi_reali": {
                    "cost_id": cost_entry["cost_id"],
                    "tipo": data.category,
                    "descrizione": f"Fatt. {source_invoice.get('numero', '')} — {source_invoice.get('fornitore', '')}",
                    "fornitore": source_invoice.get("fornitore", ""),
                    "importo": round(amount, 2),
                    "data": now.isoformat(),
                    "fr_id": invoice_id,
                    "note": data.note or "",
                    "is_mock": is_mock,
                }},
                "$set": {"updated_at": now},
            },
        )

    # Save cost entry
    await db[COST_ENTRIES].insert_one(cost_entry)

    # If real invoice, mark as processed
    if not is_mock:
        await db.fatture_ricevute.update_one(
            {"fr_id": invoice_id, "user_id": uid},
            {"$set": {
                "imputazione": {
                    "destinazione": data.target_type,
                    "commessa_id": data.target_id,
                    "importo": round(amount, 2),
                    "data": now.isoformat(),
                    "category": data.category,
                },
                "status": "registrata",
                "updated_at": now,
            }},
        )

    category_labels = {
        "materiali": "Materiale Ferroso",
        "lavorazioni_esterne": "Lavorazione Esterna",
        "consumabili": "Consumabili",
        "trasporti": "Trasporti",
    }

    return {
        "message": f"{round(amount, 2)}€ assegnati a {data.target_type}: {cost_entry.get('target_name', data.target_type)}",
        "cost_id": cost_entry["cost_id"],
        "importo": round(amount, 2),
        "target_type": data.target_type,
        "target_name": cost_entry.get("target_name", ""),
        "category": category_labels.get(data.category, data.category),
    }


@router.get("/commessa/{commessa_id}")
async def get_commessa_costs(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get all costs assigned to a specific commessa, with financial analysis."""
    uid = user["user_id"]

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "value": 1, "costi_reali": 1, "title": 1},
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    costi = commessa.get("costi_reali", [])
    valore_preventivo = float(commessa.get("value", 0) or 0)

    # Group by category
    by_category = {}
    totale_costi = 0
    for c in costi:
        cat = c.get("tipo", "materiali")
        if cat not in by_category:
            by_category[cat] = {"totale": 0, "voci": []}
        importo = float(c.get("importo", 0) or 0)
        by_category[cat]["totale"] += importo
        by_category[cat]["voci"].append(c)
        totale_costi += importo

    margine = valore_preventivo - totale_costi
    margine_pct = (margine / valore_preventivo * 100) if valore_preventivo > 0 else 0

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "title": commessa.get("title", ""),
        "valore_preventivo": round(valore_preventivo, 2),
        "totale_costi": round(totale_costi, 2),
        "margine": round(margine, 2),
        "margine_percentuale": round(margine_pct, 1),
        "costi_per_categoria": by_category,
        "num_voci": len(costi),
    }


@router.get("/commesse-search")
async def search_commesse_for_costs(q: str = "", user: dict = Depends(get_current_user)):
    """Search commesse for the cost assignment dropdown."""
    uid = user["user_id"]
    filt = {"user_id": uid}
    if q:
        filt["$or"] = [
            {"numero": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
            {"client_name": {"$regex": q, "$options": "i"}},
        ]
    items = await db.commesse.find(filt, {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1, "value": 1, "status": 1}).sort("created_at", -1).to_list(20)
    return {"commesse": items}
