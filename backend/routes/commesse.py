"""Commesse (Projects / Workshop Orders) — Enhanced Hub Architecture.

Macchina a stati event-driven + Kanban board + Module hub.
Backward compatible with existing Kanban status field.

Lifecycle states (stato):
  richiesta → bozza → rilievo_completato → firmato →
  in_produzione → fatturato → chiuso  (+ sospesa)

The Kanban `status` field is kept for the board drag-and-drop and
auto-synced when `stato` changes via events.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/commesse", tags=["commesse"])
logger = logging.getLogger(__name__)
COLLECTION = "commesse"


# ── Lifecycle States & Events ────────────────────────────────────

STATI_LIFECYCLE = [
    "richiesta", "bozza", "rilievo_completato", "firmato",
    "in_produzione", "fatturato", "chiuso", "sospesa",
]

# Maps lifecycle stato → Kanban column (best-effort sync)
STATO_TO_KANBAN = {
    "richiesta":           "preventivo",
    "bozza":               "preventivo",
    "rilievo_completato":  "approvvigionamento",
    "firmato":             "lavorazione",
    "in_produzione":       "lavorazione",
    "fatturato":           "pronto_consegna",
    "chiuso":              "completato",
    "sospesa":             None,  # keep current kanban status
}

STATO_META = {
    "richiesta":           {"label": "Richiesta",           "color": "violet",  "order": 0},
    "bozza":               {"label": "Bozza",               "color": "slate",   "order": 1},
    "rilievo_completato":  {"label": "Rilievo Completato",  "color": "amber",   "order": 2},
    "firmato":             {"label": "Firmato",              "color": "blue",    "order": 3},
    "in_produzione":       {"label": "In Produzione",        "color": "orange",  "order": 4},
    "fatturato":           {"label": "Fatturato",            "color": "emerald", "order": 5},
    "chiuso":              {"label": "Chiuso",               "color": "slate",   "order": 6},
    "sospesa":             {"label": "Sospesa",              "color": "red",     "order": 7},
}

# Evento → { from: [allowed current states], to: new state }
# None in "from" means creation event (no prior state)
EVENTO_TRANSITIONS = {
    "COMMESSA_CREATA":        {"from": [None],                                                       "to": "bozza"},
    "RICHIESTA_PREVENTIVO":   {"from": [None],                                                       "to": "richiesta"},
    "RILIEVO_COMPLETATO":     {"from": ["bozza", "richiesta"],                                       "to": "rilievo_completato"},
    "FIRMA_CLIENTE":          {"from": ["rilievo_completato"],                                        "to": "firmato"},
    "PREVENTIVO_ACCETTATO":   {"from": ["richiesta", "bozza", "rilievo_completato"],                  "to": "firmato"},
    "AVVIO_PRODUZIONE":       {"from": ["firmato"],                                                   "to": "in_produzione"},
    "FATTURA_EMESSA":         {"from": ["in_produzione", "firmato"],                                  "to": "fatturato"},
    "CHIUSURA_COMMESSA":      {"from": ["fatturato", "in_produzione", "firmato"],                     "to": "chiuso"},
    "SOSPENSIONE":            {"from": ["bozza", "richiesta", "rilievo_completato", "firmato", "in_produzione"], "to": "sospesa"},
    "RIATTIVAZIONE":          {"from": ["sospesa"],                                                   "to": "__previous__"},
}

# Informational events — recorded but don't change stato
EVENTI_INFORMATIVI = [
    "PREVENTIVO_CREATO", "PREVENTIVO_GENERATO", "PDF_PREVENTIVO_GENERATO",
    "PRODUZIONE_GENERATA", "PRODUZIONE_INIZIATA", "PRODUZIONE_COMPLETATA",
    "FATTURA_GENERATA", "FATTURA_PAGATA", "DDT_CREATO",
    "MODULO_COLLEGATO", "MODULO_SCOLLEGATO", "NOTA_AGGIUNTA",
    "FPC_PROGETTO_CREATO", "CE_GENERATA", "DOSSIER_GENERATO",
]


# ── Kanban (kept for backward compatibility) ─────────────────────

KANBAN_META = {
    "preventivo":         {"label": "Nuove Commesse",     "order": 0},
    "approvvigionamento": {"label": "Approvvigionamento", "order": 1},
    "lavorazione":        {"label": "In Lavorazione",     "order": 2},
    "conto_lavoro":       {"label": "Conto Lavoro",       "order": 3},
    "pronto_consegna":    {"label": "Pronto / Consegna",  "order": 4},
    "montaggio":          {"label": "Montaggio / Posa",   "order": 5},
    "completato":         {"label": "Completato",         "order": 6},
}


# ── Pydantic Models ──────────────────────────────────────────────

class CantiereData(BaseModel):
    indirizzo: Optional[str] = ""
    citta: Optional[str] = ""
    cap: Optional[str] = ""
    contesto: Optional[str] = ""   # privato | condominio | industriale
    ambiente: Optional[str] = ""   # interno | esterno

class CommessaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    client_id: Optional[str] = None
    client_name: Optional[str] = ""
    description: Optional[str] = ""
    riferimento: Optional[str] = ""
    cantiere: Optional[CantiereData] = None
    value: Optional[float] = 0
    deadline: Optional[str] = None
    priority: Optional[str] = "media"
    notes: Optional[str] = ""
    # Normativa fields
    classe_exc: Optional[str] = ""          # EXC1, EXC2, EXC3, EXC4
    tipologia_chiusura: Optional[str] = ""  # cancello, ringhiera, porta, scala, struttura, altro
    normativa_tipo: Optional[str] = ""      # EN_1090, EN_13241, NESSUNA
    # Shortcut — pre-link a module at creation
    linked_preventivo_id: Optional[str] = None
    linked_distinta_id: Optional[str] = None
    linked_rilievo_id: Optional[str] = None
    # If True, start as "richiesta" (no survey)
    is_richiesta: Optional[bool] = False

class CommessaUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    riferimento: Optional[str] = None
    cantiere: Optional[CantiereData] = None
    value: Optional[float] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    classe_exc: Optional[str] = None
    tipologia_chiusura: Optional[str] = None

class EventoRequest(BaseModel):
    tipo: str
    note: Optional[str] = ""
    payload: Optional[dict] = None

class LinkModuleRequest(BaseModel):
    tipo: str     # rilievo | distinta | preventivo | fattura | ddt | fpc_project | certificazione
    module_id: str


# ── Helpers ──────────────────────────────────────────────────────

def make_empty_moduli():
    return {
        "rilievo_id": None,
        "distinta_id": None,
        "preventivo_id": None,
        "fatture_ids": [],
        "ddt_ids": [],
        "fpc_project_id": None,
        "certificazione_id": None,
    }


def ensure_moduli(doc):
    """Backward compat: migrate old linked_* fields to moduli dict."""
    if "moduli" not in doc:
        doc["moduli"] = make_empty_moduli()
        doc["moduli"]["preventivo_id"] = doc.get("linked_preventivo_id")
        doc["moduli"]["distinta_id"] = doc.get("linked_distinta_id")
        doc["moduli"]["rilievo_id"] = doc.get("linked_rilievo_id")
    if "stato" not in doc:
        doc["stato"] = "bozza"
    if "eventi" not in doc:
        doc["eventi"] = []
    if "cantiere" not in doc:
        doc["cantiere"] = {}
    if "riferimento" not in doc:
        doc["riferimento"] = ""
    # Initialize operational fields for backward compat
    if "approvvigionamento" not in doc:
        doc["approvvigionamento"] = {"richieste": [], "ordini": [], "arrivi": []}
    if "fasi_produzione" not in doc:
        doc["fasi_produzione"] = []
    if "conto_lavoro" not in doc:
        doc["conto_lavoro"] = []
    return doc


def build_event(tipo, user, note="", payload=None):
    return {
        "tipo": tipo,
        "data": datetime.now(timezone.utc).isoformat(),
        "operatore_id": user.get("user_id", ""),
        "operatore_nome": user.get("name", user.get("email", "")),
        "note": note or "",
        "payload": payload or {},
    }


async def generate_commessa_number(uid):
    """Generate sequential commessa number: NF-YYYY-NNNNNN."""
    year = datetime.now(timezone.utc).year
    count = await db[COLLECTION].count_documents({"user_id": uid})
    return f"NF-{year}-{count + 1:06d}"


# ── CRUD ─────────────────────────────────────────────────────────

@router.get("/")
async def list_commesse(
    status: Optional[str] = Query(None),
    stato: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if status:
        q["status"] = status
    if stato:
        q["stato"] = stato
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
            {"numero": {"$regex": search, "$options": "i"}},
        ]
    items = await db[COLLECTION].find(q, {"_id": 0, "eventi": 0}).sort("created_at", -1).to_list(500)
    for item in items:
        ensure_moduli(item)
    return {"items": items, "total": len(items)}


@router.post("/", status_code=201)
async def create_commessa(data: CommessaCreate, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    cid = f"com_{uuid.uuid4().hex[:12]}"
    numero = await generate_commessa_number(uid)

    client_name = data.client_name or ""
    if data.client_id and not client_name:
        client = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0, "business_name": 1})
        client_name = client.get("business_name", "") if client else ""

    initial_stato = "richiesta" if data.is_richiesta else "bozza"
    initial_event_type = "RICHIESTA_PREVENTIVO" if data.is_richiesta else "COMMESSA_CREATA"
    initial_kanban = STATO_TO_KANBAN.get(initial_stato, "preventivo")

    moduli = make_empty_moduli()
    moduli["preventivo_id"] = data.linked_preventivo_id
    moduli["distinta_id"] = data.linked_distinta_id
    moduli["rilievo_id"] = data.linked_rilievo_id

    doc = {
        "commessa_id": cid,
        "numero": numero,
        "user_id": uid,
        "title": data.title,
        "client_id": data.client_id or "",
        "client_name": client_name,
        "description": data.description or "",
        "riferimento": data.riferimento or "",
        "cantiere": (data.cantiere.model_dump() if data.cantiere else {}),
        "value": float(data.value or 0),
        "deadline": data.deadline,
        "status": initial_kanban,
        "stato": initial_stato,
        "stato_precedente": None,
        "priority": data.priority or "media",
        "moduli": moduli,
        "eventi": [build_event(initial_event_type, user, f"Commessa {numero} creata")],
        "notes": data.notes or "",
        "classe_exc": data.classe_exc or "",
        "tipologia_chiusura": data.tipologia_chiusura or "",
        "normativa_tipo": data.normativa_tipo or "",
        "status_history": [{"status": initial_kanban, "date": now.isoformat(), "note": "Creazione"}],
        # Keep old fields for backward compat
        "linked_preventivo_id": data.linked_preventivo_id,
        "linked_distinta_id": data.linked_distinta_id,
        "linked_rilievo_id": data.linked_rilievo_id,
        # Operational fields for commessa_ops routes
        "approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []},
        "fasi_produzione": [],
        "conto_lavoro": [],
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"commessa_id": cid}, {"_id": 0})
    return created


@router.get("/stati", response_model=None)
async def get_stati_meta():
    """Return lifecycle states metadata."""
    return {"stati": STATO_META, "transitions": {k: v for k, v in EVENTO_TRANSITIONS.items()}}


@router.get("/board/view")
async def get_board_view(user: dict = Depends(get_current_user)):
    """Return all commesse grouped by Kanban status for the board.
    Also includes accepted quotes (preventivi accettati) without a linked commessa.
    """
    uid = user["user_id"]
    items = await db[COLLECTION].find({"user_id": uid}, {"_id": 0, "eventi": 0}).sort("updated_at", -1).to_list(500)

    columns = {}
    for key, meta in KANBAN_META.items():
        columns[key] = {"id": key, "label": meta["label"], "order": meta["order"], "items": []}

    # Collect all preventivo IDs already linked to a commessa
    linked_prev_ids = set()
    for item in items:
        ensure_moduli(item)
        st = item.get("status", "preventivo")
        if st in columns:
            columns[st]["items"].append(item)
        # Track linked preventivo IDs
        prev_id = item.get("moduli", {}).get("preventivo_id") or item.get("linked_preventivo_id")
        if prev_id:
            linked_prev_ids.add(prev_id)

    # Fetch accepted preventivi without a linked commessa
    accepted_prevs = await db.preventivi.find(
        {"user_id": uid, "status": "accettato"},
        {"_id": 0, "preventivo_id": 1, "number": 1, "subject": 1,
         "client_id": 1, "client_name": 1, "_migrated_client_name": 1,
         "totals": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", -1).to_list(200)

    for prev in accepted_prevs:
        if prev["preventivo_id"] in linked_prev_ids:
            continue  # Already has a commessa, skip
        # Resolve client name
        client_name = prev.get("client_name", "")
        if not client_name and prev.get("client_id"):
            c = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1})
            client_name = c.get("business_name", "") if c else prev.get("_migrated_client_name", "")
        elif not client_name:
            client_name = prev.get("_migrated_client_name", "")
        # Build a board-compatible card item
        # Note: preventivo_id already has 'prev_' prefix, so just use it directly for uniqueness
        card = {
            "commessa_id": prev['preventivo_id'],  # Already has 'prev_' prefix
            "preventivo_id": prev["preventivo_id"],
            "is_preventivo": True,
            "title": prev.get("subject") or prev.get("number", "Preventivo"),
            "numero": prev.get("number", ""),
            "client_name": client_name,
            "value": float(prev.get("totals", {}).get("total", 0)),
            "priority": "media",
            "status": "preventivo",
            "created_at": prev.get("created_at"),
            "updated_at": prev.get("updated_at"),
        }
        columns["preventivo"]["items"].append(card)

    sorted_cols = sorted(columns.values(), key=lambda c: c["order"])
    total = sum(len(col["items"]) for col in sorted_cols)
    return {"columns": sorted_cols, "total": total}


@router.get("/{commessa_id}")
async def get_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Commessa non trovata")
    ensure_moduli(doc)
    return doc


@router.put("/{commessa_id}")
async def update_commessa(commessa_id: str, data: CommessaUpdate, user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    existing = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not existing:
        raise HTTPException(404, "Commessa non trovata")

    updates = {}
    for k, v in data.model_dump().items():
        if v is not None:
            if k == "cantiere":
                updates["cantiere"] = v
            else:
                updates[k] = v
    updates["updated_at"] = datetime.now(timezone.utc)

    await db[COLLECTION].update_one({"commessa_id": commessa_id}, {"$set": updates})
    updated = await db[COLLECTION].find_one({"commessa_id": commessa_id}, {"_id": 0})
    ensure_moduli(updated)
    return updated


@router.delete("/{commessa_id}")
async def delete_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one({"commessa_id": commessa_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Commessa non trovata")
    return {"message": "Commessa eliminata"}


# ── Kanban: Status Update (Drag & Drop) ─────────────────────────

@router.patch("/{commessa_id}/status")
async def update_commessa_status(
    commessa_id: str,
    new_status: str = Body(..., embed=True),
    user: dict = Depends(get_current_user),
):
    """Update Kanban status — called on drag & drop. Does NOT change lifecycle stato."""
    uid = user["user_id"]
    if new_status not in KANBAN_META:
        raise HTTPException(422, f"Stato Kanban non valido: {new_status}")

    existing = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not existing:
        raise HTTPException(404, "Commessa non trovata")

    now = datetime.now(timezone.utc)
    history_entry = {"status": new_status, "date": now.isoformat(), "note": f"Spostata a: {KANBAN_META[new_status]['label']}"}

    await db[COLLECTION].update_one(
        {"commessa_id": commessa_id},
        {
            "$set": {"status": new_status, "updated_at": now},
            "$push": {"status_history": history_entry},
        },
    )
    updated = await db[COLLECTION].find_one({"commessa_id": commessa_id}, {"_id": 0})
    ensure_moduli(updated)
    return updated


# ── Event Sourcing: Emit Event ───────────────────────────────────

class ChecklistToggle(BaseModel):
    checked: bool = False

@router.patch("/{commessa_id}/checklist/{item_key}")
async def toggle_checklist_item(
    commessa_id: str, item_key: str,
    body: ChecklistToggle,
    user: dict = Depends(get_current_user)
):
    """Toggle a single checklist item. Uses $set puntuale."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one(
        {"commessa_id": commessa_id, "user_id": uid},
        {"_id": 0, "commessa_id": 1}
    )
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    now = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"commessa_id": commessa_id},
        {"$set": {
            f"checklist_stato.{item_key}": {
                "checked": body.checked,
                "data": now,
                "utente": user.get("name", uid),
                "documento_id": None,
            },
            "updated_at": now,
        }}
    )
    return {"item_key": item_key, "checked": body.checked}


