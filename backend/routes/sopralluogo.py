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
from services.audit_trail import log_activity

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
    await log_activity(user, "create", "rilievo", doc["sopralluogo_id"], label=doc_number)
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
    await log_activity(user, "delete", "rilievo", sopralluogo_id)
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
    tipo_perizia = doc.get("tipo_perizia", "cancelli")
    result = await analyze_photos(photo_data, doc.get("descrizione_utente", ""), tipo_perizia=tipo_perizia)

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
async def genera_preventivo(
    sopralluogo_id: str,
    variante: str = Query("B", description="Variante selezionata: A, B o C"),
    user: dict = Depends(get_current_user),
):
    """Generate a draft quote from the AI analysis.

    Uses the selected variant (A/B/C) for pricing. Creates a clean
    single-line quote with synthetic text + reference to the perizia.
    """
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")

    analisi = doc.get("analisi_ai")
    if not analisi:
        raise HTTPException(400, "Esegui prima l'analisi AI")

    varianti = analisi.get("varianti", {})
    selected = varianti.get(variante.upper(), {})

    # Build quote lines
    lines = []
    doc_number = doc.get("document_number", "")

    # Synthetic invoice line from AI or fallback
    testo_sintetico = analisi.get("testo_sintetico_fattura", "")
    titolo_variante = selected.get("titolo", f"Variante {variante.upper()}")

    if not testo_sintetico:
        testo_sintetico = f"Messa a norma chiusura automatica c/o {doc.get('indirizzo', '')} secondo EN 12453/EN 13241"

    desc_line = f"{testo_sintetico} — {titolo_variante} (rif. Perizia {doc_number})"

    costo_variante = selected.get("costo_stimato", 0)

    if costo_variante > 0:
        # Single clean line with variant cost
        lines.append({
            "line_id": f"line_{uuid.uuid4().hex[:8]}",
            "codice": f"PER-{variante.upper()}",
            "description": desc_line,
            "quantity": 1,
            "unit_price": costo_variante,
            "discount": 0,
            "vat_rate": 22,
            "line_total": costo_variante,
            "vat_amount": round(costo_variante * 0.22, 2),
        })
    else:
        # Fallback: use materials list like before
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
        # Add manodopera
        rischi_confermati = [r for r in analisi.get("rischi", []) if r.get("confermato", True)]
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

    # Create the preventivo using the same schema as preventivi.py
    prev_id = f"prev_{uuid.uuid4().hex[:10]}"
    now_dt = datetime.now(timezone.utc)
    year = now_dt.year
    uid = user["user_id"]
    now = now_dt.isoformat()

    # Atomic counter for sequential numbering (same as preventivi.py)
    counter_id = f"PRV-{uid}-{year}"
    counter = await db.document_counters.find_one_and_update(
        {"counter_id": counter_id},
        {"$inc": {"counter": 1}},
        upsert=True,
        return_document=True,
    )
    seq = counter.get("counter", 1)
    prev_number = f"PRV-{year}-{seq:04d}"

    rischi_confermati = [r for r in analisi.get("rischi", []) if r.get("confermato", True)]
    rischi_text = "\n".join(
        f"- {r.get('zona', '')}: {r.get('problema', '')} ({r.get('norma_riferimento', '')})"
        for r in rischi_confermati
    )

    # Compute line totals
    computed_lines = []
    for line in lines:
        line["netto"] = line["unit_price"] * line["quantity"]
        line["line_total"] = line["netto"]
        line["vat_amount"] = round(line["netto"] * line["vat_rate"] / 100, 2)
        computed_lines.append(line)

    subtotal = sum(ln["line_total"] for ln in computed_lines)
    total_iva = sum(ln["vat_amount"] for ln in computed_lines)
    totals = {
        "subtotal": round(subtotal, 2),
        "sconto_globale": 0,
        "imponibile": round(subtotal, 2),
        "total_iva": round(total_iva, 2),
        "total": round(subtotal + total_iva, 2),
        "acconto": 0,
        "netto_a_pagare": round(subtotal + total_iva, 2),
    }

    preventivo = {
        "preventivo_id": prev_id,
        "user_id": uid,
        "number": prev_number,
        "client_id": doc.get("client_id", ""),
        "subject": f"Messa a Norma — {titolo_variante} — Perizia {doc_number}",
        "notes": f"Sopralluogo: {doc.get('indirizzo', '')}\n"
                 f"Tipo chiusura: {analisi.get('tipo_chiusura', '')}\n"
                 f"Conformita: {analisi.get('conformita_percentuale', 0)}%\n"
                 f"Variante selezionata: {variante.upper()} — {titolo_variante}\n\n"
                 f"Criticita riscontrate:\n{rischi_text}\n\n"
                 f"Vedi Perizia Tecnica allegata ({doc_number}) per dettagli completi.",
        "note_pagamento": "",
        "riferimento": doc_number,
        "normativa": "EN_13241",
        "validity_days": 30,
        "giorni_consegna": selected.get("tempo_stimato", ""),
        "sconto_globale": 0,
        "acconto": 0,
        "lines": computed_lines,
        "totals": totals,
        "status": "bozza",
        "sopralluogo_id": doc.get("sopralluogo_id"),
        "variante_selezionata": variante.upper(),
        "created_at": now,
        "updated_at": now,
    }

    await db.preventivi.insert_one(preventivo)
    preventivo.pop("_id", None)

    # Update sopralluogo with preventivo reference
    await db[COLLECTION].update_one(
        {"sopralluogo_id": sopralluogo_id},
        {"$set": {
            "preventivo_id": prev_id,
            "variante_selezionata": variante.upper(),
            "status": "completato",
            "updated_at": now,
        }},
    )

    return {"preventivo": preventivo, "message": f"Preventivo {prev_number} (Variante {variante.upper()}) generato con successo"}


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


