"""
Smistatore Intelligente — Route API per analisi certificati multi-pagina e disegni tecnici.
POST /api/smistatore/analyze/{doc_id} → Analizza un documento PDF con AI Vision
POST /api/smistatore/analyze-drawing/{doc_id} → Analizza disegno tecnico per bulloneria
POST /api/smistatore/drawing-to-rdp/{doc_id} → Crea RdP da bulloneria estratta
GET  /api/smistatore/index/{commessa_id} → Lista pagine indicizzate per commessa
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from core.security import get_current_user, tenant_match
from core.database import db
from core.rate_limiter import limiter
from services.smistatore_intelligente import analyze_and_index_document, analyze_drawing_document

router = APIRouter(prefix="/smistatore", tags=["smistatore"])
logger = logging.getLogger(__name__)


class CreateRdpFromDrawingRequest(BaseModel):
    selected_indices: List[int] = []
    fornitore_nome: Optional[str] = ""
    note: Optional[str] = ""


@router.post("/analyze/{doc_id}")
@limiter.limit("10/minute")
async def analyze_document(request: Request, doc_id: str, user: dict = Depends(get_current_user)):
    """
    Analizza un documento PDF caricato con AI Vision.
    Spacchetta le pagine, estrae metadati (numero colata, materiale, dimensioni),
    fa matching con i lotti materiale della commessa.
    """
    doc = await db.commessa_documents.find_one(
        {"doc_id": doc_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    if not doc.get("file_base64"):
        raise HTTPException(400, "Documento senza contenuto PDF")

    content_type = doc.get("content_type", "")
    if "pdf" not in content_type.lower() and not doc.get("nome_file", "").lower().endswith(".pdf"):
        raise HTTPException(400, "Solo documenti PDF possono essere analizzati")

    import base64
    try:
        pdf_bytes = base64.b64decode(doc["file_base64"])
    except Exception:
        raise HTTPException(400, "Contenuto PDF non valido")

    commessa_id = doc.get("commessa_id", "")
    if not commessa_id:
        raise HTTPException(400, "Documento non associato a una commessa")

    try:
        result = await analyze_and_index_document(
            doc_id=doc_id,
            pdf_bytes=pdf_bytes,
            commessa_id=commessa_id,
            user_id=user["user_id"],
            db=db,
        )
    except Exception as e:
        logger.error(f"[SMISTATORE] Error: {e}", exc_info=True)
        raise HTTPException(500, f"Errore nell'analisi: {str(e)}")

    return result


@router.get("/index/{commessa_id}")
async def get_page_index(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get all indexed certificate pages for a commessa."""
    pages = await db.doc_page_index.find(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "page_pdf_b64": 0}
    ).sort("doc_id", 1).to_list(500)

    return {
        "commessa_id": commessa_id,
        "total_pages": len(pages),
        "matched": len([p for p in pages if p["matching_status"] == "matched"]),
        "scorta": len([p for p in pages if p["matching_status"] == "scorta"]),
        "consumabili": len([p for p in pages if p["matching_status"] == "consumabile_auto"]),
        "pages": pages,
    }


@router.get("/scorte")
async def get_scorte(user: dict = Depends(get_current_user)):
    """Get all 'scorta' (unmatched) certificate pages across all commesse."""
    scorte = await db.doc_page_index.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user), "matching_status": "scorta"},
        {"_id": 0, "page_pdf_b64": 0}
    ).sort("analyzed_at", -1).to_list(200)

    return {"total_scorte": len(scorte), "scorte": scorte}


