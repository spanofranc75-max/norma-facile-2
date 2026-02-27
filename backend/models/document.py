"""Document models for legal document generation."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Types of legal documents."""
    CONTRATTO = "contratto"
    LETTERA = "lettera"
    DIFFIDA = "diffida"
    ATTO = "atto"
    PROCURA = "procura"
    ALTRO = "altro"


class DocumentStatus(str, Enum):
    """Document status."""
    BOZZA = "bozza"
    COMPLETATO = "completato"
    ARCHIVIATO = "archiviato"


class DocumentBase(BaseModel):
    """Base document model."""
    title: str
    document_type: DocumentType
    content: Optional[str] = None


class DocumentCreate(BaseModel):
    """Model for creating a document."""
    title: str
    document_type: DocumentType
    prompt: str  # User's request for AI generation
    context: Optional[str] = None  # Additional context


class Document(DocumentBase):
    """Full document model."""
    model_config = ConfigDict(extra="ignore")
    
    document_id: str
    user_id: str
    status: DocumentStatus = DocumentStatus.BOZZA
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentResponse(BaseModel):
    """Document response for API."""
    model_config = ConfigDict(extra="ignore")
    
    document_id: str
    title: str
    document_type: DocumentType
    content: Optional[str] = None
    status: DocumentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """List of documents response."""
    documents: List[DocumentResponse]
    total: int
