"""Document routes - Placeholder for Phase 2."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from core.security import get_current_user
from models.document import DocumentCreate, DocumentResponse, DocumentListResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def get_documents(user: dict = Depends(get_current_user)):
    """
    Get all documents for current user.
    TODO: Implement in Phase 2
    """
    return DocumentListResponse(documents=[], total=0)


@router.post("/", response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    user: dict = Depends(get_current_user)
):
    """
    Create a new legal document using AI.
    TODO: Implement in Phase 2
    """
    raise HTTPException(status_code=501, detail="Funzionalità in arrivo nella Fase 2")