@router.post("/{commessa_id}/eventi")
async def emit_event(commessa_id: str, req: EventoRequest, user: dict = Depends(get_current_user)):
    """Emit a lifecycle event. Validates state transition rules."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    ensure_moduli(doc)
    current_stato = doc.get("stato", "bozza")
    tipo = req.tipo.upper()

    # Check if it's a state-changing event
    if tipo in EVENTO_TRANSITIONS:
        trans = EVENTO_TRANSITIONS[tipo]
        allowed_from = trans["from"]

        # Validate current state is allowed
        if allowed_from != [None] and current_stato not in allowed_from:
            raise HTTPException(
                400,
                f"Transizione non valida: {tipo} non permesso da stato '{current_stato}'. "
                f"Stati consentiti: {allowed_from}"
            )

        new_stato = trans["to"]

        # Handle RIATTIVAZIONE — restore previous state
        if new_stato == "__previous__":
            new_stato = doc.get("stato_precedente", "bozza")

        # Build updates
        now = datetime.now(timezone.utc)
        updates = {
            "stato": new_stato,
            "updated_at": now,
        }

        # Store previous state for potential SOSPESA recovery
        if tipo == "SOSPENSIONE":
            updates["stato_precedente"] = current_stato

        # Auto-sync Kanban status
        kanban = STATO_TO_KANBAN.get(new_stato)
        if kanban:
            updates["status"] = kanban

        event = build_event(tipo, user, req.note, req.payload)
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$set": updates, "$push": {"eventi": event}},
        )

        logger.info(f"Commessa {commessa_id}: {tipo} → {new_stato}")
        return {
            "message": f"Evento {tipo} emesso. Stato: {STATO_META.get(new_stato, {}).get('label', new_stato)}",
            "stato": new_stato,
            "stato_label": STATO_META.get(new_stato, {}).get("label", new_stato),
        }

    elif tipo in EVENTI_INFORMATIVI or tipo.startswith("CUSTOM_"):
        # Informational event — just record it, no state change
        event = build_event(tipo, user, req.note, req.payload)
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$push": {"eventi": event}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        )
        return {"message": f"Evento {tipo} registrato", "stato": current_stato}

    else:
        raise HTTPException(400, f"Tipo evento sconosciuto: {tipo}")


# ── Module Linking ───────────────────────────────────────────────

MODULE_FIELDS = {
    "rilievo":        "rilievo_id",
    "distinta":       "distinta_id",
    "preventivo":     "preventivo_id",
    "fattura":        "fatture_ids",
    "ddt":            "ddt_ids",
    "fpc_project":    "fpc_project_id",
    "certificazione": "certificazione_id",
}


@router.get("/{commessa_id}/available-modules")
async def get_available_modules(commessa_id: str, tipo: str = "preventivo", user: dict = Depends(get_current_user)):
    """Get available modules of a given type for linking to a commessa."""
    uid = user["user_id"]
    results = []

    if tipo == "preventivo":
        docs = await db.preventivi.find(
            {"user_id": uid},
            {"_id": 0, "preventivo_id": 1, "number": 1, "client_name": 1, "status": 1}
        ).to_list(100)
        for d in docs:
            results.append({
                "id": d["preventivo_id"],
                "label": f"{d.get('number', d['preventivo_id'])} — {d.get('client_name', 'N/D')}",
                "status": d.get("status", ""),
            })
    elif tipo == "fattura":
        docs = await db.invoices.find(
            {"user_id": uid},
            {"_id": 0, "invoice_id": 1, "document_number": 1, "document_type": 1, "status": 1}
        ).to_list(200)
        for d in docs:
            results.append({
                "id": d["invoice_id"],
                "label": f"{d.get('document_number', d['invoice_id'])} ({d.get('document_type','FT')})",
                "status": d.get("status", ""),
            })
    elif tipo == "ddt":
        docs = await db.ddt.find(
            {"user_id": uid},
            {"_id": 0, "ddt_id": 1, "number": 1, "ddt_type": 1, "status": 1}
        ).to_list(200)
        for d in docs:
            results.append({
                "id": d["ddt_id"],
                "label": f"DDT {d.get('number', d['ddt_id'])} ({d.get('ddt_type','vendita')})",
                "status": d.get("status", ""),
            })
    elif tipo == "rilievo":
        docs = await db.rilievi.find(
            {"user_id": uid},
            {"_id": 0, "rilievo_id": 1, "title": 1, "status": 1}
        ).to_list(100)
        for d in docs:
            results.append({
                "id": d["rilievo_id"],
                "label": d.get("title", d["rilievo_id"]),
                "status": d.get("status", ""),
            })
    elif tipo == "distinta":
        docs = await db.distinte.find(
            {"user_id": uid},
            {"_id": 0, "distinta_id": 1, "title": 1, "product_name": 1}
        ).to_list(100)
        for d in docs:
            results.append({
                "id": d["distinta_id"],
                "label": d.get("title") or d.get("product_name", d["distinta_id"]),
            })

    return {"modules": results}


@router.post("/{commessa_id}/link-module")
async def link_module(commessa_id: str, req: LinkModuleRequest, user: dict = Depends(get_current_user)):
    """Link a module (preventivo, fattura, etc.) to this commessa."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    field = MODULE_FIELDS.get(req.tipo)
    if not field:
        raise HTTPException(400, f"Tipo modulo non valido: {req.tipo}. Validi: {list(MODULE_FIELDS.keys())}")

    ensure_moduli(doc)
    now = datetime.now(timezone.utc)

    if field.endswith("_ids"):
        # Array field — append if not already there
        current = doc.get("moduli", {}).get(field, [])
        if req.module_id in current:
            return {"message": f"Modulo {req.tipo} gia' collegato", "moduli": doc["moduli"]}
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {
                "$push": {f"moduli.{field}": req.module_id},
                "$set": {"updated_at": now},
            },
        )
    else:
        # Single value field
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$set": {f"moduli.{field}": req.module_id, "updated_at": now}},
        )

    # Also keep backward-compat fields
    compat_map = {"preventivo_id": "linked_preventivo_id", "distinta_id": "linked_distinta_id", "rilievo_id": "linked_rilievo_id"}
    if field in compat_map:
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$set": {compat_map[field]: req.module_id}},
        )

    # Record informational event
    event = build_event("MODULO_COLLEGATO", user, f"{req.tipo} collegato", {"tipo": req.tipo, "module_id": req.module_id})
    await db[COLLECTION].update_one({"commessa_id": commessa_id}, {"$push": {"eventi": event}})

    updated = await db[COLLECTION].find_one({"commessa_id": commessa_id}, {"_id": 0})
    ensure_moduli(updated)
    return {"message": f"Modulo {req.tipo} collegato", "moduli": updated["moduli"]}


