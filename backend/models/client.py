"""Client models for anagrafica clienti / fornitori."""
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ClientStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class ClientType(str, Enum):
    """Tipo soggetto."""
    CLIENTE = "cliente"
    FORNITORE = "fornitore"
    CLIENTE_FORNITORE = "cliente_fornitore"


class ContactPerson(BaseModel):
    """Persona di riferimento con preferenze invio documenti."""
    model_config = ConfigDict(extra="ignore")

    tipo: str = ""
    nome: str = ""
    telefono: str = ""
    email: str = ""
    include_preventivi: bool = False
    include_fatture: bool = False
    include_solleciti: bool = False
    include_ordini: bool = False
    include_ddt: bool = False
    note: str = ""

    @model_validator(mode="before")
    @classmethod
    def _nulls_to_defaults(cls, data):
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class ClientBase(BaseModel):
    """Base client model — scheda completa."""
    model_config = ConfigDict(extra="ignore")

    business_name: str = Field(..., description="Ragione sociale / Nome")
    client_type: str = Field(default="cliente", description="cliente, fornitore, cliente_fornitore")
    persona_fisica: bool = False
    titolo: Optional[str] = ""
    cognome: Optional[str] = ""
    nome: Optional[str] = ""

    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = Field(default="0000000", description="Codice destinatario SDI")
    pec: Optional[str] = None

    address: Optional[str] = ""
    cap: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    country: Optional[str] = "IT"

    phone: Optional[str] = None
    cellulare: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    sito_web: Optional[str] = None

    contacts: List[ContactPerson] = []

    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None

    supplier_payment_type_id: Optional[str] = None
    supplier_payment_type_label: Optional[str] = None
    supplier_iban: Optional[str] = None
    supplier_banca: Optional[str] = None

    notes: Optional[str] = None
    status: str = Field(default="active", description="active, archived, blocked")
    successor_client_id: Optional[str] = Field(default=None, description="ID del cliente successore")

    @model_validator(mode="before")
    @classmethod
    def _nulls_to_defaults(cls, data):
        """Strip null values so Pydantic uses field defaults instead of rejecting them."""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class ClientCreate(ClientBase):
    """Model for creating a client."""
    pass


class ClientUpdate(BaseModel):
    """Model for updating a client — all optional."""
    model_config = ConfigDict(extra="ignore")

    business_name: Optional[str] = None
    client_type: Optional[str] = None
    persona_fisica: Optional[bool] = None
    titolo: Optional[str] = None
    cognome: Optional[str] = None
    nome: Optional[str] = None
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = None
    pec: Optional[str] = None
    address: Optional[str] = None
    cap: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    cellulare: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    sito_web: Optional[str] = None
    contacts: Optional[List[ContactPerson]] = None
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None
    supplier_payment_type_id: Optional[str] = None
    supplier_payment_type_label: Optional[str] = None
    supplier_iban: Optional[str] = None
    supplier_banca: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    successor_client_id: Optional[str] = None


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
    client_type: str = "cliente"
    persona_fisica: bool = False
    titolo: Optional[str] = ""
    cognome: Optional[str] = ""
    nome: Optional[str] = ""
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = None
    pec: Optional[str] = None
    address: Optional[str] = ""
    cap: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    country: Optional[str] = "IT"
    phone: Optional[str] = None
    cellulare: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    sito_web: Optional[str] = None
    contacts: List[ContactPerson] = []
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None
    supplier_payment_type_id: Optional[str] = None
    supplier_payment_type_label: Optional[str] = None
    supplier_iban: Optional[str] = None
    supplier_banca: Optional[str] = None
    notes: Optional[str] = None
    status: str = "active"
    successor_client_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClientListResponse(BaseModel):
    """List of clients response."""
    clients: List[ClientResponse]
    total: int
