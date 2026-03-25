"""
CAM (Criteri Ambientali Minimi) Routes
Gestione conformità ambientale per carpenteria metallica.
DM 23 giugno 2022 n. 256
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from io import BytesIO
import uuid
import logging

from core.security import get_current_user
from core.database import db
from models.cam import (
    MetodoProduttivo, calcola_cam_commessa, calcola_conformita_cam, calcola_co2_risparmiata,
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
        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
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
    query = {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
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
        {"lotto_id": lotto_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not lotto:
        raise HTTPException(404, "Lotto non trovato")
    return lotto


@router.put("/lotti/{lotto_id}")
async def update_lotto_cam(lotto_id: str, data: LottoMaterialeCAM, user: dict = Depends(get_current_user)):
    """Aggiorna un lotto CAM."""
    existing = await db.lotti_cam.find_one({"lotto_id": lotto_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]})
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


@router.delete("/lotti/{lotto_id}")
async def delete_lotto_cam(lotto_id: str, user: dict = Depends(get_current_user)):
    """Elimina un singolo lotto CAM."""
    result = await db.lotti_cam.delete_one({"lotto_id": lotto_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    logger.info(f"CAM lotto {lotto_id} deleted")
    return {"message": "Lotto CAM eliminato"}


@router.delete("/lotti/commessa/{commessa_id}")
async def delete_all_lotti_cam(commessa_id: str, user: dict = Depends(get_current_user)):
    """Elimina tutti i lotti CAM di una commessa."""
    result = await db.lotti_cam.delete_many({"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]})
    logger.info(f"Deleted {result.deleted_count} CAM lotti for commessa {commessa_id}")
    return {"message": f"{result.deleted_count} lotti CAM eliminati", "deleted_count": result.deleted_count}


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
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0, "numero": 1, "cliente": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")
    
    # Recupera lotti associati
    cursor = db.lotti_cam.find(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    lotti = await cursor.to_list(100)
    
    if not lotti:
        # Prova anche i material_batches
        cursor_batches = db.material_batches.find(
            {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
            {"_id": 0}
        )
        batches = await cursor_batches.to_list(100)
        
        # Converti batches in formato lotti, using new CAM fields if present
        for b in batches:
            perc_ric = b.get("percentuale_riciclato")
            if perc_ric is None:
                perc_ric = 75  # Default forno elettrico
            metodo = b.get("metodo_produttivo") or "forno_elettrico_non_legato"
            lotti.append({
                "descrizione": b.get("dimensions") or b.get("material_type", "Acciaio"),
                "peso_kg": b.get("peso_kg", 0),
                "percentuale_riciclato": perc_ric,
                "metodo_produttivo": metodo,
                "uso_strutturale": True,
                "certificazione": b.get("certificazione_epd", "dichiarazione_produttore") if b.get("certificazione_epd") else "dichiarazione_produttore",
                "distanza_trasporto_km": b.get("distanza_trasporto_km"),
                "fornitore": b.get("supplier_name", ""),
                "numero_colata": b.get("heat_number", ""),
                "ddt_numero": b.get("ddt_numero", ""),
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
            "distanza_trasporto_km": mat.get("distanza_trasporto_km") or mat.get("km_approvvigionamento"),
            "fornitore": mat.get("fornitore", ""),
            "numero_colata": mat.get("numero_colata", ""),
            "ddt_numero": mat.get("ddt_numero", ""),
        }
        for mat in lotti
    ])
    
    risultato["commessa_id"] = commessa_id
    risultato["commessa_numero"] = commessa.get("numero", "")
    risultato["data_calcolo"] = datetime.now(timezone.utc).isoformat()
    
    # Salva il calcolo
    await db.calcoli_cam.update_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"$set": {**risultato, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}},
        upsert=True
    )
    
    return risultato


@router.get("/calcolo/{commessa_id}")
async def get_calcolo_cam(commessa_id: str, user: dict = Depends(get_current_user)):
    """Recupera l'ultimo calcolo CAM per una commessa."""
    calcolo = await db.calcoli_cam.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
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
        {"doc_id": doc_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
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
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
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
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}
    ) or {}
    
    # 4. Get client if linked
    cliente = None
    client_name = commessa.get("client_name", "")
    if client_name:
        cliente = await db.clients.find_one(
            {"business_name": client_name, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}
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
    query = {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    if anno:
        query["$or"] = [
            {"created_at": {"$gte": datetime(anno, 1, 1), "$lte": datetime(anno, 12, 31, 23, 59, 59)}},
            {"created_at": {"$gte": f"{anno}-01-01", "$lte": f"{anno}-12-31T23:59:59"}},
        ]
    
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
            # Sustainability Dashboard KPIs (empty state)
            "alberi_equivalenti": 0,
            "indice_economia_circolare": 0,
            "co2_per_commessa": [],
            "trend_mensile": [],
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
            {"commessa_id": {"$in": commesse_ids}, "user_id": user["user_id"], "tenant_id": user["tenant_id"]},
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
    
    # ── Sustainability KPIs ──────────────────────────────
    # "Effetto Foresta": 1 albero assorbe ~22 kg CO2/anno (fonte: European Environment Agency)
    KG_CO2_PER_ALBERO_ANNO = 22.0
    alberi_equivalenti = round(co2["co2_risparmiata_kg"] / KG_CO2_PER_ALBERO_ANNO, 1) if co2["co2_risparmiata_kg"] > 0 else 0
    
    # Indice Economia Circolare (0-100): media ponderata % riciclato
    indice_economia_circolare = round(perc_media, 1)
    
    # CO2 per commessa (for bar chart)
    co2_per_commessa = []
    for c in commesse_list:
        c_co2 = calcola_co2_risparmiata(c["peso_kg"], c["peso_riciclato_kg"])
        co2_per_commessa.append({
            "commessa_id": c.get("commessa_id", ""),
            "numero": c.get("numero", "N/A"),
            "titolo": c.get("titolo", ""),
            "co2_risparmiata_kg": c_co2["co2_risparmiata_kg"],
            "peso_kg": round(c["peso_kg"], 1),
        })
    
    # Trend mensile: aggregazione per mese di creazione lotto
    trend_mensile = {}
    for lotto in all_lotti:
        created = lotto.get("created_at", "")
        if isinstance(created, datetime):
            mese = created.strftime("%Y-%m")
        elif isinstance(created, str) and len(created) >= 7:
            mese = created[:7]  # "YYYY-MM"
        else:
            continue
        if mese not in trend_mensile:
            trend_mensile[mese] = {"mese": mese, "peso_kg": 0, "peso_riciclato_kg": 0, "co2_risparmiata_kg": 0}
        peso_l = lotto.get("peso_kg", 0)
        perc_l = lotto.get("percentuale_riciclato", 0)
        peso_ric_l = peso_l * perc_l / 100
        trend_mensile[mese]["peso_kg"] += peso_l
        trend_mensile[mese]["peso_riciclato_kg"] += peso_ric_l
        co2_l = calcola_co2_risparmiata(peso_l, peso_ric_l)
        trend_mensile[mese]["co2_risparmiata_kg"] += co2_l["co2_risparmiata_kg"]
    
    trend_list = sorted(trend_mensile.values(), key=lambda x: x["mese"])
    for t in trend_list:
        t["peso_kg"] = round(t["peso_kg"], 1)
        t["peso_riciclato_kg"] = round(t["peso_riciclato_kg"], 1)
        t["co2_risparmiata_kg"] = round(t["co2_risparmiata_kg"], 1)
    
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
        # Sustainability Dashboard KPIs
        "alberi_equivalenti": alberi_equivalenti,
        "indice_economia_circolare": indice_economia_circolare,
        "co2_per_commessa": co2_per_commessa,
        "trend_mensile": trend_list,
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
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}
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


@router.get("/green-certificate/{commessa_id}")
async def green_certificate_pdf(
    commessa_id: str,
    user: dict = Depends(get_current_user)
):
    """Generate a branded Green Certificate PDF for a specific commessa."""
    uid = user["user_id"]
    tid = user["tenant_id"]

    # Get commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Get CAM lotti for this commessa
    cursor = db.lotti_cam.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0}
    )
    lotti = await cursor.to_list(500)
    if not lotti:
        raise HTTPException(400, "Nessun lotto CAM per questa commessa. Aggiungi materiali dalla sezione CAM.")

    # Calculate CO2
    peso_totale = sum(lot.get("peso_kg", 0) for lot in lotti)
    peso_riciclato = sum(lot.get("peso_kg", 0) * lot.get("percentuale_riciclato", 0) / 100 for lot in lotti)
    co2_data = calcola_co2_risparmiata(peso_totale, peso_riciclato)

    # Get company settings
    company = await db.company_settings.find_one({"user_id": uid, "tenant_id": tid}, {"_id": 0}) or {}

    from services.pdf_green_certificate import generate_green_certificate
    try:
        pdf_buf = generate_green_certificate(company, commessa, lotti, co2_data)
    except Exception as e:
        logger.error(f"Green Certificate PDF error: {e}")
        raise HTTPException(500, f"Errore generazione certificato: {str(e)}")

    numero = commessa.get("numero", commessa_id)
    filename = f"Green_Certificate_{numero}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@router.get("/archivio-certificati")
