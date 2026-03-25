"""
Controlli Visivi + Registro Non Conformità — Obbligatori per EN 1090 e EN 13241.
Il Pulsante Magico blocca la generazione PDF se manca il controllo visivo.
Ogni 👎 crea automaticamente una riga nel Registro NC + alert admin.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.security import get_current_user, tenant_match
from core.database import db

router = APIRouter(tags=["qualita"])
logger = logging.getLogger(__name__)

CONTROLLI_COLL = "controlli_visivi"
NC_COLL = "registro_nc"
ALERT_COLL = "officina_alerts"


# ── MODELS ──

class ControlloVisivoCreate(BaseModel):
    commessa_id: str
    voce_id: Optional[str] = ""
    normativa_tipo: str
    esito: bool               # True = OK (👍), False = NOK (👎)
    note: Optional[str] = ""
    foto_doc_id: Optional[str] = ""  # ID del documento foto allegato
    operatore_id: Optional[str] = ""
    operatore_nome: Optional[str] = ""


class NCUpdate(BaseModel):
    stato: Optional[str] = None       # aperta, in_corso, chiusa
    azione_correttiva: Optional[str] = None
    chiusa_da: Optional[str] = None
    note_chiusura: Optional[str] = None


# ── CONTROLLI VISIVI ──

@router.post("/controlli-visivi")
async def create_controllo_visivo(data: ControlloVisivoCreate, user: dict = Depends(get_current_user)):
    """
    Registra un Controllo Visivo finale (obbligatorio per EN 1090 e EN 13241).
    Se esito = 👎, crea automaticamente una Non Conformità + alert admin.
    """
    now = datetime.now(timezone.utc)
    ctrl_id = f"ctrl_{uuid.uuid4().hex[:10]}"

    # Get commessa info for alerts
    commessa = await db.commesse.find_one(
        {"commessa_id": data.commessa_id}, {"_id": 0, "numero": 1, "user_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    doc = {
        "controllo_id": ctrl_id,
        "commessa_id": data.commessa_id,
        "voce_id": data.voce_id or "",
        "normativa_tipo": data.normativa_tipo,
        "esito": data.esito,
        "note": data.note or "",
        "foto_doc_id": data.foto_doc_id or "",
        "operatore_id": data.operatore_id or "",
        "operatore_nome": data.operatore_nome or "",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "created_at": now.isoformat(),
    }
    await db[CONTROLLI_COLL].insert_one(doc)
    doc.pop("_id", None)

    nc_created = None
    if not data.esito:
        nc_created = await _create_nc(
            commessa_id=data.commessa_id,
            commessa_numero=commessa.get("numero", ""),
            admin_id=commessa.get("user_id", user["user_id"]),
            voce_id=data.voce_id or "",
            tipo="controllo_visivo_nok",
            descrizione=f"Controllo visivo finale NOK — {data.note or 'Nessun dettaglio'}",
            operatore_nome=data.operatore_nome or "",
            normativa=data.normativa_tipo,
            source_id=ctrl_id,
        )

    logger.info(f"[CTRL VISIVO] {ctrl_id} — esito={'OK' if data.esito else 'NOK'} — commessa {data.commessa_id}")

    return {
        "controllo_id": ctrl_id,
        "esito": data.esito,
        "nc_creata": nc_created is not None,
        "nc_id": nc_created.get("nc_id") if nc_created else None,
    }


@router.get("/controlli-visivi/{commessa_id}")
async def list_controlli_visivi(commessa_id: str, user: dict = Depends(get_current_user)):
    """Lista controlli visivi per una commessa."""
    controlli = await db[CONTROLLI_COLL].find(
        {"commessa_id": commessa_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"controlli": controlli}


@router.get("/controlli-visivi/{commessa_id}/check")
async def check_controlli_completi(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Verifica se tutti i controlli visivi obbligatori sono stati completati.
    Usato dal Pulsante Magico per decidere se generare il PDF.
    """
    # Get all voci for this commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "normativa_tipo": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    voci = await db.voci_lavoro.find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(50)

    # Build list of voci that need visual inspection
    voci_obbligatorie = []
    norm_princ = commessa.get("normativa_tipo", "GENERICA")
    if norm_princ in ("EN_1090", "EN_13241"):
        voci_obbligatorie.append({"voce_id": "__principale__", "normativa": norm_princ})
    for v in voci:
        if v.get("normativa_tipo") in ("EN_1090", "EN_13241"):
            voci_obbligatorie.append({"voce_id": v["voce_id"], "normativa": v["normativa_tipo"]})

    # Check each one
    controlli = await db[CONTROLLI_COLL].find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).to_list(200)

    mancanti = []
    nok_senza_azione = []

    for voce_req in voci_obbligatorie:
        vid = voce_req["voce_id"]
        voce_ctrls = [c for c in controlli if c.get("voce_id", "") == vid or
                      (vid == "__principale__" and not c.get("voce_id"))]
        if not voce_ctrls:
            mancanti.append(vid)
        else:
            latest = sorted(voce_ctrls, key=lambda c: c.get("created_at", ""), reverse=True)[0]
            if not latest.get("esito"):
                # Check if there's a closed NC for this
                nc = await db[NC_COLL].find_one(
                    {"commessa_id": commessa_id, "voce_id": vid, "tipo": "controllo_visivo_nok", "stato": "chiusa"},
                    {"_id": 0}
                )
                if not nc:
                    nok_senza_azione.append(vid)

    completo = len(mancanti) == 0 and len(nok_senza_azione) == 0
    return {
        "completo": completo,
        "voci_obbligatorie": len(voci_obbligatorie),
        "mancanti": mancanti,
        "nok_senza_azione_correttiva": nok_senza_azione,
        "messaggio": "Tutti i controlli visivi completati" if completo
            else f"{len(mancanti)} controlli mancanti, {len(nok_senza_azione)} NOK senza azione correttiva"
    }


