"""Core Engine — NormaConfig Store + Universal Validation + Calculation Engine.

Every norm is a NormaConfig object that injects rules into a universal validation engine.
Adding a new norm = adding a new JSON config. Zero code changes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum
import uuid
import math
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from core.engine.climate_zones import ZONE_LIMITS, ClimateZone
from services.fascicolo_generator import generate_fascicolo_pdf, generate_fascicolo_zip
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/engine", tags=["core_engine"])


# ══════════════════════════════════════════════════════════════════
# 1. NORMA CONFIG — Data-driven norm definitions
# ══════════════════════════════════════════════════════════════════

class PerformanceReq(BaseModel):
    code: str
    label: str
    calculation_method: Optional[str] = None
    test_reference: Optional[str] = None
    threshold_by_zone: bool = False
    mandatory: bool = True
    unit: Optional[str] = None
    description: Optional[str] = None


class ValidationRule(BaseModel):
    rule_id: str = ""
    condition: str  # e.g. "product_height > 2500"
    action: str  # e.g. "BLOCK_CE_MARKING", "WARN", "SUGGEST"
    message: str = ""
    severity: str = "error"  # error, warning, info


class MandatoryField(BaseModel):
    field: str
    label: str
    type: str = "text"  # text, number, select, boolean
    options: Optional[List[str]] = None
    default: Optional[Any] = None
    description: Optional[str] = None


class NormaConfigCreate(BaseModel):
    norma_id: str = Field(..., min_length=3, max_length=50)
    title: str
    standard_ref: str  # e.g. "EN 1090-1", "EN 13241"
    product_types: List[str] = []  # Which product types this norm covers
    required_performances: List[PerformanceReq] = []
    mandatory_fields: List[MandatoryField] = []
    validation_rules: List[ValidationRule] = []
    calculation_methods: List[str] = []  # e.g. ["ISO_10077_1", "EN_12210"]
    notes: Optional[str] = None
    active: bool = True


class NormaConfigUpdate(BaseModel):
    title: Optional[str] = None
    product_types: Optional[List[str]] = None
    required_performances: Optional[List[PerformanceReq]] = None
    mandatory_fields: Optional[List[MandatoryField]] = None
    validation_rules: Optional[List[ValidationRule]] = None
    calculation_methods: Optional[List[str]] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


# ── NormaConfig CRUD ─────────────────────────────────────────────

@router.get("/norme")
async def list_norme(
    active_only: bool = True,
    user: dict = Depends(get_current_user)
):
    """List all norm configurations."""
    query = {}
    if active_only:
        query["active"] = True
    cursor = db.norme_config.find(query, {"_id": 0}).sort("norma_id", 1)
    items = await cursor.to_list(length=100)
    return {"norme": items, "total": len(items)}


@router.get("/norme/{norma_id}")
async def get_norma(
    norma_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a single norm configuration."""
    item = await db.norme_config.find_one({"norma_id": norma_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, f"Norma '{norma_id}' non trovata")
    return item


@router.post("/norme", status_code=201)
async def create_norma(
    data: NormaConfigCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new norm configuration."""
    existing = await db.norme_config.find_one({"norma_id": data.norma_id}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Norma '{data.norma_id}' già esistente")

    now = datetime.now(timezone.utc)
    doc = {
        **data.model_dump(),
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.norme_config.insert_one(doc)
    created = await db.norme_config.find_one({"norma_id": data.norma_id}, {"_id": 0})
    return created


@router.put("/norme/{norma_id}")
async def update_norma(
    norma_id: str,
    data: NormaConfigUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a norm configuration."""
    existing = await db.norme_config.find_one({"norma_id": norma_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, f"Norma '{norma_id}' non trovata")

    update_dict = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    # Serialize nested models
    for key in ["required_performances", "mandatory_fields", "validation_rules"]:
        if key in update_dict:
            update_dict[key] = [
                item.model_dump() if hasattr(item, 'model_dump') else item
                for item in update_dict[key]
            ]
    update_dict["updated_at"] = datetime.now(timezone.utc)
    await db.norme_config.update_one({"norma_id": norma_id}, {"$set": update_dict})
    updated = await db.norme_config.find_one({"norma_id": norma_id}, {"_id": 0})
    return updated


@router.delete("/norme/{norma_id}")
async def delete_norma(
    norma_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a norm configuration."""
    result = await db.norme_config.delete_one({"norma_id": norma_id})
    if result.deleted_count == 0:
        raise HTTPException(404, f"Norma '{norma_id}' non trovata")
    return {"message": f"Norma '{norma_id}' eliminata"}


@router.post("/norme/seed")
async def seed_norme(user: dict = Depends(get_current_user)):
    """Seed the database with standard Italian norms."""
    now = datetime.now(timezone.utc)
    norme = _get_seed_norme()
    created = 0
    for norma in norme:
        existing = await db.norme_config.find_one({"norma_id": norma["norma_id"]}, {"_id": 0})
        if not existing:
            norma["created_by"] = user["user_id"]
            norma["created_at"] = now
            norma["updated_at"] = now
            await db.norme_config.insert_one(norma)
            created += 1
    return {"message": f"Seed completato: {created} norme create", "created": created}


# ══════════════════════════════════════════════════════════════════
# 2. COMPONENTI — Vetri, Telai, Distanziatori, Produttori
# ══════════════════════════════════════════════════════════════════

class ComponentType(str, Enum):
    VETRO = "vetro"
    TELAIO = "telaio"
    DISTANZIATORE = "distanziatore"


class ComponentCreate(BaseModel):
    codice: str
    label: str
    tipo: ComponentType
    produttore: Optional[str] = None
    produttore_id: Optional[str] = None
    # Thermal properties
    ug: Optional[float] = None  # Glass Ug
    uf: Optional[float] = None  # Frame Uf
    psi: Optional[float] = None  # Spacer Psi
    thickness_mm: Optional[float] = None
    # Extra
    specs: Optional[dict] = None
    note: Optional[str] = None


class ComponentUpdate(BaseModel):
    label: Optional[str] = None
    produttore: Optional[str] = None
    produttore_id: Optional[str] = None
    ug: Optional[float] = None
    uf: Optional[float] = None
    psi: Optional[float] = None
    thickness_mm: Optional[float] = None
    specs: Optional[dict] = None
    note: Optional[str] = None


@router.get("/componenti")
async def list_componenti(
    tipo: Optional[ComponentType] = None,
    q: Optional[str] = None,
    produttore: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List components (glass, frames, spacers) with optional filters."""
    query = {}
    if tipo:
        query["tipo"] = tipo.value
    if produttore:
        query["produttore"] = {"$regex": produttore, "$options": "i"}
    if q:
        query["$or"] = [
            {"codice": {"$regex": q, "$options": "i"}},
            {"label": {"$regex": q, "$options": "i"}},
            {"produttore": {"$regex": q, "$options": "i"}},
        ]
    cursor = db.componenti.find(query, {"_id": 0}).sort([("tipo", 1), ("codice", 1)])
    items = await cursor.to_list(length=200)
    return {"componenti": items, "total": len(items)}


@router.get("/componenti/{comp_id}")
async def get_componente(comp_id: str, user: dict = Depends(get_current_user)):
    """Get a single component."""
    item = await db.componenti.find_one({"comp_id": comp_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Componente non trovato")
    return item


@router.post("/componenti", status_code=201)
async def create_componente(
    data: ComponentCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new component."""
    existing = await db.componenti.find_one({"codice": data.codice, "tipo": data.tipo.value}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"Componente '{data.codice}' tipo '{data.tipo.value}' già esistente")

    now = datetime.now(timezone.utc)
    doc = {
        "comp_id": f"comp_{uuid.uuid4().hex[:10]}",
        **data.model_dump(),
        "tipo": data.tipo.value,
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.componenti.insert_one(doc)
    created = await db.componenti.find_one({"comp_id": doc["comp_id"]}, {"_id": 0})
    return created


@router.put("/componenti/{comp_id}")
async def update_componente(
    comp_id: str,
    data: ComponentUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a component."""
    existing = await db.componenti.find_one({"comp_id": comp_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Componente non trovato")

    update_dict = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc)
    await db.componenti.update_one({"comp_id": comp_id}, {"$set": update_dict})
    updated = await db.componenti.find_one({"comp_id": comp_id}, {"_id": 0})
    return updated


@router.delete("/componenti/{comp_id}")
async def delete_componente(comp_id: str, user: dict = Depends(get_current_user)):
    """Delete a component."""
    result = await db.componenti.delete_one({"comp_id": comp_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Componente non trovato")
    return {"message": "Componente eliminato"}


@router.post("/componenti/seed")
async def seed_componenti(user: dict = Depends(get_current_user)):
    """Seed with standard glass, frame, spacer types."""
    now = datetime.now(timezone.utc)
    components = _get_seed_componenti()
    created = 0
    for comp in components:
        existing = await db.componenti.find_one(
            {"codice": comp["codice"], "tipo": comp["tipo"]}, {"_id": 0}
        )
        if not existing:
            comp["comp_id"] = f"comp_{uuid.uuid4().hex[:10]}"
            comp["created_by"] = user["user_id"]
            comp["created_at"] = now
            comp["updated_at"] = now
            await db.componenti.insert_one(comp)
            created += 1
    return {"message": f"Seed completato: {created} componenti creati", "created": created}


# ══════════════════════════════════════════════════════════════════
# 3. UNIVERSAL VALIDATION + CALCULATION ENGINE
# ══════════════════════════════════════════════════════════════════

class ConfigureRequest(BaseModel):
    """Request to configure a product — the engine returns what's needed."""
    product_type: str  # e.g. "cancello", "finestra"


class CalculateRequest(BaseModel):
    """Request to calculate performance values."""
    norma_id: str
    product_type: str
    # Dimensions
    height_mm: float = 0
    width_mm: float = 0
    frame_width_mm: float = 80
    # Component selections
    vetro_id: Optional[str] = None  # comp_id of glass
    telaio_id: Optional[str] = None  # comp_id of frame
    distanziatore_id: Optional[str] = None  # comp_id of spacer
    # Climate zone
    zona_climatica: Optional[str] = None  # A, B, C, D, E, F
    # Additional specs
    specs: dict = {}


class ValidateRequest(BaseModel):
    """Request to validate a product configuration against a norm."""
    norma_id: str
    product_type: str
    specs: dict = {}
    calculated_values: dict = {}


@router.post("/configure")
async def configure_product(
    req: ConfigureRequest,
    user: dict = Depends(get_current_user)
):
    """Given a product type, return all required norms, fields, and available components."""
    product = req.product_type.lower()

    # Find applicable norms
    norme = await db.norme_config.find(
        {"product_types": product, "active": True},
        {"_id": 0}
    ).to_list(length=20)

    if not norme:
        # Fallback: try broad match
        norme = await db.norme_config.find(
            {"product_types": {"$regex": product, "$options": "i"}, "active": True},
            {"_id": 0}
        ).to_list(length=20)

    # Get available components
    vetri = await db.componenti.find({"tipo": "vetro"}, {"_id": 0}).to_list(100)
    telai = await db.componenti.find({"tipo": "telaio"}, {"_id": 0}).to_list(100)
    distanziatori = await db.componenti.find({"tipo": "distanziatore"}, {"_id": 0}).to_list(100)

    # Aggregate all mandatory fields and performances
    all_fields = []
    all_performances = []
    all_calculations = []
    has_thermal = False

    for norma in norme:
        all_fields.extend(norma.get("mandatory_fields", []))
        all_performances.extend(norma.get("required_performances", []))
        all_calculations.extend(norma.get("calculation_methods", []))
        if "ISO_10077_1" in norma.get("calculation_methods", []):
            has_thermal = True

    # Zone limits for thermal
    zone_limits = {z.value: lim for z, lim in ZONE_LIMITS.items()} if has_thermal else {}

    return {
        "product_type": product,
        "norme": norme,
        "mandatory_fields": all_fields,
        "required_performances": all_performances,
        "calculation_methods": all_calculations,
        "has_thermal_calc": has_thermal,
        "zone_limits": zone_limits,
        "componenti": {
            "vetri": vetri,
            "telai": telai,
            "distanziatori": distanziatori,
        },
    }


@router.post("/calculate")
async def calculate_performance(
    req: CalculateRequest,
    user: dict = Depends(get_current_user)
):
    """Run the calculation engine for a product configuration."""
    norma = await db.norme_config.find_one({"norma_id": req.norma_id}, {"_id": 0})
    if not norma:
        raise HTTPException(404, f"Norma '{req.norma_id}' non trovata")

    results = {}
    warnings = []
    suggestions = []

    calc_methods = norma.get("calculation_methods", [])

    # ── ISO 10077-1: Thermal Transmittance Uw ──
    if "ISO_10077_1" in calc_methods and req.height_mm > 0 and req.width_mm > 0:
        uw_result = await _calc_uw(req)
        results["thermal"] = uw_result
        warnings.extend(uw_result.get("warnings", []))
        suggestions.extend(uw_result.get("suggestions", []))

    # ── EN 12210: Air Permeability (simplified classification) ──
    if "EN_12210" in calc_methods:
        results["air_permeability"] = _classify_air_permeability(req.specs)

    # ── EN 12211: Wind Resistance (simplified classification) ──
    if "EN_12211" in calc_methods:
        results["wind_resistance"] = _classify_wind_resistance(req.specs)

    # ── EN 12208: Water Tightness (simplified classification) ──
    if "EN_12208" in calc_methods:
        results["water_tightness"] = _classify_water_tightness(req.specs)

    # ── Run validation rules ──
    validation = _run_validation_rules(
        norma.get("validation_rules", []),
        {**req.specs, "product_height": req.height_mm, "product_width": req.width_mm},
        results
    )

    return {
        "norma_id": req.norma_id,
        "product_type": req.product_type,
        "results": results,
        "validation": validation,
        "warnings": warnings,
        "suggestions": suggestions,
        "compliant": validation["compliant"],
    }


@router.post("/validate")
async def validate_product(
    req: ValidateRequest,
    user: dict = Depends(get_current_user)
):
    """Validate a product against a norm's rules."""
    norma = await db.norme_config.find_one({"norma_id": req.norma_id}, {"_id": 0})
    if not norma:
        raise HTTPException(404, f"Norma '{req.norma_id}' non trovata")

    # Check mandatory fields
    errors = []
    for field in norma.get("mandatory_fields", []):
        val = req.specs.get(field["field"])
        if val is None or (isinstance(val, str) and val.strip() == ""):
            errors.append({"field": field["field"], "message": f"{field['label']} obbligatorio"})

    # Run validation rules
    combined = {**req.specs, **req.calculated_values}
    rule_results = _run_validation_rules(norma.get("validation_rules", []), combined, req.calculated_values)

    return {
        "norma_id": req.norma_id,
        "field_errors": errors,
        "rule_results": rule_results,
        "compliant": len(errors) == 0 and rule_results["compliant"],
    }


# ══════════════════════════════════════════════════════════════════
# INTERNAL: Calculation Methods
# ══════════════════════════════════════════════════════════════════

async def _calc_uw(req: CalculateRequest) -> dict:
    """Calculate Uw using ISO 10077-1 formula.
    Uw = (Ag*Ug + Af*Uf + lg*Ψg) / (Ag + Af)
    """
    # Get component data from DB
    vetro = None
    telaio = None
    distanziatore = None

    if req.vetro_id:
        vetro = await db.componenti.find_one({"comp_id": req.vetro_id}, {"_id": 0})
    if req.telaio_id:
        telaio = await db.componenti.find_one({"comp_id": req.telaio_id}, {"_id": 0})
    if req.distanziatore_id:
        distanziatore = await db.componenti.find_one({"comp_id": req.distanziatore_id}, {"_id": 0})

    # Fallback to specs if no component selected
    ug = (vetro or {}).get("ug") or req.specs.get("ug", 2.8)
    uf = (telaio or {}).get("uf") or req.specs.get("uf", 5.9)
    psi_val = (distanziatore or {}).get("psi") or req.specs.get("psi", 0.08)

    h_m = req.height_mm / 1000
    w_m = req.width_mm / 1000
    fw = req.frame_width_mm / 1000

    total_area = h_m * w_m
    glass_h = max(h_m - 2 * fw, 0.01)
    glass_w = max(w_m - 2 * fw, 0.01)

    ag = glass_h * glass_w
    af = total_area - ag
    lg = 2 * (glass_h + glass_w)

    denominator = max(ag + af, 0.01)
    uw = round((ag * ug + af * uf + lg * psi_val) / denominator, 2)

    # Check compliance per zone
    zone_compliance = {}
    for zone, limit in ZONE_LIMITS.items():
        zone_compliance[zone.value] = {
            "limit": limit,
            "compliant": uw <= limit,
            "delta": round(limit - uw, 2),
        }

    # Generate suggestions
    warnings = []
    suggestions = []
    zona = req.zona_climatica
    if zona:
        try:
            zone_enum = ClimateZone(zona.upper())
            limit = ZONE_LIMITS.get(zone_enum, 999)
            if uw > limit:
                warnings.append(f"Uw = {uw} W/m²K supera il limite di {limit} per Zona {zona}")
                # Suggest better glass
                if ug > 1.5:
                    suggestions.append({
                        "type": "UPGRADE_GLASS",
                        "message": f"Cambia il vetro con uno basso emissivo + argon (Ug ≤ 1.0) per ottenere l'Ecobonus in Zona {zona}",
                        "priority": "high",
                    })
                if psi_val > 0.05:
                    suggestions.append({
                        "type": "UPGRADE_SPACER",
                        "message": "Usa un distanziatore Warm Edge (Ψ ≤ 0.04) per migliorare la prestazione termica",
                        "priority": "medium",
                    })
        except ValueError:
            pass

    ecobonus = any(zc["compliant"] for zc in zone_compliance.values())

    return {
        "uw": uw,
        "ag": round(ag, 4),
        "af": round(af, 4),
        "lg": round(lg, 4),
        "ug": ug,
        "uf": uf,
        "psi": psi_val,
        "total_area_m2": round(total_area, 4),
        "vetro_label": (vetro or {}).get("label", "Personalizzato"),
        "telaio_label": (telaio or {}).get("label", "Personalizzato"),
        "distanziatore_label": (distanziatore or {}).get("label", "Personalizzato"),
        "zone_compliance": zone_compliance,
        "ecobonus_eligible": ecobonus,
        "warnings": warnings,
        "suggestions": suggestions,
    }


def _classify_air_permeability(specs: dict) -> dict:
    """EN 12210 — Air permeability classification."""
    classe = specs.get("air_class", 0)
    classes = {
        0: {"label": "Nessuna prestazione dichiarata", "ref_pressure_pa": 0},
        1: {"label": "Classe 1", "ref_pressure_pa": 150},
        2: {"label": "Classe 2", "ref_pressure_pa": 300},
        3: {"label": "Classe 3", "ref_pressure_pa": 600},
        4: {"label": "Classe 4", "ref_pressure_pa": 600},
    }
    return classes.get(int(classe), classes[0])


def _classify_wind_resistance(specs: dict) -> dict:
    """EN 12211 — Wind load resistance."""
    classe = specs.get("wind_class", "")
    classes = {
        "1": {"label": "Classe 1 (400 Pa)", "pressure_pa": 400},
        "2": {"label": "Classe 2 (800 Pa)", "pressure_pa": 800},
        "3": {"label": "Classe 3 (1200 Pa)", "pressure_pa": 1200},
        "4": {"label": "Classe 4 (1600 Pa)", "pressure_pa": 1600},
        "5": {"label": "Classe 5 (2000 Pa)", "pressure_pa": 2000},
    }
    return classes.get(str(classe), {"label": "Non classificato", "pressure_pa": 0})


def _classify_water_tightness(specs: dict) -> dict:
    """EN 12208 — Water tightness."""
    classe = specs.get("water_class", "")
    classes = {
        "1A": {"label": "Classe 1A (0 Pa)", "pressure_pa": 0},
        "2A": {"label": "Classe 2A (50 Pa)", "pressure_pa": 50},
        "3A": {"label": "Classe 3A (100 Pa)", "pressure_pa": 100},
        "4A": {"label": "Classe 4A (150 Pa)", "pressure_pa": 150},
        "5A": {"label": "Classe 5A (200 Pa)", "pressure_pa": 200},
        "6A": {"label": "Classe 6A (250 Pa)", "pressure_pa": 250},
        "7A": {"label": "Classe 7A (300 Pa)", "pressure_pa": 300},
        "E750": {"label": "E750 (750 Pa)", "pressure_pa": 750},
    }
    return classes.get(str(classe), {"label": "Non classificato", "pressure_pa": 0})


def _run_validation_rules(rules: list, context: dict, calculated: dict) -> dict:
    """Run validation rules from NormaConfig against product data."""
    errors = []
    warnings = []
    blocked = False

    for rule in rules:
        condition = rule.get("condition", "")
        action = rule.get("action", "WARN")
        message = rule.get("message", condition)

        try:
            # Safe evaluation of simple conditions
            result = _eval_condition(condition, {**context, **calculated})
            if result:
                entry = {"rule": condition, "message": message, "action": action}
                if action == "BLOCK_CE_MARKING":
                    errors.append(entry)
                    blocked = True
                elif action == "WARN":
                    warnings.append(entry)
                elif action == "SUGGEST":
                    warnings.append(entry)
        except Exception as e:
            logger.warning(f"Rule evaluation failed: {condition} — {str(e)}")

    return {
        "compliant": not blocked and len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "blocked": blocked,
    }


def _eval_condition(condition: str, context: dict) -> bool:
    """Safely evaluate a simple condition string against context values."""
    # Support basic comparisons: "field > value", "field < value", "field == value"
    import re
    patterns = [
        (r'(\w+)\s*>\s*(\d+(?:\.\d+)?)', lambda m: _get_num(context, m.group(1)) > float(m.group(2))),
        (r'(\w+)\s*<\s*(\d+(?:\.\d+)?)', lambda m: _get_num(context, m.group(1)) < float(m.group(2))),
        (r'(\w+)\s*>=\s*(\d+(?:\.\d+)?)', lambda m: _get_num(context, m.group(1)) >= float(m.group(2))),
        (r'(\w+)\s*<=\s*(\d+(?:\.\d+)?)', lambda m: _get_num(context, m.group(1)) <= float(m.group(2))),
        (r'(\w+)\s*==\s*"?([^"]+)"?', lambda m: str(context.get(m.group(1), "")) == m.group(2).strip()),
        (r'(\w+)\s*!=\s*"?([^"]+)"?', lambda m: str(context.get(m.group(1), "")) != m.group(2).strip()),
    ]
    for pattern, evaluator in patterns:
        match = re.match(pattern, condition.strip())
        if match:
            return evaluator(match)
    return False


def _get_num(ctx: dict, key: str) -> float:
    """Get numeric value from context."""
    val = ctx.get(key, 0)
    if isinstance(val, dict):
        val = val.get("uw", val.get("value", 0))
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ══════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════

def _get_seed_norme() -> list:
    """Standard Italian norms seed data."""
    return [
        {
            "norma_id": "EN_1090_1",
            "title": "Strutture di acciaio e alluminio — Marcatura CE",
            "standard_ref": "EN 1090-1",
            "product_types": ["tettoia", "scala", "soppalco", "ringhiera", "pensilina", "recinzione"],
            "required_performances": [
                {"code": "EXEC_CLASS", "label": "Classe di Esecuzione", "mandatory": True, "unit": "", "description": "EXC1-EXC4 secondo EN 1090-2"},
                {"code": "DURABILITY", "label": "Durabilità", "mandatory": True, "description": "Protezione dalla corrosione"},
                {"code": "FIRE_REACTION", "label": "Reazione al Fuoco", "mandatory": True, "description": "Classificazione secondo EN 13501-1"},
                {"code": "DANGEROUS_SUBST", "label": "Sostanze Pericolose", "mandatory": False, "description": "Dichiarazione NPD o specifica"},
            ],
            "mandatory_fields": [
                {"field": "product_type", "label": "Tipo Prodotto", "type": "text"},
                {"field": "execution_class", "label": "Classe di Esecuzione", "type": "select", "options": ["EXC1", "EXC2", "EXC3", "EXC4"]},
                {"field": "durability", "label": "Durabilità", "type": "text"},
                {"field": "reaction_to_fire", "label": "Reazione al Fuoco", "type": "text"},
            ],
            "validation_rules": [
                {"rule_id": "R1", "condition": "execution_class == EXC4", "action": "WARN", "message": "EXC4 richiede controlli di qualità ISO 3834-2", "severity": "warning"},
            ],
            "calculation_methods": [],
            "notes": "Norma per strutture in acciaio e alluminio. Richiede FPC (Factory Production Control).",
            "active": True,
        },
        {
            "norma_id": "EN_13241",
            "title": "Cancelli e porte industriali — Marcatura CE",
            "standard_ref": "EN 13241",
            "product_types": ["cancello", "portone"],
            "required_performances": [
                {"code": "MECH_RESIST", "label": "Resistenza Meccanica", "mandatory": True, "description": "Resistenza a impatto, cicli apertura/chiusura"},
                {"code": "SAFE_OPENING", "label": "Sicurezza di Apertura", "mandatory": True, "description": "Dispositivi di sicurezza EN 12453"},
                {"code": "DURABILITY", "label": "Durabilità", "mandatory": True, "description": "N. cicli e protezione corrosione"},
                {"code": "UW_VALUE", "label": "Trasmittanza Termica", "calculation_method": "ISO_10077_1", "threshold_by_zone": True, "mandatory": False, "unit": "W/m²K", "description": "Opzionale per Ecobonus"},
                {"code": "AIR_PERMEABILITY", "label": "Permeabilità all'aria", "test_reference": "EN_1026", "mandatory": False, "description": "Classe 1-4 secondo EN 12207"},
            ],
            "mandatory_fields": [
                {"field": "product_type", "label": "Tipo Prodotto", "type": "text"},
                {"field": "mechanical_resistance", "label": "Resistenza Meccanica", "type": "text"},
                {"field": "safe_opening", "label": "Sicurezza di Apertura", "type": "text"},
                {"field": "durability", "label": "Durabilità", "type": "text"},
            ],
            "validation_rules": [
                {"rule_id": "R1", "condition": "product_height > 2500", "action": "WARN", "message": "Altezza > 2.5m: verificare cerniere aggiuntive e rinforzi strutturali", "severity": "warning"},
                {"rule_id": "R2", "condition": "product_height > 4000", "action": "BLOCK_CE_MARKING", "message": "Altezza > 4m: richiede calcolo strutturale specifico secondo EN 12424", "severity": "error"},
            ],
            "calculation_methods": ["ISO_10077_1", "EN_12210"],
            "notes": "Cancelli motorizzati: obbligatorio rispetto EN 12453 (sicurezza).",
            "active": True,
        },
        {
            "norma_id": "UNI_EN_14351_1",
            "title": "Finestre e porte esterne pedonali — Marcatura CE",
            "standard_ref": "EN 14351-1",
            "product_types": ["finestra", "portafinestra"],
            "required_performances": [
                {"code": "UW_VALUE", "label": "Trasmittanza Termica", "calculation_method": "ISO_10077_1", "threshold_by_zone": True, "mandatory": True, "unit": "W/m²K", "description": "OBBLIGATORIO per legge. Limiti per zona climatica."},
                {"code": "AIR_PERMEABILITY", "label": "Permeabilità all'aria", "test_reference": "EN_1026", "mandatory": True, "unit": "Classe", "description": "Test EN 1026, classificazione EN 12207"},
                {"code": "WATER_TIGHTNESS", "label": "Tenuta all'acqua", "test_reference": "EN_1027", "mandatory": True, "unit": "Classe", "description": "Test EN 1027, classificazione EN 12208"},
                {"code": "WIND_RESISTANCE", "label": "Resistenza al vento", "test_reference": "EN_12211", "mandatory": True, "unit": "Classe", "description": "Test EN 12211, classificazione EN 12210"},
                {"code": "DURABILITY", "label": "Durabilità", "mandatory": True, "description": "Protezione dalla corrosione e invecchiamento"},
                {"code": "SOUND_INSULATION", "label": "Isolamento acustico", "mandatory": False, "unit": "dB", "description": "Rw secondo EN ISO 10140"},
            ],
            "mandatory_fields": [
                {"field": "product_type", "label": "Tipo Prodotto", "type": "text"},
                {"field": "durability", "label": "Durabilità", "type": "text"},
                {"field": "air_class", "label": "Classe Permeabilità Aria", "type": "select", "options": ["1", "2", "3", "4"]},
                {"field": "water_class", "label": "Classe Tenuta Acqua", "type": "select", "options": ["1A", "2A", "3A", "4A", "5A", "6A", "7A", "E750"]},
                {"field": "wind_class", "label": "Classe Resistenza Vento", "type": "select", "options": ["1", "2", "3", "4", "5"]},
            ],
            "validation_rules": [
                {"rule_id": "R1", "condition": "product_height > 2500", "action": "WARN", "message": "Altezza > 2.5m: richiedere cerniera aggiuntiva e verificare classe vento", "severity": "warning"},
                {"rule_id": "R2", "condition": "product_width > 1800", "action": "WARN", "message": "Larghezza > 1.8m: verificare rinforzi traverso e deformazione telaio", "severity": "warning"},
            ],
            "calculation_methods": ["ISO_10077_1", "EN_12210", "EN_12211", "EN_12208"],
            "notes": "Calcolo termico OBBLIGATORIO. Uw deve rispettare DM 26/06/2015 per zona climatica del cantiere.",
            "active": True,
        },
    ]


def _get_seed_componenti() -> list:
    """Standard glass, frame, spacer seed data."""
    vetri = [
        {"codice": "V-SING-4", "label": "Vetro singolo 4mm", "tipo": "vetro", "ug": 5.8, "thickness_mm": 4, "produttore": "Generico"},
        {"codice": "V-DV-ARIA", "label": "Doppio vetro (aria)", "tipo": "vetro", "ug": 2.8, "thickness_mm": 24, "produttore": "Generico"},
        {"codice": "V-DV-ARGON", "label": "Doppio vetro (argon)", "tipo": "vetro", "ug": 2.6, "thickness_mm": 24, "produttore": "Generico"},
        {"codice": "V-DV-BE", "label": "Doppio vetro basso emissivo", "tipo": "vetro", "ug": 1.1, "thickness_mm": 24, "produttore": "Generico"},
        {"codice": "V-DV-BE-AR", "label": "Doppio vetro basso emissivo + argon", "tipo": "vetro", "ug": 1.0, "thickness_mm": 24, "produttore": "Generico"},
        {"codice": "V-TV-BE-AR", "label": "Triplo vetro basso emissivo + argon", "tipo": "vetro", "ug": 0.6, "thickness_mm": 44, "produttore": "Generico"},
        {"codice": "V-PAN-40", "label": "Pannello sandwich coibentato 40mm", "tipo": "vetro", "ug": 0.7, "thickness_mm": 40, "produttore": "Generico"},
        {"codice": "V-PAN-60", "label": "Pannello sandwich coibentato 60mm", "tipo": "vetro", "ug": 0.5, "thickness_mm": 60, "produttore": "Generico"},
    ]
    telai = [
        {"codice": "T-ACC-STD", "label": "Acciaio zincato standard", "tipo": "telaio", "uf": 5.9, "produttore": "Generico"},
        {"codice": "T-ACC-TT", "label": "Acciaio con taglio termico", "tipo": "telaio", "uf": 3.2, "produttore": "Generico"},
        {"codice": "T-ALU-STD", "label": "Alluminio standard", "tipo": "telaio", "uf": 5.7, "produttore": "Generico"},
        {"codice": "T-ALU-TT", "label": "Alluminio con taglio termico", "tipo": "telaio", "uf": 2.8, "produttore": "Generico"},
        {"codice": "T-PVC", "label": "PVC multicamera", "tipo": "telaio", "uf": 1.3, "produttore": "Generico"},
        {"codice": "T-LEGNO-M", "label": "Legno morbido (pino, abete)", "tipo": "telaio", "uf": 1.8, "produttore": "Generico"},
        {"codice": "T-LEGNO-D", "label": "Legno duro (rovere)", "tipo": "telaio", "uf": 2.0, "produttore": "Generico"},
        {"codice": "T-FERRO", "label": "Ferro battuto / pieno", "tipo": "telaio", "uf": 7.0, "produttore": "Generico"},
    ]
    distanziatori = [
        {"codice": "D-ALU", "label": "Canalina alluminio (standard)", "tipo": "distanziatore", "psi": 0.08, "produttore": "Generico"},
        {"codice": "D-WE-PL", "label": "Warm Edge plastica", "tipo": "distanziatore", "psi": 0.04, "produttore": "Generico"},
        {"codice": "D-WE-INOX", "label": "Warm Edge acciaio inox", "tipo": "distanziatore", "psi": 0.06, "produttore": "Generico"},
        {"codice": "D-SWE", "label": "Super Warm Edge (Swisspacer)", "tipo": "distanziatore", "psi": 0.03, "produttore": "Generico"},
        {"codice": "D-NONE", "label": "Nessuna (pannello pieno)", "tipo": "distanziatore", "psi": 0.00, "produttore": "Generico"},
    ]
    return vetri + telai + distanziatori
