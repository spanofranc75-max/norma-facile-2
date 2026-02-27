"""Sicurezza Cantieri (POS Generator) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import os
import uuid
import logging
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.sicurezza import (
    PosCreate, PosUpdate, PosResponse, PosListResponse, PosStatus,
    RISCHI_LAVORAZIONI, MACCHINE_ATTREZZATURE, DPI_LIST,
)
from services.pos_pdf_service import generate_pos_pdf
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sicurezza", tags=["sicurezza"])

LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


# ── Reference data endpoints ────────────────────────────────────

@router.get("/rischi")
async def get_rischi():
    return {"rischi": RISCHI_LAVORAZIONI, "macchine": MACCHINE_ATTREZZATURE, "dpi": DPI_LIST}


# ── CRUD ─────────────────────────────────────────────────────────

async def _populate_names(doc: dict):
    if doc.get("client_id"):
        c = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = c.get("business_name") if c else None


@router.get("/", response_model=PosListResponse)
async def get_pos_list(
    status: Optional[PosStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status.value

    total = await db.pos_documents.count_documents(query)
    cursor = db.pos_documents.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        await _populate_names(d)
    return PosListResponse(pos_list=[PosResponse(**d) for d in docs], total=total)


@router.get("/{pos_id}", response_model=PosResponse)
async def get_pos(pos_id: str, user: dict = Depends(get_current_user)):
    doc = await db.pos_documents.find_one({"pos_id": pos_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "POS non trovato")
    await _populate_names(doc)
    return PosResponse(**doc)


@router.post("/", response_model=PosResponse, status_code=201)
async def create_pos(data: PosCreate, user: dict = Depends(get_current_user)):
    pos_id = f"pos_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc = {
        "pos_id": pos_id,
        "user_id": user["user_id"],
        "project_name": data.project_name,
        "client_id": data.client_id,
        "distinta_id": data.distinta_id,
        "cantiere": data.cantiere.model_dump(),
        "selected_risks": data.selected_risks,
        "selected_machines": data.selected_machines,
        "selected_dpi": data.selected_dpi,
        "ai_risk_assessment": None,
        "status": PosStatus.BOZZA.value,
        "notes": data.notes,
        "created_at": now,
        "updated_at": now,
    }
    await db.pos_documents.insert_one(doc)
    created = await db.pos_documents.find_one({"pos_id": pos_id}, {"_id": 0})
    await _populate_names(created)
    logger.info(f"POS created: {pos_id}")
    return PosResponse(**created)


@router.put("/{pos_id}", response_model=PosResponse)
async def update_pos(pos_id: str, data: PosUpdate, user: dict = Depends(get_current_user)):
    existing = await db.pos_documents.find_one({"pos_id": pos_id, "user_id": user["user_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "POS non trovato")

    upd = {}
    for field in ["project_name", "client_id", "distinta_id", "ai_risk_assessment", "notes"]:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val
    if data.cantiere is not None:
        upd["cantiere"] = data.cantiere.model_dump()
    if data.selected_risks is not None:
        upd["selected_risks"] = data.selected_risks
    if data.selected_machines is not None:
        upd["selected_machines"] = data.selected_machines
    if data.selected_dpi is not None:
        upd["selected_dpi"] = data.selected_dpi
    if data.status is not None:
        upd["status"] = data.status.value

    upd["updated_at"] = datetime.now(timezone.utc)
    await db.pos_documents.update_one({"pos_id": pos_id}, {"$set": upd})
    updated = await db.pos_documents.find_one({"pos_id": pos_id}, {"_id": 0})
    await _populate_names(updated)
    logger.info(f"POS updated: {pos_id}")
    return PosResponse(**updated)


@router.delete("/{pos_id}")
async def delete_pos(pos_id: str, user: dict = Depends(get_current_user)):
    result = await db.pos_documents.delete_one({"pos_id": pos_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "POS non trovato")
    logger.info(f"POS deleted: {pos_id}")
    return {"message": "POS eliminato con successo"}


# ── AI Risk Assessment ───────────────────────────────────────────

@router.post("/{pos_id}/genera-rischi")
async def generate_risk_assessment(pos_id: str, user: dict = Depends(get_current_user)):
    """Use GPT-4o to generate risk assessment text based on selected risks."""
    doc = await db.pos_documents.find_one({"pos_id": pos_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "POS non trovato")

    selected = doc.get("selected_risks", [])
    if not selected:
        raise HTTPException(400, "Nessuna lavorazione selezionata. Seleziona almeno un rischio.")

    risk_labels = []
    for r in RISCHI_LAVORAZIONI:
        if r["id"] in selected:
            risk_labels.append(r["label"])

    machine_labels = []
    for m in MACCHINE_ATTREZZATURE:
        if m["id"] in doc.get("selected_machines", []):
            machine_labels.append(m["label"])

    prompt = f"""Sei un esperto di sicurezza sul lavoro italiano (D.Lgs. 81/2008).
Genera una VALUTAZIONE DEI RISCHI SPECIFICI formale per un cantiere di carpenteria metallica.

PROGETTO: {doc.get('project_name', '-')}
CANTIERE: {doc.get('cantiere', {}).get('address', '-')}, {doc.get('cantiere', {}).get('city', '-')}

LAVORAZIONI PREVISTE:
{chr(10).join(f'- {l}' for l in risk_labels)}

MACCHINE/ATTREZZATURE:
{chr(10).join(f'- {m}' for m in machine_labels) if machine_labels else '- Non specificate'}

Per OGNI lavorazione, genera:
1. DESCRIZIONE DEL RISCHIO
2. PROBABILITA' (P: 1-4) e DANNO (D: 1-4) con LIVELLO DI RISCHIO (R = P x D)
3. MISURE DI PREVENZIONE E PROTEZIONE specifiche
4. DPI NECESSARI

Scrivi in italiano formale, come in un documento POS reale.
Usa paragrafi separati per ogni lavorazione.
NON usare markdown, scrivi testo semplice con titoli in MAIUSCOLO."""

    try:
        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"pos-risk-{pos_id}",
            system_message="Sei un consulente per la sicurezza sul lavoro specializzato in cantieri di carpenteria metallica. Rispondi sempre in italiano formale."
        ).with_model("openai", "gpt-4o")

        response = await chat.send_message(UserMessage(text=prompt))

        await db.pos_documents.update_one(
            {"pos_id": pos_id},
            {"$set": {"ai_risk_assessment": response, "updated_at": datetime.now(timezone.utc)}},
        )

        logger.info(f"AI risk assessment generated for POS {pos_id}")
        return {"pos_id": pos_id, "ai_risk_assessment": response, "status": "generated"}

    except Exception as e:
        logger.error(f"AI generation failed for POS {pos_id}: {e}")
        raise HTTPException(500, f"Errore nella generazione AI: {str(e)}")


# ── PDF Generation ───────────────────────────────────────────────

@router.get("/{pos_id}/pdf")
async def get_pos_pdf(pos_id: str, user: dict = Depends(get_current_user)):
    """Generate and download POS PDF."""
    doc = await db.pos_documents.find_one({"pos_id": pos_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "POS non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    pdf_buffer = generate_pos_pdf(doc, company, doc.get("ai_risk_assessment"))

    filename = f"POS_{doc.get('project_name', pos_id).replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
