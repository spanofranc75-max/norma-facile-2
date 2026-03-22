"""Company settings model for invoice header/supplier info."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr, validator
from typing import Optional
from datetime import datetime


class BankDetails(BaseModel):
    """Coordinate bancarie — singolo conto (legacy, backward compat)."""
    bank_name: str = ""
    iban: str = ""
    bic_swift: Optional[str] = None


class BankAccount(BaseModel):
    """Conto corrente aziendale."""
    account_id: Optional[str] = None
    bank_name: str = ""
    iban: str = ""
    bic_swift: Optional[str] = None
    intestatario: Optional[str] = None
    predefinito: bool = False


class CompanySettings(BaseModel):
    """Impostazioni aziendali per intestazione fatture."""
    model_config = ConfigDict(extra="ignore")
    
    settings_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Business info
    business_name: str = ""
    legal_name: Optional[str] = None  # If different from business_name
    
    # Fiscal data
    partita_iva: str = ""
    codice_fiscale: str = ""
    regime_fiscale: str = "RF01"  # Ordinario
    
    # Address
    address: str = ""
    cap: str = ""
    city: str = ""
    province: str = ""
    country: str = "IT"
    
    # Contact
    phone: Optional[str] = None
    email: Optional[str] = None
    pec: Optional[str] = None
    website: Optional[str] = None
    
    # Bank details (legacy single)
    bank_details: BankDetails = Field(default_factory=BankDetails)
    # Multiple bank accounts
    bank_accounts: list = Field(default_factory=list)
    
    # SDI / Fatturazione Elettronica
    codice_destinatario: Optional[str] = None  # Codice SDI 7 chars
    natura_giuridica: Optional[str] = None  # es. "S.r.l.s.", "S.r.l.", "Ditta individuale"
    
    # Logo (base64 data URI)
    logo_url: Optional[str] = None
    
    # Firma digitale (base64 data URI - immagine PNG/JPG)
    firma_digitale: Optional[str] = None
    
    # Figure aziendali sicurezza (defaults per POS)
    # Struttura: [{"ruolo": "DATORE_LAVORO", "nome": "...", "telefono": "", "email": ""}, ...]
    figure_aziendali: list = Field(default_factory=list)

    # EN 1090 — Dati certificazione aziendali
    responsabile_nome: Optional[str] = None  # Nome e cognome responsabile/amministratore
    ruolo_firmatario: Optional[str] = None  # es. "Legale Rappresentante"
    ente_certificatore: Optional[str] = None  # es. "Rina Service"
    ente_certificatore_numero: Optional[str] = None  # es. "0474"
    certificato_en1090_numero: Optional[str] = None  # Numero certificato EN 1090
    classe_esecuzione_default: Optional[str] = None  # EXC1, EXC2, EXC3, EXC4
    certificato_en13241_numero: Optional[str] = None  # Numero certificato EN 13241
    
    # Condizioni di vendita
    condizioni_vendita: Optional[str] = None

    # Aruba SDI Integration (legacy)
    aruba_username: Optional[str] = None
    aruba_password: Optional[str] = None
    aruba_sandbox: bool = True
    
    # Fatture in Cloud Integration
    fic_company_id: Optional[str] = None
    fic_access_token: Optional[str] = None
    
    # Timestamps
    updated_at: Optional[datetime] = None


class CompanySettingsUpdate(BaseModel):
    """Model for updating company settings."""
    business_name: Optional[str] = None
    legal_name: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_fiscale: Optional[str] = None
    regime_fiscale: Optional[str] = None
    address: Optional[str] = None
    cap: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    pec: Optional[str] = None
    website: Optional[str] = None
    bank_details: Optional[BankDetails] = None
    bank_accounts: Optional[list] = None
    codice_destinatario: Optional[str] = None
    natura_giuridica: Optional[str] = None
    logo_url: Optional[str] = None
    firma_digitale: Optional[str] = None
    responsabile_nome: Optional[str] = None
    ruolo_firmatario: Optional[str] = None
    ente_certificatore: Optional[str] = None
    ente_certificatore_numero: Optional[str] = None
    certificato_en1090_numero: Optional[str] = None
    classe_esecuzione_default: Optional[str] = None
    certificato_en13241_numero: Optional[str] = None
    condizioni_vendita: Optional[str] = None
    figure_aziendali: Optional[list] = None
    aruba_username: Optional[str] = None
    aruba_password: Optional[str] = None
    aruba_sandbox: Optional[bool] = None
    fic_company_id: Optional[str] = None
    fic_access_token: Optional[str] = None

    @validator("email", "pec", pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v
