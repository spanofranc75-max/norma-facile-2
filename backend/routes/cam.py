"""
CAM (Criteri Ambientali Minimi) Routes
Gestione conformità ambientale per carpenteria metallica.
DM 23 giugno 2022 n. 256
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
from io import BytesIO
import uuid
import logging

from core.security import get_current_user
from core.database import db
from models.cam import (
    DatiCAMMateriale, MetodoProduttivo, TipoCertificazioneCAM,
    calcola_cam_commessa, calcola_conformita_cam, SOGLIE_CAM_ACCIAIO
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cam", tags=["CAM - Criteri Ambientali Minimi"])


# ══════════════════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════════════════

class LottoMaterialeCAM(BaseModel):
    """Lotto materiale con dati CAM."""
    descrizione: str
    fornitore: Optional[str] = None
    numero_colata: Optional[str] = None
    peso_kg: float = 0
    qualita_acciaio: Optional[str] = None  # Es: S275JR, S355J2
    # Dati CAM
    percentuale_riciclato: float = 0
    metodo_produttivo: str = "forno_elettrico_non_legato"
    tipo_certificazione: str = "nessuna"
    numero_certificazione: Optional[str] = None
    ente_certificatore: Optional[str] = None
    data_certificazione: Optional[str] = None
    km_approvvigionamento: Optional[float] = None
    uso_strutturale: bool = True
    # Riferimenti
    ddt_riferimento: Optional[str] = None
    commessa_id: Optional[str] = None
    note: Optional[str] = None


class MaterialeCommessaCAM(BaseModel):
    """Materiale associato a una commessa per calcolo CAM."""
    lotto_id: str
    peso_utilizzato_kg: float
    note: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  LOTTI MATERIALI CAM
# ══════════════════════════════════════════════════════════════════

@router.get("/soglie")
async def get_soglie_cam():
    """Restituisce le soglie CAM per tipo di acciaio (DM 23/06/2022)."""
    return {
        "normativa": "DM 23 giugno 2022 n. 256",
        "in_vigore_dal": "2022-12-04",
        "soglie": {
            "strutturale": {
                "forno_elettrico_non_legato": 75,
                "forno_elettrico_legato": 60,
                "ciclo_integrale": 12,
            },
            "non_strutturale": {
                "forno_elettrico_non_legato": 65,
                "forno_elettrico_legato": 60,
                "ciclo_integrale": 12,
            },
        },
        "certificazioni_ammesse": [
            {"codice": "epd", "nome": "EPD - Environmental Product Declaration", "norma": "ISO 14025, EN 15804"},
            {"codice": "remade_in_italy", "nome": "ReMade in Italy", "ente": "ACCREDIA"},
            {"codice": "dichiarazione_produttore", "nome": "Dichiarazione del Produttore"},
            {"codice": "altra_accreditata", "nome": "Altra certificazione accreditata"},
        ],
        "note": "Per appalti pubblici dal 2026, obbligatorio al 100% nei bandi gara."
    }


@router.post("/lotti")
async def create_lotto_cam(data: LottoMaterialeCAM, user: dict = Depends(get_current_user)):
    """Crea un nuovo lotto materiale con dati CAM."""
    lotto_id = f"lot_{uuid.uuid4().hex[:10]}"
    
    # Calcola conformità
    try:
        metodo = MetodoProduttivo(data.metodo_produttivo)
    except ValueError:
        metodo = MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO
    
    conformita = calcola_conformita_cam(
        data.peso_kg, 
        data.percentuale_riciclato,
        metodo,
        data.uso_strutturale
    )
    
    doc = {
        "lotto_id": lotto_id,
        "user_id": user["user_id"],
        "descrizione": data.descrizione,
        "fornitore": data.fornitore,
        "numero_colata": data.numero_colata,
        "peso_kg": data.peso_kg,
        "qualita_acciaio": data.qualita_acciaio,
        # CAM
        "percentuale_riciclato": data.percentuale_riciclato,
        "metodo_produttivo": data.metodo_produttivo,
        "tipo_certificazione": data.tipo_certificazione,
        "numero_certificazione": data.numero_certificazione,
        "ente_certificatore": data.ente_certificatore,
        "data_certificazione": data.data_certificazione,
        "km_approvvigionamento": data.km_approvvigionamento,
        "uso_strutturale": data.uso_strutturale,
        # Conformità calcolata
        "conforme_cam": conformita["conforme"],
        "soglia_minima_cam": conformita["soglia_minima"],
        "peso_riciclato_kg": conformita["peso_riciclato_kg"],
        # Riferimenti
        "ddt_riferimento": data.ddt_riferimento,
        "commessa_id": data.commessa_id,
        "note": data.note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.lotti_cam.insert_one(doc)
    doc.pop("_id", None)
    
    return {"message": "Lotto CAM creato", "lotto": doc}


@router.get("/lotti")
async def list_lotti_cam(
    commessa_id: Optional[str] = None,
    fornitore: Optional[str] = None,
    solo_conformi: bool = False,
    user: dict = Depends(get_current_user)
):
    """Lista lotti materiali CAM."""
    query = {"user_id": user["user_id"]}
    if commessa_id:
        query["commessa_id"] = commessa_id
    if fornitore:
        query["fornitore"] = {"$regex": fornitore, "$options": "i"}
    if solo_conformi:
        query["conforme_cam"] = True
    
    cursor = db.lotti_cam.find(query, {"_id": 0}).sort("created_at", -1)
    lotti = await cursor.to_list(500)
    
    return {"lotti": lotti, "total": len(lotti)}


@router.get("/lotti/{lotto_id}")
async def get_lotto_cam(lotto_id: str, user: dict = Depends(get_current_user)):
    """Dettaglio singolo lotto CAM."""
    lotto = await db.lotti_cam.find_one(
        {"lotto_id": lotto_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not lotto:
        raise HTTPException(404, "Lotto non trovato")
    return lotto


@router.put("/lotti/{lotto_id}")
async def update_lotto_cam(lotto_id: str, data: LottoMaterialeCAM, user: dict = Depends(get_current_user)):
    """Aggiorna un lotto CAM."""
    existing = await db.lotti_cam.find_one({"lotto_id": lotto_id, "user_id": user["user_id"]})
    if not existing:
        raise HTTPException(404, "Lotto non trovato")
    
    # Ricalcola conformità
    try:
        metodo = MetodoProduttivo(data.metodo_produttivo)
    except ValueError:
        metodo = MetodoProduttivo.FORNO_ELETTRICO_NON_LEGATO
    
    conformita = calcola_conformita_cam(
        data.peso_kg, 
        data.percentuale_riciclato,
        metodo,
        data.uso_strutturale
    )
    
    update_data = {
        "descrizione": data.descrizione,
        "fornitore": data.fornitore,
        "numero_colata": data.numero_colata,
        "peso_kg": data.peso_kg,
        "qualita_acciaio": data.qualita_acciaio,
        "percentuale_riciclato": data.percentuale_riciclato,
        "metodo_produttivo": data.metodo_produttivo,
        "tipo_certificazione": data.tipo_certificazione,
        "numero_certificazione": data.numero_certificazione,
        "ente_certificatore": data.ente_certificatore,
        "data_certificazione": data.data_certificazione,
        "km_approvvigionamento": data.km_approvvigionamento,
        "uso_strutturale": data.uso_strutturale,
        "conforme_cam": conformita["conforme"],
        "soglia_minima_cam": conformita["soglia_minima"],
        "peso_riciclato_kg": conformita["peso_riciclato_kg"],
        "ddt_riferimento": data.ddt_riferimento,
        "commessa_id": data.commessa_id,
        "note": data.note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.lotti_cam.update_one({"lotto_id": lotto_id}, {"$set": update_data})
    return {"message": "Lotto aggiornato"}


# ══════════════════════════════════════════════════════════════════
#  CALCOLO CAM COMMESSA
# ══════════════════════════════════════════════════════════════════

@router.post("/calcola/{commessa_id}")
async def calcola_cam_per_commessa(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Calcola la conformità CAM totale per una commessa.
    Usa i lotti materiali associati alla commessa.
    """
    # Verifica esistenza commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "numero": 1, "cliente": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")
    
    # Recupera lotti associati
    cursor = db.lotti_cam.find(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    lotti = await cursor.to_list(100)
    
    if not lotti:
        # Prova anche i material_batches
        cursor_batches = db.material_batches.find(
            {"commessa_id": commessa_id, "user_id": user["user_id"]},
            {"_id": 0}
        )
        batches = await cursor_batches.to_list(100)
        
        # Converti batches in formato lotti
        for b in batches:
            lotti.append({
                "descrizione": b.get("tipo_materiale") or b.get("material_type", "Acciaio"),
                "peso_kg": b.get("peso_kg", 0),
                "percentuale_riciclato": b.get("percentuale_riciclato", 75),  # Default forno elettrico
                "metodo_produttivo": b.get("metodo_produttivo", "forno_elettrico_non_legato"),
                "uso_strutturale": True,
                "certificazione": b.get("tipo_certificazione", "dichiarazione_produttore"),
            })
    
    # Calcola
    risultato = calcola_cam_commessa([
        {
            "descrizione": l.get("descrizione", "Materiale"),
            "peso_kg": l.get("peso_kg", 0),
            "percentuale_riciclato": l.get("percentuale_riciclato", 0),
            "metodo_produttivo": l.get("metodo_produttivo", "forno_elettrico_non_legato"),
            "uso_strutturale": l.get("uso_strutturale", True),
            "certificazione": l.get("tipo_certificazione") or l.get("certificazione", "nessuna"),
        }
        for l in lotti
    ])
    
    risultato["commessa_id"] = commessa_id
    risultato["commessa_numero"] = commessa.get("numero", "")
    risultato["data_calcolo"] = datetime.now(timezone.utc).isoformat()
    
    # Salva il calcolo
    await db.calcoli_cam.update_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"$set": {**risultato, "user_id": user["user_id"]}},
        upsert=True
    )
    
    return risultato


