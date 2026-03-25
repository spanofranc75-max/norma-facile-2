"""Consumable Batches (Fili, Gas, Elettrodi) — Smart ISO 3834 Traceability.

Manages welding consumables (wire, gas, electrodes) extracted from purchase invoices.
Auto-assigns consumables to compatible open commesse based on diameter/normativa rules.
"""
import uuid
import re
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/consumables", tags=["consumables"])
logger = logging.getLogger(__name__)

COLL = "consumable_batches"


# ── Models ───────────────────────────────────────────────────────

class ConsumableBatchCreate(BaseModel):
    tipo: str = "filo"  # filo, gas, elettrodo
    descrizione: str = ""
    lotto: str = ""
    fornitore: str = ""
    data_acquisto: Optional[str] = None
    diametro_mm: Optional[float] = None
    normativa_target: Optional[str] = None  # en_1090, en_13241, entrambe - None means auto-detect
    quantita: Optional[float] = None
    unita_misura: str = "kg"
    prezzo_unitario: Optional[float] = None
    fattura_id: Optional[str] = None
    note: Optional[str] = ""


class ConsumableBatchUpdate(BaseModel):
    stato: Optional[str] = None  # attivo, esaurito
    note: Optional[str] = None
    quantita: Optional[float] = None


# ── Keyword detection for consumable type ────────────────────────

KW_FILO = ["filo", "sg2", "sg3", "er70", "bobina", "rotolo", "wire"]
KW_GAS = ["gas", "argon", "co2", "miscela", "bombola", "argo"]
KW_ELETTRODO = ["elettrod", "bacchett", "tig rod", "7018", "6013"]

# Diameter patterns
DIAM_PATTERN = re.compile(r"(\d+[.,]\d+)\s*mm|diam[.\s]*(\d+[.,]\d+)|ø\s*(\d+[.,]\d+)", re.IGNORECASE)
DIAM_STANDALONE = re.compile(r"\b(0[.,][68]|1[.,][0246]|2[.,][04])\b")


def _detect_consumable_type(text: str) -> Optional[str]:
    """Detect consumable type from description text.
    Priority: elettrodo > filo > gas (bacchette TIG override ER70)
    """
    t = text.lower()
    # Check elettrodo first (bacchette TIG with ER70 are electrodes, not wire)
    if any(kw in t for kw in KW_ELETTRODO):
        return "elettrodo"
    if any(kw in t for kw in KW_FILO):
        return "filo"
    if any(kw in t for kw in KW_GAS):
        return "gas"
    return None


def _extract_diameter(text: str) -> Optional[float]:
    """Extract wire/electrode diameter in mm from text."""
    m = DIAM_PATTERN.search(text)
    if m:
        val = next(g for g in m.groups() if g is not None)
        return float(val.replace(",", "."))
    m2 = DIAM_STANDALONE.search(text)
    if m2:
        return float(m2.group(1).replace(",", "."))
    return None