async def get_archivio_certificati(user: dict = Depends(get_current_user)):
    """Get all unassigned certificate profiles from the archive."""
    cursor = db.archivio_certificati.find(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}
    ).sort("updated_at", -1)
    items = await cursor.to_list(200)
    return {"archivio": items, "totale": len(items)}


@router.post("/archivio-certificati/{numero_colata}/assegna")
async def assegna_archivio_a_commessa(
    numero_colata: str, commessa_id: str, user: dict = Depends(get_current_user)
):
    """Assign an archived certificate profile to a commessa."""
    item = await db.archivio_certificati.find_one(
        {"numero_colata": numero_colata, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}
    )
    if not item:
        raise HTTPException(404, "Profilo non trovato in archivio")

    metodo = item.get("metodo_produttivo") or "forno_elettrico_non_legato"
    perc_ric = float(item.get("percentuale_riciclato") or 75)
    soglie = {"forno_elettrico_non_legato": 75, "forno_elettrico_legato": 60, "ciclo_integrale": 12}
    soglia = soglie.get(metodo, 75)

    cam_id = f"cam_{uuid.uuid4().hex[:10]}"
    await db.lotti_cam.insert_one({
        "lotto_id": cam_id, "user_id": user["user_id"], "tenant_id": user["tenant_id"],
        "commessa_id": commessa_id,
        "descrizione": item.get("dimensioni") or item.get("qualita_acciaio", "Materiale"),
        "fornitore": item.get("fornitore", ""),
        "numero_colata": numero_colata,
        "peso_kg": float(item.get("peso_kg") or 0),
        "qualita_acciaio": item.get("qualita_acciaio", ""),
        "percentuale_riciclato": perc_ric,
        "metodo_produttivo": metodo,
        "tipo_certificazione": "dichiarazione_produttore",
        "numero_certificazione": item.get("n_certificato", ""),
        "uso_strutturale": True,
        "soglia_minima_cam": soglia,
        "conforme_cam": perc_ric >= soglia,
        "source_doc_id": item.get("source_doc_id", ""),
        "note": "Assegnato da archivio",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await db.archivio_certificati.delete_one(
        {"numero_colata": numero_colata, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    )

    return {"message": f"Profilo {numero_colata} assegnato a commessa {commessa_id}", "cam_lotto_id": cam_id}


# ══════════════════════════════════════════════════════════════════
#  CAM ALERT — Pre-generation compliance check
# ══════════════════════════════════════════════════════════════════

@router.get("/alert/{commessa_id}")
async def cam_alert(commessa_id: str, user: dict = Depends(get_current_user)):
    """Check CAM compliance status for a commessa BEFORE PDF generation.
    Returns alert level and actionable suggestions."""
    uid = user["user_id"]
    tid = user["tenant_id"]

    # Collect material from batches + lotti_cam
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "certificate_base64": 0}
    ).to_list(200)

    cam_materiali = []
    for b in batches:
        perc = b.get("percentuale_riciclato")
        if perc is not None:
            cam_materiali.append({
                "descrizione": b.get("dimensions") or b.get("material_type", "Acciaio"),
                "peso_kg": b.get("peso_kg", 0),
                "percentuale_riciclato": perc,
                "metodo_produttivo": b.get("metodo_produttivo", "forno_elettrico_non_legato"),
                "uso_strutturale": True,
                "certificazione": "dichiarazione_produttore",
                "fornitore": b.get("supplier_name", ""),
                "numero_colata": b.get("heat_number", ""),
            })

    # Also include lotti_cam
    lotti = await db.lotti_cam.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0}
    ).to_list(100)
    for lc in lotti:
        already = any(cm.get("numero_colata") == lc.get("numero_colata") and cm.get("numero_colata") for cm in cam_materiali)
        if not already:
            cam_materiali.append({
                "descrizione": lc.get("descrizione", "Materiale"),
                "peso_kg": lc.get("peso_kg", 0),
                "percentuale_riciclato": lc.get("percentuale_riciclato", 0),
                "metodo_produttivo": lc.get("metodo_produttivo", "forno_elettrico_non_legato"),
                "uso_strutturale": True,
                "certificazione": lc.get("tipo_certificazione", "dichiarazione_produttore"),
            })

    if not cam_materiali:
        n_batches_no_cam = len([b for b in batches if b.get("percentuale_riciclato") is None])
        return {
            "level": "warning" if batches else "info",
            "conforme": None,
            "message": f"Nessun dato CAM registrato. {n_batches_no_cam} lotti senza % riciclato." if batches else "Nessun lotto materiale registrato.",
            "percentuale_riciclato": None,
            "soglia_minima": None,
            "suggerimenti": [
                "Compilare il campo '% Riciclato' nei lotti materiale",
                "Richiedere dichiarazione contenuto riciclato ai fornitori",
            ],
        }

    calc = calcola_cam_commessa(cam_materiali)
    conforme = calc.get("conforme_cam", False)
    perc_tot = calc.get("percentuale_riciclato_totale", 0)
    soglia = calc.get("soglia_minima_richiesta", 75)
    delta = round(perc_tot - soglia, 2)

    # Find problematic materials (below threshold)
    non_conformi = [r for r in calc.get("righe", []) if not r.get("conforme_cam")]
    n_no_cam = len([b for b in batches if b.get("percentuale_riciclato") is None])

    suggerimenti = []
    if not conforme:
        if non_conformi:
            worst = max(non_conformi, key=lambda r: r.get("peso_kg", 0))
            suggerimenti.append(
                f"Il lotto critico e '{worst.get('descrizione')}' ({worst.get('fornitore', '')}) "
                f"con {worst.get('percentuale_riciclato', 0):.1f}% riciclato "
                f"(soglia: {worst.get('soglia_minima', 75)}%)"
            )
        suggerimenti.append("Valutare fornitori alternativi con acciaio da forno elettrico (EAF)")
        if delta > -5:
            suggerimenti.append(f"Mancano solo {abs(delta):.1f}% — un lotto aggiuntivo EAF potrebbe risolvere")
    if n_no_cam > 0:
        suggerimenti.append(f"{n_no_cam} lotti senza dati CAM: compilare per migliorare la precisione")

    return {
        "level": "success" if conforme else "danger",
        "conforme": conforme,
        "message": f"CAM {'CONFORME' if conforme else 'NON CONFORME'}: {perc_tot:.1f}% riciclato (soglia {soglia:.0f}%)",
        "percentuale_riciclato": round(perc_tot, 2),
        "soglia_minima": soglia,
        "delta": delta,
        "n_materiali": len(cam_materiali),
        "n_non_conformi": len(non_conformi),
        "n_senza_dati_cam": n_no_cam,
        "suggerimenti": suggerimenti,
    }



