"""Distinta Materiali (Bill of Materials) models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DistintaStatus(str, Enum):
    """Stato della distinta."""
    BOZZA = "bozza"
    CONFERMATA = "confermata"
    ORDINATA = "ordinata"
    COMPLETATA = "completata"


class MaterialCategory(str, Enum):
    """Categoria materiale."""
    PROFILO = "profilo"
    ACCESSORIO = "accessorio"
    FERRAMENTA = "ferramenta"
    VETRO = "vetro"
    GUARNIZIONE = "guarnizione"
    ALTRO = "altro"


class MaterialItem(BaseModel):
    """Single material item in the BOM."""
    item_id: Optional[str] = None
    category: MaterialCategory = MaterialCategory.PROFILO
    code: str = ""  # Product code
    name: str  # Profile/material name
    description: Optional[str] = None
    
    # Dimensions
    length_mm: float = 0  # Length in mm
    width_mm: Optional[float] = None  # Width in mm (for sheets)
    height_mm: Optional[float] = None  # Height in mm
    
    # Quantities
    quantity: float = 1
    unit: str = "pz"  # pz, m, m², kg
    
    # Weight & Cost
    weight_per_unit: float = 0  # kg per unit/meter
    cost_per_unit: float = 0  # € per unit/meter
    
    # Calculated (filled on save)
    total_length: Optional[float] = None  # length_mm * quantity
    total_weight: Optional[float] = None
    total_cost: Optional[float] = None
    
    # Notes
    notes: Optional[str] = None


class DistintaBase(BaseModel):
    """Base distinta model."""
    name: str
    rilievo_id: Optional[str] = None  # Link to source Rilievo
    client_id: Optional[str] = None  # Link to client
    notes: Optional[str] = None


class DistintaCreate(DistintaBase):
    """Model for creating a distinta."""
    items: List[MaterialItem] = []


class DistintaUpdate(BaseModel):
    """Model for updating a distinta."""
    name: Optional[str] = None
    rilievo_id: Optional[str] = None
    client_id: Optional[str] = None
    status: Optional[DistintaStatus] = None
    items: Optional[List[MaterialItem]] = None
    notes: Optional[str] = None


class DistintaTotals(BaseModel):
    """Calculated totals for the BOM."""
    total_items: int = 0
    total_length_m: float = 0  # Total length in meters
    total_weight_kg: float = 0
    total_cost: float = 0
    
    # Breakdown by category
    by_category: dict = {}  # {"profilo": {"count": 5, "weight": 10, "cost": 100}, ...}


class Distinta(DistintaBase):
    """Full distinta model."""
    model_config = ConfigDict(extra="ignore")
    
    distinta_id: str
    user_id: str
    status: DistintaStatus = DistintaStatus.BOZZA
    items: List[MaterialItem] = []
    totals: DistintaTotals = Field(default_factory=DistintaTotals)
    created_at: datetime
    updated_at: Optional[datetime] = None


class DistintaResponse(BaseModel):
    """Distinta response for API."""
    model_config = ConfigDict(extra="ignore")
    
    distinta_id: str
    name: str
    rilievo_id: Optional[str] = None
    rilievo_name: Optional[str] = None  # Populated from rilievo
    client_id: Optional[str] = None
    client_name: Optional[str] = None  # Populated from client
    status: DistintaStatus
    items: List[MaterialItem] = []
    totals: DistintaTotals
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DistintaListResponse(BaseModel):
    """List of distinte response."""
    distinte: List[DistintaResponse]
    total: int
