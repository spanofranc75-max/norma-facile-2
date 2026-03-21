"""Company Document model for the Archivio Documentale Aziendale module."""
from pydantic import BaseModel
from typing import Optional, List, Literal

CATEGORIES = ["manuali", "procedure", "certificazioni", "template", "normative", "organigramma", "sicurezza_globale", "altro"]
CategoryType = Literal["manuali", "procedure", "certificazioni", "template", "normative", "organigramma", "sicurezza_globale", "altro"]

# Document types that are "global" - auto-attached to security packages
GLOBAL_DOC_TYPES = {
    "durc": {"label": "DURC", "desc": "Documento Unico di Regolarita Contributiva"},
    "visura": {"label": "Visura Camerale", "desc": "Visura CCIAA aggiornata"},
    "white_list": {"label": "White List", "desc": "Iscrizione White List Prefettura"},
    "patente_crediti": {"label": "Patente a Crediti", "desc": "Patente a Crediti INAIL"},
    "dvr": {"label": "DVR", "desc": "Documento di Valutazione dei Rischi (D.Lgs 81/08)"},
}

# Allegati Tecnici POS — valutazioni specifiche rischio
ALLEGATI_POS_TYPES = {
    "rumore": {"label": "Valutazione Rumore", "desc": "Valutazione esposizione al rumore (D.Lgs 81/08 Titolo VIII)"},
    "vibrazioni": {"label": "Valutazione Vibrazioni", "desc": "Valutazione esposizione a vibrazioni meccaniche (D.Lgs 81/08)"},
    "mmc": {"label": "Valutazione MMC", "desc": "Movimentazione Manuale dei Carichi (D.Lgs 81/08 Titolo VI)"},
}


class CompanyDocumentCreate(BaseModel):
    title: str
    category: CategoryType
    tags: List[str] = []


class VersionEntry(BaseModel):
    version: int
    filename: str
    safe_filename: str
    content_type: str
    size_kb: int = 0
    uploaded_by: Optional[str] = None
    upload_date: str
    note: str = ""


class CompanyDocumentResponse(BaseModel):
    doc_id: str
    title: str
    category: CategoryType
    filename: str
    content_type: str
    size_kb: int = 0
    tags: List[str] = []
    uploaded_by: Optional[str] = None
    upload_date: str
    version: int = 1
    version_count: int = 1


class CompanyDocumentList(BaseModel):
    items: List[CompanyDocumentResponse]
    total: int


class VersionListResponse(BaseModel):
    doc_id: str
    title: str
    current_version: int
    versions: List[VersionEntry]
