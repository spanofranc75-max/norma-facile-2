"""Sicurezza Cantieri (POS Generator) models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PosStatus(str, Enum):
    BOZZA = "bozza"
    COMPLETO = "completo"
    APPROVATO = "approvato"


# ── Predefined Risk Database ──
RISCHI_LAVORAZIONI = [
    {"id": "saldatura", "label": "Saldatura in opera", "category": "Lavorazioni a caldo", "icon": "Flame"},
    {"id": "saldatura_tig", "label": "Saldatura TIG/MIG", "category": "Lavorazioni a caldo", "icon": "Flame"},
    {"id": "taglio_plasma", "label": "Taglio al plasma", "category": "Lavorazioni a caldo", "icon": "Flame"},
    {"id": "molatura", "label": "Molatura / Smerigliatura", "category": "Lavorazioni meccaniche", "icon": "Disc"},
    {"id": "foratura", "label": "Foratura con trapano a colonna", "category": "Lavorazioni meccaniche", "icon": "Disc"},
    {"id": "taglio_flessibile", "label": "Taglio con flessibile (smerigliatrice)", "category": "Lavorazioni meccaniche", "icon": "Disc"},
    {"id": "piegatura", "label": "Piegatura lamiere / profili", "category": "Lavorazioni meccaniche", "icon": "Disc"},
    {"id": "lavoro_quota", "label": "Lavoro in quota (> 2m)", "category": "Rischi specifici", "icon": "ArrowUp"},
    {"id": "movimentazione", "label": "Movimentazione carichi pesanti", "category": "Rischi specifici", "icon": "Package"},
    {"id": "montaggio_cantiere", "label": "Montaggio in cantiere", "category": "Rischi specifici", "icon": "Wrench"},
    {"id": "verniciatura", "label": "Verniciatura / Zincatura", "category": "Rischi chimici", "icon": "Droplets"},
    {"id": "sabbiatura", "label": "Sabbiatura", "category": "Rischi chimici", "icon": "Droplets"},
    {"id": "spazi_confinati", "label": "Lavoro in spazi confinati", "category": "Rischi specifici", "icon": "AlertTriangle"},
]

MACCHINE_ATTREZZATURE = [
    {"id": "saldatrice_mig", "label": "Saldatrice MIG/MAG", "category": "Saldatura"},
    {"id": "saldatrice_tig", "label": "Saldatrice TIG", "category": "Saldatura"},
    {"id": "saldatrice_elettrodo", "label": "Saldatrice a elettrodo", "category": "Saldatura"},
    {"id": "smerigliatrice", "label": "Smerigliatrice angolare (Flessibile)", "category": "Taglio/Finitura"},
    {"id": "trapano_colonna", "label": "Trapano a colonna", "category": "Foratura"},
    {"id": "trapano_portatile", "label": "Trapano avvitatore portatile", "category": "Foratura"},
    {"id": "segatrice", "label": "Segatrice a nastro", "category": "Taglio"},
    {"id": "plasma", "label": "Tagliatrice al plasma", "category": "Taglio"},
    {"id": "pressa_piegatrice", "label": "Pressa piegatrice", "category": "Piegatura"},
    {"id": "carroponte", "label": "Carroponte / Gru", "category": "Sollevamento"},
    {"id": "muletto", "label": "Muletto / Carrello elevatore", "category": "Sollevamento"},
    {"id": "ponteggio", "label": "Ponteggio / Trabattello", "category": "Lavoro in quota"},
    {"id": "piattaforma_aerea", "label": "Piattaforma aerea (PLE)", "category": "Lavoro in quota"},
    {"id": "compressore", "label": "Compressore", "category": "Generico"},
]

DPI_LIST = [
    {"id": "casco", "label": "Casco di protezione", "category": "Testa"},
    {"id": "occhiali", "label": "Occhiali di protezione", "category": "Occhi"},
    {"id": "maschera_saldatura", "label": "Maschera per saldatura", "category": "Occhi"},
    {"id": "visiera", "label": "Visiera antiproiezione", "category": "Occhi"},
    {"id": "tappi_auricolari", "label": "Tappi auricolari / Cuffie", "category": "Udito"},
    {"id": "guanti_pelle", "label": "Guanti in pelle per saldatura", "category": "Mani"},
    {"id": "guanti_antitaglio", "label": "Guanti antitaglio", "category": "Mani"},
    {"id": "guanti_chimici", "label": "Guanti protezione chimica", "category": "Mani"},
    {"id": "scarpe_antinfortunistiche", "label": "Scarpe antinfortunistiche S3", "category": "Piedi"},
    {"id": "imbracatura", "label": "Imbracatura anticaduta", "category": "Anticaduta"},
    {"id": "grembiule_saldatura", "label": "Grembiule per saldatura", "category": "Corpo"},
    {"id": "tuta_lavoro", "label": "Tuta da lavoro ignifuga", "category": "Corpo"},
    {"id": "maschera_ffp2", "label": "Maschera FFP2 / FFP3", "category": "Vie respiratorie"},
]


class CantiereInfo(BaseModel):
    address: str = ""
    city: str = ""
    duration_days: int = 30
    start_date: Optional[str] = None
    committente: str = ""
    responsabile_lavori: str = ""
    coordinatore_sicurezza: str = ""


class PosCreate(BaseModel):
    project_name: str
    client_id: Optional[str] = None
    distinta_id: Optional[str] = None
    cantiere: CantiereInfo = Field(default_factory=CantiereInfo)
    selected_risks: List[str] = []
    selected_machines: List[str] = []
    selected_dpi: List[str] = []
    notes: Optional[str] = None


class PosUpdate(BaseModel):
    project_name: Optional[str] = None
    client_id: Optional[str] = None
    distinta_id: Optional[str] = None
    cantiere: Optional[CantiereInfo] = None
    selected_risks: Optional[List[str]] = None
    selected_machines: Optional[List[str]] = None
    selected_dpi: Optional[List[str]] = None
    ai_risk_assessment: Optional[str] = None
    status: Optional[PosStatus] = None
    notes: Optional[str] = None


class PosResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pos_id: str
    project_name: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    distinta_id: Optional[str] = None
    cantiere: CantiereInfo = Field(default_factory=CantiereInfo)
    selected_risks: List[str] = []
    selected_machines: List[str] = []
    selected_dpi: List[str] = []
    ai_risk_assessment: Optional[str] = None
    status: PosStatus = PosStatus.BOZZA
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PosListResponse(BaseModel):
    pos_list: List[PosResponse]
    total: int
