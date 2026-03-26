"""
Registro Saldatura per Commessa — Tracciabilita operativa EN 1090.
Chi ha saldato cosa, quando, con quale WPS e patentino.

GET    /api/registro-saldatura/{commessa_id}           — Lista righe registro
POST   /api/registro-saldatura/{commessa_id}           — Aggiungi riga
PUT    /api/registro-saldatura/{commessa_id}/{riga_id} — Modifica riga
DELETE /api/registro-saldatura/{commessa_id}/{riga_id} — Elimina riga
GET    /api/registro-saldatura/{commessa_id}/saldatori-idonei — Saldatori filtrati per processo
"""
import uuid
import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from core.database import db
from core.security import get_current_user, tenant_match
from core.rbac import require_role

router = APIRouter(prefix="/registro-saldatura", tags=["registro-saldatura"])
logger = logging.getLogger(__name__)


class RigaSaldatura(BaseModel):
    giunto: str = Field(..., description="Identificativo giunto (es. G1, G2)")
    posizione_dwg: str = Field("", description="Posizione nel disegno (es. Pos.4 STR02)")
    saldatore_id: str = Field(..., description="ID saldatore (welder_id)")
    wps_id: Optional[str] = None
    processo: str = Field("135", description="Processo di saldatura (135=MIG/MAG, 111=SMAW, 141=TIG)")
    data_esecuzione: str = Field("", description="YYYY-MM-DD")
    esito_vt: str = Field("da_eseguire", description="da_eseguire | conforme | non_conforme")
    note: str = ""


@router.get("/{commessa_id}")
async def list_registro(commessa_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Lista completa del registro saldatura per la commessa."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "commessa_id": 1, "numero": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    righe = await db.registro_saldatura.find(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    ).sort("data_esecuzione", -1).to_list(500)

    # Enrich with welder names and WPS info
    welder_ids = list(set(r.get("saldatore_id") for r in righe if r.get("saldatore_id")))
    wps_ids = list(set(r.get("wps_id") for r in righe if r.get("wps_id")))

    welders_map = {}
    if welder_ids:
        welders = await db.welders.find(
            {"welder_id": {"$in": welder_ids}}, {"_id": 0, "welder_id": 1, "name": 1, "punzone": 1}
        ).to_list(100)
        welders_map = {w["welder_id"]: w for w in welders}

    wps_map = {}
    if wps_ids:
        wps_list = await db.wps.find(
            {"wps_id": {"$in": wps_ids}}, {"_id": 0, "wps_id": 1, "process": 1, "base_material_group": 1}
        ).to_list(50)
        wps_map = {w["wps_id"]: w for w in wps_list}

    enriched = []
    for r in righe:
        w = welders_map.get(r.get("saldatore_id"), {})
        wps = wps_map.get(r.get("wps_id"), {})
        enriched.append({
            **r,
            "saldatore_nome": w.get("name", "?"),
            "saldatore_punzone": w.get("punzone", ""),
            "wps_processo": wps.get("process", r.get("processo", "")),
            "wps_materiale": wps.get("base_material_group", ""),
        })

    stats = {
        "totale": len(righe),
        "conformi": sum(1 for r in righe if r.get("esito_vt") == "conforme"),
        "non_conformi": sum(1 for r in righe if r.get("esito_vt") == "non_conforme"),
        "da_eseguire": sum(1 for r in righe if r.get("esito_vt") == "da_eseguire"),
    }

    return {"righe": enriched, "stats": stats, "numero": commessa.get("numero", "")}


@router.post("/{commessa_id}")
async def add_riga(commessa_id: str, data: RigaSaldatura, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Aggiungi una riga al registro saldatura."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Verify welder exists
    welder = await db.welders.find_one(
        {"welder_id": data.saldatore_id}, {"_id": 0, "welder_id": 1, "name": 1, "qualifications": 1}
    )
    if not welder:
        raise HTTPException(404, "Saldatore non trovato")

    # Verify welder has valid qualification for the process
    today = date.today()
    processo_ok = False
    for q in welder.get("qualifications", []):
        proc = q.get("process", "")
        expiry = q.get("expiry_date", "")
        if proc == data.processo or not proc:
            if expiry:
                try:
                    if date.fromisoformat(str(expiry)[:10]) >= today:
                        processo_ok = True
                        break
                except (ValueError, TypeError):
                    pass
            else:
                processo_ok = True
                break
    # Allow even without strict match but warn
    if not processo_ok:
        logger.warning(f"Saldatore {data.saldatore_id} potrebbe non avere patentino valido per processo {data.processo}")

    riga_id = f"rs_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "riga_id": riga_id,
        "commessa_id": commessa_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "giunto": data.giunto,
        "posizione_dwg": data.posizione_dwg,
        "saldatore_id": data.saldatore_id,
        "wps_id": data.wps_id or "",
        "processo": data.processo,
        "data_esecuzione": data.data_esecuzione or now[:10],
        "esito_vt": data.esito_vt,
        "note": data.note,
        "created_at": now,
    }
    await db.registro_saldatura.insert_one(doc)

    return {
        "message": "Riga aggiunta al registro",
        "riga_id": riga_id,
        "saldatore": welder.get("name", ""),
        "processo_validato": processo_ok,
    }


@router.put("/{commessa_id}/{riga_id}")
async def update_riga(commessa_id: str, riga_id: str, data: RigaSaldatura, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Aggiorna una riga del registro (es. esito VT dopo controllo)."""
    existing = await db.registro_saldatura.find_one(
        {"riga_id": riga_id, "commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Riga non trovata")

    await db.registro_saldatura.update_one(
        {"riga_id": riga_id},
        {"$set": {
            "giunto": data.giunto,
            "posizione_dwg": data.posizione_dwg,
            "saldatore_id": data.saldatore_id,
            "wps_id": data.wps_id or "",
            "processo": data.processo,
            "data_esecuzione": data.data_esecuzione,
            "esito_vt": data.esito_vt,
            "note": data.note,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    return {"message": "Riga aggiornata", "riga_id": riga_id}


@router.delete("/{commessa_id}/{riga_id}")
async def delete_riga(commessa_id: str, riga_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Elimina una riga dal registro."""
    result = await db.registro_saldatura.delete_one(
        {"riga_id": riga_id, "commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Riga non trovata")
    return {"message": "Riga eliminata"}


@router.get("/{commessa_id}/saldatori-idonei")
async def saldatori_idonei(commessa_id: str, processo: str = "135", user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Filtra saldatori con patentino valido per il processo richiesto."""
    today = date.today()
    welders = await db.welders.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).to_list(200)

    idonei = []
    for w in welders:
        for q in w.get("qualifications", []):
            proc = q.get("process", "")
            expiry = q.get("expiry_date", "")
            # Match: same process OR no process specified (general qualification)
            if proc == processo or not proc:
                valid = True
                if expiry:
                    try:
                        valid = date.fromisoformat(str(expiry)[:10]) >= today
                    except (ValueError, TypeError):
                        valid = False
                if valid:
                    idonei.append({
                        "welder_id": w["welder_id"],
                        "name": w.get("name", ""),
                        "punzone": w.get("punzone", ""),
                        "processo": proc or processo,
                        "patentino": q.get("standard", ""),
                        "scadenza": expiry,
                    })
                    break

    return {"saldatori": idonei, "processo": processo, "totale": len(idonei)}
