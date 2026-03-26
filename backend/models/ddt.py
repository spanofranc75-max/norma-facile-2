"""DDT (Documento di Trasporto) models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DDTLine(BaseModel):
    line_id: Optional[str] = None
    codice_articolo: Optional[str] = ""
    description: str = ""
    unit: str = "pz"
    quantity: float = 0
    qta_fatturata: float = 0
    unit_price: float = 0
    sconto_1: float = 0
    sconto_2: float = 0
    vat_rate: str = "22"
    notes: str = ""


class DestinazioneMerce(BaseModel):
    ragione_sociale: str = ""
    indirizzo: str = ""
    cap: str = ""
    localita: str = ""
    provincia: str = ""
    telefono: str = ""
    cellulare: str = ""
    paese: str = "IT"


class DDTCreate(BaseModel):
    ddt_type: str = Field(default="vendita", description="vendita, conto_lavoro, rientro_conto_lavoro")
    number: Optional[str] = None  # Optional: override auto-generated number
    client_id: Optional[str] = None
    subject: str = ""
    destinazione: Optional[DestinazioneMerce] = None
    # Transport
    causale_trasporto: str = "Vendita"
    aspetto_beni: str = ""
    vettore: str = ""
    mezzo_trasporto: str = ""
    porto: str = "Franco"
    data_ora_trasporto: Optional[str] = None
    num_colli: int = 0
    peso_lordo_kg: float = 0
    peso_netto_kg: float = 0
    # Payment / financial
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    stampa_prezzi: bool = True
    riferimento: str = ""
    acconto: float = 0
    sconto_globale: float = 0
    notes: str = ""
    lines: List[DDTLine] = []


class DDTUpdate(BaseModel):
    number: Optional[str] = None  # Editable number
    ddt_type: Optional[str] = None
    client_id: Optional[str] = None
    subject: Optional[str] = None
    destinazione: Optional[DestinazioneMerce] = None
    causale_trasporto: Optional[str] = None
    aspetto_beni: Optional[str] = None
    vettore: Optional[str] = None
    mezzo_trasporto: Optional[str] = None
    porto: Optional[str] = None
    data_ora_trasporto: Optional[str] = None
    num_colli: Optional[int] = None
    peso_lordo_kg: Optional[float] = None
    peso_netto_kg: Optional[float] = None
    payment_type_id: Optional[str] = None
    payment_type_label: Optional[str] = None
    stampa_prezzi: Optional[bool] = None
    riferimento: Optional[str] = None
    acconto: Optional[float] = None
    sconto_globale: Optional[float] = None
    notes: Optional[str] = None
    lines: Optional[List[DDTLine]] = None
    status: Optional[str] = None