@router.post("/{commessa_id}/unlink-module")
async def unlink_module(commessa_id: str, req: LinkModuleRequest, user: dict = Depends(get_current_user)):
    """Unlink a module from this commessa."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    field = MODULE_FIELDS.get(req.tipo)
    if not field:
        raise HTTPException(400, f"Tipo modulo non valido: {req.tipo}")

    now = datetime.now(timezone.utc)
    if field.endswith("_ids"):
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$pull": {f"moduli.{field}": req.module_id}, "$set": {"updated_at": now}},
        )
    else:
        await db[COLLECTION].update_one(
            {"commessa_id": commessa_id},
            {"$set": {f"moduli.{field}": None, "updated_at": now}},
        )

    event = build_event("MODULO_SCOLLEGATO", user, f"{req.tipo} scollegato", {"tipo": req.tipo, "module_id": req.module_id})
    await db[COLLECTION].update_one({"commessa_id": commessa_id}, {"$push": {"eventi": event}})

    return {"message": f"Modulo {req.tipo} scollegato"}


# ── Hub View (aggregated) ────────────────────────────────────────

@router.get("/{commessa_id}/hub")
async def get_commessa_hub(commessa_id: str, user: dict = Depends(get_current_user)):
    """Full hub view: commessa + all linked modules fetched from their collections."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    ensure_moduli(doc)
    # Garantisci che checklist_stato sia sempre un oggetto
    if "checklist_stato" not in doc:
        doc["checklist_stato"] = {}
    moduli = doc.get("moduli", {})

    hub = {
        "commessa": doc,
        "moduli_dettaglio": {},
    }

    proj = {"_id": 0}
    proj_light = {"_id": 0, "certificate_base64": 0}  # exclude heavy fields

    # Fetch linked modules in parallel-style
    if moduli.get("rilievo_id"):
        r = await db.rilievi.find_one({"rilievo_id": moduli["rilievo_id"], "user_id": uid}, proj)
        if r:
            hub["moduli_dettaglio"]["rilievo"] = r

    if moduli.get("distinta_id"):
        d = await db.distinte.find_one({"distinta_id": moduli["distinta_id"], "user_id": uid}, proj)
        if d:
            hub["moduli_dettaglio"]["distinta"] = d

    if moduli.get("preventivo_id"):
        p = await db.preventivi.find_one({"preventivo_id": moduli["preventivo_id"], "user_id": uid}, proj)
        if p:
            hub["moduli_dettaglio"]["preventivo"] = p

    if moduli.get("fatture_ids"):
        fatture = await db.invoices.find(
            {"invoice_id": {"$in": moduli["fatture_ids"]}, "user_id": uid}, proj
        ).to_list(50)
        hub["moduli_dettaglio"]["fatture"] = fatture

    if moduli.get("ddt_ids"):
        ddts = await db.ddt_documents.find(
            {"ddt_id": {"$in": moduli["ddt_ids"]}, "user_id": uid}, proj
        ).to_list(50)
        hub["moduli_dettaglio"]["ddt"] = ddts

    if moduli.get("fpc_project_id"):
        fpc = await db.fpc_projects.find_one({"project_id": moduli["fpc_project_id"], "user_id": uid}, proj_light)
        if fpc:
            hub["moduli_dettaglio"]["fpc_project"] = fpc

    if moduli.get("certificazione_id"):
        cert = await db.certificazioni.find_one({"cert_id": moduli["certificazione_id"], "user_id": uid}, proj)
        if cert:
            hub["moduli_dettaglio"]["certificazione"] = cert

    # Compute invoicing summary if preventivo exists
    prev = hub["moduli_dettaglio"].get("preventivo")
    if prev:
        total_prev = float(prev.get("totals", {}).get("total", 0))
        total_invoiced = float(prev.get("total_invoiced", 0))
        hub["fatturazione_summary"] = {
            "total_preventivo": total_prev,
            "total_invoiced": total_invoiced,
            "remaining": round(total_prev - total_invoiced, 2),
            "percentage": round(total_invoiced / total_prev * 100, 1) if total_prev > 0 else 0,
        }

    return hub


