"""Diario di Produzione — Time tracking per commessa.
Registra sessioni di lavoro per fase, con più operatori e più giornate.
Calcola costi effettivi e confronto con ore preventivate.
Include anagrafica operatori semplificata (solo nome).
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user, tenant_match
from core.rbac import require_role

router = APIRouter(prefix="/commesse", tags=["diario-produzione"])
logger = logging.getLogger(__name__)

COLL = "commesse_ops"
DIARIO_COLL = "diario_produzione"
OPERATORI_COLL = "operatori"


class Operatore(BaseModel):
    id: str
    nome: str


class DiarioEntry(BaseModel):
    data: str  # ISO date YYYY-MM-DD
    fase: str
    ore: float  # durata sessione
    operatori: List[Operatore]  # lista operatori coinvolti
    note: Optional[str] = ""
    voce_id: Optional[str] = None          # Matrioska: quale voce di lavoro
    numero_colata: Optional[str] = None    # EN 1090: numero colata / cert 3.1
    wps_usata: Optional[str] = None        # EN 1090: WPS utilizzata
    note_collaudo: Optional[str] = None    # EN 13241: note collaudo/sicurezza


class DiarioEntryUpdate(BaseModel):
    data: Optional[str] = None
    fase: Optional[str] = None
    ore: Optional[float] = None
    operatori: Optional[List[Operatore]] = None
    note: Optional[str] = None
    voce_id: Optional[str] = None
    numero_colata: Optional[str] = None
    wps_usata: Optional[str] = None
    note_collaudo: Optional[str] = None


class OrePreventivateInput(BaseModel):
    ore_preventivate: float


async def _get_team_admin_id(user: dict) -> str:
    role = user.get("role", "admin")
    if role == "admin":
        return user["user_id"]
    return user.get("team_owner_id", user["user_id"])


# ── CRUD ─────────────────────────────────────────────────────────

@router.get("/{cid}/diario")
async def list_diario(
    cid: str,
    mese: Optional[str] = Query(None, description="Filtro mese YYYY-MM"),
    fase: Optional[str] = Query(None, description="Filtro fase"),
    user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina")),
):
    """List diary entries for a commessa, optionally filtered."""
    admin_id = await _get_team_admin_id(user)
    query = {"commessa_id": cid, "admin_id": admin_id, "tenant_id": tenant_match(user)}
    if mese:
        query["data"] = {"$regex": f"^{mese}"}
    if fase:
        query["fase"] = fase

    entries = await db[DIARIO_COLL].find(query, {"_id": 0}).sort("data", -1).to_list(500)
    return {"entries": entries}


@router.post("/{cid}/diario")
async def create_diario_entry(cid: str, entry: DiarioEntry, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Create a new work session entry."""
    admin_id = await _get_team_admin_id(user)
    now = datetime.now(timezone.utc)
    entry_id = f"dp_{uuid.uuid4().hex[:10]}"

    num_operatori = len(entry.operatori)
    ore_totali = round(entry.ore * num_operatori, 2)

    doc = {
        "entry_id": entry_id,
        "commessa_id": cid,
        "admin_id": admin_id,
        "data": entry.data,
        "fase": entry.fase,
        "ore": entry.ore,
        "operatori": [o.model_dump() for o in entry.operatori],
        "ore_totali": ore_totali,
        "note": entry.note or "",
        "voce_id": entry.voce_id or "",
        "numero_colata": entry.numero_colata or "",
        "wps_usata": entry.wps_usata or "",
        "note_collaudo": entry.note_collaudo or "",
        "created_by": user["user_id"],
        "tenant_id": tenant_match(user),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db[DIARIO_COLL].insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"Diario entry created: {entry_id} for commessa {cid}, fase {entry.fase}, {entry.ore}h x {num_operatori} op = {ore_totali}h")
    return doc


