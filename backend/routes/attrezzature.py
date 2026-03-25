"""
Scadenzario Attrezzature — Gestione tarature saldatrici e chiavi dinamometriche.

Se la taratura di una chiave dinamometrica è scaduta, crea un alert admin.
Il modulo serraggio nel Diario di Montaggio verifica lo stato taratura.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.security import get_current_user
from core.database import db

router = APIRouter(prefix="/attrezzature", tags=["attrezzature"])
logger = logging.getLogger(__name__)

ATTR_COLL = "attrezzature"
ALERT_COLL = "officina_alerts"

TIPI_ATTREZZATURA = ["saldatrice", "chiave_dinamometrica", "altro"]


class AttrezzaturaCreate(BaseModel):
    tipo: str                      # saldatrice | chiave_dinamometrica | altro
    modello: str
    numero_serie: Optional[str] = ""
    marca: Optional[str] = ""
    data_taratura: str             # ISO date: "2026-01-15"
    prossima_taratura: str         # ISO date: "2027-01-15"
    note: Optional[str] = ""


class AttrezzaturaUpdate(BaseModel):
    modello: Optional[str] = None
    numero_serie: Optional[str] = None
    marca: Optional[str] = None
    data_taratura: Optional[str] = None
    prossima_taratura: Optional[str] = None
    note: Optional[str] = None


@router.post("")
async def create_attrezzatura(data: AttrezzaturaCreate, user: dict = Depends(get_current_user)):
    """Registra una nuova attrezzatura con data di taratura."""
    if data.tipo not in TIPI_ATTREZZATURA:
        raise HTTPException(400, f"Tipo non valido. Valori: {TIPI_ATTREZZATURA}")

    attr_id = f"attr_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    doc = {
        "attr_id": attr_id,
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "tipo": data.tipo,
        "modello": data.modello,
        "numero_serie": data.numero_serie or "",
        "marca": data.marca or "",
        "data_taratura": data.data_taratura,
        "prossima_taratura": data.prossima_taratura,
        "note": data.note or "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db[ATTR_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[ATTREZZATURE] Creata: {attr_id} — {data.tipo} {data.modello}")
    return doc


@router.get("")
async def list_attrezzature(user: dict = Depends(get_current_user), tipo: str = ""):
    """Lista tutte le attrezzature dell'utente (filtro opzionale per tipo)."""
    query = {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    if tipo:
        query["tipo"] = tipo

    items = await db[ATTR_COLL].find(query, {"_id": 0}).sort("prossima_taratura", 1).to_list(200)

    # Enrich with scadenza status
    today = datetime.now(timezone.utc).date()
    for item in items:
        try:
            pross = datetime.fromisoformat(item["prossima_taratura"]).date()
            days_left = (pross - today).days
            item["scaduta"] = days_left < 0
            item["in_scadenza"] = 0 <= days_left <= 30
            item["giorni_rimasti"] = days_left
        except (ValueError, KeyError):
            item["scaduta"] = False
            item["in_scadenza"] = False
            item["giorni_rimasti"] = None

    return {"attrezzature": items, "total": len(items)}


@router.patch("/{attr_id}")
async def update_attrezzatura(attr_id: str, data: AttrezzaturaUpdate, user: dict = Depends(get_current_user)):
    """Aggiorna i dati di un'attrezzatura."""
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for field in ["modello", "numero_serie", "marca", "data_taratura", "prossima_taratura", "note"]:
        val = getattr(data, field)
        if val is not None:
            updates[field] = val

    result = await db[ATTR_COLL].update_one(
        {"attr_id": attr_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Attrezzatura non trovata")
    return {"message": "Attrezzatura aggiornata", "attr_id": attr_id}


@router.delete("/{attr_id}")
async def delete_attrezzatura(attr_id: str, user: dict = Depends(get_current_user)):
    """Elimina un'attrezzatura."""
    result = await db[ATTR_COLL].delete_one({"attr_id": attr_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Attrezzatura non trovata")
    return {"message": "Attrezzatura eliminata"}


# ── CHECK TARATURA per il modulo serraggio ──

@router.get("/check-taratura")
async def check_taratura_chiavi(user: dict = Depends(get_current_user)):
    """
    Verifica se ci sono chiavi dinamometriche con taratura scaduta.
    Usato dal modulo serraggio nel Diario di Montaggio.
    """
    today = datetime.now(timezone.utc).date()
    chiavi = await db[ATTR_COLL].find(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "tipo": "chiave_dinamometrica"},
        {"_id": 0}
    ).to_list(50)

    scadute = []
    in_scadenza = []
    valide = []

    for c in chiavi:
        try:
            pross = datetime.fromisoformat(c["prossima_taratura"]).date()
            days_left = (pross - today).days
            c["giorni_rimasti"] = days_left
            if days_left < 0:
                c["scaduta"] = True
                scadute.append(c)
            elif days_left <= 30:
                c["in_scadenza"] = True
                in_scadenza.append(c)
            else:
                valide.append(c)
        except (ValueError, KeyError):
            valide.append(c)

    # Create admin alert if any expired
    if scadute:
        for chiave in scadute:
            existing = await db[ALERT_COLL].find_one({
                "admin_id": user["user_id"],
                "tipo": "taratura_scaduta",
                "attr_id": chiave["attr_id"],
                "letto": False,
            })
            if not existing:
                alert = {
                    "alert_id": f"alert_{uuid.uuid4().hex[:10]}",
                    "admin_id": user["user_id"],
                    "tipo": "taratura_scaduta",
                    "attr_id": chiave["attr_id"],
                    "messaggio": f"TARATURA SCADUTA: {chiave['modello']} (S/N: {chiave.get('numero_serie', 'N/D')}) — scaduta da {abs(chiave['giorni_rimasti'])} giorni",
                    "letto": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db[ALERT_COLL].insert_one(alert)
                alert.pop("_id", None)
                logger.warning(f"[ATTREZZATURE] Alert taratura scaduta: {chiave['modello']}")

    return {
        "tutte_valide": len(scadute) == 0,
        "scadute": scadute,
        "in_scadenza": in_scadenza,
        "valide": valide,
        "totale_chiavi": len(chiavi),
    }
