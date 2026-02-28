"""Company settings model for invoice header/supplier info."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime


class BankDetails(BaseModel):
    """Coordinate bancarie."""
    bank_name: str = ""
    iban: str = ""
    bic_swift: Optional[str] = None


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
    email: Optional[EmailStr] = None
    pec: Optional[EmailStr] = None
    website: Optional[str] = None
    
    # Bank details
    bank_details: BankDetails = Field(default_factory=BankDetails)
    
    # Logo (base64 data URI)
    logo_url: Optional[str] = None
    
    # Condizioni di vendita
    condizioni_vendita: Optional[str] = None
    
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
    email: Optional[EmailStr] = None
    pec: Optional[EmailStr] = None
    website: Optional[str] = None
    bank_details: Optional[BankDetails] = None
    logo_url: Optional[str] = None
    condizioni_vendita: Optional[str] = None
