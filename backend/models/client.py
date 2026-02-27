"""Client models for anagrafica clienti."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ClientType(str, Enum):
    """Tipo cliente."""
    AZIENDA = "azienda"
    PRIVATO = "privato"
    PUBBLICA_AMMINISTRAZIONE = "pa"


class ClientBase(BaseModel):
    """Base client model."""
    business_name: str = Field(..., description="Ragione sociale / Nome")
    client_type: ClientType = ClientType.AZIENDA
    
    # Fiscal data
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = Field(default="0000000", description="Codice destinatario SDI")
    pec: Optional[EmailStr] = None
    
    # Address
    address: str = ""
    cap: str = ""
    city: str = ""
    province: str = ""
    country: str = "IT"
    
    # Contact
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    
    # Notes
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    """Model for creating a client."""
    pass


class ClientUpdate(BaseModel):
    """Model for updating a client."""
    business_name: Optional[str] = None
    client_type: Optional[ClientType] = None
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = None
    pec: Optional[EmailStr] = None
    address: Optional[str] = None
    cap: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    notes: Optional[str] = None


class Client(ClientBase):
    """Full client model with ID and timestamps."""
    model_config = ConfigDict(extra="ignore")
    
    client_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClientResponse(BaseModel):
    """Client response for API."""
    model_config = ConfigDict(extra="ignore")
    
    client_id: str
    business_name: str
    client_type: ClientType
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = None
    pec: Optional[str] = None
    address: str = ""
    cap: str = ""
    city: str = ""
    province: str = ""
    country: str = "IT"
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClientListResponse(BaseModel):
    """List of clients response."""
    clients: List[ClientResponse]
    total: int
