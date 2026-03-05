"""Sopralluogo & Messa a Norma AI routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from typing import Optional
import os
import uuid
import base64
import logging
from datetime import datetime, timezone

from core.security import get_current_user
from core.database import db
from models.sopralluogo import (
    SopralluogoCreate, SopralluogoUpdate,
    ArticoloPeriziaCreate, ArticoloPeriziaUpdate,
)
from services.object_storage import upload_photo, get_object
from services.vision_analysis import analyze_photos

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sopralluoghi", tags=["sopralluoghi"])

COLLECTION = "sopralluoghi"
ARTICOLI_COLLECTION = "articoli_perizia"


# ── Helper ──

async def next_sopralluogo_number(user_id: str) -> str:
    year = datetime.now(timezone.utc).strftime("%Y")
    count = await db[COLLECTION].count_documents({"user_id": user_id})
    return f"SOP-{year}/{count + 1:04d}"


# ── Articoli Perizia (Configurable catalog) - MUST be before /{sopralluogo_id} routes ──

DEFAULT_ARTICOLI = [
    {"codice": "SIC-001", "descrizione": "Costa sensibile di sicurezza 8K2 (2m)", "prezzo_base": 180, "unita": "pz", "keyword_ai": "costa", "categoria": "sicurezza"},
    {"codice": "SIC-002", "descrizione": "Costa sensibile ottica (2.5m)", "prezzo_base": 350, "unita": "pz", "keyword_ai": "costa ottica", "categoria": "sicurezza"},
    {"codice": "SIC-003", "descrizione": "Coppia fotocellule orientabili", "prezzo_base": 85, "unita": "coppia", "keyword_ai": "fotocellula", "categoria": "sicurezza"},
    {"codice": "SIC-004", "descrizione": "Lampeggiante con antenna integrata", "prezzo_base": 45, "unita": "pz", "keyword_ai": "lampeggiante", "categoria": "sicurezza"},
    {"codice": "SIC-005", "descrizione": "Selettore a chiave da incasso", "prezzo_base": 35, "unita": "pz", "keyword_ai": "selettore", "categoria": "sicurezza"},
    {"codice": "SIC-006", "descrizione": "Rete anti-cesoiamento 25x25mm (al mq)", "prezzo_base": 28, "unita": "mq", "keyword_ai": "rete", "categoria": "sicurezza"},
    {"codice": "SIC-007", "descrizione": "Protezione anti-caduta per sezionale", "prezzo_base": 220, "unita": "pz", "keyword_ai": "anti-caduta", "categoria": "sicurezza"},
    {"codice": "AUT-001", "descrizione": "Encoder per motore scorrevole", "prezzo_base": 95, "unita": "pz", "keyword_ai": "encoder", "categoria": "automazione"},
    {"codice": "AUT-002", "descrizione": "Finecorsa magnetico (coppia)", "prezzo_base": 40, "unita": "coppia", "keyword_ai": "finecorsa", "categoria": "automazione"},
    {"codice": "AUT-003", "descrizione": "Centralina di comando universale", "prezzo_base": 180, "unita": "pz", "keyword_ai": "centralina", "categoria": "automazione"},
    {"codice": "AUT-004", "descrizione": "Motore scorrevole 400kg", "prezzo_base": 450, "unita": "pz", "keyword_ai": "motore", "categoria": "automazione"},
    {"codice": "STR-001", "descrizione": "Pattino guida nylon rinforzato", "prezzo_base": 12, "unita": "pz", "keyword_ai": "guida", "categoria": "struttura"},
    {"codice": "STR-002", "descrizione": "Binario di scorrimento (al ml)", "prezzo_base": 25, "unita": "ml", "keyword_ai": "binario", "categoria": "struttura"},
    {"codice": "ACC-001", "descrizione": "Batteria tampone 12V", "prezzo_base": 35, "unita": "pz", "keyword_ai": "batteria", "categoria": "accessori"},
]


async def _seed_default_articoli(user_id: str):
    """Insert default articles for a new user."""
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for art in DEFAULT_ARTICOLI:
        docs.append({
            "articolo_id": f"art_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            **art,
            "note": "",
            "created_at": now,
            "updated_at": now,
        })
    if docs:
        await db[ARTICOLI_COLLECTION].insert_many(docs)
        logger.info(f"Seeded {len(docs)} default articoli for user {user_id}")


@router.get("/articoli-catalogo")
async def list_articoli(user: dict = Depends(get_current_user)):
    """List all articles in the perizia catalog. Seeds defaults if empty."""
    count = await db[ARTICOLI_COLLECTION].count_documents({"user_id": user["user_id"]})
    if count == 0:
        await _seed_default_articoli(user["user_id"])
    items = await db[ARTICOLI_COLLECTION].find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("categoria", 1).to_list(500)
    return {"items": items}


@router.post("/articoli-catalogo")
async def create_articolo(data: ArticoloPeriziaCreate, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "articolo_id": f"art_{uuid.uuid4().hex[:8]}",
        "user_id": user["user_id"],
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    await db[ARTICOLI_COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/articoli-catalogo/{articolo_id}")
async def update_articolo(articolo_id: str, data: ArticoloPeriziaUpdate, user: dict = Depends(get_current_user)):
    raw = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    raw["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db[ARTICOLI_COLLECTION].find_one_and_update(
        {"articolo_id": articolo_id, "user_id": user["user_id"]},
        {"$set": raw},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(404, "Articolo non trovato")
    return result


@router.delete("/articoli-catalogo/{articolo_id}")
async def delete_articolo(articolo_id: str, user: dict = Depends(get_current_user)):
    result = await db[ARTICOLI_COLLECTION].delete_one(
        {"articolo_id": articolo_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Articolo non trovato")
    return {"deleted": True}


# ── CRUD Sopralluoghi ──

@router.post("/")
async def create_sopralluogo(data: SopralluogoCreate, user: dict = Depends(get_current_user)):
    doc_number = await next_sopralluogo_number(user["user_id"])
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "sopralluogo_id": f"sop_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "document_number": doc_number,
        **data.model_dump(),
        "foto": [],
        "analisi_ai": None,
        "note_tecnico": "",
        "preventivo_id": None,
        "status": "bozza",
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/")
async def list_sopralluoghi(
    search: str = "",
    status: str = "",
    limit: int = Query(50, le=200),
    skip: int = 0,
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["user_id"]}
    if search:
        query["$or"] = [
            {"document_number": {"$regex": search, "$options": "i"}},
            {"indirizzo": {"$regex": search, "$options": "i"}},
            {"descrizione_utente": {"$regex": search, "$options": "i"}},
        ]
    if status:
        query["status"] = status

    docs = await db[COLLECTION].find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db[COLLECTION].count_documents(query)

    # Enrich with client names
    client_ids = list({d.get("client_id") for d in docs if d.get("client_id")})
    client_map = {}
    if client_ids:
        clients = await db.clients.find(
            {"client_id": {"$in": client_ids}},
            {"_id": 0, "client_id": 1, "business_name": 1},
        ).to_list(len(client_ids))
        client_map = {c["client_id"]: c["business_name"] for c in clients}

    for d in docs:
        d["client_name"] = client_map.get(d.get("client_id"), "")

    return {"items": docs, "total": total}


@router.get("/{sopralluogo_id}")
async def get_sopralluogo(sopralluogo_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")
    # Enrich client name
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = client.get("business_name", "") if client else ""
    return doc


@router.put("/{sopralluogo_id}")
async def update_sopralluogo(sopralluogo_id: str, data: SopralluogoUpdate, user: dict = Depends(get_current_user)):
    raw = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    raw["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db[COLLECTION].find_one_and_update(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"$set": raw},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(404, "Sopralluogo non trovato")
    return result


@router.delete("/{sopralluogo_id}")
async def delete_sopralluogo(sopralluogo_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one({"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Sopralluogo non trovato")
    return {"deleted": True}


# ── Photo Upload & Download ──

@router.post("/{sopralluogo_id}/upload-foto")
async def upload_foto(
    sopralluogo_id: str,
    file: UploadFile = File(...),
    label: str = Form("foto"),
    user: dict = Depends(get_current_user),
):
    doc = await db[COLLECTION].find_one({"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]})
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"Formato non supportato: {file.content_type}. Usa JPEG, PNG o WebP.")

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File troppo grande (max 10MB)")

    storage_info = upload_photo(user["user_id"], file_data, file.filename, file.content_type)
    foto_entry = {
        "foto_id": f"foto_{uuid.uuid4().hex[:8]}",
        **storage_info,
        "label": label,
    }

    await db[COLLECTION].update_one(
        {"sopralluogo_id": sopralluogo_id},
        {
            "$push": {"foto": foto_entry},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return foto_entry


@router.delete("/{sopralluogo_id}/foto/{foto_id}")
async def delete_foto(sopralluogo_id: str, foto_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].update_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"$pull": {"foto": {"foto_id": foto_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Foto non trovata")
    return {"deleted": True}


@router.get("/foto/{path:path}")
async def download_foto(path: str, user: dict = Depends(get_current_user)):
    """Download a photo from object storage."""
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        raise HTTPException(404, f"Foto non trovata: {str(e)[:100]}")


# ── AI Analysis ──

@router.post("/{sopralluogo_id}/analizza")
async def analizza_sopralluogo(sopralluogo_id: str, user: dict = Depends(get_current_user)):
    """Run AI Vision analysis on uploaded photos."""
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")

    foto_list = doc.get("foto", [])
    if not foto_list:
        raise HTTPException(400, "Carica almeno una foto prima di analizzare")

    # Download photos and encode as base64
    photo_data = []
    for foto in foto_list:
        try:
            data, ct = get_object(foto["storage_path"])
            b64 = base64.b64encode(data).decode("utf-8")
            photo_data.append({
                "base64": b64,
                "mime_type": ct,
                "label": foto.get("label", "foto"),
            })
        except Exception as e:
            logger.warning(f"Failed to download photo {foto.get('foto_id')}: {e}")

    if not photo_data:
        raise HTTPException(500, "Impossibile recuperare le foto dallo storage")

    # Run analysis
    result = await analyze_photos(photo_data, doc.get("descrizione_utente", ""))

    # Match materials to catalog articles
    articoli = await db[ARTICOLI_COLLECTION].find({"user_id": user["user_id"]}, {"_id": 0}).to_list(200)
    materiali = result.get("materiali_suggeriti", [])
    for mat in materiali:
        keyword = mat.get("keyword", "").lower()
        for art in articoli:
            art_keyword = art.get("keyword_ai", "").lower()
            if art_keyword and art_keyword in keyword or keyword in art_keyword:
                mat["articolo_id"] = art.get("articolo_id")
                mat["prezzo"] = art.get("prezzo_base", 0)
                mat["descrizione_catalogo"] = art.get("descrizione", "")
                break

    result["materiali_suggeriti"] = materiali

    # Save analysis
    await db[COLLECTION].update_one(
        {"sopralluogo_id": sopralluogo_id},
        {"$set": {
            "analisi_ai": result,
            "status": "analizzato",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return result


# ── Generate Preventivo from Analysis ──

@router.post("/{sopralluogo_id}/genera-preventivo")
async def genera_preventivo(sopralluogo_id: str, user: dict = Depends(get_current_user)):
    """Generate a draft quote from the AI analysis."""
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")

    analisi = doc.get("analisi_ai")
    if not analisi:
        raise HTTPException(400, "Esegui prima l'analisi AI")

    # Build quote lines from confirmed materials
    lines = []
    rischi_confermati = [r for r in analisi.get("rischi", []) if r.get("confermato", True)]
    materiali = analisi.get("materiali_suggeriti", [])

    for mat in materiali:
        desc = mat.get("descrizione_catalogo") or mat.get("descrizione", "")
        lines.append({
            "line_id": f"line_{uuid.uuid4().hex[:8]}",
            "codice": mat.get("articolo_id", ""),
            "description": desc,
            "quantity": mat.get("quantita", 1),
            "unit_price": mat.get("prezzo", 0),
            "discount": 0,
            "vat_rate": 22,
            "line_total": mat.get("prezzo", 0) * mat.get("quantita", 1),
            "vat_amount": round(mat.get("prezzo", 0) * mat.get("quantita", 1) * 0.22, 2),
        })

    # Add manodopera line
    if lines:
        ore_stimate = max(2, len(rischi_confermati) * 1.5)
        lines.append({
            "line_id": f"line_{uuid.uuid4().hex[:8]}",
            "codice": "MAN",
            "description": f"Manodopera installazione e messa a norma ({ore_stimate:.0f}h stimate)",
            "quantity": ore_stimate,
            "unit_price": 45,
            "discount": 0,
            "vat_rate": 22,
            "line_total": ore_stimate * 45,
            "vat_amount": round(ore_stimate * 45 * 0.22, 2),
        })

    # Create the preventivo
    year = datetime.now(timezone.utc).strftime("%Y")
    q_count = await db.preventivi.count_documents({"user_id": user["user_id"]})
    prev_number = f"PRV-{year}-{q_count + 1:04d}"

    now = datetime.now(timezone.utc).isoformat()
    rischi_text = "\n".join(
        f"- {r.get('zona', '')}: {r.get('problema', '')} ({r.get('norma_riferimento', '')})"
        for r in rischi_confermati
    )

    preventivo = {
        "quote_id": f"quote_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "document_number": prev_number,
        "client_id": doc.get("client_id", ""),
        "issue_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "valid_until": "",
        "subject": f"Messa a Norma - Sopralluogo {doc.get('document_number', '')}",
        "notes": f"Sopralluogo: {doc.get('indirizzo', '')}\nTipo: {analisi.get('tipo_chiusura', '')}\nConformità: {analisi.get('conformita_percentuale', 0)}%\n\nCriticità riscontrate:\n{rischi_text}",
        "internal_notes": f"Generato automaticamente da sopralluogo {doc.get('sopralluogo_id', '')}",
        "lines": lines,
        "status": "bozza",
        "payment_terms": "",
        "payment_method": "",
        "sopralluogo_id": doc.get("sopralluogo_id"),
        "created_at": now,
        "updated_at": now,
    }

    await db.preventivi.insert_one(preventivo)
    preventivo.pop("_id", None)

    # Update sopralluogo with preventivo reference
    await db[COLLECTION].update_one(
        {"sopralluogo_id": sopralluogo_id},
        {"$set": {
            "preventivo_id": preventivo["quote_id"],
            "status": "completato",
            "updated_at": now,
        }},
    )

    return {"preventivo": preventivo, "message": f"Preventivo {prev_number} generato con successo"}


# ── PDF Generation ──

@router.get("/{sopralluogo_id}/pdf")
async def genera_pdf_perizia(sopralluogo_id: str, user: dict = Depends(get_current_user)):
    """Generate a PDF perizia report with photos and analysis."""
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")

    if not doc.get("analisi_ai"):
        raise HTTPException(400, "Esegui prima l'analisi AI per generare il PDF")

    # Get company settings
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Enrich client name
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "business_name": 1})
        doc["client_name"] = client.get("business_name", "") if client else ""

    # Download photos as base64
    photos_b64 = []
    for foto in doc.get("foto", []):
        try:
            data, ct = get_object(foto["storage_path"])
            photos_b64.append({
                "base64": base64.b64encode(data).decode("utf-8"),
                "mime_type": ct,
                "label": foto.get("label", "foto"),
            })
        except Exception as e:
            logger.warning(f"Failed to download photo for PDF: {e}")

    from services.pdf_perizia_sopralluogo import generate_perizia_pdf
    pdf_bytes = generate_perizia_pdf(doc, company, photos_b64)

    filename = f"Perizia_{doc.get('document_number', 'SOP').replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
