"""Perizia Sinistro (Damage Assessment) models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Codici Danno Database ──

CODICI_DANNO = [
    {
        "codice": "S1-DEF",
        "categoria": "Struttura",
        "label": "Deformazione plastica profilo",
        "norma": "EN 1090-2",
        "implicazione": "Snervamento acciaio. La raddrizzatura altera le proprieta meccaniche del materiale invalidando la certificazione originale.",
        "azione": "Sostituzione integrale del modulo.",
        "icon": "shield-alert",
        "color": "red",
    },
    {
        "codice": "S2-WELD",
        "categoria": "Struttura",
        "label": "Cricca/rottura saldatura",
        "norma": "EN 1090-2",
        "implicazione": "Cedimento giunto strutturale. Saldatura in opera non certificata comporta decadenza della Marcatura CE.",
        "azione": "Sostituzione (sconsigliata riparazione in opera).",
        "icon": "shield-alert",
        "color": "red",
    },
    {
        "codice": "A1-ANCH",
        "categoria": "Ancoraggio",
        "label": "Tassello sfilato/allentato",
        "norma": "ETAG 001",
        "implicazione": "Perdita tenuta meccanica dell'ancorante. Rischio ribaltamento sotto carico vento.",
        "azione": "Rifacimento fori e ancorante chimico certificato ETA.",
        "icon": "anchor",
        "color": "orange",
    },
    {
        "codice": "A2-CONC",
        "categoria": "Ancoraggio",
        "label": "Crepa nel cordolo/cemento",
        "norma": "NTC 2018",
        "implicazione": "Degrado del supporto strutturale. Compromessa la capacita portante del basamento.",
        "azione": "Ripristino con malta tixotropica strutturale e nuovo ancoraggio.",
        "icon": "anchor",
        "color": "orange",
    },
    {
        "codice": "P1-ZINC",
        "categoria": "Protezione",
        "label": "Zincatura esposta/fratturata",
        "norma": "ISO 1461 / ISO 12944",
        "implicazione": "Perdita protezione galvanica. Esposizione acciaio a fenomeni ossidativi non riparabili con verniciatura in loco.",
        "azione": "Trattamento industriale (non ritocco a mano). Ripristino ciclo anticorrosivo.",
        "icon": "paint-bucket",
        "color": "blue",
    },
    {
        "codice": "G1-GAP",
        "categoria": "Sicurezza",
        "label": "Alterazione distanze anti-cesoiamento",
        "norma": "EN 13241",
        "implicazione": "Rischio schiacciamento. Le distanze di sicurezza non rispettano piu i requisiti della norma prodotto.",
        "azione": "Riallineamento millimetrico e test spazi. Aggiornamento DoP.",
        "icon": "ruler",
        "color": "yellow",
    },
    {
        "codice": "M1-FORCE",
        "categoria": "Automazione",
        "label": "Sforzo anomalo motore/braccio",
        "norma": "EN 12453",
        "implicazione": "Sicurezza in uso compromessa. Forze di impatto fuori norma possono causare lesioni.",
        "azione": "Test delle forze con strumento certificato. Sostituzione componenti se fuori tolleranza.",
        "icon": "zap",
        "color": "purple",
    },
]

CODICI_DANNO_MAP = {c["codice"]: c for c in CODICI_DANNO}


class ModuloDanneggiato(BaseModel):
    """A single damaged module with dimensions."""
    descrizione: str = ""
    lunghezza_ml: float = 0
    altezza_m: float = 0
    note: str = ""


class VoceCosto(BaseModel):
    """Single cost line item for the perizia."""
    codice: str = ""
    descrizione: str = ""
    unita: str = "corpo"
    quantita: float = 1
    prezzo_unitario: float = 0
    totale: float = 0


class Localizzazione(BaseModel):
    """Geolocation data."""
    indirizzo: str = ""
    lat: float = 0
    lng: float = 0
    comune: str = ""
    provincia: str = ""


class PeriziaCreate(BaseModel):
    client_id: Optional[str] = None
    localizzazione: Optional[Localizzazione] = None
    tipo_danno: str = Field(default="strutturale", description="strutturale, estetico, automatismi")
    descrizione_utente: str = ""
    codici_danno: List[str] = []  # Selected damage codes e.g. ["S1-DEF", "P1-ZINC"]
    prezzo_ml_originale: float = 0
    coefficiente_maggiorazione: float = 20
    moduli: List[ModuloDanneggiato] = []
    foto: List[str] = []
    ai_analysis: str = ""
    stato_di_fatto: str = ""
    nota_tecnica: str = ""
    voci_costo: List[VoceCosto] = []
    lettera_accompagnamento: str = ""
    notes: str = ""
    smaltimento: bool = True
    accesso_difficile: bool = False
    sconto_cortesia: float = 0
    commessa_id: Optional[str] = None


class PeriziaUpdate(BaseModel):
    client_id: Optional[str] = None
    localizzazione: Optional[Localizzazione] = None
    tipo_danno: Optional[str] = None
    descrizione_utente: Optional[str] = None
    codici_danno: Optional[List[str]] = None
    prezzo_ml_originale: Optional[float] = None
    coefficiente_maggiorazione: Optional[float] = None
    moduli: Optional[List[ModuloDanneggiato]] = None
    foto: Optional[List[str]] = None
    ai_analysis: Optional[str] = None
    stato_di_fatto: Optional[str] = None
    nota_tecnica: Optional[str] = None
    voci_costo: Optional[List[VoceCosto]] = None
    lettera_accompagnamento: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    smaltimento: Optional[bool] = None
    accesso_difficile: Optional[bool] = None
    sconto_cortesia: Optional[float] = None
    commessa_id: Optional[str] = None
