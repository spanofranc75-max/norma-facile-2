"""
Montaggio — API per Fase 4: Montaggio e Tracciabilità.

Endpoint:
- POST /montaggio/ddt/analyze        → AI Vision analisi DDT bulloneria
- POST /montaggio/ddt/save           → Salva dati DDT bulloneria (manuali o da AI)
- GET  /montaggio/ddt/{commessa_id}  → Lista DDT bulloneria per commessa
- GET  /montaggio/torque-table       → Tabella coppie di serraggio completa
- GET  /montaggio/torque             → Coppia di serraggio per diametro+classe
- POST /montaggio/diario             → Salva diario di montaggio completo
- GET  /montaggio/diario/{commessa_id} → Lista diari montaggio per commessa
- POST /montaggio/foto/{commessa_id} → Upload foto montaggio (giunti/ancoraggi)
- POST /montaggio/firma              → Salva firma digitale cliente
"""
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core.database import db

router = APIRouter(prefix="/montaggio", tags=["montaggio"])
logger = logging.getLogger(__name__)

DDT_COLL = "bulloneria_ddt"
MONTAGGIO_COLL = "diario_montaggio"
DOC_COLL = "commessa_documents"


# ── MODELS ───────────────────────────────────────────────────

class BulloneItem(BaseModel):
    diametro: str
    classe: str
    lotto: Optional[str] = ""
    quantita: Optional[str] = ""
    descrizione: Optional[str] = ""


class DDTSaveRequest(BaseModel):
    commessa_id: str
    voce_id: str = ""
    admin_id: str = ""
    fornitore: Optional[str] = ""
    numero_ddt: Optional[str] = ""
    data_ddt: Optional[str] = ""
    lotto_generale: Optional[str] = ""
    bulloni: List[BulloneItem]
    foto_ddt_doc_id: Optional[str] = ""
    source: str = "manuale"


class SerraggioItem(BaseModel):
    diametro: str
    classe: str
    coppia_nm: Optional[float] = None
    confermato: bool = False
    chiave_dinamometrica: bool = False


class DiarioMontaggioRequest(BaseModel):
    commessa_id: str
    voce_id: str = ""
    admin_id: str = ""
    operatore_id: str
    operatore_nome: str
    serraggi: List[SerraggioItem] = []
    fondazioni_ok: Optional[bool] = None
    foto_giunti_doc_ids: List[str] = []
    foto_ancoraggi_doc_ids: List[str] = []


class FirmaClienteRequest(BaseModel):
    commessa_id: str
    voce_id: str = ""
    montaggio_id: str
    firma_base64: str
    firma_nome: str


class VarianteCreate(BaseModel):
    commessa_id: str
    voce_id: str = ""
    operatore_id: str
    operatore_nome: str
    descrizione: str
    foto_doc_id: str  # mandatory photo


# ── DDT ANALYSIS (AI Vision) ────────────────────────────────

@router.post("/ddt/analyze")
async def analyze_ddt(
    file: UploadFile = File(...),
    commessa_id: str = Form(""),
    voce_id: str = Form(""),
):
    """Upload a DDT photo and analyze it with AI Vision to extract bolt data."""
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    image_b64 = base64.b64encode(content).decode("utf-8")

    from services.montaggio_service import analyze_ddt_bulloneria
    result = await analyze_ddt_bulloneria(image_b64)

    if result.get("error"):
        logger.warning(f"[MONTAGGIO] DDT analysis warning: {result['error']}")

    return {
        "analysis": result,
        "commessa_id": commessa_id,
        "voce_id": voce_id,
        "image_b64_preview": image_b64[:200] + "..." if len(image_b64) > 200 else image_b64,
    }


# ── DDT SAVE ─────────────────────────────────────────────────

