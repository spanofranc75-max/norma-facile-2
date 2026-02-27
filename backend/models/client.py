"""Client models for anagrafica clienti / fornitori."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ClientType(str, Enum):
    """Tipo soggetto."""
    CLIENTE = "cliente"
    FORNITORE = "fornitore"
    CLIENTE_FORNITORE = "cliente_fornitore"


class ContactPerson(BaseModel):
    """Persona di riferimento con preferenze invio documenti."""
    tipo: str = ""  # es: Commerciale, Amministrativo, Titolare
    nome: str = ""
    telefono: str = ""
    email: str = ""
    # Document email preferences
    include_preventivi: bool = False
    include_fatture: bool = False
    include_solleciti: bool = False
    include_ordini: bool = False
    include_ddt: bool = False
    note: str = ""


class ClientBase(BaseModel):
    """Base client model — scheda completa."""
    # Anagrafica
    business_name: str = Field(..., description="Ragione sociale / Nome")
    client_type: str = Field(default="cliente", description="cliente, fornitore, cliente_fornitore")
    persona_fisica: bool = False
    titolo: str = ""
    cognome: str = ""
    nome: str = ""

    # Dati fiscali
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_sdi: Optional[str] = Field(default="0000000", description="Codice destinatario SDI")
    pec: Optional[str] = None

    # Indirizzo
    address: str = ""
    cap: str = ""
    city: str = ""
    province: str = ""
    country: str = "IT"

    # Contatti principali
    phone: Optional[str] = None
    cellulare: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    sito_web: Optional[str] = None

    # Persone di riferimento
    contacts: List[ContactPerson] = []

    # Condizioni pagamento (link a PaymentType)
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None  # Cached label for display
    iban: Optional[str] = None
    banca: Optional[str] = None

    # Note
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    """Model for creating a client."""
    pass


class ClientUpdate(BaseModel):
    """Model for updating a client — all optional."""
    business_name: Optional[str] = None
    client_type: Optional[ClientType] = None
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
    client_type: str = "cliente"  # String for backward compat
    persona_fisica: bool = False
    titolo: str = ""
    cognome: str = ""
    nome: str = ""
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
    cellulare: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    sito_web: Optional[str] = None
    contacts: List[ContactPerson] = []
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    iban: Optional[str] = None
    banca: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClientListResponse(BaseModel):
    """List of clients response."""
    clients: List[ClientResponse]
    total: int
