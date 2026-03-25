"""
Pacco Documenti Cantiere — Route API per il "Pulsante Magico".
GET /api/commesse/{id}/pacco-documenti → PDF download
"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from core.security import get_current_user, tenant_match
from services.pacco_documenti import generate_pacco_documenti

router = APIRouter(tags=["pacco-documenti"])
logger = logging.getLogger(__name__)


@router.get("/commesse/{commessa_id}/pacco-documenti")
async def download_pacco_documenti(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Pulsante Magico — Genera e scarica il Pacco Documenti Cantiere (PDF).
    Include tutte le parti pertinenti (A: EN 1090, B: EN 13241, C: Generiche).
    """
    try:
        pdf_buffer = await generate_pacco_documenti(commessa_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        logger.error(f"[PACCO] Errore generazione: {e}", exc_info=True)
        raise HTTPException(500, f"Errore nella generazione del pacco documenti: {str(e)}")

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="pacco_documenti_{commessa_id}.pdf"'
        },
    )
