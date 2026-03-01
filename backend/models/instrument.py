"""Instrument model for the Registro Apparecchiature & Strumenti module."""
from pydantic import BaseModel
from typing import Optional, List, Literal

InstrumentType = Literal["misura", "saldatura", "macchinario", "altro"]
InstrumentStatus = Literal["attivo", "in_manutenzione", "fuori_uso", "scaduto"]


class InstrumentCreate(BaseModel):
    name: str
    serial_number: str
    type: InstrumentType = "misura"
    manufacturer: Optional[str] = None
    purchase_date: Optional[str] = None
    last_calibration_date: Optional[str] = None
    next_calibration_date: Optional[str] = None
    calibration_interval_months: Optional[int] = 12
    status: InstrumentStatus = "attivo"
    notes: Optional[str] = None


class InstrumentResponse(BaseModel):
    instrument_id: str
    name: str
    serial_number: str
    type: InstrumentType
    manufacturer: Optional[str] = None
    purchase_date: Optional[str] = None
    last_calibration_date: Optional[str] = None
    next_calibration_date: Optional[str] = None
    calibration_interval_months: Optional[int] = 12
    status: InstrumentStatus
    computed_status: str  # real-time status considering expiry
    days_until_expiry: Optional[int] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class InstrumentList(BaseModel):
    items: List[InstrumentResponse]
    total: int
    stats: dict