# ── Keyword lists for smart normativa detection ─────────────────

KW_13241 = ["cancell", "portone", "scorrevol", "battente", "chiusura", "serranda", "sezionale", "barriera"]
KW_1090 = ["tettoia", "scala", "soppalco", "trave", "struttura", "pensilina", "carpenteria", "ringhier"]
KW_MOTOR = ["motore", "motorizzat", "motorizzaz", "bft", "came", "faac", "nice", "automazione", "fotocellul"]


def _classify_line(description: str):
    """Classify a single line description as EN_1090, EN_13241, or None."""
    text = description.lower()
    is_1090 = any(kw in text for kw in KW_1090)
    is_13241 = any(kw in text for kw in KW_13241)
    if is_1090 and not is_13241:
        return "EN_1090"
    if is_13241 and not is_1090:
        return "EN_13241"
    if is_1090 and is_13241:
        return "EN_1090"  # Default priority to EN 1090 for ambiguous single lines
    return None


def analyze_preventivo_content(preventivo: dict):
    """Analyze preventivo lines and detect normativa conflict.
    Returns a report with groups and suggested action.
    """
    items_1090 = []
    items_13241 = []
    items_other = []

    for idx, line in enumerate(preventivo.get("lines", [])):
        desc = line.get("description") or ""  # Handle None values
        classification = _classify_line(desc)
        item = {
            "index": idx,
            "line_id": line.get("line_id", ""),
            "description": desc,
            "quantity": line.get("quantity", 1),
            "unit": line.get("unit", "pz"),
            "unit_price": line.get("unit_price", 0),
        }
        if classification == "EN_1090":
            items_1090.append(item)
        elif classification == "EN_13241":
            items_13241.append(item)
        else:
            items_other.append(item)

    has_1090 = len(items_1090) > 0
    has_13241 = len(items_13241) > 0
    conflict = has_1090 and has_13241

    # Detect motorization from full text
    # Handle None values: .get() returns None if key exists with None value
    subject = preventivo.get("subject") or ""
    notes = preventivo.get("notes") or ""
    line_descs = [(l.get("description") or "") for l in preventivo.get("lines", [])]
    full_text = " ".join([subject, notes] + line_descs).lower()
    is_motorizzato = any(kw in full_text for kw in KW_MOTOR)

    if conflict:
        suggested_action = "split"
    elif has_1090 or has_13241:
        suggested_action = "single"
    else:
        suggested_action = "single"

    # Determine single normativa when no conflict
    single_normativa = None
    if not conflict:
        if has_13241:
            single_normativa = "EN_13241"
        elif has_1090:
            single_normativa = "EN_1090"

    return {
        "conflict": conflict,
        "suggested_action": suggested_action,
        "single_normativa": single_normativa,
        "is_motorizzato": is_motorizzato,
        "groups": {
            "en_1090": items_1090,
            "en_13241": items_13241,
            "non_classificati": items_other,
        },
        "score_1090": len(items_1090),
        "score_13241": len(items_13241),
    }