@router.put("/{cid}/diario/{entry_id}")
async def update_diario_entry(
    cid: str, entry_id: str, entry: DiarioEntryUpdate, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))
):
    """Update a work session entry."""
    admin_id = await _get_team_admin_id(user)
    updates = {}

    if entry.data is not None:
        updates["data"] = entry.data
    if entry.fase is not None:
        updates["fase"] = entry.fase
    if entry.ore is not None:
        updates["ore"] = entry.ore
    if entry.operatori is not None:
        updates["operatori"] = [o.model_dump() for o in entry.operatori]
    if entry.note is not None:
        updates["note"] = entry.note
    if entry.voce_id is not None:
        updates["voce_id"] = entry.voce_id
    if entry.numero_colata is not None:
        updates["numero_colata"] = entry.numero_colata
    if entry.wps_usata is not None:
        updates["wps_usata"] = entry.wps_usata
    if entry.note_collaudo is not None:
        updates["note_collaudo"] = entry.note_collaudo

    if not updates:
        raise HTTPException(400, "Nessun dato da aggiornare")

    # Recalculate ore_totali if ore or operatori changed
    if "ore" in updates or "operatori" in updates:
        existing = await db[DIARIO_COLL].find_one({"entry_id": entry_id}, {"_id": 0})
        if existing:
            ore = updates.get("ore", existing.get("ore", 0))
            ops = updates.get("operatori", existing.get("operatori", []))
            updates["ore_totali"] = round(ore * len(ops), 2)

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db[DIARIO_COLL].update_one(
        {"entry_id": entry_id, "commessa_id": cid, "admin_id": admin_id, "tenant_id": tenant_match(user)},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Voce diario non trovata")

    doc = await db[DIARIO_COLL].find_one({"entry_id": entry_id}, {"_id": 0})
    return doc


@router.delete("/{cid}/diario/{entry_id}")
async def delete_diario_entry(cid: str, entry_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Delete a work session entry."""
    admin_id = await _get_team_admin_id(user)
    result = await db[DIARIO_COLL].delete_one(
        {"entry_id": entry_id, "commessa_id": cid, "admin_id": admin_id, "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Voce diario non trovata")
    return {"message": "Voce eliminata"}


# ── RIEPILOGO ────────────────────────────────────────────────────

@router.get("/{cid}/diario/riepilogo")
async def get_diario_riepilogo(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Get summary stats: total hours, per phase, per operator, cost analysis."""
    admin_id = await _get_team_admin_id(user)

    entries = await db[DIARIO_COLL].find(
        {"commessa_id": cid, "admin_id": admin_id, "tenant_id": tenant_match(user)}, {"_id": 0}
    ).to_list(1000)

    # Get company hourly cost
    cost_doc = await db.company_costs.find_one({"user_id": admin_id, "tenant_id": tenant_match(user)}, {"_id": 0})
    costo_orario = cost_doc.get("costo_orario_pieno", 0) if cost_doc else 0

    # Get estimated hours from production phases
    ops_doc = await db[COLL].find_one({"commessa_id": cid}, {"_id": 0, "fasi_produzione": 1})
    fasi = ops_doc.get("fasi_produzione", []) if ops_doc else []

    # Aggregate per phase (using ore_totali = person-hours)
    per_fase = {}
    per_operatore = {}
    totale_ore_totali = 0  # person-hours
    totale_sessioni = 0

    for e in entries:
        fase = e.get("fase", "altro")
        ore_totali = e.get("ore_totali", e.get("ore", 0))
        totale_ore_totali += ore_totali
        totale_sessioni += 1

        if fase not in per_fase:
            per_fase[fase] = {"ore_totali": 0, "ore_preventivate": 0, "label": fase, "sessioni": 0}
        per_fase[fase]["ore_totali"] += ore_totali
        per_fase[fase]["sessioni"] += 1

        # Per operator
        operatori = e.get("operatori", [])
        if not operatori and e.get("operatore_id"):
            operatori = [{"id": e["operatore_id"], "nome": e.get("operatore_nome", "?")}]
        for op in operatori:
            op_id = op.get("id", "")
            if op_id not in per_operatore:
                per_operatore[op_id] = {"nome": op.get("nome", "?"), "ore": 0, "sessioni": 0}
            per_operatore[op_id]["ore"] += e.get("ore", 0)
            per_operatore[op_id]["sessioni"] += 1

    # Add estimated hours from phases
    totale_preventivate = 0
    for f in fasi:
        tipo = f.get("tipo", "")
        ore_prev = f.get("ore_preventivate", 0)
        totale_preventivate += ore_prev
        if tipo in per_fase:
            per_fase[tipo]["ore_preventivate"] = ore_prev
            per_fase[tipo]["label"] = f.get("label", tipo)
        elif ore_prev > 0:
            per_fase[tipo] = {
                "ore_totali": 0,
                "ore_preventivate": ore_prev,
                "label": f.get("label", tipo),
                "sessioni": 0,
            }

    costo_effettivo = totale_ore_totali * costo_orario
    costo_preventivato = totale_preventivate * costo_orario

    return {
        "totale_ore_totali": round(totale_ore_totali, 2),
        "totale_ore_preventivate": round(totale_preventivate, 2),
        "totale_sessioni": totale_sessioni,
        "costo_orario": round(costo_orario, 2),
        "costo_effettivo": round(costo_effettivo, 2),
        "costo_preventivato": round(costo_preventivato, 2),
        "scostamento": round(costo_effettivo - costo_preventivato, 2) if totale_preventivate > 0 else None,
        "per_fase": list(per_fase.values()),
        "per_operatore": list(per_operatore.values()),
    }


# ── ORE PREVENTIVATE PER FASE ────────────────────────────────────

@router.put("/{cid}/produzione/{fase_tipo}/ore-preventivate")
async def set_ore_preventivate(
    cid: str, fase_tipo: str, data: OrePreventivateInput, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))
):
    """Set estimated hours for a production phase."""
    result = await db[COLL].update_one(
        {"commessa_id": cid, "fasi_produzione.tipo": fase_tipo},
        {"$set": {"fasi_produzione.$.ore_preventivate": data.ore_preventivate}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Fase non trovata")
    return {"message": "Ore preventivate aggiornate", "fase": fase_tipo, "ore": data.ore_preventivate}


# ── ANAGRAFICA OPERATORI (semplice, solo nome) ──────────────────

class OperatoreInput(BaseModel):
    nome: str
    mansione: Optional[str] = ""


@router.get("/{cid}/operatori", tags=["operatori"])
async def list_operatori(cid: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """List all operators for the account.
    
    Merges data from:
    - operatori collection (legacy, simple name-only)
    - dipendenti collection (Risorse Umane HR)
    - welders collection (Anagrafica Operai)
    """
    admin_id = await _get_team_admin_id(user)
    
    # 1. Load from operatori collection (legacy)
    ops_raw = await db[OPERATORI_COLL].find(
        {"admin_id": admin_id, "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("nome", 1).to_list(200)
    
    seen_names = {o.get("nome", "").strip().lower() for o in ops_raw}
    
    # 2. Load from welders collection (Anagrafica Operai — primary source)
    welders = await db["welders"].find(
        {"user_id": admin_id, "is_active": True, "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("name", 1).to_list(200)
    
    for w in welders:
        name = w.get("name", "").strip()
        if name.lower() not in seen_names:
            ops_raw.append({
                "op_id": w.get("welder_id", ""),
                "admin_id": admin_id,
                "nome": name,
                "mansione": w.get("role", ""),
                "source": "welders",
            })
            seen_names.add(name.lower())
    
    # 3. Load from dipendenti collection (Risorse Umane HR)
    dipendenti = await db["dipendenti"].find(
        {"user_id": admin_id, "attivo": True, "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("nome", 1).to_list(200)
    
    for dip in dipendenti:
        full_name = f"{dip.get('nome', '')} {dip.get('cognome', '')}".strip()
        if full_name.lower() not in seen_names:
            ops_raw.append({
                "op_id": dip.get("dipendente_id", ""),
                "admin_id": admin_id,
                "nome": full_name,
                "mansione": dip.get("ruolo", dip.get("tipo_contratto", "")),
                "source": "dipendenti",
            })
            seen_names.add(full_name.lower())
    
    return {"operatori": ops_raw}


@router.post("/{cid}/operatori", tags=["operatori"])
async def create_operatore(cid: str, data: OperatoreInput, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Create a new operator (just name, no email/login needed)."""
    admin_id = await _get_team_admin_id(user)
    op_id = f"op_{uuid.uuid4().hex[:8]}"

    doc = {
        "op_id": op_id,
        "admin_id": admin_id,
        "nome": data.nome.strip(),
        "mansione": data.mansione.strip() if data.mansione else "",
        "tenant_id": tenant_match(user),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db[OPERATORI_COLL].insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"Operatore created: {op_id} - {data.nome}")
    return doc


@router.delete("/{cid}/operatori/{op_id}", tags=["operatori"])
async def delete_operatore(cid: str, op_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Delete an operator."""
    admin_id = await _get_team_admin_id(user)
    result = await db[OPERATORI_COLL].delete_one({"op_id": op_id, "admin_id": admin_id, "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Operatore non trovato")
    return {"message": "Operatore eliminato"}



# ── PATENTINI OPERATORI ──────────────────────────────────────────

class PatentinoInput(BaseModel):
    tipo: str               # es. "Saldatura EN ISO 9606-1", "Brasatura"
    numero: Optional[str] = ""
    scadenza: str           # YYYY-MM-DD
    ente: Optional[str] = ""  # es. "IIS", "TÜV"


@router.post("/{cid}/operatori/{op_id}/patentini", tags=["operatori"])
async def add_patentino(cid: str, op_id: str, data: PatentinoInput, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Add a welding certificate to an operator."""
    admin_id = await _get_team_admin_id(user)
    pat_id = f"pat_{uuid.uuid4().hex[:8]}"

    patentino = {
        "pat_id": pat_id,
        "tipo": data.tipo,
        "numero": data.numero or "",
        "scadenza": data.scadenza,
        "ente": data.ente or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db[OPERATORI_COLL].update_one(
        {"op_id": op_id, "admin_id": admin_id, "tenant_id": tenant_match(user)},
        {"$push": {"patentini": patentino}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Operatore non trovato")
    return {"message": "Patentino aggiunto", "patentino": patentino}


@router.delete("/{cid}/operatori/{op_id}/patentini/{pat_id}", tags=["operatori"])
async def remove_patentino(cid: str, op_id: str, pat_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico", "officina"))):
    """Remove a welding certificate from an operator."""
    admin_id = await _get_team_admin_id(user)
    result = await db[OPERATORI_COLL].update_one(
        {"op_id": op_id, "admin_id": admin_id, "tenant_id": tenant_match(user)},
        {"$pull": {"patentini": {"pat_id": pat_id}}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Operatore non trovato")
    return {"message": "Patentino rimosso"}
