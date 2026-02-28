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
    calcola_cam_commessa, calcola_conformita_cam, SOGLIE_CAM_ACCIAIO,
    calcola_co2_risparmiata,
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
            "descrizione": mat.get("descrizione", "Materiale"),
            "peso_kg": mat.get("peso_kg", 0),
            "percentuale_riciclato": mat.get("percentuale_riciclato", 0),
            "metodo_produttivo": mat.get("metodo_produttivo", "forno_elettrico_non_legato"),
            "uso_strutturale": mat.get("uso_strutturale", True),
            "certificazione": mat.get("tipo_certificazione") or mat.get("certificazione", "nessuna"),
        }
        for mat in lotti
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
        # CAM - Use AI-extracted data if available
        percentuale_riciclato=metadata.get("percentuale_riciclato") if metadata.get("percentuale_riciclato") is not None else 75,
        metodo_produttivo=metadata.get("metodo_produttivo") or "forno_elettrico_non_legato",
        tipo_certificazione=_map_cert_type(metadata.get("certificazione_ambientale")),
        numero_certificazione=metadata.get("n_certificato", ""),
        ente_certificatore=metadata.get("ente_certificatore_ambientale"),
        data_certificazione=metadata.get("data_certificato", ""),
        ddt_riferimento=doc.get("nome_file", ""),
        commessa_id=commessa_id,
        note=f"Importato da certificato AI - Doc ID: {doc_id}",
    )
    
    return await create_lotto_cam(lotto_data, user)


def _map_cert_type(cert_str: str | None) -> str:
    """Map AI-extracted certification type to enum value."""
    if not cert_str:
        return "dichiarazione_produttore"
    lower = cert_str.lower()
    if "epd" in lower:
        return "epd"
    if "remade" in lower:
        return "remade_in_italy"
    if "dichiarazione" in lower or "produttore" in lower:
        return "dichiarazione_produttore"
    return "altra_accreditata"


# ══════════════════════════════════════════════════════════════════
#  GENERAZIONE PDF DICHIARAZIONE CAM
# ══════════════════════════════════════════════════════════════════