# ── Analyze Preventivo (for frontend conflict detection) ─────────

@router.get("/analyze-preventivo/{preventivo_id}")
async def analyze_preventivo_endpoint(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Analyze a preventivo's lines and detect normativa conflicts (EN 1090 vs EN 13241)."""
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")
    return analyze_preventivo_content(prev)


# ── Quick Create from Preventivo ─────────────────────────────────

async def _create_single_commessa(preventivo, user, normativa_override=None, items_filter=None, suffix="", parent_preventivo_id=None):
    """Internal helper: creates a single commessa from a preventivo (or a subset of its items).
    Used both for single-commessa creation and split-commessa creation.
    """
    uid = user["user_id"]
    prev = preventivo
    preventivo_id = prev["preventivo_id"]

    client_name = ""
    if prev.get("client_id"):
        client = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1})
        client_name = client.get("business_name", "") if client else ""

    # Filter items if specified
    lines = prev.get("lines", [])
    if items_filter is not None:
        lines = [l for idx, l in enumerate(lines) if idx in items_filter]

    # Calculate value from filtered lines
    value = 0
    for l in lines:
        qty = float(l.get("quantity", 1) or 1)
        price = float(l.get("unit_price", 0) or 0)
        s1 = float(l.get("sconto_1", 0) or 0) / 100
        s2 = float(l.get("sconto_2", 0) or 0) / 100
        value += qty * price * (1 - s1) * (1 - s2)

    # Detect normativa: fonte primaria = campo esplicito del preventivo
    # Fallback = keyword matching solo se il campo non è presente
    prev_normativa = prev.get("normativa") or None
    if prev_normativa and prev_normativa != "NESSUNA":
        # Campo esplicito scelto dall'utente — fonte più affidabile
        detected_normativa = normativa_override or prev_normativa
    elif normativa_override:
        detected_normativa = normativa_override
    else:
        # Fallback: keyword matching sul testo delle righe
        full_text = " ".join([(prev.get("subject") or ""), (prev.get("notes") or "")] +
                             [(l.get("description") or "") for l in lines]).lower()
        score_13241 = sum(1 for kw in KW_13241 if kw in full_text)
        score_1090 = sum(1 for kw in KW_1090 if kw in full_text)
        if score_13241 > score_1090 and score_13241 > 0:
            detected_normativa = "EN_13241"
        elif score_1090 > score_13241 and score_1090 > 0:
            detected_normativa = "EN_1090"
        else:
            detected_normativa = None

    full_text = " ".join([(prev.get("subject") or ""), (prev.get("notes") or "")] +
                         [(l.get("description") or "") for l in lines]).lower()
    is_motorizzato = any(kw in full_text for kw in KW_MOTOR)
    detected_azionamento = "motorizzato" if is_motorizzato and detected_normativa == "EN_13241" else (
        "manuale" if detected_normativa == "EN_13241" else None
    )

    now = datetime.now(timezone.utc)
    cid = f"com_{uuid.uuid4().hex[:12]}"
    numero = await generate_commessa_number(uid)
    if suffix:
        numero = f"{numero}-{suffix}"

    moduli = make_empty_moduli()
    moduli["preventivo_id"] = preventivo_id

    # Build title
    norm_labels = {"EN_1090": "Strutture", "EN_13241": "Cancelli/Chiusure"}
    title_suffix = f" ({norm_labels.get(detected_normativa, '')})" if detected_normativa and suffix else ""
    title = (prev.get("subject") or f"Commessa da {prev.get('number', preventivo_id)}") + title_suffix

    doc = {
        "commessa_id": cid,
        "numero": numero,
        "user_id": uid,
        "title": title,
        "client_id": prev.get("client_id", ""),
        "client_name": client_name,
        "description": prev.get("notes", ""),
        "riferimento": prev.get("riferimento", ""),
        "cantiere": {},
        "value": round(value, 2),
        "deadline": None,
        "status": "preventivo",
        "stato": "richiesta",
        "stato_precedente": None,
        "priority": "media",
        "moduli": moduli,
        "eventi": [
            build_event("RICHIESTA_PREVENTIVO", user, f"Creata da preventivo {prev.get('number', '')}"),
            build_event("MODULO_COLLEGATO", user, "Preventivo collegato", {"tipo": "preventivo", "module_id": preventivo_id}),
        ],
        "notes": f"Generata da Preventivo {prev.get('number', '')}",
        "linked_preventivo_id": preventivo_id,
        "linked_distinta_id": None,
        "linked_rilievo_id": None,
        "split_items": [i["line_id"] if isinstance(i, dict) else i for i in (items_filter or [])],
        "split_suffix": suffix,
        "status_history": [{"status": "preventivo", "date": now.isoformat(), "note": f"Creata da preventivo {prev.get('number', '')}"}],
        "created_at": now,
        "updated_at": now,
    }

    # Copia campi aggiuntivi dal preventivo se presenti
    compliance = prev.get("compliance_detail") or {}
    if prev.get("classe_exc") or compliance.get("classe_exc"):
        doc["classe_exc"] = prev.get("classe_exc") or compliance.get("classe_exc", "")
    if prev.get("redatto_da") or prev.get("ingegnere"):
        doc["riferimento_ingegnere"] = prev.get("redatto_da") or prev.get("ingegnere", "")
    if prev.get("numero_disegno") or prev.get("n_disegno"):
        doc["numero_disegno"] = prev.get("numero_disegno") or prev.get("n_disegno", "")

    if detected_normativa:
        doc["normativa_tipo"] = detected_normativa
        note_norm = "EN 13241 (Cancelli)" if detected_normativa == "EN_13241" else "EN 1090 (Strutture)"
        if detected_azionamento:
            doc["detected_azionamento"] = detected_azionamento
            note_norm += f" — {detected_azionamento.title()}"
        doc["eventi"].append(
            build_event("NORMATIVA_RILEVATA", user, f"Normativa rilevata: {note_norm}")
        )
    if suffix:
        doc["eventi"].append(
            build_event("SPLIT_COMMESSA", user, f"Split commessa (suffisso {suffix}) da preventivo misto")
        )

    await db[COLLECTION].insert_one(doc)

    # If EN 13241 detected, auto-create gate certification
    if detected_normativa == "EN_13241":
        from routes.gate_certification import DEFAULT_RISCHI
        tipo_map = {
            "scorrevol": "cancello_scorrevole", "battente": "cancello_battente",
            "portone": "portone_industriale", "serranda": "serranda",
            "sezionale": "portone_sezionale", "barriera": "barriera",
        }
        tipo_chiusura = "cancello_scorrevole"
        for kw, tipo in tipo_map.items():
            if kw in full_text:
                tipo_chiusura = tipo
                break

        azionamento = detected_azionamento or "manuale"
        rischi = [dict(r) for r in DEFAULT_RISCHI] if azionamento == "motorizzato" else []

        gate_doc = {
            "cert_id": f"gate_{uuid.uuid4().hex[:12]}",
            "commessa_id": cid,
            "user_id": uid,
            "tipo_chiusura": tipo_chiusura,
            "azionamento": azionamento,
            "larghezza_mm": None, "altezza_mm": None, "peso_kg": None,
            "resistenza_vento": "Classe 2",
            "permeabilita_aria": "NPD", "resistenza_termica": "NPD",
            "sicurezza_apertura": "Conforme", "sostanze_pericolose": "NPD",
            "resistenza_acqua": "NPD",
            "analisi_rischi": rischi,
            "prove_forza": [],
            "motore_marca": "", "motore_modello": "", "motore_matricola": "",
            "fotocellule": "", "costola_sicurezza": "", "centralina": "", "telecomando": "",
            "strumento_id": None, "sistema_cascata": "", "note": "",
            "created_at": now, "updated_at": now,
        }
        await db.gate_certifications.insert_one(gate_doc)
        await db[COLLECTION].update_one(
            {"commessa_id": cid}, {"$set": {"gate_cert_id": gate_doc["cert_id"]}}
        )

    created = await db[COLLECTION].find_one({"commessa_id": cid}, {"_id": 0})
    return created