@router.get("/report-mensile/pdf")
async def report_cam_mensile_pdf(user: dict = Depends(get_current_user)):
    """Report CAM Mensile — PDF con trend % riciclato, breakdown commesse, proiezione trimestrale."""
    import html as html_mod
    from weasyprint import HTML as WP_HTML
    from datetime import datetime, timezone

    _e = html_mod.escape
    uid = user["user_id"]
    tid = user["tenant_id"]
    now = datetime.now(timezone.utc)

    # Get company info
    company = await db.company_settings.find_one({"user_id": uid, "tenant_id": tid}, {"_id": 0}) or {}
    biz = _e(company.get("business_name", ""))
    logo = company.get("logo_url", "")

    # Get all commesse with material batches
    commesse = await db.commesse.find(
        {"user_id": uid, "tenant_id": tid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "stato": 1, "created_at": 1}
    ).to_list(500)

    batches = await db.material_batches.find(
        {"user_id": uid, "tenant_id": tid, "percentuale_riciclato": {"$ne": None}},
        {"_id": 0, "commessa_id": 1, "peso_kg": 1, "percentuale_riciclato": 1,
         "metodo_produttivo": 1, "created_at": 1}
    ).to_list(2000)

    # Per-commessa breakdown
    cam_data = {}
    for b in batches:
        cid = b["commessa_id"]
        if cid not in cam_data:
            cam_data[cid] = {"peso": 0, "peso_ric": 0, "batches": 0}
        peso = b.get("peso_kg", 0) or 0
        perc = b.get("percentuale_riciclato", 0) or 0
        cam_data[cid]["peso"] += peso
        cam_data[cid]["peso_ric"] += peso * perc / 100
        cam_data[cid]["batches"] += 1

    # Build per-commessa table
    rows_html = ""
    total_peso = 0
    total_peso_ric = 0
    soglia = 75
    n_conformi = 0
    n_non_conformi = 0

    for c in commesse:
        cid = c["commessa_id"]
        if cid not in cam_data:
            continue
        d = cam_data[cid]
        perc = round(d["peso_ric"] / d["peso"] * 100, 1) if d["peso"] > 0 else 0
        conf = perc >= soglia
        total_peso += d["peso"]
        total_peso_ric += d["peso_ric"]
        if conf:
            n_conformi += 1
        else:
            n_non_conformi += 1

        color = "#16A34A" if conf else "#DC2626"
        badge = "CONFORME" if conf else "NON CONFORME"
        rows_html += f"""<tr>
            <td>{_e(c.get('numero', cid))}</td>
            <td>{_e(c.get('title', '')[:40])}</td>
            <td style="text-align:right;">{d['peso']:,.1f}</td>
            <td style="text-align:right;">{d['peso_ric']:,.1f}</td>
            <td style="text-align:center;font-weight:700;color:{color};">{perc:.1f}%</td>
            <td style="text-align:center;"><span style="background:{'#dcfce7' if conf else '#fee2e2'};color:{color};padding:2px 8px;border-radius:4px;font-size:7pt;font-weight:700;">{badge}</span></td>
        </tr>"""

    perc_globale = round(total_peso_ric / total_peso * 100, 1) if total_peso > 0 else 0

    # Monthly trend (last 6 months)
    trend_data = {}
    for b in batches:
        ca = b.get("created_at")
        if ca and hasattr(ca, "strftime"):
            key = ca.strftime("%Y-%m")
        elif ca and isinstance(ca, str):
            key = ca[:7]
        else:
            continue
        if key not in trend_data:
            trend_data[key] = {"peso": 0, "peso_ric": 0}
        peso = b.get("peso_kg", 0) or 0
        perc = b.get("percentuale_riciclato", 0) or 0
        trend_data[key]["peso"] += peso
        trend_data[key]["peso_ric"] += peso * perc / 100

    sorted_months = sorted(trend_data.keys())[-6:]
    trend_rows = ""
    trend_percs = []
    for m in sorted_months:
        d = trend_data[m]
        p = round(d["peso_ric"] / d["peso"] * 100, 1) if d["peso"] > 0 else 0
        trend_percs.append(p)
        bar_w = min(max(p, 5), 100)
        bar_color = "#16A34A" if p >= soglia else "#DC2626"
        trend_rows += f"""<tr>
            <td style="width:80px;">{m}</td>
            <td style="width:60px;text-align:right;font-weight:700;color:{'#16A34A' if p >= soglia else '#DC2626'};">{p:.1f}%</td>
            <td><div style="background:#f1f5f9;border-radius:4px;height:16px;position:relative;">
                <div style="background:{bar_color};border-radius:4px;height:16px;width:{bar_w}%;"></div>
                <div style="position:absolute;left:{soglia}%;top:0;bottom:0;border-left:2px dashed #94A3B8;"></div>
            </div></td>
        </tr>"""

    # Quarterly projection
    if len(trend_percs) >= 2:
        avg_delta = sum(trend_percs[i] - trend_percs[i - 1] for i in range(1, len(trend_percs))) / (len(trend_percs) - 1)
        proj_3m = round(perc_globale + avg_delta * 3, 1)
        proj_text = f"Proiezione trimestrale: <strong>{proj_3m:.1f}%</strong> (trend {'positivo' if avg_delta > 0 else 'negativo'}: {'+' if avg_delta > 0 else ''}{avg_delta:.1f}%/mese)"
    else:
        proj_text = "Dati insufficienti per la proiezione trimestrale (servono almeno 2 mesi)"

    # Build PDF
    pdf_html = f"""<!DOCTYPE html><html><head><style>
    @page {{
        size: A4; margin: 18mm 14mm 22mm 14mm;
        @bottom-left {{ content: "Report CAM Mensile — DM 23/06/2022"; font-size: 7pt; color: #999; font-family: Helvetica; }}
        @bottom-right {{ content: "Pag. " counter(page) " di " counter(pages); font-size: 7pt; color: #777; font-family: Helvetica; }}
    }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1E293B; }}
    h1 {{ font-size: 16pt; color: #1E293B; margin: 0 0 2mm; }}
    h2 {{ font-size: 11pt; color: #1a3a6b; margin: 8mm 0 3mm; border-bottom: 2px solid #1a3a6b; padding-bottom: 2mm; }}
    table {{ width: 100%; border-collapse: collapse; margin: 3mm 0; }}
    th {{ background: #1a3a6b; color: white; padding: 2.5mm 3mm; font-size: 7.5pt; text-align: left; font-weight: 600; text-transform: uppercase; }}
    td {{ padding: 2mm 3mm; border-bottom: 0.5px solid #E2E8F0; font-size: 8.5pt; }}
    tr:nth-child(even) {{ background: #FAFBFC; }}
    .kpi-row {{ display: table; width: 100%; margin: 4mm 0; }}
    .kpi-cell {{ display: table-cell; width: 25%; text-align: center; padding: 3mm; border: 1px solid #e2e8f0; }}
    .kpi-val {{ font-size: 18pt; font-weight: 800; }}
    .kpi-lbl {{ font-size: 7pt; color: #64748B; text-transform: uppercase; margin-top: 1mm; }}
    </style></head><body>

    <div style="background:#1a3a6b;color:white;padding:5mm 6mm;margin-bottom:6mm;">
        <table style="margin:0;"><tr>
            <td style="border:none;color:white;vertical-align:middle;width:60%;">
                {f'<img src="{logo}" style="max-height:28px;max-width:120px;margin-right:8px;vertical-align:middle;" />' if logo else ''}
                <span style="font-size:13pt;font-weight:800;">{biz}</span>
            </td>
            <td style="border:none;color:white;text-align:right;font-size:8pt;vertical-align:middle;">
                Report generato il {now.strftime('%d/%m/%Y %H:%M')}
            </td>
        </tr></table>
    </div>

    <h1>Report CAM Mensile</h1>
    <p style="font-size:9pt;color:#64748B;margin-bottom:5mm;">Criteri Ambientali Minimi — DM 23/06/2022 n. 256 — Art. 57 D.Lgs. 36/2023</p>

    <div class="kpi-row">
        <div class="kpi-cell">
            <div class="kpi-val" style="color:{'#16A34A' if perc_globale >= soglia else '#DC2626'};">{perc_globale:.1f}%</div>
            <div class="kpi-lbl">% Riciclato Globale</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-val" style="color:#1a3a6b;">{total_peso:,.0f} kg</div>
            <div class="kpi-lbl">Peso Totale Acciaio</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-val" style="color:#16A34A;">{n_conformi}</div>
            <div class="kpi-lbl">Commesse Conformi</div>
        </div>
        <div class="kpi-cell">
            <div class="kpi-val" style="color:{'#DC2626' if n_non_conformi > 0 else '#16A34A'};">{n_non_conformi}</div>
            <div class="kpi-lbl">Non Conformi</div>
        </div>
    </div>

    <h2>Dettaglio per Commessa</h2>
    <table>
        <thead><tr><th>Commessa</th><th>Oggetto</th><th>Peso (kg)</th><th>Riciclato (kg)</th><th>%</th><th>Esito</th></tr></thead>
        <tbody>{rows_html}</tbody>
        <tr style="font-weight:700;background:#e8f0f7;">
            <td colspan="2" style="text-align:right;">TOTALE</td>
            <td style="text-align:right;">{total_peso:,.1f}</td>
            <td style="text-align:right;">{total_peso_ric:,.1f}</td>
            <td style="text-align:center;font-weight:800;color:{'#16A34A' if perc_globale >= soglia else '#DC2626'};">{perc_globale:.1f}%</td>
            <td></td>
        </tr>
    </table>

    <h2>Trend Mensile (ultimi 6 mesi)</h2>
    <table>
        <thead><tr><th style="width:80px;">Mese</th><th style="width:60px;">%</th><th>Barra (linea tratteggiata = soglia {soglia}%)</th></tr></thead>
        <tbody>{trend_rows}</tbody>
    </table>

    <h2>Proiezione Trimestrale</h2>
    <div style="background:#f8f9fa;padding:4mm 5mm;border-left:4px solid #1a3a6b;margin:3mm 0;">
        <p style="margin:0;font-size:10pt;">{proj_text}</p>
    </div>

    <div style="margin-top:10mm;padding:4mm;border:1px solid #e2e8f0;border-radius:4px;font-size:8pt;color:#64748B;">
        <strong>Nota:</strong> Il presente report e generato automaticamente dal sistema 1090 Norma Facile.
        I dati sono basati sui certificati di colata (EN 10204 3.1) e le dichiarazioni dei produttori registrate nel sistema.
        Soglia di riferimento: {soglia}% per acciaio non legato da forno elettrico (DM 23/06/2022, Allegato par. 2.5.4).
    </div>
    </body></html>"""

    pdf_bytes = WP_HTML(string=pdf_html).write_pdf()
    fname = f"Report_CAM_{now.strftime('%Y_%m')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"'}
    )