@router.get("/dichiarazione-pdf/{commessa_id}")
async def genera_dichiarazione_cam_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Genera la Dichiarazione di Conformità CAM come PDF.
    Calcola al volo i dati e produce il documento ufficiale.
    """
    # 1. Get commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")
    
    # 2. Calculate CAM
    calcolo_result = await calcola_cam_per_commessa(commessa_id, user)
    
    if not calcolo_result.get("righe"):
        raise HTTPException(400, "Nessun materiale CAM trovato per questa commessa. Aggiungi i lotti materiale prima di generare la dichiarazione.")
    
    # 3. Get company settings
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"]}, {"_id": 0}
    ) or {}
    
    # 4. Get client if linked
    cliente = None
    client_name = commessa.get("client_name", "")
    if client_name:
        cliente = await db.clients.find_one(
            {"business_name": client_name, "user_id": user["user_id"]}, {"_id": 0}
        )
    
    # 5. Generate PDF
    from services.pdf_cam_declaration import generate_cam_declaration_pdf
    try:
        pdf_bytes = generate_cam_declaration_pdf(calcolo_result, commessa, company, cliente)
    except Exception as e:
        logger.error(f"CAM PDF generation error: {e}")
        raise HTTPException(500, f"Errore generazione PDF: {str(e)}")
    
    numero = commessa.get("numero", commessa_id)
    filename = f"Dichiarazione_CAM_{numero}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )



# ══════════════════════════════════════════════════════════════════
#  REPORT AZIENDALE CAM MULTI-COMMESSA
# ══════════════════════════════════════════════════════════════════

@router.get("/report-aziendale")
async def report_aziendale_cam(
    anno: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """
    Report riepilogativo CAM multi-commessa con calcolo CO2.
    Aggrega tutti i lotti CAM dell'utente per anno.
    """
    query = {"user_id": user["user_id"]}
    if anno:
        query["created_at"] = {
            "$gte": f"{anno}-01-01",
            "$lte": f"{anno}-12-31T23:59:59",
        }
    
    # Get all CAM lots
    cursor = db.lotti_cam.find(query, {"_id": 0}).sort("created_at", -1)
    all_lotti = await cursor.to_list(2000)
    
    if not all_lotti:
        return {
            "anno": anno or datetime.now().year,
            "totale_lotti": 0,
            "peso_totale_kg": 0,
            "peso_riciclato_kg": 0,
            "percentuale_riciclato_media": 0,
            "co2": calcola_co2_risparmiata(0, 0),
            "commesse": [],
            "fornitori": [],
            "metodi_produttivi": {},
            "commesse_conformi": 0,
            "commesse_totali": 0,
        }
    
    # Aggregate by commessa
    commesse_map = {}
    fornitori_map = {}
    metodi_map = {}
    
    peso_totale = 0
    peso_riciclato = 0
    
    for lotto in all_lotti:
        peso = lotto.get("peso_kg", 0)
        perc_ric = lotto.get("percentuale_riciclato", 0)
        peso_ric = peso * perc_ric / 100
        peso_totale += peso
        peso_riciclato += peso_ric
        
        # By commessa
        cid = lotto.get("commessa_id", "senza_commessa")
        if cid not in commesse_map:
            commesse_map[cid] = {"commessa_id": cid, "peso_kg": 0, "peso_riciclato_kg": 0, "lotti": 0, "conforme": True}
        commesse_map[cid]["peso_kg"] += peso
        commesse_map[cid]["peso_riciclato_kg"] += peso_ric
        commesse_map[cid]["lotti"] += 1
        if not lotto.get("conforme_cam", False):
            commesse_map[cid]["conforme"] = False
        
        # By fornitore
        forn = lotto.get("fornitore", "Sconosciuto") or "Sconosciuto"
        if forn not in fornitori_map:
            fornitori_map[forn] = {"fornitore": forn, "peso_kg": 0, "peso_riciclato_kg": 0, "lotti": 0}
        fornitori_map[forn]["peso_kg"] += peso
        fornitori_map[forn]["peso_riciclato_kg"] += peso_ric
        fornitori_map[forn]["lotti"] += 1
        
        # By metodo
        metodo = lotto.get("metodo_produttivo", "sconosciuto")
        if metodo not in metodi_map:
            metodi_map[metodo] = {"peso_kg": 0, "lotti": 0}
        metodi_map[metodo]["peso_kg"] += peso
        metodi_map[metodo]["lotti"] += 1
    
    # Enrich commesse with names
    commesse_ids = [c for c in commesse_map.keys() if c != "senza_commessa"]
    if commesse_ids:
        comm_cursor = db.commesse.find(
            {"commessa_id": {"$in": commesse_ids}, "user_id": user["user_id"]},
            {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "client_name": 1}
        )
        comm_docs = await comm_cursor.to_list(500)
        comm_names = {c["commessa_id"]: c for c in comm_docs}
        
        for cid, data in commesse_map.items():
            info = comm_names.get(cid, {})
            data["numero"] = info.get("numero", "")
            data["titolo"] = info.get("title", "")
            data["cliente"] = info.get("client_name", "")
            data["percentuale_riciclato"] = round(data["peso_riciclato_kg"] / data["peso_kg"] * 100, 1) if data["peso_kg"] > 0 else 0
    
    # Enrich fornitori
    for fdata in fornitori_map.values():
        fdata["percentuale_riciclato"] = round(fdata["peso_riciclato_kg"] / fdata["peso_kg"] * 100, 1) if fdata["peso_kg"] > 0 else 0
    
    perc_media = round(peso_riciclato / peso_totale * 100, 1) if peso_totale > 0 else 0
    co2 = calcola_co2_risparmiata(peso_totale, peso_riciclato)
    
    commesse_list = sorted(commesse_map.values(), key=lambda x: x["peso_kg"], reverse=True)
    fornitori_list = sorted(fornitori_map.values(), key=lambda x: x["peso_kg"], reverse=True)
    
    return {
        "anno": anno or datetime.now().year,
        "totale_lotti": len(all_lotti),
        "peso_totale_kg": round(peso_totale, 2),
        "peso_riciclato_kg": round(peso_riciclato, 2),
        "percentuale_riciclato_media": perc_media,
        "co2": co2,
        "commesse": commesse_list,
        "fornitori": fornitori_list,
        "metodi_produttivi": metodi_map,
        "commesse_conformi": sum(1 for c in commesse_list if c.get("conforme")),
        "commesse_totali": len(commesse_list),
        "data_report": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/report-aziendale/pdf")
async def report_aziendale_cam_pdf(
    anno: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """Genera il PDF del Bilancio di Sostenibilità Ambientale."""
    # Get report data
    report = await report_aziendale_cam(anno, user)
    
    if report["totale_lotti"] == 0:
        raise HTTPException(400, "Nessun dato CAM disponibile per il periodo selezionato.")
    
    # Get company settings
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"]}, {"_id": 0}
    ) or {}
    
    from services.pdf_cam_report import generate_cam_report_pdf
    try:
        pdf_bytes = generate_cam_report_pdf(report, company)
    except Exception as e:
        logger.error(f"CAM Report PDF error: {e}")
        raise HTTPException(500, f"Errore generazione PDF: {str(e)}")
    
    anno_label = anno or datetime.now().year
    filename = f"Bilancio_Sostenibilita_CAM_{anno_label}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )
