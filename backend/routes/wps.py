"""
WPS (Welding Procedure Specification) routes for EN 1090 compliance.
Auto-suggests WPS parameters based on material, process, and thickness.
Matches qualified welders to the job requirements.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/wps", tags=["wps"])

# ── EN 1090 Knowledge Base ──

WELDING_PROCESSES = {
    "111": {"label": "SMAW (Elettrodo rivestito)", "short": "MMA", "gas": None, "filler": "Elettrodo"},
    "135": {"label": "MAG (Filo pieno)", "short": "MAG", "gas": "Ar+CO2 / CO2", "filler": "Filo pieno"},
    "136": {"label": "FCAW (Filo animato)", "short": "FCAW", "gas": "Ar+CO2 / CO2", "filler": "Filo animato"},
    "138": {"label": "MAG (Filo animato metal-cored)", "short": "MAG-MC", "gas": "Ar+CO2", "filler": "Filo metal-cored"},
    "141": {"label": "TIG", "short": "TIG", "gas": "Argon puro", "filler": "Bacchetta TIG"},
    "21":  {"label": "Resistenza a punti", "short": "RSW", "gas": None, "filler": None},
    "131": {"label": "MIG (Alluminio)", "short": "MIG", "gas": "Argon puro", "filler": "Filo alluminio"},
}

MATERIAL_GROUPS = {
    "1.1": {"label": "S235 / S275 (Fe360-Fe430)", "materials": ["S235JR", "S235J0", "S235J2", "S275JR", "S275J0", "S275J2"],
            "preheat_threshold": 25, "carbon_eq": "<=0.35"},
    "1.2": {"label": "S355 (Fe510)", "materials": ["S355JR", "S355J0", "S355J2", "S355K2"],
            "preheat_threshold": 25, "carbon_eq": "<=0.42"},
    "1.3": {"label": "S420-S460 (alta resistenza)", "materials": ["S420", "S460", "S460M", "S460ML"],
            "preheat_threshold": 20, "carbon_eq": "<=0.47"},
    "2.1": {"label": "Acciaio termomeccanico (TMCP)", "materials": ["S355M", "S355ML", "S460M"],
            "preheat_threshold": 20, "carbon_eq": "<=0.40"},
    "8.1": {"label": "Acciaio inox austenitico", "materials": ["AISI 304", "AISI 304L", "AISI 316", "AISI 316L", "1.4301", "1.4404"],
            "preheat_threshold": None, "carbon_eq": "N/A"},
    "21.1": {"label": "Alluminio (serie 5xxx/6xxx)", "materials": ["5083", "5754", "6060", "6082"],
             "preheat_threshold": None, "carbon_eq": "N/A"},
}

WELDING_POSITIONS = [
    {"code": "PA", "label": "Piano (orizzontale)"},
    {"code": "PB", "label": "Angolo piano"},
    {"code": "PC", "label": "Orizzontale (parete verticale)"},
    {"code": "PD", "label": "Angolo sopratesta"},
    {"code": "PE", "label": "Sopratesta"},
    {"code": "PF", "label": "Verticale ascendente"},
    {"code": "PG", "label": "Verticale discendente"},
]

JOINT_TYPES = [
    {"code": "BW", "label": "Testa a testa (Butt Weld)"},
    {"code": "FW", "label": "Angolo / a T (Fillet Weld)"},
    {"code": "BW+FW", "label": "Combinato"},
]

EXC_CLASSES = {
    "EXC1": {"min_process_control": "basso", "ndt_pct": 0, "description": "Classe base (edifici semplici)"},
    "EXC2": {"min_process_control": "medio", "ndt_pct": 10, "description": "Standard (edifici, ponti leggeri)"},
    "EXC3": {"min_process_control": "alto", "ndt_pct": 20, "description": "Alto (strutture importanti)"},
    "EXC4": {"min_process_control": "molto alto", "ndt_pct": 100, "description": "Massimo (strutture critiche)"},
}

# Filler material suggestions per process + material group
FILLER_SUGGESTIONS = {
    ("111", "1.1"): {"filler": "E42 2 B 42 H5 (es. ESAB OK 48.00)", "standard": "EN ISO 2560"},
    ("111", "1.2"): {"filler": "E46 4 B 42 H5 (es. ESAB OK 48.60)", "standard": "EN ISO 2560"},
    ("111", "1.3"): {"filler": "E50 4 B 12 H5", "standard": "EN ISO 2560"},
    ("135", "1.1"): {"filler": "G 42 2 M21 3Si1 (es. SG2 / ER70S-6)", "standard": "EN ISO 14341"},
    ("135", "1.2"): {"filler": "G 46 2 M21 3Si1 (es. SG3 / ER70S-6)", "standard": "EN ISO 14341"},
    ("135", "1.3"): {"filler": "G 50 4 M21 3Mn2NiCrMo", "standard": "EN ISO 14341"},
    ("136", "1.1"): {"filler": "T 42 2 P M21 1 H10 (es. Dual Shield 7100)", "standard": "EN ISO 17632"},
    ("136", "1.2"): {"filler": "T 46 2 P M21 1 H10", "standard": "EN ISO 17632"},
    ("141", "1.1"): {"filler": "W 42 2 3Si1 (es. TIG ER70S-6)", "standard": "EN ISO 636"},
    ("141", "1.2"): {"filler": "W 46 2 3Si1", "standard": "EN ISO 636"},
    ("141", "8.1"): {"filler": "W 19 12 3 L (es. ER316L)", "standard": "EN ISO 14343"},
    ("135", "8.1"): {"filler": "G 19 12 3 L (es. 316LSi)", "standard": "EN ISO 14343"},
    ("131", "21.1"): {"filler": "S Al 5183 (AlMg4.5Mn0.7)", "standard": "EN ISO 18273"},
    ("141", "21.1"): {"filler": "S Al 5356 (AlMg5)", "standard": "EN ISO 18273"},
}

# Gas suggestions
GAS_SUGGESTIONS = {
    "135": {"1.1": "M21 (Ar 82% + CO2 18%)", "1.2": "M21 (Ar 82% + CO2 18%)", "1.3": "M21 (Ar 82% + CO2 18%)",
            "8.1": "M12 (Ar 97.5% + CO2 2.5%)", "default": "M21 (Ar 82% + CO2 18%)"},
    "136": {"default": "M21 (Ar 82% + CO2 18%) oppure CO2 100%"},
    "141": {"default": "I1 (Argon 99.99%)"},
    "131": {"default": "I1 (Argon 99.99%)"},
}


def suggest_preheat(material_group: str, thickness: float) -> dict:
    """Suggest preheat temperature based on EN 1011-2."""
    mg = MATERIAL_GROUPS.get(material_group, {})
    threshold = mg.get("preheat_threshold")
    if threshold is None:
        return {"temp_min": None, "note": "Preriscaldo generalmente non richiesto per questo materiale"}
    if material_group in ("8.1", "21.1"):
        return {"temp_min": None, "note": "Preriscaldo non richiesto"}
    if thickness <= threshold:
        return {"temp_min": None, "note": f"Non richiesto (spessore <= {threshold}mm)"}
    if thickness <= 40:
        temp = 75 if material_group == "1.1" else 100
    elif thickness <= 60:
        temp = 100 if material_group in ("1.1", "1.2") else 125
    else:
        temp = 125 if material_group in ("1.1", "1.2") else 150
    return {"temp_min": temp, "note": f"Preriscaldo consigliato >= {temp}°C (EN 1011-2)"}


def suggest_interpass(material_group: str) -> dict:
    """Suggest max interpass temperature."""
    if material_group.startswith("8"):
        return {"temp_max": 150, "note": "Max 150°C per acciai inox austenitici"}
    if material_group.startswith("21"):
        return {"temp_max": 120, "note": "Max 120°C per alluminio"}
    return {"temp_max": 250, "note": "Max 250°C per acciai al carbonio (EN 1011-2)"}


# ── Pydantic Models ──

class WPSCreate(BaseModel):
    title: str
    commessa_id: Optional[str] = None
    process: str
    material_group: str
    base_material: Optional[str] = None
    thickness_min: float = 1
    thickness_max: float = 40
    joint_type: str = "BW"
    positions: List[str] = ["PA"]
    exec_class: str = "EXC2"
    filler_material: Optional[str] = None
    filler_standard: Optional[str] = None
    shielding_gas: Optional[str] = None
    preheat_temp: Optional[float] = None
    interpass_temp_max: Optional[float] = None
    welding_params: Optional[dict] = None
    notes: Optional[str] = None

class WPSUpdate(BaseModel):
    title: Optional[str] = None
    process: Optional[str] = None
    material_group: Optional[str] = None
    base_material: Optional[str] = None
    thickness_min: Optional[float] = None
    thickness_max: Optional[float] = None
    joint_type: Optional[str] = None
    positions: Optional[List[str]] = None
    exec_class: Optional[str] = None
    filler_material: Optional[str] = None
    filler_standard: Optional[str] = None
    shielding_gas: Optional[str] = None
    preheat_temp: Optional[float] = None
    interpass_temp_max: Optional[float] = None
    welding_params: Optional[dict] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ── Reference Data ──

@router.get("/reference-data")
async def get_wps_reference_data():
    """Return all reference data for WPS creation forms."""
    return {
        "processes": WELDING_PROCESSES,
        "material_groups": MATERIAL_GROUPS,
        "positions": WELDING_POSITIONS,
        "joint_types": JOINT_TYPES,
        "exec_classes": EXC_CLASSES,
    }


# ── WPS Suggestion Engine ──

@router.get("/suggest")
async def suggest_wps(
    process: str = Query(..., description="Codice processo (es. 135)"),
    material_group: str = Query(..., description="Gruppo materiale (es. 1.2)"),
    thickness: float = Query(..., description="Spessore (mm)"),
    joint_type: str = Query("BW", description="Tipo giunto"),
    exec_class: str = Query("EXC2", description="Classe esecuzione"),
    user: dict = Depends(get_current_user),
):
    """Auto-suggest WPS parameters based on EN 1090 rules."""
    proc_info = WELDING_PROCESSES.get(process)
    mat_info = MATERIAL_GROUPS.get(material_group)
    if not proc_info:
        raise HTTPException(400, f"Processo {process} non riconosciuto")
    if not mat_info:
        raise HTTPException(400, f"Gruppo materiale {material_group} non riconosciuto")

    # Filler material
    filler = FILLER_SUGGESTIONS.get((process, material_group), {})

    # Gas
    gas_proc = GAS_SUGGESTIONS.get(process, {})
    gas = gas_proc.get(material_group, gas_proc.get("default", proc_info.get("gas")))

    # Preheat
    preheat = suggest_preheat(material_group, thickness)

    # Interpass
    interpass = suggest_interpass(material_group)

    # NDT requirements
    exc_info = EXC_CLASSES.get(exec_class, {})

    # Find qualified welders
    qualified_welders = []
    async for w in db.welders.find(
        {"user_id": user["user_id"], "is_active": True}, {"_id": 0}
    ):
        for q in w.get("qualifications", []):
            q_process = q.get("process", "")
            q_material = q.get("material_group", "")
            # Match process code
            if process in q_process or q_process in process:
                # Check material compatibility
                if not q_material or material_group in q_material or q_material in material_group:
                    from routes.welders import _qual_status
                    status, days = _qual_status(q.get("expiry_date", ""))
                    if status in ("attivo", "in_scadenza"):
                        qualified_welders.append({
                            "welder_id": w["welder_id"],
                            "name": w["name"],
                            "stamp_id": w["stamp_id"],
                            "qual_process": q_process,
                            "qual_material": q_material,
                            "qual_thickness": q.get("thickness_range"),
                            "qual_status": status,
                            "days_until_expiry": days,
                        })
                    break

    return {
        "process": {**proc_info, "code": process},
        "material": {**mat_info, "code": material_group},
        "thickness": thickness,
        "joint_type": joint_type,
        "exec_class": {**exc_info, "code": exec_class},
        "suggestion": {
            "filler_material": filler.get("filler", "Da specificare"),
            "filler_standard": filler.get("standard", ""),
            "shielding_gas": gas,
            "preheat": preheat,
            "interpass": interpass,
            "ndt_percentage": exc_info.get("ndt_pct", 0),
        },
        "qualified_welders": qualified_welders,
    }


# ── CRUD ──

@router.post("/")
async def create_wps(data: WPSCreate, user: dict = Depends(get_current_user)):
    """Create a new WPS document."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc).isoformat()

    # Auto-number
    count = await db.wps_documents.count_documents({"user_id": uid})
    wps_number = f"WPS-{count + 1:03d}"

    doc = {
        "wps_id": f"wps_{uuid.uuid4().hex[:12]}",
        "wps_number": wps_number,
        "user_id": uid,
        "status": "bozza",
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    await db.wps_documents.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/")
async def list_wps(
    user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    commessa_id: Optional[str] = None,
):
    """List all WPS documents."""
    uid = user["user_id"]
    query = {"user_id": uid}
    if status:
        query["status"] = status
    if commessa_id:
        query["commessa_id"] = commessa_id

    items = []
    async for doc in db.wps_documents.find(query, {"_id": 0}).sort("created_at", -1):
        items.append(doc)
    return {"items": items, "total": len(items)}


@router.get("/{wps_id}")
async def get_wps(wps_id: str, user: dict = Depends(get_current_user)):
    """Get a single WPS document."""
    doc = await db.wps_documents.find_one(
        {"wps_id": wps_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "WPS non trovato")
    return doc


@router.put("/{wps_id}")
async def update_wps(wps_id: str, data: WPSUpdate, user: dict = Depends(get_current_user)):
    """Update a WPS document."""
    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.wps_documents.update_one(
        {"wps_id": wps_id, "user_id": user["user_id"]},
        {"$set": update_dict}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "WPS non trovato")

    doc = await db.wps_documents.find_one(
        {"wps_id": wps_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    return doc


@router.delete("/{wps_id}")
async def delete_wps(wps_id: str, user: dict = Depends(get_current_user)):
    """Delete a WPS document."""
    result = await db.wps_documents.delete_one(
        {"wps_id": wps_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "WPS non trovato")
    return {"message": "WPS eliminato"}