def _extract_lotto(text: str) -> str:
    """Extract batch/lot number from text."""
    patterns = [
        re.compile(r"lotto?\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
        re.compile(r"batch\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
        re.compile(r"lot\s*[:\-]?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
    ]
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1).strip()
    return ""


def _determine_normativa_target(tipo: str, diametro: Optional[float]) -> str:
    """Determine normativa target based on type and diameter.
    
    Rules:
    - Gas -> entrambe (used everywhere)
    - Filo >= 1.0mm -> en_1090 (structural welding)
    - Filo 0.8mm -> en_13241 (gates/light work)
    - Elettrodo -> en_1090 (structural, typically)
    - Default -> entrambe
    """
    if tipo == "gas":
        return "entrambe"
    if tipo == "filo" and diametro:
        if diametro >= 1.0:
            return "en_1090"
        if diametro <= 0.8:
            return "en_13241"
    if tipo == "elettrodo":
        return "en_1090"
    return "entrambe"


# ── Smart Import: Analyze invoice lines ──────────────────────────

async def analyze_and_import_invoice_consumables(fattura: dict, user_id: str):
    """Analyze a purchase invoice's lines and auto-create consumable batches.
    Returns list of created batches.
    """
    created = []
    fornitore = fattura.get("fornitore_nome", "")
    data_doc = fattura.get("data_documento", "")
    fattura_id = fattura.get("fattura_id", "")

    for line in fattura.get("linee", []):
        desc = line.get("descrizione") or ""
        tipo = _detect_consumable_type(desc)
        if not tipo:
            continue

        diametro = _extract_diameter(desc)
        lotto = _extract_lotto(desc)
        normativa = _determine_normativa_target(tipo, diametro)

        batch = {
            "batch_id": f"cb_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "tipo": tipo,
            "descrizione": desc.strip(),
            "lotto": lotto,
            "fornitore": fornitore,
            "data_acquisto": data_doc,
            "diametro_mm": diametro,
            "normativa_target": normativa,
            "quantita": float(line.get("quantita", 0) or 0),
            "unita_misura": line.get("unita_misura", "kg"),
            "prezzo_unitario": float(line.get("prezzo_unitario", 0) or 0),
            "fattura_id": fattura_id,
            "fattura_numero": fattura.get("numero_documento", ""),
            "stato": "attivo",
            "note": "",
            "assegnazioni": [],  # List of commesse this batch is assigned to
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Avoid duplicates: same fattura + same line description
        existing = await db[COLL].find_one({
            "user_id": user_id,
            "fattura_id": fattura_id,
            "descrizione": batch["descrizione"],
        })
        if existing:
            continue

        await db[COLL].insert_one(batch)
        created.append(batch)
        logger.info(f"Consumable batch created: {tipo} {desc[:40]} -> {normativa}")

    # Auto-propagate to open commesse
    if created:
        await _auto_assign_to_commesse(created, user_id)

    return created


async def _auto_assign_to_commesse(batches: list, user_id: str):
    """Auto-assign consumable batches to compatible open commesse."""
    # Get all open commesse (in_produzione or lavorazione)
    open_commesse = await db.commesse.find(
        {
            "user_id": user_id,
            "status": {"$in": ["preventivo", "approvvigionamento", "lavorazione", "in_produzione"]},
        },
        {"_id": 0, "commessa_id": 1, "normativa_tipo": 1, "numero": 1},
    ).to_list(100)

    for batch in batches:
        target = batch["normativa_target"]
        compatible = []
        for c in open_commesse:
            norm = c.get("normativa_tipo", "")
            if target == "entrambe":
                compatible.append(c)
            elif target == "en_1090" and norm == "EN_1090":
                compatible.append(c)
            elif target == "en_13241" and norm == "EN_13241":
                compatible.append(c)

        if compatible:
            assignments = [
                {"commessa_id": c["commessa_id"], "numero": c.get("numero", ""), "auto": True}
                for c in compatible
            ]
            await db[COLL].update_one(
                {"batch_id": batch["batch_id"]},
                {"$set": {"assegnazioni": assignments}},
            )
            batch["assegnazioni"] = assignments
            logger.info(f"Batch {batch['batch_id']} auto-assigned to {len(assignments)} commesse")


# ── API Endpoints ────────────────────────────────────────────────

@router.get("/")
async def list_consumable_batches(
    stato: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List all consumable batches (optionally filtered by stato or tipo)."""
    filt = {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    if stato:
        filt["stato"] = stato
    if tipo:
        filt["tipo"] = tipo
    items = await db[COLL].find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items, "total": len(items)}


@router.get("/for-commessa/{commessa_id}")
async def get_consumables_for_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get consumable batches compatible with a specific commessa.
    Returns both auto-assigned and manually assignable batches.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "commessa_id": 1, "normativa_tipo": 1, "numero": 1},
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    norm = commessa.get("normativa_tipo", "")

    # Get all active batches
    all_batches = await db[COLL].find(
        {"user_id": uid, "tenant_id": tid, "stato": "attivo"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)

    # Split into assigned and available
    assigned = []
    available = []
    for b in all_batches:
        is_assigned = any(a["commessa_id"] == commessa_id for a in b.get("assegnazioni", []))
        is_compatible = (
            b["normativa_target"] == "entrambe"
            or (b["normativa_target"] == "en_1090" and norm == "EN_1090")
            or (b["normativa_target"] == "en_13241" and norm == "EN_13241")
            or not norm  # No normativa = accept all
        )
        if is_assigned:
            assigned.append(b)
        elif is_compatible:
            available.append(b)

    return {
        "assigned": assigned,
        "available": available,
        "commessa_normativa": norm,
    }


@router.post("/")
async def create_consumable_batch(data: ConsumableBatchCreate, user: dict = Depends(get_current_user)):
    """Manually create a consumable batch."""
    batch = {
        "batch_id": f"cb_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "tipo": data.tipo,
        "descrizione": data.descrizione,
        "lotto": data.lotto,
        "fornitore": data.fornitore,
        "data_acquisto": data.data_acquisto or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "diametro_mm": data.diametro_mm,
        "normativa_target": data.normativa_target or _determine_normativa_target(data.tipo, data.diametro_mm),
        "quantita": data.quantita,
        "unita_misura": data.unita_misura,
        "prezzo_unitario": data.prezzo_unitario,
        "fattura_id": data.fattura_id,
        "fattura_numero": "",
        "stato": "attivo",
        "note": data.note or "",
        "assegnazioni": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db[COLL].insert_one(batch)

    # Auto-assign
    await _auto_assign_to_commesse([batch], user["user_id"])
    # Re-fetch to get assignments
    updated = await db[COLL].find_one({"batch_id": batch["batch_id"]}, {"_id": 0})
    return updated


@router.put("/{batch_id}")
async def update_consumable_batch(batch_id: str, data: ConsumableBatchUpdate, user: dict = Depends(get_current_user)):
    """Update a consumable batch (stato, note, quantita)."""
    update_fields = {}
    if data.stato is not None:
        update_fields["stato"] = data.stato
    if data.note is not None:
        update_fields["note"] = data.note
    if data.quantita is not None:
        update_fields["quantita"] = data.quantita
    if not update_fields:
        raise HTTPException(400, "Nessun campo da aggiornare")
    result = await db[COLL].update_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"message": "Lotto aggiornato"}


@router.post("/{batch_id}/assign/{commessa_id}")
async def assign_batch_to_commessa(batch_id: str, commessa_id: str, user: dict = Depends(get_current_user)):
    """Manually assign a consumable batch to a commessa."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    batch = await db[COLL].find_one({"batch_id": batch_id, "user_id": uid, "tenant_id": tid})
    if not batch:
        raise HTTPException(404, "Lotto non trovato")
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "commessa_id": 1, "numero": 1},
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Check if already assigned
    assignments = batch.get("assegnazioni", [])
    if any(a["commessa_id"] == commessa_id for a in assignments):
        return {"message": "Lotto gia' assegnato a questa commessa"}

    assignments.append({
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "auto": False,
    })
    await db[COLL].update_one(
        {"batch_id": batch_id},
        {"$set": {"assegnazioni": assignments}},
    )
    return {"message": f"Lotto assegnato a commessa {commessa.get('numero', commessa_id)}"}


@router.delete("/{batch_id}/assign/{commessa_id}")
async def unassign_batch_from_commessa(batch_id: str, commessa_id: str, user: dict = Depends(get_current_user)):
    """Remove a consumable batch assignment from a commessa."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    result = await db[COLL].update_one(
        {"batch_id": batch_id, "user_id": uid, "tenant_id": tid},
        {"$pull": {"assegnazioni": {"commessa_id": commessa_id}}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"message": "Assegnazione rimossa"}


@router.delete("/{batch_id}")
async def delete_consumable_batch(batch_id: str, user: dict = Depends(get_current_user)):
    """Delete a consumable batch."""
    result = await db[COLL].delete_one({"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"message": "Lotto eliminato"}


@router.post("/analyze-invoice/{fattura_id}")
async def analyze_invoice_for_consumables(fattura_id: str, user: dict = Depends(get_current_user)):
    """Manually trigger consumable analysis for a specific invoice.
    
    Note: fattura_id parameter can be either fr_id or fattura_id field.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    # Try fr_id first (primary key), then fattura_id field
    fattura = await db.fatture_ricevute.find_one(
        {"fr_id": fattura_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0},
    )
    if not fattura:
        # Fallback: try fattura_id field
        fattura = await db.fatture_ricevute.find_one(
            {"fattura_id": fattura_id, "user_id": uid, "tenant_id": tid},
            {"_id": 0},
        )
    if not fattura:
        raise HTTPException(404, "Fattura non trovata")

    # Ensure fattura has fattura_id field set for consumable import
    if "fattura_id" not in fattura:
        fattura["fattura_id"] = fattura.get("fr_id", fattura_id)

    created = await analyze_and_import_invoice_consumables(fattura, uid)
    return {
        "message": f"Analisi completata: {len(created)} consumabili rilevati",
        "created": [{k: v for k, v in b.items() if k != "_id"} for b in created],
    }
