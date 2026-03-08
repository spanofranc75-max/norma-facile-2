"""Rilievo (On-Site Survey) models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class RilievoStatus(str, Enum):
    """Stato del rilievo."""
    BOZZA = "bozza"
    COMPLETATO = "completato"
    ARCHIVIATO = "archiviato"


class SketchData(BaseModel):
    """Data for a sketch/drawing."""
    sketch_id: Optional[str] = None
    name: str = ""
    background_image: Optional[str] = None  # Base64 or URL of background photo
    drawing_data: str = ""  # JSON string from canvas library
    dimensions: Optional[dict] = None  # {"width": 100, "height": 200, etc.}
    created_at: Optional[datetime] = None


class PhotoData(BaseModel):
    """Data for a site photo."""
    photo_id: Optional[str] = None
    name: str = ""
    image_data: str = ""  # Base64 encoded image
    caption: Optional[str] = None
    created_at: Optional[datetime] = None


class RilievoBase(BaseModel):
    """Base rilievo model."""
    client_id: str
    project_name: str
    survey_date: date = Field(default_factory=date.today)
    location: Optional[str] = None  # Address or location description
    notes: Optional[str] = None  # Technical notes
    commessa_id: Optional[str] = None


class RilievoCreate(RilievoBase):
    """Model for creating a rilievo."""
    sketches: List[SketchData] = []
    photos: List[PhotoData] = []


class RilievoUpdate(BaseModel):
    """Model for updating a rilievo."""
    client_id: Optional[str] = None
    project_name: Optional[str] = None
    survey_date: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    sketches: Optional[List[SketchData]] = None
    photos: Optional[List[PhotoData]] = None
    status: Optional[RilievoStatus] = None
    commessa_id: Optional[str] = None


class Rilievo(RilievoBase):
    """Full rilievo model."""
    model_config = ConfigDict(extra="ignore")
    
    rilievo_id: str
    user_id: str
    status: RilievoStatus = RilievoStatus.BOZZA
    sketches: List[SketchData] = []
    photos: List[PhotoData] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class RilievoResponse(BaseModel):
    """Rilievo response for API."""
    model_config = ConfigDict(extra="ignore")
    
    rilievo_id: str
    client_id: str
    client_name: Optional[str] = None
    project_name: str
    survey_date: date
    location: Optional[str] = None
    status: RilievoStatus
    sketches: List[SketchData] = []
    photos: List[PhotoData] = []
    notes: Optional[str] = None
    commessa_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class RilievoListResponse(BaseModel):
    """List of rilievi response."""
    rilievi: List[RilievoResponse]
    total: int
