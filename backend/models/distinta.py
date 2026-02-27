"""Distinta Materiali (Bill of Materials) models - Smart BOM for Fabbri."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DistintaStatus(str, Enum):
    BOZZA = "bozza"
    CONFERMATA = "confermata"
    ORDINATA = "ordinata"
    COMPLETATA = "completata"


class MaterialCategory(str, Enum):
    PROFILO = "profilo"
    ACCESSORIO = "accessorio"
    FERRAMENTA = "ferramenta"
    VETRO = "vetro"
    GUARNIZIONE = "guarnizione"
    ALTRO = "altro"


class MaterialItem(BaseModel):
    item_id: Optional[str] = None
    category: MaterialCategory = MaterialCategory.PROFILO
    code: str = ""
    name: str
    description: Optional[str] = None

    # Profile reference
    profile_id: Optional[str] = None
    profile_label: Optional[str] = None

    # Dimensions
    length_mm: float = 0
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None

    # Quantities
    quantity: float = 1
    unit: str = "pz"

    # Weight & Cost & Surface per meter
    weight_per_meter: float = 0
    surface_per_meter: float = 0
    cost_per_unit: float = 0

    # Legacy field (kept for backward compat)
    weight_per_unit: float = 0

    # Calculated
    total_length: Optional[float] = None
    total_weight: Optional[float] = None
    total_surface: Optional[float] = None
    total_cost: Optional[float] = None

    notes: Optional[str] = None


class DistintaBase(BaseModel):
    name: str
    rilievo_id: Optional[str] = None
    client_id: Optional[str] = None
    notes: Optional[str] = None


class DistintaCreate(DistintaBase):
    items: List[MaterialItem] = []


class DistintaUpdate(BaseModel):
    name: Optional[str] = None
    rilievo_id: Optional[str] = None
    client_id: Optional[str] = None
    status: Optional[DistintaStatus] = None
    items: Optional[List[MaterialItem]] = None
    notes: Optional[str] = None


class DistintaTotals(BaseModel):
    total_items: int = 0
    total_length_m: float = 0
    total_weight_kg: float = 0
    total_surface_mq: float = 0
    total_cost: float = 0
    by_category: dict = {}


class Distinta(DistintaBase):
    model_config = ConfigDict(extra="ignore")
    distinta_id: str
    user_id: str
    status: DistintaStatus = DistintaStatus.BOZZA
    items: List[MaterialItem] = []
    totals: DistintaTotals = Field(default_factory=DistintaTotals)
    created_at: datetime
    updated_at: Optional[datetime] = None


class DistintaResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    distinta_id: str
    name: str
    rilievo_id: Optional[str] = None
    rilievo_name: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    status: DistintaStatus
    items: List[MaterialItem] = []
    totals: DistintaTotals
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DistintaListResponse(BaseModel):
    distinte: List[DistintaResponse]
    total: int


class BarCalculationResult(BaseModel):
    profile_id: str
    profile_label: str
    cuts: List[float] = []
    total_length_mm: float = 0
    total_length_m: float = 0
    bar_length_mm: int = 6000
    bars_needed: int = 0
    waste_mm: float = 0
    waste_percent: float = 0


class BarCalculationResponse(BaseModel):
    results: List[BarCalculationResult] = []
    total_bars: int = 0
