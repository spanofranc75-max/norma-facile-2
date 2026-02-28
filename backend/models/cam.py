"""
CAM (Criteri Ambientali Minimi) Models and Utilities
DM 23 giugno 2022 n. 256 - Edilizia
Requisiti per carpenteria metallica e acciaio strutturale.
"""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class MetodoProduttivo(str, Enum):
    """Metodo produttivo dell'acciaio - determina la soglia minima di riciclato."""
    FORNO_ELETTRICO_NON_LEGATO = "forno_elettrico_non_legato"  # 75%
    FORNO_ELETTRICO_LEGATO = "forno_elettrico_legato"          # 60%
    CICLO_INTEGRALE = "ciclo_integrale"                        # 12%
    SCONOSCIUTO = "sconosciuto"


class TipoCertificazioneCAM(str, Enum):
    """Certificazioni ammesse per dimostrare conformità CAM."""
    EPD = "epd"                           # Environmental Product Declaration (ISO 14025, EN 15804)
    REMADE_IN_ITALY = "remade_in_italy"   # Certificazione ReMade in Italy (ACCREDIA)
    DICHIARAZIONE_PRODUTTORE = "dichiarazione_produttore"  # Dichiarazione del produttore
    ALTRA_ACCREDITATA = "altra_accreditata"  # Altra certificazione accreditata
    NESSUNA = "nessuna"


# Soglie minime CAM per tipo di acciaio (DM 23/06/2022)
SOGLIE_CAM_ACCIAIO = {
    # Usi strutturali
    "strutturale": {
        MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO: 75,
        MetodoProduttivo.FORNO_ELETTRICO_LEGATO: 60,
        MetodoProduttivo.CICLO_INTEGRALE: 12,
        MetodoProduttivo.SCONOSCIUTO: 75,  # Default più restrittivo
    },
    # Usi non strutturali
    "non_strutturale": {
        MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO: 65,
        MetodoProduttivo.FORNO_ELETTRICO_LEGATO: 60,
        MetodoProduttivo.CICLO_INTEGRALE: 12,
        MetodoProduttivo.SCONOSCIUTO: 65,
    },
}


class DatiCAMMateriale(BaseModel):
    """Dati CAM per un singolo lotto/materiale."""
    percentuale_riciclato: float = 0  # % dichiarata dal fornitore
    metodo_produttivo: MetodoProduttivo = MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO
    tipo_certificazione: TipoCertificazioneCAM = TipoCertificazioneCAM.NESSUNA
    numero_certificazione: Optional[str] = None
    ente_certificatore: Optional[str] = None  # Es: "ICMQ", "Bureau Veritas", ecc.
    data_certificazione: Optional[str] = None
    scadenza_certificazione: Optional[str] = None
    km_approvvigionamento: Optional[float] = None  # Distanza in km
    uso_strutturale: bool = True  # Se è per uso strutturale
    note_cam: Optional[str] = None


class RigaCalcoloCAM(BaseModel):
    """Riga di calcolo CAM per la dichiarazione."""
    materiale_id: str
    descrizione: str
    peso_kg: float
    percentuale_riciclato: float
    peso_riciclato_kg: float  # = peso_kg * (percentuale_riciclato / 100)
    metodo_produttivo: str
    certificazione: str
    conforme_cam: bool


class CalcoloCAMCommessa(BaseModel):
    """Risultato del calcolo CAM per una commessa."""
    commessa_id: str
    commessa_numero: str
    peso_totale_kg: float
    peso_riciclato_kg: float
    percentuale_riciclato_totale: float  # (peso_riciclato / peso_totale) * 100
    soglia_minima_richiesta: float  # La più alta tra i materiali usati
    conforme_cam: bool
    righe: List[RigaCalcoloCAM]
    data_calcolo: str
    note: Optional[str] = None


def calcola_conformita_cam(
    peso_kg: float,
    percentuale_riciclato: float,
    metodo_produttivo: MetodoProduttivo,
    uso_strutturale: bool = True
) -> dict:
    """
    Calcola se un materiale è conforme CAM.
    
    Returns:
        {
            "peso_riciclato_kg": float,
            "soglia_minima": float,
            "conforme": bool,
            "margine": float  # positivo = sopra soglia, negativo = sotto
        }
    """
    categoria = "strutturale" if uso_strutturale else "non_strutturale"
    soglia = SOGLIE_CAM_ACCIAIO[categoria].get(metodo_produttivo, 75)
    
    peso_riciclato = peso_kg * (percentuale_riciclato / 100)
    conforme = percentuale_riciclato >= soglia
    margine = percentuale_riciclato - soglia
    
    return {
        "peso_riciclato_kg": round(peso_riciclato, 2),
        "soglia_minima": soglia,
        "conforme": conforme,
        "margine": round(margine, 1),
    }


def calcola_cam_commessa(materiali: List[dict]) -> dict:
    """
    Calcola la conformità CAM totale per una commessa.
    
    Args:
        materiali: Lista di dict con:
            - descrizione: str
            - peso_kg: float
            - percentuale_riciclato: float
            - metodo_produttivo: str (enum value)
            - uso_strutturale: bool
            - certificazione: str
    
    Returns:
        Dizionario con calcolo totale e per-riga.
    """
    if not materiali:
        return {
            "peso_totale_kg": 0,
            "peso_riciclato_kg": 0,
            "percentuale_riciclato_totale": 0,
            "soglia_minima_richiesta": 75,
            "conforme_cam": False,
            "righe": [],
            "note": "Nessun materiale specificato",
        }
    
    peso_totale = 0
    peso_riciclato_totale = 0
    soglia_max = 0
    righe = []
    
    for mat in materiali:
        peso = mat.get("peso_kg", 0)
        perc_ric = mat.get("percentuale_riciclato", 0)
        metodo = mat.get("metodo_produttivo", "forno_elettrico_non_legato")
        uso_strutt = mat.get("uso_strutturale", True)
        
        try:
            metodo_enum = MetodoProduttivo(metodo)
        except ValueError:
            metodo_enum = MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO
        
        calc = calcola_conformita_cam(peso, perc_ric, metodo_enum, uso_strutt)
        
        peso_totale += peso
        peso_riciclato_totale += calc["peso_riciclato_kg"]
        soglia_max = max(soglia_max, calc["soglia_minima"])
        
        righe.append({
            "descrizione": mat.get("descrizione", "Materiale"),
            "peso_kg": peso,
            "percentuale_riciclato": perc_ric,
            "peso_riciclato_kg": calc["peso_riciclato_kg"],
            "metodo_produttivo": metodo,
            "certificazione": mat.get("certificazione", "nessuna"),
            "conforme_cam": calc["conforme"],
            "soglia_minima": calc["soglia_minima"],
        })
    
    perc_totale = (peso_riciclato_totale / peso_totale * 100) if peso_totale > 0 else 0
    conforme = perc_totale >= soglia_max
    
    return {
        "peso_totale_kg": round(peso_totale, 2),
        "peso_riciclato_kg": round(peso_riciclato_totale, 2),
        "percentuale_riciclato_totale": round(perc_totale, 1),
        "soglia_minima_richiesta": soglia_max,
        "conforme_cam": conforme,
        "righe": righe,
    }
