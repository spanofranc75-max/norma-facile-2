"""Models for EN 1090 Factory Production Control (FPC) system."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid


# ── Welders Registry ──────────────────────────────────────────

class WelderCreate(BaseModel):
    name: str
    qualification_level: str = ""          # e.g. "ISO 9606-1 135 P BW"
    license_expiry: Optional[str] = None   # ISO date string
    notes: Optional[str] = ""


class WelderOut(BaseModel):
    welder_id: str
    user_id: str
    name: str
    qualification_level: str = ""
    license_expiry: Optional[str] = None
    notes: str = ""
    is_expired: bool = False
    created_at: str


# ── Material Batches (Tracciabilità) ──────────────────────────

class MaterialBatchCreate(BaseModel):
    supplier_name: str
    material_type: str                     # e.g. "S275JR", "S355J2"
    heat_number: str                       # Numero Colata from mill cert 3.1
    certificate_base64: Optional[str] = None   # PDF base64
    certificate_filename: Optional[str] = None
    notes: Optional[str] = ""
    received_date: Optional[str] = None    # ISO date


class MaterialBatchOut(BaseModel):
    batch_id: str
    user_id: str
    supplier_name: str
    material_type: str
    heat_number: str
    has_certificate: bool = False
    certificate_filename: Optional[str] = None
    notes: str = ""
    received_date: Optional[str] = None
    created_at: str


# ── FPC Project Data ──────────────────────────────────────────

class FPCControl(BaseModel):
    control_type: str      # "dimensional", "visual", "ndt_ut", "ndt_mt", etc.
    label: str
    checked: bool = False
    checked_by: Optional[str] = None
    checked_at: Optional[str] = None


class FPCData(BaseModel):
    execution_class: str = ""              # EXC1, EXC2, EXC3, EXC4
    wps_id: Optional[str] = None           # Welding Procedure Specification
    welder_id: Optional[str] = None
    welder_name: Optional[str] = None
    material_batches: List[str] = []       # List of batch_ids
    controls: List[FPCControl] = []
    ce_label_generated: bool = False
    ce_label_generated_at: Optional[str] = None


class ProjectCreate(BaseModel):
    preventivo_id: str
    execution_class: str                   # Required at conversion


class ProjectOut(BaseModel):
    project_id: str
    user_id: str
    preventivo_id: str
    preventivo_number: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    subject: str = ""
    status: str = "in_progress"            # in_progress, completed, archived
    fpc_data: Optional[dict] = None
    lines: list = []
    created_at: str
    updated_at: Optional[str] = None


# Default FPC controls for new projects
DEFAULT_FPC_CONTROLS = [
    {"control_type": "dimensional", "label": "Controllo dimensionale", "checked": False},
    {"control_type": "visual", "label": "Controllo visivo saldature (EN ISO 5817)", "checked": False},
    {"control_type": "material_cert", "label": "Verifica certificati materiale 3.1", "checked": False},
    {"control_type": "welder_cert", "label": "Verifica qualifica saldatore", "checked": False},
    {"control_type": "wps_compliance", "label": "Conformità WPS", "checked": False},
    {"control_type": "surface_prep", "label": "Preparazione superfici", "checked": False},
    {"control_type": "marking", "label": "Marcatura e identificazione pezzi", "checked": False},
]