@router.post("/analyze-drawing/{doc_id}")
@limiter.limit("10/minute")
async def analyze_drawing(request: Request, doc_id: str, user: dict = Depends(get_current_user)):
    """
    Analizza un disegno tecnico (PDF/immagine) con AI Vision.
    Estrae la lista di bulloneria (diametro, classe, quantita) e propone una RdP.
    """
    doc = await db.commessa_documents.find_one(
        {"doc_id": doc_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    if not doc.get("file_base64"):
        raise HTTPException(400, "Documento senza contenuto")

    commessa_id = doc.get("commessa_id", "")
    if not commessa_id:
        raise HTTPException(400, "Documento non associato a una commessa")

    content_type = doc.get("content_type", "").lower()
    nome_file = doc.get("nome_file", "").lower()
    is_pdf = "pdf" in content_type or nome_file.endswith(".pdf")
    is_image = any(x in content_type for x in ["image/png", "image/jpeg", "image/jpg", "image/webp"])

    if not is_pdf and not is_image:
        raise HTTPException(400, "Solo PDF o immagini possono essere analizzati")

    import base64
    try:
        file_bytes = base64.b64decode(doc["file_base64"])
    except Exception:
        raise HTTPException(400, "Contenuto file non valido")

    # For images, convert directly to base64 for Vision
    if is_image:
        from services.smistatore_intelligente import analyze_drawing_for_fasteners
        image_b64 = doc["file_base64"]
        analysis = await analyze_drawing_for_fasteners(image_b64)

        if analysis.get("errore"):
            raise HTTPException(400, f"Errore nell'analisi: {analysis.get('note_aggiuntive', 'Immagine non leggibile')}")

        now = datetime.now(timezone.utc)
        bulloneria = analysis.get("bulloneria", [])

        await db.commessa_documents.update_one(
            {"doc_id": doc_id},
            {"$set": {
                "metadata_estratti.drawing_analysis": True,
                "metadata_estratti.titolo_disegno": analysis.get("titolo_disegno", ""),
                "metadata_estratti.numero_disegno": analysis.get("numero_disegno", ""),
                "metadata_estratti.bulloneria": bulloneria,
                "metadata_estratti.bulloneria_count": len(bulloneria),
                "metadata_estratti.drawing_analyzed_at": now.isoformat(),
            }}
        )

        rdp_lines = []
        for b in bulloneria:
            desc_parts = []
            if b.get("tipo"):
                desc_parts.append(b["tipo"].replace("_", " ").title())
            if b.get("diametro"):
                desc_parts.append(b["diametro"])
            if b.get("lunghezza_mm"):
                desc_parts.append(f"x{b['lunghezza_mm']}mm")
            if b.get("classe") and b["classe"] != "da_verificare":
                desc_parts.append(f"Cl.{b['classe']}")
            if b.get("norma"):
                desc_parts.append(f"({b['norma']})")
            rdp_lines.append({
                "descrizione": " ".join(desc_parts) or b.get("descrizione", "Bullone"),
                "quantita": b.get("quantita", 1),
                "unita_misura": "pz",
                "diametro": b.get("diametro", ""),
                "classe": b.get("classe", ""),
                "lunghezza_mm": b.get("lunghezza_mm"),
                "tipo": b.get("tipo", "bullone"),
                "norma": b.get("norma", ""),
            })

        return {
            "doc_id": doc_id,
            "commessa_id": commessa_id,
            "titolo_disegno": analysis.get("titolo_disegno", ""),
            "numero_disegno": analysis.get("numero_disegno", ""),
            "pagine_analizzate": 1,
            "bulloneria_totale": len(bulloneria),
            "bulloneria": bulloneria,
            "rdp_proposta": rdp_lines,
        }

    # For PDFs, use the full multi-page analysis
    try:
        result = await analyze_drawing_document(
            doc_id=doc_id,
            pdf_bytes=file_bytes,
            commessa_id=commessa_id,
            user_id=user["user_id"],
            db=db,
        )
    except Exception as e:
        logger.error(f"[SMISTATORE-DRAWING] Error: {e}", exc_info=True)
        raise HTTPException(500, f"Errore nell'analisi: {str(e)}")

    return result


@router.post("/drawing-to-rdp/{doc_id}")
async def create_rdp_from_drawing(doc_id: str, data: CreateRdpFromDrawingRequest, user: dict = Depends(get_current_user)):
    """
    Crea una Richiesta di Preventivo (RdP) dalla bulloneria estratta da un disegno.
    Salva la RdP nella sezione approvvigionamento della commessa.
    """
    doc = await db.commessa_documents.find_one(
        {"doc_id": doc_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    bulloneria = doc.get("metadata_estratti", {}).get("bulloneria", [])
    if not bulloneria:
        raise HTTPException(400, "Nessuna bulloneria estratta. Analizza prima il disegno.")

    commessa_id = doc.get("commessa_id", "")
    if not commessa_id:
        raise HTTPException(400, "Documento non associato a una commessa")

    # Filter by selected indices (if provided)
    if data.selected_indices:
        selected = [bulloneria[i] for i in data.selected_indices if 0 <= i < len(bulloneria)]
    else:
        selected = bulloneria

    if not selected:
        raise HTTPException(400, "Nessun elemento selezionato")

    now = datetime.now(timezone.utc)
    rdp_id = f"rdp_{uuid.uuid4().hex[:10]}"

    # Build righe for the RdP
    righe = []
    for b in selected:
        desc_parts = []
        if b.get("tipo"):
            desc_parts.append(b["tipo"].replace("_", " ").title())
        if b.get("diametro"):
            desc_parts.append(b["diametro"])
        if b.get("lunghezza_mm"):
            desc_parts.append(f"x{b['lunghezza_mm']}mm")
        if b.get("classe") and b["classe"] != "da_verificare":
            desc_parts.append(f"Cl.{b['classe']}")
        if b.get("norma"):
            desc_parts.append(f"({b['norma']})")

        righe.append({
            "descrizione": " ".join(desc_parts) or b.get("descrizione", "Bullone"),
            "quantita": b.get("quantita", 1),
            "unita_misura": "pz",
            "richiede_cert_31": True,
            "note": f"Diametro: {b.get('diametro', '?')}, Classe: {b.get('classe', '?')}",
        })

    rdp = {
        "rdp_id": rdp_id,
        "fornitore_nome": data.fornitore_nome or "Da assegnare",
        "fornitore_id": "",
        "righe": righe,
        "importo_totale": 0,
        "note": (data.note or "") + f"\nGenerata automaticamente da AI Vision — Disegno {doc.get('nome_file', '')}",
        "riferimento_doc_id": doc_id,
        "stato": "bozza",
        "data_creazione": now.isoformat(),
    }

    # Ensure approvvigionamento structure exists
    await db.commesse.update_one(
        {"commessa_id": commessa_id, "approvvigionamento": {"$exists": False}},
        {"$set": {"approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []}}}
    )

    # Push RdP into commessa
    await db.commesse.update_one(
        {"commessa_id": commessa_id},
        {"$push": {"approvvigionamento.richieste": rdp}}
    )

    # Mark document as having generated an RdP
    await db.commessa_documents.update_one(
        {"doc_id": doc_id},
        {"$set": {
            "metadata_estratti.rdp_generata": True,
            "metadata_estratti.rdp_id": rdp_id,
        }}
    )

    return {
        "message": f"RdP creata con {len(righe)} righe di bulloneria",
        "rdp_id": rdp_id,
        "commessa_id": commessa_id,
        "righe_count": len(righe),
    }
