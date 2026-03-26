"""Rilievo (On-Site Survey) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from typing import Optional
from io import BytesIO
import uuid
from datetime import datetime, timezone
from core.security import get_current_user, tenant_match
from core.rbac import require_role
from core.database import db
from models.rilievo import (
    RilievoCreate, RilievoUpdate, RilievoResponse, RilievoListResponse,
    RilievoStatus, SketchData, PhotoData
)
from services.rilievo_pdf_service import rilievo_pdf_service
from services.audit_trail import log_activity
from services.object_storage import get_object, put_object
import logging

logger = logging.getLogger(__name__)
import math

router = APIRouter(prefix="/rilievi", tags=["rilievi"])


@router.get("/", response_model=RilievoListResponse)
async def get_rilievi(
    client_id: Optional[str] = None,
    status: Optional[RilievoStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Get all rilievi for current user with optional filters."""
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status.value
    
    total = await db.rilievi.count_documents(query)
    
    rilievi_cursor = db.rilievi.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
    rilievi = await rilievi_cursor.to_list(length=limit)
    
    # Populate client names
    for rilievo in rilievi:
        client = await db.clients.find_one(
            {"client_id": rilievo.get("client_id")},
            {"_id": 0, "business_name": 1}
        )
        rilievo["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoListResponse(
        rilievi=[RilievoResponse(**r) for r in rilievi],
        total=total
    )