# ── Email Perizia ──

@router.post("/{sopralluogo_id}/invia-email")
async def invia_perizia_email(
    sopralluogo_id: str,
    payload: dict = None,
    user: dict = Depends(get_current_user),
):
    """Send the perizia PDF to the client via email with custom subject/body."""
    payload = payload or {}
    doc = await db[COLLECTION].find_one(
        {"sopralluogo_id": sopralluogo_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Sopralluogo non trovato")
    if not doc.get("analisi_ai"):
        raise HTTPException(400, "Esegui prima l'analisi AI")

    # Get client email
    client_email = None
    if doc.get("client_id"):
        client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0})
        if client:
            client_email = client.get("email") or client.get("pec")
            doc["client_name"] = client.get("business_name", "")

    if not client_email:
        raise HTTPException(400, "Il cliente non ha un indirizzo email configurato. Aggiungi l'email nella scheda cliente.")

    # Generate PDF
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

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
            logger.warning(f"Failed to download photo for email PDF: {e}")

    from services.pdf_perizia_sopralluogo import generate_perizia_pdf
    pdf_bytes = generate_perizia_pdf(doc, company, photos_b64)
    filename = f"Perizia_{doc.get('document_number', 'SOP').replace('/', '-')}.pdf"

    # Use custom subject/body from frontend or fallback
    from services.email_service import send_email_with_attachment
    company_name = company.get("company_name", "")

    subject = payload.get("subject", "").strip()
    body = payload.get("body", "").strip()

    if not subject:
        subject = f"Perizia Tecnica {doc.get('document_number', '')} — Relazione di Sopralluogo"
    if not body:
        body = f"In allegato la perizia tecnica.\n\nCordiali saluti,\n{company_name}"

    success = await send_email_with_attachment(
        to_email=client_email,
        subject=subject,
        body=body,
        pdf_bytes=pdf_bytes,
        filename=filename,
        user_id=user["user_id"],
    )

    if success:
        await db[COLLECTION].update_one(
            {"sopralluogo_id": sopralluogo_id},
            {"$set": {
                "email_inviata": True,
                "email_inviata_at": datetime.now(timezone.utc).isoformat(),
                "email_subject": subject,
            }},
        )
        return {"message": f"Perizia inviata a {client_email}", "email": client_email}
    else:
        raise HTTPException(500, "Errore nell'invio email. Verifica la configurazione del servizio email (Resend).")
