"""Audit & Non-Conformity models for the Audit module."""
from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal


AuditType = Literal["interno", "esterno_ente", "cliente"]
AuditOutcome = Literal["positivo", "negativo", "con_osservazioni"]
NCStatus = Literal["aperta", "in_lavorazione", "chiusa"]
NCPriority = Literal["alta", "media", "bassa"]


class AuditCreate(BaseModel):
    date: str
    audit_type: AuditType
    auditor_name: str
    scope: Optional[str] = None
    outcome: AuditOutcome = "positivo"
    notes: Optional[str] = None
    next_audit_date: Optional[str] = None

    @field_validator("auditor_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Il campo non può essere vuoto")
        return v.strip()


class AuditResponse(BaseModel):
    audit_id: str
    date: str
    audit_type: AuditType
    auditor_name: str
    scope: Optional[str] = None
    outcome: AuditOutcome
    notes: Optional[str] = None
    next_audit_date: Optional[str] = None
    has_report: bool = False
    report_filename: Optional[str] = None
    nc_count: int = 0
    nc_open: int = 0
    created_at: str
    updated_at: str


class AuditList(BaseModel):
    items: List[AuditResponse]
    total: int
    stats: dict


class NCCreate(BaseModel):
    date: str
    description: str
    source: Optional[str] = None
    priority: NCPriority = "media"
    audit_id: Optional[str] = None
    commessa_ref: Optional[str] = None

    @field_validator("description")
    @classmethod
    def desc_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("La descrizione non può essere vuota")
        return v.strip()


class NCUpdate(BaseModel):
    description: Optional[str] = None
    cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    priority: Optional[NCPriority] = None
    status: Optional[NCStatus] = None
    notes: Optional[str] = None


class NCResponse(BaseModel):
    nc_id: str
    nc_number: str
    date: str
    description: str
    source: Optional[str] = None
    cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    priority: NCPriority
    status: NCStatus
    audit_id: Optional[str] = None
    audit_ref: Optional[str] = None
    commessa_ref: Optional[str] = None
    closure_date: Optional[str] = None
    closed_by: Optional[str] = None
    notes: Optional[str] = None
    days_open: Optional[int] = None
    created_at: str
    updated_at: str


class NCList(BaseModel):
    items: List[NCResponse]
    total: int
    stats: dict