# ── REGISTRO NON CONFORMITA' ──

async def _create_nc(
    commessa_id: str, commessa_numero: str, admin_id: str,
    voce_id: str, tipo: str, descrizione: str,
    operatore_nome: str, normativa: str, source_id: str,
) -> dict:
    """Create a Non-Conformity entry + alert for admin. Called automatically on 👎."""
    now = datetime.now(timezone.utc)
    nc_id = f"nc_{uuid.uuid4().hex[:10]}"

    nc_doc = {
        "nc_id": nc_id,
        "commessa_id": commessa_id,
        "commessa_numero": commessa_numero,
        "admin_id": admin_id,
        "voce_id": voce_id,
        "tipo": tipo,
        "descrizione": descrizione,
        "operatore_nome": operatore_nome,
        "normativa": normativa,
        "source_id": source_id,
        "stato": "aperta",
        "azione_correttiva": "",
        "chiusa_da": "",
        "note_chiusura": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db[NC_COLL].insert_one(nc_doc)
    nc_doc.pop("_id", None)

    # Create immediate alert for admin dashboard
    alert = {
        "alert_id": f"alert_{uuid.uuid4().hex[:10]}",
        "admin_id": admin_id,
        "commessa_id": commessa_id,
        "commessa_numero": commessa_numero,
        "voce_id": voce_id,
        "tipo": "non_conformita",
        "messaggio": f"NC: {descrizione}",
        "operatore_nome": operatore_nome,
        "normativa": normativa,
        "nc_id": nc_id,
        "letto": False,
        "created_at": now.isoformat(),
    }
    await db[ALERT_COLL].insert_one(alert)
    alert.pop("_id", None)

    logger.warning(f"[NC] Creata: {nc_id} — {descrizione} — commessa {commessa_numero}")
    return nc_doc


@router.get("/registro-nc/{commessa_id}")
async def list_nc(commessa_id: str, user: dict = Depends(get_current_user)):
    """Lista Non Conformità per una commessa."""
    ncs = await db[NC_COLL].find(
        {"commessa_id": commessa_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"non_conformita": ncs, "total": len(ncs), "aperte": len([n for n in ncs if n["stato"] == "aperta"])}


@router.get("/registro-nc")
async def list_all_nc(user: dict = Depends(get_current_user), stato: str = None):
    """Lista tutte le NC dell'utente."""
    query = {"admin_id": user["user_id"]}
    if stato:
        query["stato"] = stato
    ncs = await db[NC_COLL].find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"non_conformita": ncs, "total": len(ncs)}


@router.patch("/registro-nc/{nc_id}")
async def update_nc(nc_id: str, data: NCUpdate, user: dict = Depends(get_current_user)):
    """Aggiorna una NC (chiusura, azione correttiva, ecc.)."""
    now = datetime.now(timezone.utc)
    updates = {"updated_at": now.isoformat()}
    if data.stato is not None:
        updates["stato"] = data.stato
    if data.azione_correttiva is not None:
        updates["azione_correttiva"] = data.azione_correttiva
    if data.chiusa_da is not None:
        updates["chiusa_da"] = data.chiusa_da
    if data.note_chiusura is not None:
        updates["note_chiusura"] = data.note_chiusura

    result = await db[NC_COLL].update_one(
        {"nc_id": nc_id, "admin_id": user["user_id"]},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "NC non trovata")
    return {"message": "NC aggiornata", "nc_id": nc_id}
