"""Models for EN 13241 (Gates) & EN 12453 (Automation) certification."""
from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class TipoChiusura(str, Enum):
    CANCELLO_SCORREVOLE = "cancello_scorrevole"
    CANCELLO_BATTENTE = "cancello_battente"
    PORTONE_INDUSTRIALE = "portone_industriale"
    SERRANDA = "serranda"
    PORTONE_SEZIONALE = "portone_sezionale"
    BARRIERA = "barriera"


class Azionamento(str, Enum):
    MANUALE = "manuale"
    MOTORIZZATO = "motorizzato"


class ClasseVento(str, Enum):
    CLASSE_0 = "Classe 0"
    CLASSE_1 = "Classe 1"
    CLASSE_2 = "Classe 2"
    CLASSE_3 = "Classe 3"
    CLASSE_4 = "Classe 4"
    CLASSE_5 = "Classe 5"


class RischioItem(BaseModel):
    id: str
    descrizione: str
    presente: bool = False
    misura_adottata: str = ""
    conforme: bool = False


class ProvaForza(BaseModel):
    punto_misura: str  # "bordo_primario", "bordo_secondario", etc.
    forza_dinamica_n: Optional[float] = None  # Must be < 400N
    forza_statica_n: Optional[float] = None  # Must be < 150N
    conforme: bool = False


class GateCertificationCreate(BaseModel):
    commessa_id: str
    tipo_chiusura: TipoChiusura
    azionamento: Azionamento = Azionamento.MANUALE
    # Dimensions
    larghezza_mm: Optional[float] = None
    altezza_mm: Optional[float] = None
    peso_kg: Optional[float] = None
    # EN 13241 Performance
    resistenza_vento: ClasseVento = ClasseVento.CLASSE_2
    permeabilita_aria: str = "NPD"
    resistenza_termica: str = "NPD"
    sicurezza_apertura: str = "Conforme"
    sostanze_pericolose: str = "NPD"
    resistenza_acqua: str = "NPD"
    # EN 12453 Automation (only if motorizzato)
    analisi_rischi: Optional[List[RischioItem]] = None
    prove_forza: Optional[List[ProvaForza]] = None
    # Components
    motore_marca: str = ""
    motore_modello: str = ""
    motore_matricola: str = ""
    fotocellule: str = ""
    costola_sicurezza: str = ""
    centralina: str = ""
    telecomando: str = ""
    strumento_id: Optional[str] = None  # linked instrument from registry
    # System info
    sistema_cascata: str = ""  # e.g. "Fac", "Rolling Center", "BFT"
    note: str = ""


class GateCertificationUpdate(BaseModel):
    tipo_chiusura: Optional[TipoChiusura] = None
    azionamento: Optional[Azionamento] = None
    larghezza_mm: Optional[float] = None
    altezza_mm: Optional[float] = None
    peso_kg: Optional[float] = None
    resistenza_vento: Optional[ClasseVento] = None
    permeabilita_aria: Optional[str] = None
    resistenza_termica: Optional[str] = None
    sicurezza_apertura: Optional[str] = None
    sostanze_pericolose: Optional[str] = None
    resistenza_acqua: Optional[str] = None
    analisi_rischi: Optional[List[RischioItem]] = None
    prove_forza: Optional[List[ProvaForza]] = None
    motore_marca: Optional[str] = None
    motore_modello: Optional[str] = None
    motore_matricola: Optional[str] = None
    fotocellule: Optional[str] = None
    costola_sicurezza: Optional[str] = None
    centralina: Optional[str] = None
    telecomando: Optional[str] = None
    strumento_id: Optional[str] = None
    sistema_cascata: Optional[str] = None
    note: Optional[str] = None