@router.post("/ddt/save")
async def save_ddt(data: DDTSaveRequest):
    """Save DDT bolt data (from AI analysis or manual entry) to DB."""
    now = datetime.now(timezone.utc)

    # Get admin_id from commessa if not provided
    admin_id = data.admin_id
    if not admin_id:
        commessa = await db.commesse.find_one(
            {"commessa_id": data.commessa_id}, {"_id": 0, "user_id": 1}
        )
        if commessa:
            admin_id = commessa["user_id"]

    # Enrich with torque values
    from services.montaggio_service import get_torque_nm
    bulloni_enriched = []
    for b in data.bulloni:
        bd = b.model_dump()
        torque = get_torque_nm(b.diametro, b.classe)
        bd["coppia_nm"] = torque
        bulloni_enriched.append(bd)

    ddt_id = f"bdt_{uuid.uuid4().hex[:10]}"
    doc = {
        "ddt_id": ddt_id,
        "commessa_id": data.commessa_id,
        "voce_id": data.voce_id or "",
        "admin_id": admin_id,
        "fornitore": data.fornitore or "",
        "numero_ddt": data.numero_ddt or "",
        "data_ddt": data.data_ddt or "",
        "lotto_generale": data.lotto_generale or "",
        "bulloni": bulloni_enriched,
        "foto_ddt_doc_id": data.foto_ddt_doc_id or "",
        "source": data.source,
        "analyzed_at": now.isoformat(),
        "created_at": now.isoformat(),
    }

    await db[DDT_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[MONTAGGIO] DDT saved: {ddt_id} — {len(bulloni_enriched)} bulloni — commessa {data.commessa_id}")
    return doc


# ── DDT LIST ─────────────────────────────────────────────────

@router.get("/ddt/{commessa_id}")
async def list_ddt(commessa_id: str, voce_id: str = ""):
    """List all saved DDTs for a commessa (optionally filtered by voce)."""
    query = {"commessa_id": commessa_id}
    if voce_id:
        query["voce_id"] = voce_id

    ddts = await db[DDT_COLL].find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    return {"ddts": ddts, "count": len(ddts)}


# ── TORQUE TABLE ─────────────────────────────────────────────

@router.get("/torque-table")
async def get_torque_table():
    """Return the full ISO 898-1 torque table."""
    from services.montaggio_service import get_torque_table_full, AVAILABLE_DIAMETERS, AVAILABLE_CLASSES
    return {
        "table": get_torque_table_full(),
        "diameters": AVAILABLE_DIAMETERS,
        "classes": AVAILABLE_CLASSES,
    }


@router.get("/torque")
async def get_torque(diametro: str, classe: str):
    """Get the tightening torque for a specific diameter and class."""
    from services.montaggio_service import get_torque_nm
    torque = get_torque_nm(diametro, classe)
    if torque is None:
        raise HTTPException(404, f"Coppia non trovata per {diametro} classe {classe}")
    return {"diametro": diametro, "classe": classe, "coppia_nm": torque, "unita": "Nm"}


# ── DIARIO MONTAGGIO ─────────────────────────────────────────

@router.post("/diario")
async def save_diario_montaggio(data: DiarioMontaggioRequest):
    """Save a complete assembly diary entry."""
    now = datetime.now(timezone.utc)

    # Get admin_id from commessa if not provided
    admin_id = data.admin_id
    if not admin_id:
        commessa = await db.commesse.find_one(
            {"commessa_id": data.commessa_id}, {"_id": 0, "user_id": 1}
        )
        if commessa:
            admin_id = commessa["user_id"]

    montaggio_id = f"mtg_{uuid.uuid4().hex[:10]}"
    doc = {
        "montaggio_id": montaggio_id,
        "commessa_id": data.commessa_id,
        "voce_id": data.voce_id or "",
        "admin_id": admin_id,
        "operatore_id": data.operatore_id,
        "operatore_nome": data.operatore_nome,
        "serraggi": [s.model_dump() for s in data.serraggi],
        "fondazioni_ok": data.fondazioni_ok,
        "foto_giunti_doc_ids": data.foto_giunti_doc_ids,
        "foto_ancoraggi_doc_ids": data.foto_ancoraggi_doc_ids,
        "firma_cliente_base64": "",
        "firma_cliente_nome": "",
        "firma_cliente_data": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db[MONTAGGIO_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[MONTAGGIO] Diario saved: {montaggio_id} — commessa {data.commessa_id}")
    return doc


@router.get("/diario/{commessa_id}")
async def list_diario_montaggio(commessa_id: str, voce_id: str = ""):
    """List assembly diary entries for a commessa."""
    query = {"commessa_id": commessa_id}
    if voce_id:
        query["voce_id"] = voce_id

    entries = await db[MONTAGGIO_COLL].find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    return {"entries": entries, "count": len(entries)}


# ── FOTO MONTAGGIO (giunti / ancoraggi) ─────────────────────

@router.post("/foto/{commessa_id}")
async def upload_foto_montaggio(
    commessa_id: str,
    file: UploadFile = File(...),
    voce_id: str = Form(""),
    operatore_id: str = Form(""),
    operatore_nome: str = Form(""),
    tipo_foto: str = Form("giunti"),  # "giunti" or "ancoraggi"
):
    """Upload a mandatory assembly photo (joints or anchors)."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "user_id": 1, "numero": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    now = datetime.now(timezone.utc)
    numero = commessa.get("numero", commessa_id)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    prefix = "MONTAGGIO_GIUNTI" if tipo_foto == "giunti" else "MONTAGGIO_ANCORAGGI"
    clean_name = f"{prefix}_{numero}_{timestamp}.jpg"

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    doc = {
        "doc_id": doc_id,
        "commessa_id": commessa_id,
        "user_id": commessa["user_id"],
        "nome_file": clean_name,
        "tipo": "foto_montaggio",
        "content_type": file.content_type or "image/jpeg",
        "file_base64": base64.b64encode(content).decode("utf-8"),
        "size_bytes": len(content),
        "metadata_estratti": {
            "source": "montaggio",
            "tipo_foto": tipo_foto,
            "voce_id": voce_id or "__principale__",
            "operatore_id": operatore_id,
            "operatore_nome": operatore_nome,
        },
        "note": f"Foto montaggio ({tipo_foto}) — {numero}",
        "uploaded_at": now.isoformat(),
        "uploaded_by": operatore_nome or operatore_id,
    }

    await db[DOC_COLL].insert_one(doc)
    doc.pop("_id", None)
    doc.pop("file_base64", None)

    logger.info(f"[MONTAGGIO] Foto uploaded: {clean_name} → tipo={tipo_foto}")
    return {"doc_id": doc_id, "nome_file": clean_name, "tipo_foto": tipo_foto}


# ── FIRMA DIGITALE CLIENTE ───────────────────────────────────

@router.post("/firma")
async def save_firma_cliente(data: FirmaClienteRequest):
    """Save client's digital signature on the assembly completion report."""
    now = datetime.now(timezone.utc)

    result = await db[MONTAGGIO_COLL].update_one(
        {"montaggio_id": data.montaggio_id},
        {"$set": {
            "firma_cliente_base64": data.firma_base64,
            "firma_cliente_nome": data.firma_nome,
            "firma_cliente_data": now.isoformat(),
            "updated_at": now.isoformat(),
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Diario montaggio non trovato")

    logger.info(f"[MONTAGGIO] Firma cliente salvata: {data.montaggio_id} — {data.firma_nome}")
    return {
        "montaggio_id": data.montaggio_id,
        "firma_salvata": True,
        "firma_nome": data.firma_nome,
        "firma_data": now.isoformat(),
    }


VARIANTI_COLL = "varianti_montaggio"


# ── VARIANTI DI MONTAGGIO ────────────────────────────────────

@router.post("/variante")
async def create_variante(data: VarianteCreate):
    """Save a variant note with mandatory photo for the assembly diary."""
    if not data.foto_doc_id:
        raise HTTPException(400, "Foto obbligatoria per la nota di variante")
    if not data.descrizione.strip():
        raise HTTPException(400, "Descrizione obbligatoria")

    now = datetime.now(timezone.utc)

    # Get admin_id
    commessa = await db.commesse.find_one(
        {"commessa_id": data.commessa_id}, {"_id": 0, "user_id": 1, "numero": 1}
    )
    admin_id = commessa["user_id"] if commessa else ""

    var_id = f"var_{uuid.uuid4().hex[:10]}"
    doc = {
        "variante_id": var_id,
        "commessa_id": data.commessa_id,
        "voce_id": data.voce_id or "",
        "admin_id": admin_id,
        "operatore_id": data.operatore_id,
        "operatore_nome": data.operatore_nome,
        "descrizione": data.descrizione.strip(),
        "foto_doc_id": data.foto_doc_id,
        "created_at": now.isoformat(),
    }

    await db[VARIANTI_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[MONTAGGIO] Variante creata: {var_id} — {data.descrizione[:50]}")
    return doc


@router.get("/varianti/{commessa_id}")
async def list_varianti(commessa_id: str, voce_id: str = ""):
    """List variant notes for a commessa."""
    query = {"commessa_id": commessa_id}
    if voce_id:
        query["voce_id"] = voce_id

    varianti = await db[VARIANTI_COLL].find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    return {"varianti": varianti, "count": len(varianti)}
