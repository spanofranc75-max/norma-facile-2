"""Welder & Qualification models for the Registro Saldatori module."""
from pydantic import BaseModel
from typing import Optional, List, Literal

QualificationStatus = Literal["attivo", "in_scadenza", "scaduto"]


class QualificationCreate(BaseModel):
    standard: str = "ISO 9606-1"
    process: str = ""
    material_group: Optional[str] = None
    thickness_range: Optional[str] = None
    position: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: str
    notes: Optional[str] = None


class QualificationResponse(BaseModel):
    qual_id: str
    standard: str
    process: str
    material_group: Optional[str] = None
    thickness_range: Optional[str] = None
    position: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: str
    status: QualificationStatus
    days_until_expiry: Optional[int] = None
    has_file: bool = False
    filename: Optional[str] = None


class WelderCreate(BaseModel):
    name: str
    stamp_id: str
    role: Optional[str] = "saldatore"
    phone: Optional[str] = None
    email: Optional[str] = None
    hire_date: Optional[str] = None
    notes: Optional[str] = None


class WelderResponse(BaseModel):
    welder_id: str
    name: str
    stamp_id: str
    role: Optional[str] = "saldatore"
    phone: Optional[str] = None
    email: Optional[str] = None
    hire_date: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None
    qualifications: List[QualificationResponse] = []
    overall_status: str  # "ok", "warning", "expired", "no_qual"
    active_quals: int
    expiring_quals: int
    expired_quals: int
    created_at: str
    updated_at: str


class WelderList(BaseModel):
    items: List[WelderResponse]
    total: int
    stats: dict
