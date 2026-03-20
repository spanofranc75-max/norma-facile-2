"""
SAL (Stato Avanzamento Lavori) e Acconti — Fatturazione progressiva.
Calcola il SAL dall'avanzamento reale dei Diari di Produzione.
Permette la generazione di fatture acconto basate sulla percentuale di avanzamento.

GET  /api/commesse/{cid}/sal           — Calcola SAL corrente
POST /api/commesse/{cid}/sal/acconto   — Crea fattura acconto da SAL
GET  /api/commesse/{cid}/sal/storico   — Storico SAL e acconti emessi
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/commesse", tags=["sal"])
logger = logging.getLogger(__name__)


class AccontoCreate(BaseModel):
    percentuale: float
    importo: Optional[float] = None
    note: Optional[str] = ""
    descrizione: Optional[str] = ""


async def _get_commessa(cid: str, uid: str):
    c = await db.commesse.find_one({"commessa_id": cid, "user_id": uid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Commessa non trovata")
    return c


@router.get("/{cid}/sal")
async def calcola_sal(cid: str, user: dict = Depends(get_current_user)):
    """
    Calcola lo Stato Avanzamento Lavori corrente basato su:
    - Ore lavorate (diario produzione) vs ore preventivate
    - Fasi produzione completate
    - Conto lavoro rientrati
    - Acconti gia emessi
    """
    commessa = await _get_commessa(cid, user["user_id"])
    admin_id = user.get("team_owner_id", user["user_id"]) if user.get("role") != "admin" else user["user_id"]

    # 1. Ore lavorate dal diario produzione
    diario = await db.diario_produzione.find(
        {"commessa_id": cid, "admin_id": admin_id}, {"_id": 0}
    ).to_list(1000)

    ore_lavorate = sum(e.get("ore_totali", e.get("ore", 0)) for e in diario)

    # Ore preventivate (from commessa or preventivo)
    ore_preventivate = commessa.get("ore_preventivate", 0)
    if not ore_preventivate:
        prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0, "ore_stimate": 1, "totals": 1})
            if prev:
                ore_preventivate = prev.get("ore_stimate", 0)

    avanzamento_ore = min(round((ore_lavorate / ore_preventivate * 100), 1) if ore_preventivate > 0 else 0, 100)

    # 2. Fasi produzione completate
    comm_ops = await db.commesse_ops.find_one({"commessa_id": cid}, {"_id": 0})
    fasi = (comm_ops or {}).get("fasi_produzione", []) if comm_ops else []
    # Also check commessa for fasi_produzione (backward compat)
    if not fasi:
        fasi = commessa.get("fasi_produzione", [])
    fasi_totali = len(fasi) if fasi else 1
    fasi_completate = len([f for f in fasi if f.get("stato") == "completata"])
    avanzamento_fasi = round((fasi_completate / fasi_totali * 100), 1) if fasi_totali > 0 else 0

    # 3. Conto lavoro status (check both commesse_ops and commesse collections)
    cl_items = (comm_ops or {}).get("conto_lavoro", []) if comm_ops else []
    if not cl_items:
        cl_items = commessa.get("conto_lavoro", [])
    cl_totali = len(cl_items)
    cl_rientrati = len([cl for cl in cl_items if cl.get("stato") in ("rientrato", "verificato")])
    avanzamento_cl = round((cl_rientrati / cl_totali * 100), 1) if cl_totali > 0 else 100

    # 4. SAL complessivo (media ponderata: ore 50%, fasi 30%, conto lavoro 20%)
    if cl_totali > 0:
        sal_percentuale = round(avanzamento_ore * 0.5 + avanzamento_fasi * 0.3 + avanzamento_cl * 0.2, 1)
    else:
        sal_percentuale = round(avanzamento_ore * 0.6 + avanzamento_fasi * 0.4, 1)

    sal_percentuale = min(sal_percentuale, 100)

    # 5. Importo commessa e calcolo valore SAL
    importo_commessa = commessa.get("importo_totale", 0) or commessa.get("valore", 0) or 0
    if not importo_commessa:
        prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0, "totals": 1})
            if prev:
                importo_commessa = (prev.get("totals") or {}).get("total_document", 0)

    valore_sal = round(importo_commessa * sal_percentuale / 100, 2)

    # 6. Acconti gia emessi
    acconti = await db.sal_acconti.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)

    totale_accontato = sum(a.get("importo", 0) for a in acconti)
    percentuale_accontata = round((totale_accontato / importo_commessa * 100), 1) if importo_commessa > 0 else 0

    residuo = round(valore_sal - totale_accontato, 2)

    return {
        "commessa_id": cid,
        "numero_commessa": commessa.get("numero", ""),
        "importo_commessa": importo_commessa,
        # Dettaglio avanzamento
        "ore_lavorate": round(ore_lavorate, 1),
        "ore_preventivate": ore_preventivate,
        "avanzamento_ore_pct": avanzamento_ore,
        "fasi_totali": fasi_totali,
        "fasi_completate": fasi_completate,
        "avanzamento_fasi_pct": avanzamento_fasi,
        "cl_totali": cl_totali,
        "cl_rientrati": cl_rientrati,
        "avanzamento_cl_pct": avanzamento_cl,
        # SAL complessivo
        "sal_percentuale": sal_percentuale,
        "valore_sal": valore_sal,
        # Acconti
        "acconti": acconti,
        "totale_accontato": totale_accontato,
        "percentuale_accontata": percentuale_accontata,
        "residuo_fatturabile": max(residuo, 0),
    }


@router.post("/{cid}/sal/acconto")
async def crea_acconto(cid: str, data: AccontoCreate, user: dict = Depends(get_current_user)):
    """Crea un acconto (fattura SAL) basato sulla percentuale di avanzamento."""
    commessa = await _get_commessa(cid, user["user_id"])

    if data.percentuale <= 0 or data.percentuale > 100:
        raise HTTPException(400, "Percentuale deve essere tra 0 e 100")

    importo_commessa = commessa.get("importo_totale", 0) or commessa.get("valore", 0) or 0
    if not importo_commessa:
        prev_id = commessa.get("preventivo_id") or (commessa.get("moduli") or {}).get("preventivo_id")
        if prev_id:
            prev = await db.preventivi.find_one({"preventivo_id": prev_id}, {"_id": 0, "totals": 1})
            if prev:
                importo_commessa = (prev.get("totals") or {}).get("total_document", 0)

    # Calculate amount
    importo = data.importo if data.importo else round(importo_commessa * data.percentuale / 100, 2)

    # Check we're not exceeding total
    existing = await db.sal_acconti.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "importo": 1}
    ).to_list(50)
    totale_precedente = sum(a.get("importo", 0) for a in existing)

    if totale_precedente + importo > importo_commessa * 1.05:
        raise HTTPException(
            400,
            f"L'importo totale degli acconti ({totale_precedente + importo:.2f}) "
            f"supererebbe il valore della commessa ({importo_commessa:.2f})"
        )

    now = datetime.now(timezone.utc)
    acconto_id = f"sal_{uuid.uuid4().hex[:10]}"
    numero_progressivo = len(existing) + 1

    acconto = {
        "acconto_id": acconto_id,
        "commessa_id": cid,
        "user_id": user["user_id"],
        "numero_progressivo": numero_progressivo,
        "percentuale": data.percentuale,
        "importo": importo,
        "importo_commessa": importo_commessa,
        "descrizione": data.descrizione or f"SAL n.{numero_progressivo} — {data.percentuale}%",
        "note": data.note or "",
        "stato": "da_fatturare",
        "fattura_id": None,
        "created_at": now.isoformat(),
    }

    await db.sal_acconti.insert_one(acconto)
    del acconto["_id"]

    return {
        "message": f"Acconto SAL n.{numero_progressivo} creato: {importo:.2f} EUR ({data.percentuale}%)",
        "acconto": acconto,
    }


@router.post("/{cid}/sal/acconto/{acconto_id}/fattura")
async def genera_fattura_da_acconto(cid: str, acconto_id: str, user: dict = Depends(get_current_user)):
    """Genera una fattura proforma/acconto dal SAL."""
    commessa = await _get_commessa(cid, user["user_id"])
    acconto = await db.sal_acconti.find_one(
        {"acconto_id": acconto_id, "commessa_id": cid}, {"_id": 0}
    )
    if not acconto:
        raise HTTPException(404, "Acconto non trovato")
    if acconto.get("fattura_id"):
        raise HTTPException(400, "Fattura gia generata per questo acconto")

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.invoices.count_documents({"user_id": user["user_id"]})
    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    invoice_number = f"FT-{year}-{count + 1:04d}"

    numero_commessa = commessa.get("numero", cid)
    desc_line = f"Acconto SAL n.{acconto.get('numero_progressivo', 1)} — Commessa {numero_commessa} ({acconto.get('percentuale', 0)}%)"

    invoice = {
        "invoice_id": invoice_id,
        "user_id": user["user_id"],
        "number": invoice_number,
        "type": "fattura",
        "document_type": "fattura",
        "client_id": commessa.get("client_id", ""),
        "client_name": commessa.get("client_name", ""),
        "issue_date": now.strftime("%Y-%m-%d"),
        "subject": f"Acconto SAL — {numero_commessa}",
        "lines": [{
            "description": desc_line,
            "quantity": 1,
            "unit_price": acconto["importo"],
            "vat_rate": "22",
            "unit": "a corpo",
            "sconto_1": 0,
            "sconto_2": 0,
        }],
        "totals": {
            "subtotal": acconto["importo"],
            "vat_amount": round(acconto["importo"] * 0.22, 2),
            "total_document": round(acconto["importo"] * 1.22, 2),
            "line_count": 1,
        },
        "notes": acconto.get("note", ""),
        "status": "bozza",
        "riferimento_commessa": cid,
        "riferimento_sal": acconto_id,
        "created_at": now,
        "updated_at": now,
    }

    await db.invoices.insert_one(invoice)

    # Link invoice to acconto
    await db.sal_acconti.update_one(
        {"acconto_id": acconto_id},
        {"$set": {"stato": "fatturato", "fattura_id": invoice_id, "fattura_numero": invoice_number}}
    )

    return {
        "message": f"Fattura {invoice_number} generata da SAL — {acconto['importo']:.2f} EUR",
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
    }


@router.get("/{cid}/sal/storico")
async def storico_sal(cid: str, user: dict = Depends(get_current_user)):
    """Storico completo SAL e acconti per la commessa."""
    await _get_commessa(cid, user["user_id"])
    acconti = await db.sal_acconti.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)

    return {"acconti": acconti, "total": len(acconti)}
