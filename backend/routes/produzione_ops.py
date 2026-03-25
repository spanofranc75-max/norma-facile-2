"""Produzione (Production Phases) — Init, update, ore preventivate."""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user
from routes.commessa_ops_common import (
    COLL, get_commessa_or_404, ensure_ops_fields,
    ts, push_event, build_update_with_event,
)

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_FASI = [
    {"tipo": "taglio",                "label": "Taglio",                 "order": 0},
    {"tipo": "foratura",              "label": "Foratura",               "order": 1},
    {"tipo": "assemblaggio",          "label": "Assemblaggio",           "order": 2},
    {"tipo": "saldatura",             "label": "Saldatura",              "order": 3},
    {"tipo": "pulizia",               "label": "Pulizia / Sbavatura",    "order": 4},
    {"tipo": "preparazione_superfici","label": "Preparazione Superfici", "order": 5},
]


@router.post("/{cid}/produzione/init")
async def init_produzione(cid: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    if doc.get("fasi_produzione"):
        return {"message": "Fasi gia' inizializzate", "fasi": doc["fasi_produzione"]}
    deadline_str = doc.get("deadline")
    fasi = []
    total_phases = len(DEFAULT_FASI)
    for i, f in enumerate(DEFAULT_FASI):
        data_prevista = None
        if deadline_str:
            try:
                from datetime import date as date_cls
                deadline_date = date_cls.fromisoformat(deadline_str)
                today = date_cls.today()
                total_days = (deadline_date - today).days
                if total_days > 0:
                    phase_end_day = int(total_days * (i + 1) / total_phases)
                    data_prevista = (today + timedelta(days=phase_end_day)).isoformat()
            except (ValueError, TypeError):
                pass
        fasi.append({
            **f, "stato": "da_fare", "operatore": None,
            "data_inizio": None, "data_fine": None,
            "data_prevista": data_prevista, "note": "",
        })
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(set_items={"fasi_produzione": fasi}, tipo="PRODUZIONE_INIZIALIZZATA", user=user, note="Fasi produzione create"),
    )
    return {"message": "Fasi produzione inizializzate", "fasi": fasi}


@router.get("/{cid}/produzione")
async def get_produzione(cid: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    return {"fasi": doc.get("fasi_produzione", []), "conto_lavoro": doc.get("conto_lavoro", [])}


class FaseUpdate(BaseModel):
    stato: str
    operatore: Optional[str] = None
    note: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    operator_name: Optional[str] = None
    data_prevista: Optional[str] = None


@router.put("/{cid}/produzione/{fase_tipo}")
async def update_fase(cid: str, fase_tipo: str, data: FaseUpdate, user: dict = Depends(get_current_user)):
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    now = ts().isoformat()
    upd = {"fasi_produzione.$[elem].stato": data.stato}
    if data.stato == "in_corso":
        upd["fasi_produzione.$[elem].data_inizio"] = data.started_at or now
    elif data.stato == "completato":
        upd["fasi_produzione.$[elem].data_fine"] = data.completed_at or now
        if data.started_at:
            upd["fasi_produzione.$[elem].data_inizio"] = data.started_at
    if data.started_at:
        upd["fasi_produzione.$[elem].started_at"] = data.started_at
    if data.completed_at:
        upd["fasi_produzione.$[elem].completed_at"] = data.completed_at
    if data.operator_name:
        upd["fasi_produzione.$[elem].operator_name"] = data.operator_name
    if data.operatore is not None:
        upd["fasi_produzione.$[elem].operatore"] = data.operatore
    if data.note is not None:
        upd["fasi_produzione.$[elem].note"] = data.note
    if data.data_prevista is not None:
        upd["fasi_produzione.$[elem].data_prevista"] = data.data_prevista
    await db[COLL].update_one({"commessa_id": cid}, {"$set": upd}, array_filters=[{"elem.tipo": fase_tipo}])
    label_map = {f["tipo"]: f["label"] for f in DEFAULT_FASI}
    label = label_map.get(fase_tipo, fase_tipo)
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, f"FASE_{data.stato.upper()}", user, f"{label} → {data.stato}", {"fase": fase_tipo}))
    return {"message": f"{label} → {data.stato}"}
