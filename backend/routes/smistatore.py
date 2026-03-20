"""
Smistatore Intelligente — Route API per analisi certificati multi-pagina.
POST /api/smistatore/analyze/{doc_id} → Analizza un documento PDF con AI Vision
GET  /api/smistatore/index/{commessa_id} → Lista pagine indicizzate per commessa
"""
import logging

from fastapi import APIRouter, HTTPException, Depends

from core.security import get_current_user
from core.database import db
from services.smistatore_intelligente import analyze_and_index_document

router = APIRouter(prefix="/smistatore", tags=["smistatore"])
logger = logging.getLogger(__name__)


@router.post("/analyze/{doc_id}")
async def analyze_document(doc_id: str, user: dict = Depends(get_current_user)):
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
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
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
        {"user_id": user["user_id"], "matching_status": "scorta"},
        {"_id": 0, "page_pdf_b64": 0}
    ).sort("analyzed_at", -1).to_list(200)

    return {"total_scorte": len(scorte), "scorte": scorte}
