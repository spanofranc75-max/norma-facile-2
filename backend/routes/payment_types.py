"""Payment Types CRUD routes — Tipi Pagamento stile Invoicex."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid
import calendar
from datetime import datetime, timezone, timedelta, date
from core.security import get_current_user
from core.database import db
from models.payment_type import (
    PaymentTypeCreate, PaymentTypeUpdate, PaymentTypeResponse, PaymentTypeListResponse,
    SimulateRequest, SimulateResponse, SimulateDeadlineItem, QuotaItem,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment-types", tags=["payment-types"])

COLLECTION = "payment_types"

# Legacy flag → days mapping
LEGACY_FLAGS = {
    "immediato": 0, "gg_30": 30, "gg_60": 60, "gg_90": 90,
    "gg_120": 120, "gg_150": 150, "gg_180": 180, "gg_210": 210,
    "gg_240": 240, "gg_270": 270, "gg_300": 300, "gg_330": 330, "gg_360": 360,
}


def derive_quote_from_legacy(doc: dict) -> list:
    """Convert old boolean flags to quote list for backward compat."""
    days = sorted(d for flag, d in LEGACY_FLAGS.items() if doc.get(flag))
    if not days:
        return []
    share = round(100.0 / len(days), 2)
    return [{"giorni": d, "quota": share} for d in days]


def enrich_response(doc: dict) -> dict:
    """Ensure quote field is populated even for legacy data."""
    if not doc.get("quote"):
        doc["quote"] = derive_quote_from_legacy(doc)
    # Ensure new fields have defaults
    doc.setdefault("codice_fe", "")
    doc.setdefault("divisione_automatica", True)
    doc.setdefault("richiedi_giorno_scadenza", False)
    doc.setdefault("giorno_scadenza", None)
    return doc


@router.get("/", response_model=PaymentTypeListResponse)
async def get_payment_types(
    search: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if search:
        q["$or"] = [
            {"codice": {"$regex": search, "$options": "i"}},
            {"descrizione": {"$regex": search, "$options": "i"}},
        ]
    if tipo:
        q["tipo"] = tipo
    total = await db[COLLECTION].count_documents(q)
    items = await db[COLLECTION].find(q, {"_id": 0}).sort("codice", 1).to_list(200)
    enriched = [enrich_response(i) for i in items]
    return PaymentTypeListResponse(
        items=[PaymentTypeResponse(**i) for i in enriched], total=total
    )


@router.get("/{pt_id}", response_model=PaymentTypeResponse)
async def get_payment_type(pt_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Tipo pagamento non trovato")
    return PaymentTypeResponse(**enrich_response(doc))


@router.post("/", response_model=PaymentTypeResponse, status_code=201)
async def create_payment_type(
    data: PaymentTypeCreate, user: dict = Depends(get_current_user)
):
    dup = await db[COLLECTION].find_one(
        {"user_id": user["user_id"], "codice": data.codice}
    )
    if dup:
        raise HTTPException(400, f"Codice '{data.codice}' già esistente")
    pt_id = f"pt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "payment_type_id": pt_id,
        "user_id": user["user_id"],
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    # Convert QuotaItem objects to dicts for MongoDB
    if doc.get("quote"):
        doc["quote"] = [q if isinstance(q, dict) else q.model_dump() if hasattr(q, 'model_dump') else dict(q) for q in doc["quote"]]
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"payment_type_id": pt_id}, {"_id": 0})
    logger.info(f"Payment type created: {pt_id}")
    return PaymentTypeResponse(**enrich_response(created))


@router.put("/{pt_id}", response_model=PaymentTypeResponse)
async def update_payment_type(
    pt_id: str, data: PaymentTypeUpdate, user: dict = Depends(get_current_user)
):
    existing = await db[COLLECTION].find_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}
    )
    if not existing:
        raise HTTPException(404, "Tipo pagamento non trovato")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    # Convert QuotaItem objects to dicts for MongoDB
    if "quote" in update and update["quote"]:
        update["quote"] = [q if isinstance(q, dict) else q.model_dump() if hasattr(q, 'model_dump') else dict(q) for q in update["quote"]]
    update["updated_at"] = datetime.now(timezone.utc)
    await db[COLLECTION].update_one({"payment_type_id": pt_id}, {"$set": update})
    updated = await db[COLLECTION].find_one({"payment_type_id": pt_id}, {"_id": 0})
    return PaymentTypeResponse(**enrich_response(updated))


@router.delete("/{pt_id}")
async def delete_payment_type(pt_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Tipo pagamento non trovato")
    logger.info(f"Payment type deleted: {pt_id}")
    return {"message": "Tipo pagamento eliminato"}


@router.post("/{pt_id}/simulate", response_model=SimulateResponse)
async def simulate_deadlines(
    pt_id: str, req: SimulateRequest, user: dict = Depends(get_current_user)
):
    """Simulate payment deadlines given an invoice date and amount."""
    doc = await db[COLLECTION].find_one(
        {"payment_type_id": pt_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Tipo pagamento non trovato")

    enriched = enrich_response(doc)
    quote_list = enriched.get("quote", [])
    if not quote_list:
        return SimulateResponse(scadenze=[], totale_rate=0, importo_totale=0)

    try:
        invoice_date = date.fromisoformat(req.data_fattura)
    except ValueError:
        raise HTTPException(400, "Formato data non valido (YYYY-MM-DD)")

    fine_mese = enriched.get("fine_mese", False)
    extra_days = enriched.get("extra_days") or 0
    richiedi_gs = enriched.get("richiedi_giorno_scadenza", False)
    giorno_sc = enriched.get("giorno_scadenza")

    scadenze = []
    for i, q in enumerate(quote_list):
        giorni = q.get("giorni", 0) if isinstance(q, dict) else q.giorni
        quota_pct = q.get("quota", 0) if isinstance(q, dict) else q.quota

        target = invoice_date + timedelta(days=giorni)

        if fine_mese:
            last_day = calendar.monthrange(target.year, target.month)[1]
            target = target.replace(day=last_day)
            if extra_days:
                target = target + timedelta(days=extra_days)

        if richiedi_gs and giorno_sc:
            try:
                last_day = calendar.monthrange(target.year, target.month)[1]
                target = target.replace(day=min(giorno_sc, last_day))
                if target <= invoice_date + timedelta(days=giorni - 15):
                    # Push to next month if target day is before expected
                    if target.month == 12:
                        target = target.replace(year=target.year + 1, month=1, day=min(giorno_sc, 31))
                    else:
                        next_month = target.month + 1
                        last_day_next = calendar.monthrange(target.year, next_month)[1]
                        target = target.replace(month=next_month, day=min(giorno_sc, last_day_next))
            except ValueError:
                pass

        importo = round(req.importo * quota_pct / 100, 2)
        scadenze.append(SimulateDeadlineItem(
            rata=i + 1,
            giorni=giorni,
            data_scadenza=target.isoformat(),
            quota_pct=quota_pct,
            importo=importo,
        ))

    return SimulateResponse(
        scadenze=scadenze,
        totale_rate=len(scadenze),
        importo_totale=sum(s.importo for s in scadenze),
    )


@router.post("/seed-defaults")
async def seed_default_payment_types(user: dict = Depends(get_current_user)):
    """Seed common Italian payment types if none exist."""
    count = await db[COLLECTION].count_documents({"user_id": user["user_id"]})
    if count > 0:
        return {"message": f"Già presenti {count} tipi pagamento", "seeded": 0}

    defaults = [
        {"codice": "BB30", "tipo": "BON", "codice_fe": "MP05", "descrizione": "Bonifico Bancario 30 gg", "gg_30": True, "quote": [{"giorni": 30, "quota": 100}]},
        {"codice": "BB60", "tipo": "BON", "codice_fe": "MP05", "descrizione": "Bonifico Bancario 60 gg", "gg_60": True, "quote": [{"giorni": 60, "quota": 100}]},
        {"codice": "BB30-60", "tipo": "BON", "codice_fe": "MP05", "descrizione": "Bonifico Bancario 30/60 gg", "gg_30": True, "gg_60": True, "quote": [{"giorni": 30, "quota": 50}, {"giorni": 60, "quota": 50}]},
        {"codice": "BB60FM", "tipo": "BON", "codice_fe": "MP05", "descrizione": "Bonifico Bancario 60 gg FM", "gg_60": True, "fine_mese": True, "quote": [{"giorni": 60, "quota": 100}]},
        {"codice": "BB30-60-90", "tipo": "BON", "codice_fe": "MP05", "descrizione": "Bonifico Bancario 30/60/90 gg", "gg_30": True, "gg_60": True, "gg_90": True, "quote": [{"giorni": 30, "quota": 33.33}, {"giorni": 60, "quota": 33.33}, {"giorni": 90, "quota": 33.34}]},
        {"codice": "RB30", "tipo": "RIB", "codice_fe": "MP12", "descrizione": "Ricevuta Bancaria 30 gg", "gg_30": True, "banca_necessaria": True, "quote": [{"giorni": 30, "quota": 100}]},
        {"codice": "RB60", "tipo": "RIB", "codice_fe": "MP12", "descrizione": "Ricevuta Bancaria 60 gg", "gg_60": True, "banca_necessaria": True, "quote": [{"giorni": 60, "quota": 100}]},
        {"codice": "RB30-60", "tipo": "RIB", "codice_fe": "MP12", "descrizione": "Ricevuta Bancaria 30/60 gg", "gg_30": True, "gg_60": True, "banca_necessaria": True, "quote": [{"giorni": 30, "quota": 50}, {"giorni": 60, "quota": 50}]},
        {"codice": "RB90", "tipo": "RIB", "codice_fe": "MP12", "descrizione": "Ricevuta Bancaria 90 gg", "gg_90": True, "banca_necessaria": True, "quote": [{"giorni": 90, "quota": 100}]},
        {"codice": "CON", "tipo": "CON", "codice_fe": "MP01", "descrizione": "Contanti / Rimessa Diretta", "immediato": True, "quote": [{"giorni": 0, "quota": 100}]},
        {"codice": "ELETT", "tipo": "ELE", "codice_fe": "MP08", "descrizione": "Pagamento Elettronico", "immediato": True, "quote": [{"giorni": 0, "quota": 100}]},
    ]

    now = datetime.now(timezone.utc)
    docs = []
    for d in defaults:
        pt_id = f"pt_{uuid.uuid4().hex[:12]}"
        base = PaymentTypeCreate(**{**{
            "codice": "", "tipo": "BON", "descrizione": "",
        }, **d}).model_dump()
        # Convert QuotaItem to dict for MongoDB
        if base.get("quote"):
            base["quote"] = [q if isinstance(q, dict) else q.model_dump() if hasattr(q, 'model_dump') else dict(q) for q in base["quote"]]
        docs.append({
            "payment_type_id": pt_id,
            "user_id": user["user_id"],
            **base,
            "created_at": now,
            "updated_at": now,
        })
    await db[COLLECTION].insert_many(docs)
    return {"message": f"Creati {len(docs)} tipi pagamento predefiniti", "seeded": len(docs)}