@router.get("/calcolo/{commessa_id}")
async def get_calcolo_cam(commessa_id: str, user: dict = Depends(get_current_user)):
    """Recupera l'ultimo calcolo CAM per una commessa."""
    calcolo = await db.calcoli_cam.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not calcolo:
        # Calcola al volo
        return await calcola_cam_per_commessa(commessa_id, user)
    return calcolo


# ══════════════════════════════════════════════════════════════════
#  IMPORT DA CERTIFICATO AI
# ══════════════════════════════════════════════════════════════════

@router.post("/import-da-certificato/{doc_id}")
async def import_cam_da_certificato(
    doc_id: str,
    commessa_id: str,
    peso_kg: float = 0,
    user: dict = Depends(get_current_user)
):
    """
    Importa dati CAM da un certificato già analizzato con AI.
    Crea automaticamente un lotto CAM con i dati estratti.
    """
    # Trova il documento
    doc = await db.commessa_documents.find_one(
        {"doc_id": doc_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    
    metadata = doc.get("metadata_estratti", {})
    if not metadata:
        raise HTTPException(400, "Documento non ancora analizzato. Usa prima 'Analizza AI'.")
    
    # Crea lotto CAM dai dati estratti
    lotto_data = LottoMaterialeCAM(
        descrizione=metadata.get("dimensioni") or metadata.get("qualita_acciaio") or "Acciaio strutturale",
        fornitore=metadata.get("fornitore", ""),
        numero_colata=metadata.get("numero_colata", ""),
        peso_kg=peso_kg,
        qualita_acciaio=metadata.get("qualita_acciaio", ""),
        # CAM - Default per forno elettrico (più comune)
        percentuale_riciclato=metadata.get("percentuale_riciclato", 75),  # Default ottimistico
        metodo_produttivo="forno_elettrico_non_legato",
        tipo_certificazione="dichiarazione_produttore",
        numero_certificazione=metadata.get("n_certificato", ""),
        data_certificazione=metadata.get("data_certificato", ""),
        ddt_riferimento=doc.get("nome_file", ""),
        commessa_id=commessa_id,
        note=f"Importato da certificato AI - Doc ID: {doc_id}",
    )
    
    return await create_lotto_cam(lotto_data, user)
