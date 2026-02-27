"""Chat routes - Placeholder for Phase 2."""
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from models.chat import ChatRequest, ChatResponse, ConversationListResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(user: dict = Depends(get_current_user)):
    """
    Get all conversations for current user.
    TODO: Implement in Phase 2
    """
    return ConversationListResponse(conversations=[], total=0)


@router.post("/", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """
    Send message to legal assistant chatbot.
    TODO: Implement in Phase 2
    """
    raise HTTPException(status_code=501, detail="Funzionalità in arrivo nella Fase 2")
