"""Chat models for legal assistant."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Chat message role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message."""
    model_config = ConfigDict(extra="ignore")
    
    message_id: Optional[str] = None
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request from user."""
    message: str
    conversation_id: Optional[str] = None  # For continuing a conversation


class ChatResponse(BaseModel):
    """Chat response from assistant."""
    model_config = ConfigDict(extra="ignore")
    
    message_id: str
    conversation_id: str
    content: str
    timestamp: datetime


class Conversation(BaseModel):
    """Full conversation model."""
    model_config = ConfigDict(extra="ignore")
    
    conversation_id: str
    user_id: str
    title: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    """List of conversations."""
    conversations: List[dict]
    total: int
