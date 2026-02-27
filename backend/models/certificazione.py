"""Certificazioni CE (EN 1090 / EN 13241) models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CertStandard(str, Enum):
    EN_1090 = "EN 1090-1"
    EN_13241 = "EN 13241"


class ExecutionClass(str, Enum):
    EXC1 = "EXC1"
    EXC2 = "EXC2"
    EXC3 = "EXC3"
    EXC4 = "EXC4"


class CertStatus(str, Enum):
    BOZZA = "bozza"
    EMESSA = "emessa"
    REVISIONATA = "revisionata"


class TechnicalSpecs(BaseModel):
    execution_class: ExecutionClass = ExecutionClass.EXC2
    durability: str = "Classe C3 (media)"
    reaction_to_fire: str = "Classe A1 (non combustibile)"
    dangerous_substances: str = "Nessuna"
    # EN 13241 specific
    air_permeability: Optional[str] = None
    water_tightness: Optional[str] = None
    wind_resistance: Optional[str] = None
    mechanical_resistance: Optional[str] = None
    safe_opening: Optional[str] = "Conforme"
    # Custom notes
    additional_notes: Optional[str] = None


class CertificazioneCreate(BaseModel):
    project_name: str
    distinta_id: Optional[str] = None
    client_id: Optional[str] = None
    standard: CertStandard = CertStandard.EN_1090
    product_description: str = ""
    product_type: str = ""
    technical_specs: TechnicalSpecs = Field(default_factory=TechnicalSpecs)
    notes: Optional[str] = None


class CertificazioneUpdate(BaseModel):
    project_name: Optional[str] = None
    distinta_id: Optional[str] = None
    client_id: Optional[str] = None
    standard: Optional[CertStandard] = None
    product_description: Optional[str] = None
    product_type: Optional[str] = None
    technical_specs: Optional[TechnicalSpecs] = None
    status: Optional[CertStatus] = None
    notes: Optional[str] = None


class CertificazioneResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cert_id: str
    project_name: str
    distinta_id: Optional[str] = None
    distinta_name: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    standard: CertStandard
    product_description: str = ""
    product_type: str = ""
    declaration_number: str = ""
    technical_specs: TechnicalSpecs = Field(default_factory=TechnicalSpecs)
    status: CertStatus = CertStatus.BOZZA
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CertificazioneListResponse(BaseModel):
    certificazioni: List[CertificazioneResponse]
    total: int
