"""Perizia Sinistro (Damage Assessment) models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ModuloDanneggiato(BaseModel):
    """A single damaged module with dimensions."""
    descrizione: str = ""
    lunghezza_ml: float = 0
    altezza_m: float = 0
    note: str = ""


class VoceCosto(BaseModel):
    """Single cost line item for the perizia."""
    codice: str = ""
    descrizione: str = ""
    unita: str = "corpo"
    quantita: float = 1
    prezzo_unitario: float = 0
    totale: float = 0


class Localizzazione(BaseModel):
    """Geolocation data."""
    indirizzo: str = ""
    lat: float = 0
    lng: float = 0
    comune: str = ""
    provincia: str = ""


class PeriziaCreate(BaseModel):
    client_id: Optional[str] = None
    # Location
    localizzazione: Optional[Localizzazione] = None
    # Damage info
    tipo_danno: str = Field(default="strutturale", description="strutturale, estetico, automatismi")
    descrizione_utente: str = ""
    # Reference pricing
    prezzo_ml_originale: float = 0
    coefficiente_maggiorazione: float = 20
    # Modules
    moduli: List[ModuloDanneggiato] = []
    # Photos (base64 list)
    foto: List[str] = []
    # AI analysis
    ai_analysis: str = ""
    # Stato di fatto
    stato_di_fatto: str = ""
    # Nota tecnica
    nota_tecnica: str = ""
    # Cost items
    voci_costo: List[VoceCosto] = []
    # Lettera di accompagnamento tecnica
    lettera_accompagnamento: str = ""
    # Notes
    notes: str = ""


class PeriziaUpdate(BaseModel):
    client_id: Optional[str] = None
    localizzazione: Optional[Localizzazione] = None
    tipo_danno: Optional[str] = None
    descrizione_utente: Optional[str] = None
    prezzo_ml_originale: Optional[float] = None
    coefficiente_maggiorazione: Optional[float] = None
    moduli: Optional[List[ModuloDanneggiato]] = None
    foto: Optional[List[str]] = None
    ai_analysis: Optional[str] = None
    stato_di_fatto: Optional[str] = None
    nota_tecnica: Optional[str] = None
    voci_costo: Optional[List[VoceCosto]] = None
    lettera_accompagnamento: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