@router.get("/{rilievo_id}", response_model=RilievoResponse)
async def get_rilievo(
    rilievo_id: str,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Get a specific rilievo by ID."""
    rilievo = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    # Populate client name
    client = await db.clients.find_one(
        {"client_id": rilievo.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    rilievo["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**rilievo)


@router.post("/", response_model=RilievoResponse, status_code=201)
async def create_rilievo(
    rilievo_data: RilievoCreate,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Create a new rilievo."""
    # Verify client exists
    client = await db.clients.find_one(
        {"client_id": rilievo_data.client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=400, detail="Cliente non trovato")
    
    rilievo_id = f"ril_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Process sketches - add IDs and timestamps
    sketches = []
    for sketch in rilievo_data.sketches:
        sketch_dict = sketch.model_dump()
        sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
        sketch_dict["created_at"] = now
        sketches.append(sketch_dict)
    
    # Process photos - add IDs and timestamps
    photos = []
    for photo in rilievo_data.photos:
        photo_dict = photo.model_dump()
        photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
        photo_dict["created_at"] = now
        photos.append(photo_dict)
    
    rilievo_doc = {
        "rilievo_id": rilievo_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "client_id": rilievo_data.client_id,
        "project_name": rilievo_data.project_name,
        "survey_date": rilievo_data.survey_date.isoformat(),
        "location": rilievo_data.location,
        "status": RilievoStatus.BOZZA.value,
        "sketches": sketches,
        "photos": photos,
        "notes": rilievo_data.notes,
        "commessa_id": rilievo_data.commessa_id,
        "tipologia": rilievo_data.tipologia,
        "misure": rilievo_data.misure,
        "elementi": [e.model_dump() for e in rilievo_data.elementi],
        "vista_3d_config": rilievo_data.vista_3d_config,
        "created_at": now,
        "updated_at": now
    }
    
    await db.rilievi.insert_one(rilievo_doc)
    
    created = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    created["client_name"] = client.get("business_name")
    
    logger.info(f"Rilievo created: {rilievo_id} by user {user['user_id']}")
    await log_activity(user, "create", "rilievo", rilievo_id, label=rilievo_data.project_name)
    return RilievoResponse(**created)


@router.put("/{rilievo_id}", response_model=RilievoResponse)
async def update_rilievo(
    rilievo_id: str,
    rilievo_data: RilievoUpdate,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Update an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    update_dict = {}
    now = datetime.now(timezone.utc)
    
    # Update client if changed
    if rilievo_data.client_id:
        client = await db.clients.find_one(
            {"client_id": rilievo_data.client_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
        )
        if not client:
            raise HTTPException(status_code=400, detail="Cliente non trovato")
        update_dict["client_id"] = rilievo_data.client_id
    
    # Update simple fields
    if rilievo_data.project_name is not None:
        update_dict["project_name"] = rilievo_data.project_name
    if rilievo_data.survey_date is not None:
        update_dict["survey_date"] = rilievo_data.survey_date.isoformat()
    if rilievo_data.location is not None:
        update_dict["location"] = rilievo_data.location
    if rilievo_data.notes is not None:
        update_dict["notes"] = rilievo_data.notes
    if rilievo_data.status is not None:
        update_dict["status"] = rilievo_data.status.value
    if rilievo_data.commessa_id is not None:
        update_dict["commessa_id"] = rilievo_data.commessa_id
    if rilievo_data.tipologia is not None:
        update_dict["tipologia"] = rilievo_data.tipologia
    if rilievo_data.misure is not None:
        update_dict["misure"] = rilievo_data.misure
    if rilievo_data.elementi is not None:
        update_dict["elementi"] = [e.model_dump() for e in rilievo_data.elementi]
    if rilievo_data.vista_3d_config is not None:
        update_dict["vista_3d_config"] = rilievo_data.vista_3d_config
    
    # Update sketches
    if rilievo_data.sketches is not None:
        sketches = []
        for sketch in rilievo_data.sketches:
            sketch_dict = sketch.model_dump()
            if not sketch_dict.get("sketch_id"):
                sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
                sketch_dict["created_at"] = now
            sketches.append(sketch_dict)
        update_dict["sketches"] = sketches
    
    # Update photos
    if rilievo_data.photos is not None:
        photos = []
        for photo in rilievo_data.photos:
            photo_dict = photo.model_dump()
            if not photo_dict.get("photo_id"):
                photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
                photo_dict["created_at"] = now
            photos.append(photo_dict)
        update_dict["photos"] = photos
    
    update_dict["updated_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {"$set": update_dict}
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    logger.info(f"Rilievo updated: {rilievo_id}")
    await log_activity(user, "update", "rilievo", rilievo_id, label=updated.get("project_name", ""))
    return RilievoResponse(**updated)


@router.delete("/{rilievo_id}")
async def delete_rilievo(
    rilievo_id: str,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Delete a rilievo."""
    result = await db.rilievi.delete_one({
        "rilievo_id": rilievo_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user)
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    logger.info(f"Rilievo deleted: {rilievo_id}")
    await log_activity(user, "delete", "rilievo", rilievo_id)
    return {"message": "Rilievo eliminato con successo"}


# ── Photo Upload (Object Storage) ──

def _upload_rilievo_file(user_id: str, file_data: bytes, filename: str, content_type: str, subdir: str = "photos") -> dict:
    """Upload a rilievo file to object storage."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    storage_path = f"norma_facile/rilievi/{user_id}/{subdir}/{uuid.uuid4()}.{ext}"
    result = put_object(storage_path, file_data, content_type)
    return {
        "storage_path": result["path"],
        "original_filename": filename,
        "content_type": content_type,
        "size": result.get("size", len(file_data)),
    }


@router.post("/{rilievo_id}/upload-foto")
async def upload_foto_rilievo(
    rilievo_id: str,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: dict = Depends(require_role("admin", "ufficio_tecnico")),
):
    """Upload a photo to object storage and add to rilievo."""
    doc = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if not doc:
        raise HTTPException(404, "Rilievo non trovato")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"Formato non supportato: {file.content_type}")

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File troppo grande (max 10MB)")

    storage_info = _upload_rilievo_file(user["user_id"], file_data, file.filename, file.content_type)
    photo_entry = {
        "photo_id": f"ph_{uuid.uuid4().hex[:8]}",
        "name": file.filename,
        "caption": caption,
        **storage_info,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"photos": photo_entry},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    return photo_entry


@router.delete("/{rilievo_id}/foto/{photo_id}")
async def delete_foto_rilievo(rilievo_id: str, photo_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    """Remove a photo from the rilievo."""
    result = await db.rilievi.update_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$pull": {"photos": {"photo_id": photo_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Foto non trovata")
    return {"deleted": True}


@router.post("/{rilievo_id}/upload-sketch")
async def upload_sketch_rilievo(
    rilievo_id: str,
    drawing_data: str = Form(""),
    name: str = Form("Schizzo"),
    dimensions: str = Form("{}"),
    background: Optional[UploadFile] = File(None),
    user: dict = Depends(require_role("admin", "ufficio_tecnico")),
):
    """Upload a sketch with optional background image to object storage."""
    doc = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if not doc:
        raise HTTPException(404, "Rilievo non trovato")

    sketch_entry = {
        "sketch_id": f"sk_{uuid.uuid4().hex[:8]}",
        "name": name,
        "drawing_data": drawing_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Parse dimensions
    try:
        import json
        sketch_entry["dimensions"] = json.loads(dimensions)
    except Exception:
        sketch_entry["dimensions"] = {}

    # Upload background image to object storage if provided
    if background and background.size:
        bg_data = await background.read()
        if len(bg_data) > 10 * 1024 * 1024:
            raise HTTPException(400, "Background troppo grande (max 10MB)")
        bg_info = _upload_rilievo_file(user["user_id"], bg_data, background.filename, background.content_type, "sketches")
        sketch_entry["background_storage_path"] = bg_info["storage_path"]

    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"sketches": sketch_entry},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    return sketch_entry


@router.delete("/{rilievo_id}/sketch/{sketch_id}")
async def delete_sketch_rilievo(rilievo_id: str, sketch_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    """Remove a sketch from the rilievo."""
    result = await db.rilievi.update_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$pull": {"sketches": {"sketch_id": sketch_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Schizzo non trovato")
    return {"deleted": True}


@router.get("/foto-proxy/{path:path}")
async def proxy_foto_rilievo(path: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    """Proxy a photo/sketch-background from object storage."""
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        raise HTTPException(404, f"File non trovato: {str(e)[:100]}")


# ── Profili standard: peso kg/m ──
PROFILI_PESO = {
    "20x20": 1.15, "25x25": 1.45, "30x20": 1.45, "30x30": 2.15,
    "40x20": 1.74, "40x40": 3.72, "50x30": 2.93, "60x40": 4.66,
    "60x60": 6.71, "80x40": 5.59, "tondo_40": 1.21,
    "quadro_20x20": 1.15, "UPN100": 10.6, "mandorlato_4mm": 32.0,
}


def _parse_profilo_dim(profilo: str):
    """Parse '60x40' → (60, 40) mm."""
    parts = profilo.lower().replace("x", " ").split()
    nums = [float(p) for p in parts if p.replace(".", "").isdigit()]
    return (nums[0], nums[1]) if len(nums) >= 2 else (nums[0], nums[0]) if nums else (30, 30)


def _calcola_inferriata(m: dict) -> dict:
    L = float(m.get("luce_larghezza", 0))
    H = float(m.get("luce_altezza", 0))
    interasse_m = float(m.get("interasse_montanti", 120))
    n_traversi = int(m.get("numero_traversi", 2))
    n_montanti = math.ceil(L / interasse_m) + 1 if interasse_m > 0 else 2
    ml_montanti = n_montanti * H / 1000
    ml_traversi = n_traversi * L / 1000
    profilo_m = m.get("profilo_montante", "30x30")
    profilo_t = m.get("profilo_traverso", "20x20")
    peso_montanti = ml_montanti * PROFILI_PESO.get(profilo_m, 2.0)
    peso_traversi = ml_traversi * PROFILI_PESO.get(profilo_t, 1.5)
    sup = (L * H * 2) / 1_000_000  # m² entrambi i lati
    return {
        "materiali": [
            {"descrizione": f"Montante {profilo_m}", "quantita": n_montanti, "ml": round(ml_montanti, 2), "peso_kg": round(peso_montanti, 2)},
            {"descrizione": f"Traverso {profilo_t}", "quantita": n_traversi, "ml": round(ml_traversi, 2), "peso_kg": round(peso_traversi, 2)},
        ],
        "peso_totale_kg": round(peso_montanti + peso_traversi, 2),
        "superficie_verniciatura_m2": round(sup, 2),
    }


def _calcola_cancello(m: dict, pedonale: bool = False) -> dict:
    L = float(m.get("luce_netta", 0))
    H = float(m.get("altezza", 0))
    profilo_t = m.get("profilo_telaio", "60x40" if not pedonale else "40x40")
    profilo_i = m.get("profilo_infisso", "40x20" if not pedonale else "25x25")
    interasse_i = float(m.get("interasse_infissi", 100))
    ml_telaio = 2 * (L + H) / 1000
    n_infissi = math.ceil(L / interasse_i) + 1 if interasse_i > 0 else 2
    ml_infissi = n_infissi * H / 1000
    peso_t = ml_telaio * PROFILI_PESO.get(profilo_t, 4.0)
    peso_i = ml_infissi * PROFILI_PESO.get(profilo_i, 1.5)
    sup = (L * H * 2) / 1_000_000
    materiali = [
        {"descrizione": f"Telaio {profilo_t}", "quantita": 1, "ml": round(ml_telaio, 2), "peso_kg": round(peso_t, 2)},
        {"descrizione": f"Infisso {profilo_i}", "quantita": n_infissi, "ml": round(ml_infissi, 2), "peso_kg": round(peso_i, 2)},
    ]
    peso_tot = peso_t + peso_i
    if not pedonale and m.get("motorizzazione"):
        materiali.append({"descrizione": f"Motore {m.get('tipo_motore', 'FAAC')}", "quantita": 1, "ml": 0, "peso_kg": 15.0})
        peso_tot += 15.0
    return {"materiali": materiali, "peso_totale_kg": round(peso_tot, 2), "superficie_verniciatura_m2": round(sup, 2)}


def _calcola_scala(m: dict) -> dict:
    n_gradini = int(m.get("numero_gradini", 0))
    alzata = float(m.get("alzata", 175))
    pedata = float(m.get("pedata", 280))
    larghezza = float(m.get("larghezza", 900))
    diag_gradino = math.sqrt(alzata**2 + pedata**2)
    diag_totale = n_gradini * diag_gradino / 1000
    profilo_s = m.get("profilo_struttura", "UPN100")
    ml_struttura = diag_totale * 2  # 2 longheroni
    peso_struttura = ml_struttura * PROFILI_PESO.get(profilo_s, 10.0)
    tipo_gradino = m.get("tipo_gradino", "mandorlato")
    spessore = float(m.get("spessore_gradino", 4))
    area_gradino = (pedata * larghezza) / 1_000_000
    peso_gradini = n_gradini * area_gradino * spessore * 7.85  # acciaio kg/dm3 approx
    materiali = [
        {"descrizione": f"Struttura {profilo_s}", "quantita": 2, "ml": round(ml_struttura, 2), "peso_kg": round(peso_struttura, 2)},
        {"descrizione": f"Gradino {tipo_gradino} sp.{spessore}mm", "quantita": n_gradini, "ml": 0, "peso_kg": round(peso_gradini, 2)},
    ]
    peso_tot = peso_struttura + peso_gradini
    if m.get("corrimano"):
        profilo_c = m.get("profilo_corrimano", "tondo_40")
        ml_corr = diag_totale
        peso_c = ml_corr * PROFILI_PESO.get(profilo_c, 1.2)
        interasse_mc = float(m.get("interasse_montanti", 150))
        n_mc = math.ceil(diag_totale * 1000 / interasse_mc) + 1 if interasse_mc > 0 else 2
        profilo_mc = m.get("montanti_corrimano", "quadro_20x20")
        H_corrimano = 1000  # mm standard
        ml_mc = n_mc * H_corrimano / 1000
        peso_mc = ml_mc * PROFILI_PESO.get(profilo_mc, 1.15)
        materiali.append({"descrizione": f"Corrimano {profilo_c}", "quantita": 1, "ml": round(ml_corr, 2), "peso_kg": round(peso_c, 2)})
        materiali.append({"descrizione": f"Montante corrimano {profilo_mc}", "quantita": n_mc, "ml": round(ml_mc, 2), "peso_kg": round(peso_mc, 2)})
        peso_tot += peso_c + peso_mc
    sup = (diag_totale * larghezza / 1000 * 2) + (n_gradini * area_gradino * 2)
    return {"materiali": materiali, "peso_totale_kg": round(peso_tot, 2), "superficie_verniciatura_m2": round(sup, 2)}


def _calcola_recinzione(m: dict) -> dict:
    lung_tot = float(m.get("lunghezza_totale", 0))
    H = float(m.get("altezza", 0))
    interasse_pali = float(m.get("interasse_pali", 2500))
    n_pali = math.ceil(lung_tot / interasse_pali) + 1 if interasse_pali > 0 else 2
    profilo_p = m.get("profilo_palo", "60x60")
    ml_pali = n_pali * (H + 400) / 1000  # +400mm interrato
    peso_pali = ml_pali * PROFILI_PESO.get(profilo_p, 6.0)
    n_campate = n_pali - 1
    lung_campata = float(m.get("lunghezza_campata", interasse_pali))
    n_orizz = int(m.get("numero_orizzontali", 3))
    profilo_o = m.get("profilo_orizzontale", "30x20")
    ml_orizz = n_campate * n_orizz * lung_campata / 1000
    peso_orizz = ml_orizz * PROFILI_PESO.get(profilo_o, 1.45)
    interasse_v = float(m.get("interasse_verticali", 120))
    profilo_v = m.get("profilo_verticale", "20x20")
    n_vert_per_campata = math.ceil(lung_campata / interasse_v) + 1 if interasse_v > 0 else 2
    ml_vert = n_campate * n_vert_per_campata * H / 1000
    peso_vert = ml_vert * PROFILI_PESO.get(profilo_v, 1.15)
    materiali = [
        {"descrizione": f"Palo {profilo_p}", "quantita": n_pali, "ml": round(ml_pali, 2), "peso_kg": round(peso_pali, 2)},
        {"descrizione": f"Orizzontale {profilo_o}", "quantita": n_campate * n_orizz, "ml": round(ml_orizz, 2), "peso_kg": round(peso_orizz, 2)},
        {"descrizione": f"Verticale {profilo_v}", "quantita": n_campate * n_vert_per_campata, "ml": round(ml_vert, 2), "peso_kg": round(peso_vert, 2)},
    ]
    peso_tot = peso_pali + peso_orizz + peso_vert
    sup = (lung_tot * H * 2) / 1_000_000
    return {"materiali": materiali, "peso_totale_kg": round(peso_tot, 2), "superficie_verniciatura_m2": round(sup, 2)}


def _calcola_ringhiera(m: dict) -> dict:
    L = float(m.get("lunghezza", 0))
    H = float(m.get("altezza", 900))
    profilo_c = m.get("profilo_corrente", "40x40")
    ml_corrente = L / 1000 * 2  # sup + inf
    peso_corrente = ml_corrente * PROFILI_PESO.get(profilo_c, 3.72)
    profilo_m = m.get("profilo_montante", "40x40")
    interasse_m = float(m.get("interasse_montanti", 1000))
    n_mont = math.ceil(L / interasse_m) + 1 if interasse_m > 0 else 2
    ml_mont = n_mont * H / 1000
    peso_mont = ml_mont * PROFILI_PESO.get(profilo_m, 3.72)
    tipo_inf = m.get("tipo_infisso", "quadro_20x20")
    interasse_i = float(m.get("interasse_infissi", 100))
    n_infissi = math.ceil(L / interasse_i) + 1 if interasse_i > 0 else 2
    ml_infissi = n_infissi * H / 1000
    peso_infissi = ml_infissi * PROFILI_PESO.get(tipo_inf, 1.15)
    corrimano_p = m.get("corrimano", "tondo_40")
    ml_corr = L / 1000
    peso_corr = ml_corr * PROFILI_PESO.get(corrimano_p, 1.21)
    materiali = [
        {"descrizione": f"Corrente {profilo_c}", "quantita": 2, "ml": round(ml_corrente, 2), "peso_kg": round(peso_corrente, 2)},
        {"descrizione": f"Montante {profilo_m}", "quantita": n_mont, "ml": round(ml_mont, 2), "peso_kg": round(peso_mont, 2)},
        {"descrizione": f"Infisso {tipo_inf}", "quantita": n_infissi, "ml": round(ml_infissi, 2), "peso_kg": round(peso_infissi, 2)},
        {"descrizione": f"Corrimano {corrimano_p}", "quantita": 1, "ml": round(ml_corr, 2), "peso_kg": round(peso_corr, 2)},
    ]
    peso_tot = peso_corrente + peso_mont + peso_infissi + peso_corr
    sup = (L * H * 2) / 1_000_000
    return {"materiali": materiali, "peso_totale_kg": round(peso_tot, 2), "superficie_verniciatura_m2": round(sup, 2)}


CALCOLA_FN = {
    "inferriata_fissa": _calcola_inferriata,
    "cancello_carrabile": lambda m: _calcola_cancello(m, False),
    "cancello_pedonale": lambda m: _calcola_cancello(m, True),
    "scala": _calcola_scala,
    "recinzione": _calcola_recinzione,
    "ringhiera": _calcola_ringhiera,
}


@router.post("/{rilievo_id}/calcola-materiali")
async def calcola_materiali(rilievo_id: str, user: dict = Depends(require_role("admin", "ufficio_tecnico"))):
    """Dalla tipologia e misure, calcola lista materiali, peso e superficie."""
    doc = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Rilievo non trovato")

    tipologia = doc.get("tipologia", "")
    misure = doc.get("misure", {})

    if not tipologia or tipologia not in CALCOLA_FN:
        raise HTTPException(400, f"Tipologia non supportata: {tipologia}")

    risultato = CALCOLA_FN[tipologia](misure)
    risultato["tipologia"] = tipologia
    risultato["rilievo_id"] = rilievo_id
    return risultato




@router.patch("/{rilievo_id}/collega-commessa")
async def collega_rilievo_a_commessa(
    rilievo_id: str,
    payload: dict,
    user: dict = Depends(require_role("admin", "ufficio_tecnico")),
):
    """Link a rilievo to an existing commessa (bidirectional)."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    commessa_id = payload.get("commessa_id")
    if not commessa_id:
        raise HTTPException(400, "commessa_id richiesto")

    rilievo = await db.rilievi.find_one({"rilievo_id": rilievo_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not rilievo:
        raise HTTPException(404, "Rilievo non trovato")
    commessa = await db.commesse.find_one({"commessa_id": commessa_id, "user_id": uid, "tenant_id": tenant_match(user)})
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Update rilievo → commessa
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {"$set": {"commessa_id": commessa_id}},
    )
    # Update commessa → rilievo (moduli.rilievo_id)
    await db.commesse.update_one(
        {"commessa_id": commessa_id},
        {"$set": {"moduli.rilievo_id": rilievo_id, "linked_rilievo_id": rilievo_id}},
    )
    await log_activity(user, "update", "rilievo", rilievo_id,
                       label=rilievo.get("project_name", ""),
                       details={"collegato_a_commessa": commessa.get("numero", commessa_id)})
    return {"message": "Rilievo collegato alla commessa", "commessa_id": commessa_id}
async def add_sketch(
    rilievo_id: str,
    sketch: SketchData,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Add a sketch to an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    now = datetime.now(timezone.utc)
    sketch_dict = sketch.model_dump()
    sketch_dict["sketch_id"] = f"sk_{uuid.uuid4().hex[:8]}"
    sketch_dict["created_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"sketches": sketch_dict},
            "$set": {"updated_at": now}
        }
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**updated)


@router.post("/{rilievo_id}/photo", response_model=RilievoResponse)
async def add_photo(
    rilievo_id: str,
    photo: PhotoData,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Add a photo to an existing rilievo."""
    existing = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    now = datetime.now(timezone.utc)
    photo_dict = photo.model_dump()
    photo_dict["photo_id"] = f"ph_{uuid.uuid4().hex[:8]}"
    photo_dict["created_at"] = now
    
    await db.rilievi.update_one(
        {"rilievo_id": rilievo_id},
        {
            "$push": {"photos": photo_dict},
            "$set": {"updated_at": now}
        }
    )
    
    updated = await db.rilievi.find_one({"rilievo_id": rilievo_id}, {"_id": 0})
    client = await db.clients.find_one(
        {"client_id": updated.get("client_id")},
        {"_id": 0, "business_name": 1}
    )
    updated["client_name"] = client.get("business_name") if client else "N/A"
    
    return RilievoResponse(**updated)


@router.get("/{rilievo_id}/pdf")
async def get_rilievo_pdf(
    rilievo_id: str,
    user: dict = Depends(require_role("admin", "ufficio_tecnico"))
):
    """Generate and download rilievo PDF summary."""
    rilievo = await db.rilievi.find_one(
        {"rilievo_id": rilievo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo non trovato")
    
    client = await db.clients.find_one(
        {"client_id": rilievo.get("client_id")},
        {"_id": 0}
    )
    if not client:
        client = {"business_name": "N/A"}
    
    # Get company settings for header
    company = await db.company_settings.find_one(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not company:
        company = {"business_name": user.get("name", "")}
    
    # Generate PDF
    pdf_bytes = rilievo_pdf_service.generate_rilievo_pdf(rilievo, client, company)
    
    # Create filename
    project_name = rilievo.get("project_name", "rilievo").replace(" ", "_")
    filename = f"Rilievo_{project_name}.pdf"
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
