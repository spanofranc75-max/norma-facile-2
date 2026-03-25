"""
Gestione Sfridi — Materiale avanzato ricaricato a magazzino con link al certificato 3.1 originale.
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from core.security import get_current_user, tenant_match
from core.database import db

router = APIRouter(prefix="/sfridi", tags=["sfridi"])
logger = logging.getLogger(__name__)

SFRIDI_COLL = "magazzino_sfridi"


class SfridoCreate(BaseModel):
    commessa_id: str
    voce_id: Optional[str] = ""
    tipo_materiale: str          # es. "IPE 200", "HEA 160", "Tubo 80x40"
    quantita: str                # es. "3 barre", "2.5m", "150 kg"
    numero_colata: Optional[str] = ""
    certificato_doc_id: Optional[str] = ""  # link al doc 3.1 originale
    note: Optional[str] = ""


class SfridoPrelievo(BaseModel):
    commessa_id_destinazione: str
    voce_id_destinazione: Optional[str] = ""
    quantita_prelevata: str
    note: Optional[str] = ""


@router.post("")
async def create_sfrido(data: SfridoCreate, user: dict = Depends(get_current_user)):
    """Ricarica materiale avanzato a magazzino mantenendo il link al certificato 3.1."""
    sfrido_id = f"sfr_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # Verify the certificate doc exists if provided
    cert_info = None
    if data.certificato_doc_id:
        cert_doc = await db.commessa_documents.find_one(
            {"doc_id": data.certificato_doc_id},
            {"_id": 0, "doc_id": 1, "nome_file": 1, "tipo": 1, "commessa_id": 1}
        )
        if cert_doc:
            cert_info = {
                "doc_id": cert_doc["doc_id"],
                "nome_file": cert_doc.get("nome_file", ""),
                "tipo": cert_doc.get("tipo", ""),
                "commessa_origine": cert_doc.get("commessa_id", ""),
            }

    doc = {
        "sfrido_id": sfrido_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "commessa_origine": data.commessa_id,
        "voce_origine": data.voce_id or "",
        "tipo_materiale": data.tipo_materiale,
        "quantita": data.quantita,
        "numero_colata": data.numero_colata or "",
        "certificato_doc_id": data.certificato_doc_id or "",
        "certificato_info": cert_info,
        "note": data.note or "",
        "stato": "disponibile",
        "prelievi": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db[SFRIDI_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[SFRIDI] Creato: {sfrido_id} — {data.tipo_materiale} da commessa {data.commessa_id}")
    return doc


@router.get("")
async def list_sfridi(user: dict = Depends(get_current_user), stato: str = "disponibile"):
    """Lista sfridi disponibili a magazzino."""
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    if stato:
        query["stato"] = stato
    sfridi = await db[SFRIDI_COLL].find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"sfridi": sfridi, "total": len(sfridi)}


@router.get("/commessa/{commessa_id}")
async def list_sfridi_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    """Lista sfridi originati da una commessa specifica."""
    sfridi = await db[SFRIDI_COLL].find(
        {"commessa_origine": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"sfridi": sfridi}


@router.post("/{sfrido_id}/preleva")
async def preleva_sfrido(sfrido_id: str, data: SfridoPrelievo, user: dict = Depends(get_current_user)):
    """Preleva materiale da uno sfrido per una nuova commessa."""
    now = datetime.now(timezone.utc)

    sfrido = await db[SFRIDI_COLL].find_one(
        {"sfrido_id": sfrido_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not sfrido:
        raise HTTPException(404, "Sfrido non trovato")
    if sfrido["stato"] == "esaurito":
        raise HTTPException(400, "Sfrido già esaurito")

    prelievo = {
        "prelievo_id": f"prl_{uuid.uuid4().hex[:8]}",
        "commessa_id": data.commessa_id_destinazione,
        "voce_id": data.voce_id_destinazione or "",
        "quantita": data.quantita_prelevata,
        "note": data.note or "",
        "data": now.isoformat(),
    }

    await db[SFRIDI_COLL].update_one(
        {"sfrido_id": sfrido_id},
        {
            "$push": {"prelievi": prelievo},
            "$set": {"stato": "parziale", "updated_at": now.isoformat()},
        }
    )

    logger.info(f"[SFRIDI] Prelievo da {sfrido_id} per commessa {data.commessa_id_destinazione}")
    return {"message": "Prelievo registrato", "prelievo": prelievo}


@router.patch("/{sfrido_id}/esaurito")
async def mark_esaurito(sfrido_id: str, user: dict = Depends(get_current_user)):
    """Segna uno sfrido come esaurito."""
    result = await db[SFRIDI_COLL].update_one(
        {"sfrido_id": sfrido_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {"stato": "esaurito", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Sfrido non trovato")
    return {"message": "Sfrido esaurito"}
