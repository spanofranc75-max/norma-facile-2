"""Sopralluogo & Messa a Norma AI models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone


class FotoSopralluogo(BaseModel):
    """Photo attached to a survey."""
    foto_id: str = ""
    storage_path: str = ""
    original_filename: str = ""
    content_type: str = "image/jpeg"
    label: str = ""  # "motore", "guide", "panoramica", etc.
    size: int = 0


class RischioAnalisi(BaseModel):
    zona: str = ""
    tipo_rischio: str = ""
    gravita: str = ""
    problema: str = ""
    norma_riferimento: str = ""
    soluzione: str = ""
    confermato: bool = True  # User can deselect risks


class MaterialeSuggerito(BaseModel):
    keyword: str = ""
    descrizione: str = ""
    quantita: int = 1
    priorita: str = "obbligatorio"
    articolo_id: Optional[str] = None  # Matched article from catalog
    prezzo: float = 0


class AnalisiAI(BaseModel):
    tipo_chiusura: str = ""
    descrizione_generale: str = ""
    rischi: List[RischioAnalisi] = []
    dispositivi_presenti: List[str] = []
    dispositivi_mancanti: List[str] = []
    materiali_suggeriti: List[MaterialeSuggerito] = []
    note_tecniche: str = ""
    conformita_percentuale: int = 0


class SopralluogoCreate(BaseModel):
    client_id: Optional[str] = None
    indirizzo: str = ""
    comune: str = ""
    provincia: str = ""
    descrizione_utente: str = ""
    tipo_intervento: str = Field(default="messa_a_norma", description="messa_a_norma, manutenzione, nuova_installazione")
    tipo_perizia: str = Field(default="cancelli", description="cancelli, barriere, strutture")


class SopralluogoUpdate(BaseModel):
    client_id: Optional[str] = None
    indirizzo: Optional[str] = None
    comune: Optional[str] = None
    provincia: Optional[str] = None
    descrizione_utente: Optional[str] = None
    tipo_intervento: Optional[str] = None
    tipo_perizia: Optional[str] = None
    analisi_ai: Optional[dict] = None
    note_tecnico: Optional[str] = None
    status: Optional[str] = None


# ── Articoli Perizia (Configurable catalog) ──

class ArticoloPeriziaCreate(BaseModel):
    codice: str = ""
    descrizione: str = ""
    prezzo_base: float = 0
    unita: str = "pz"
    keyword_ai: str = ""  # keyword for AI matching: "costa", "fotocellula", etc.
    categoria: str = ""  # "sicurezza", "automazione", "struttura", "accessori"
    note: str = ""


class ArticoloPeriziaUpdate(BaseModel):
    codice: Optional[str] = None
    descrizione: Optional[str] = None
    prezzo_base: Optional[float] = None
    unita: Optional[str] = None
    keyword_ai: Optional[str] = None
    categoria: Optional[str] = None
    note: Optional[str] = None
