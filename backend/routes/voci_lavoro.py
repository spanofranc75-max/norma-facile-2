"""
Voci di Lavoro — CRUD per la struttura Matrioska (Cantieri Misti).
Ogni commessa puo' contenere piu' voci, ognuna con la sua normativa.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from core.security import get_current_user, tenant_match

router = APIRouter(prefix="/commesse/{commessa_id}/voci", tags=["voci_lavoro"])
db = get_database()


class VoceCreate(BaseModel):
    descrizione: str
    normativa_tipo: str  # EN_1090, EN_13241, GENERICA
    classe_exc: Optional[str] = ""
    tipologia_chiusura: Optional[str] = ""


class VoceUpdate(BaseModel):
    descrizione: Optional[str] = None
    normativa_tipo: Optional[str] = None
    classe_exc: Optional[str] = None
    tipologia_chiusura: Optional[str] = None


@router.get("/")
async def list_voci(commessa_id: str, user=Depends(get_current_user)):
    """Lista voci di lavoro di una commessa."""
    voci = await db.voci_lavoro.find(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    ).sort("ordine", 1).to_list(100)
    return {"voci": voci}


@router.post("/")
async def create_voce(commessa_id: str, body: VoceCreate, user=Depends(get_current_user)):
    """Crea una nuova voce di lavoro."""
    # Verifica che la commessa esista
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa non trovata")

    if body.normativa_tipo not in ("EN_1090", "EN_13241", "GENERICA"):
        raise HTTPException(status_code=400, detail="normativa_tipo deve essere EN_1090, EN_13241 o GENERICA")

    # Calcola ordine (prossimo disponibile)
    count = await db.voci_lavoro.count_documents({"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})

    voce = {
        "voce_id": f"voce_{uuid.uuid4().hex[:12]}",
        "commessa_id": commessa_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "descrizione": body.descrizione.strip(),
        "normativa_tipo": body.normativa_tipo,
        "classe_exc": body.classe_exc if body.normativa_tipo == "EN_1090" else "",
        "tipologia_chiusura": body.tipologia_chiusura if body.normativa_tipo == "EN_13241" else "",
        "ordine": count + 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.voci_lavoro.insert_one(voce)
    del voce["_id"]
    return voce


@router.put("/{voce_id}")
async def update_voce(commessa_id: str, voce_id: str, body: VoceUpdate, user=Depends(get_current_user)):
    """Aggiorna una voce di lavoro."""
    update_fields = {}
    if body.descrizione is not None:
        update_fields["descrizione"] = body.descrizione.strip()
    if body.normativa_tipo is not None:
        if body.normativa_tipo not in ("EN_1090", "EN_13241", "GENERICA"):
            raise HTTPException(status_code=400, detail="normativa_tipo non valido")
        update_fields["normativa_tipo"] = body.normativa_tipo
    if body.classe_exc is not None:
        update_fields["classe_exc"] = body.classe_exc
    if body.tipologia_chiusura is not None:
        update_fields["tipologia_chiusura"] = body.tipologia_chiusura

    if not update_fields:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.voci_lavoro.update_one(
        {"voce_id": voce_id, "commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Voce non trovata")

    updated = await db.voci_lavoro.find_one({"voce_id": voce_id}, {"_id": 0})
    return updated


@router.delete("/{voce_id}")
async def delete_voce(commessa_id: str, voce_id: str, user=Depends(get_current_user)):
    """Elimina una voce di lavoro."""
    result = await db.voci_lavoro.delete_one(
        {"voce_id": voce_id, "commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Voce non trovata")
    return {"message": "Voce eliminata", "voce_id": voce_id}