@router.post("/from-preventivo/{preventivo_id}")
async def create_commessa_from_preventivo(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Create a commessa from a Preventivo — auto-links the preventivo module.
    Smart Quote Analysis: auto-detects normativa (EN 1090 vs EN 13241) and azionamento from content.
    """
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")
    return await _create_single_commessa(prev, user)


@router.post("/from-preventivo/{preventivo_id}/generica")
async def create_commessa_generica(preventivo_id: str, user: dict = Depends(get_current_user)):
    """Create a generic commessa (no NF number, no normativa) for tracking OdA etc.
    Used for non-structural work that still needs order tracking and planning.
    """
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    client_name = ""
    if prev.get("client_id"):
        client = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1})
        client_name = client.get("business_name", "") if client else ""

    lines = prev.get("lines", [])
    value = sum(
        float(l.get("quantity", 1) or 1) * float(l.get("unit_price", 0) or 0)
        * (1 - float(l.get("sconto_1", 0) or 0) / 100)
        * (1 - float(l.get("sconto_2", 0) or 0) / 100)
        for l in lines
    )

    now = datetime.now(timezone.utc)
    cid = f"com_{uuid.uuid4().hex[:12]}"

    title = prev.get("subject") or f"Commessa da {prev.get('number', preventivo_id)}"
    moduli = make_empty_moduli()
    moduli["preventivo_id"] = preventivo_id

    doc = {
        "commessa_id": cid,
        "numero": f"GEN-{prev.get('number', '')}",
        "user_id": uid,
        "title": title,
        "client_id": prev.get("client_id", ""),
        "client_name": client_name,
        "description": prev.get("notes", ""),
        "riferimento": prev.get("riferimento", ""),
        "cantiere": {},
        "value": round(value, 2),
        "deadline": None,
        "status": "preventivo",
        "stato": "richiesta",
        "stato_precedente": None,
        "priority": "media",
        "generica": True,
        "moduli": moduli,
        "eventi": [
            build_event("RICHIESTA_PREVENTIVO", user, f"Commessa generica da preventivo {prev.get('number', '')}"),
            build_event("MODULO_COLLEGATO", user, "Preventivo collegato", {"tipo": "preventivo", "module_id": preventivo_id}),
        ],
        "notes": f"Commessa generica da Preventivo {prev.get('number', '')}",
        "linked_preventivo_id": preventivo_id,
        "linked_distinta_id": None,
        "linked_rilievo_id": None,
        "status_history": [{"status": "preventivo", "date": now.isoformat(), "note": f"Commessa generica da preventivo {prev.get('number', '')}"}],
        "created_at": now,
        "updated_at": now,
    }

    await db[COLLECTION].insert_one(doc)

    # Update preventivo status
    await db.preventivi.update_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"$set": {"status": "accettato", "updated_at": now}}
    )

    created = await db[COLLECTION].find_one({"commessa_id": cid}, {"_id": 0})
    return created


# ── Split Create from Preventivo (mixed normativa) ──────────────

class SplitCommessaConfig(BaseModel):
    suffix: str  # "A" or "B"
    normativa: str  # "EN_1090" or "EN_13241"
    item_indices: List[int]  # Indices of lines in the original preventivo

class SplitCommessaRequest(BaseModel):
    commesse: List[SplitCommessaConfig]

@router.post("/from-preventivo/{preventivo_id}/split")
async def create_split_commesse(preventivo_id: str, body: SplitCommessaRequest, user: dict = Depends(get_current_user)):
    """Create multiple commesse from a single Preventivo (split by normativa).
    Each commessa gets only the items assigned to it.
    """
    uid = user["user_id"]
    prev = await db.preventivi.find_one({"preventivo_id": preventivo_id, "user_id": uid}, {"_id": 0})
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    if len(body.commesse) < 2:
        raise HTTPException(400, "Lo split richiede almeno 2 commesse")

    # Validate no duplicate indices
    all_indices = []
    for cfg in body.commesse:
        all_indices.extend(cfg.item_indices)
    if len(all_indices) != len(set(all_indices)):
        raise HTTPException(400, "Indici duplicati tra le commesse")

    results = []
    for cfg in body.commesse:
        created = await _create_single_commessa(
            prev, user,
            normativa_override=cfg.normativa,
            items_filter=set(cfg.item_indices),
            suffix=cfg.suffix,
        )
        results.append(created)

    # Mark preventivo as "Accettato (Split)"
    await db.preventivi.update_one(
        {"preventivo_id": preventivo_id, "user_id": uid},
        {"$set": {
            "status": "accettato",
            "split_commesse": [{"commessa_id": r["commessa_id"], "numero": r["numero"], "normativa": r.get("normativa_tipo", "")} for r in results],
        }},
    )

    return {
        "message": f"Create {len(results)} commesse da preventivo misto",
        "commesse": results,
    }


# ── Chiusura Diretta (senza certificazione) ──────────────────────

CHIUSURA_DIRETTA_ALLOWED = [
    "richiesta", "bozza", "rilievo_completato", "firmato",
    "in_produzione", "fatturato",
]


@router.post("/{commessa_id}/complete-simple")
async def complete_commessa_simple(
    commessa_id: str,
    note: Optional[str] = Body(None, embed=True),
    user: dict = Depends(get_current_user),
):
    """Close a commessa directly without going through certification/production steps."""
    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    current_stato = doc.get("stato", "bozza")
    if current_stato not in CHIUSURA_DIRETTA_ALLOWED:
        raise HTTPException(
            400,
            f"Chiusura diretta non permessa dallo stato '{current_stato}'. "
            f"Stati consentiti: {CHIUSURA_DIRETTA_ALLOWED}"
        )

    now = datetime.now(timezone.utc)
    event = build_event(
        "CHIUSURA_DIRETTA", user,
        note or "Commessa chiusa senza certificazione (percorso semplificato)",
    )

    await db[COLLECTION].update_one(
        {"commessa_id": commessa_id},
        {
            "$set": {
                "stato": "chiuso",
                "stato_precedente": current_stato,
                "status": "completato",
                "updated_at": now,
            },
            "$push": {
                "eventi": event,
                "status_history": {
                    "status": "completato",
                    "date": now.isoformat(),
                    "note": "Chiusura diretta senza certificazione",
                },
            },
        },
    )

    logger.info(f"Commessa {commessa_id}: chiusura diretta da '{current_stato}' → chiuso")
    return {
        "message": "Commessa chiusa con successo",
        "stato": "chiuso",
        "stato_label": "Chiuso",
    }


# ── Dossier Unico di Commessa ────────────────────────────────────

@router.get("/{commessa_id}/dossier")
async def generate_commessa_dossier(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate the professional Technical Dossier (Fascicolo Tecnico).
    Replaces the old event-log dossier with the full EN 1090 document."""
    from services.pdf_super_fascicolo import generate_super_fascicolo

    uid = user["user_id"]
    doc = await db[COLLECTION].find_one({"commessa_id": commessa_id, "user_id": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")

    try:
        pdf_buf = await generate_super_fascicolo(commessa_id, uid)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Dossier generation error: {e}")
        raise HTTPException(500, f"Errore generazione dossier: {str(e)}")

    from fastapi.responses import StreamingResponse
    numero = doc.get("numero", commessa_id).replace("/", "-")
    filename = f"Dossier_{numero}.pdf"

    # Record event
    event = build_event("DOSSIER_GENERATO", user, f"Fascicolo Tecnico generato per {numero}")
    await db[COLLECTION].update_one({"commessa_id": commessa_id}, {"$push": {"eventi": event}})

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
