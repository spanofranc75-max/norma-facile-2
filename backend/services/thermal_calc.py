"""Thermal transmittance calculator (Uw) per EN ISO 10077-1.

Formula: Uw = (Ag*Ug + Af*Uf + lg*Psi) / (Ag + Af)

Where:
  Ag = glass area (m2)
  Ug = glass U-value (W/m2K)
  Af = frame area (m2)
  Uf = frame U-value (W/m2K)
  lg = glass perimeter (m)
  Psi = linear thermal transmittance of spacer (W/mK)
"""
from typing import Optional
from pydantic import BaseModel


# ── Glass types database ─────────────────────────────────────────
GLASS_TYPES = [
    {"id": "singolo", "label": "Vetro singolo 4mm", "ug": 5.8, "thickness_mm": 4},
    {"id": "doppio_aria", "label": "Doppio vetro (aria)", "ug": 2.8, "thickness_mm": 24},
    {"id": "doppio_argon", "label": "Doppio vetro (argon)", "ug": 2.6, "thickness_mm": 24},
    {"id": "doppio_be", "label": "Doppio vetro basso emissivo", "ug": 1.1, "thickness_mm": 24},
    {"id": "doppio_be_argon", "label": "Doppio vetro basso emissivo + argon", "ug": 1.0, "thickness_mm": 24},
    {"id": "triplo_be_argon", "label": "Triplo vetro basso emissivo + argon", "ug": 0.6, "thickness_mm": 44},
    {"id": "pannello_sandwich", "label": "Pannello sandwich coibentato 40mm", "ug": 0.7, "thickness_mm": 40},
    {"id": "pannello_sandwich_60", "label": "Pannello sandwich coibentato 60mm", "ug": 0.5, "thickness_mm": 60},
]

# ── Frame/profile types database ─────────────────────────────────
FRAME_TYPES = [
    {"id": "acciaio_standard", "label": "Acciaio zincato standard", "uf": 5.9},
    {"id": "acciaio_taglio_termico", "label": "Acciaio con taglio termico", "uf": 3.2},
    {"id": "alluminio_standard", "label": "Alluminio standard", "uf": 5.7},
    {"id": "alluminio_taglio_termico", "label": "Alluminio con taglio termico", "uf": 2.8},
    {"id": "pvc", "label": "PVC multicamera", "uf": 1.3},
    {"id": "legno_morbido", "label": "Legno morbido (pino, abete)", "uf": 1.8},
    {"id": "legno_duro", "label": "Legno duro (rovere)", "uf": 2.0},
    {"id": "ferro_battuto", "label": "Ferro battuto / pieno", "uf": 7.0},
]

# ── Spacer types database ────────────────────────────────────────
SPACER_TYPES = [
    {"id": "alluminio", "label": "Canalina alluminio (standard)", "psi": 0.08},
    {"id": "warm_edge_plastica", "label": "Warm Edge plastica", "psi": 0.04},
    {"id": "warm_edge_acciaio", "label": "Warm Edge acciaio inox", "psi": 0.06},
    {"id": "super_warm", "label": "Super Warm Edge (Swisspacer)", "psi": 0.03},
    {"id": "nessuna", "label": "Nessuna (pannello pieno)", "psi": 0.00},
]

# ── Ecobonus zone limits (W/m2K) ─────────────────────────────────
ZONE_LIMITS = {
    "A": 3.20,
    "B": 3.20,
    "C": 2.10,
    "D": 1.80,
    "E": 1.30,
    "F": 1.00,
}


class ThermalInput(BaseModel):
    height_mm: float  # H in mm
    width_mm: float   # L in mm
    frame_width_mm: float = 80  # frame visible width in mm
    glass_id: str = "doppio_be_argon"
    frame_id: str = "acciaio_standard"
    spacer_id: str = "alluminio"


class ThermalResult(BaseModel):
    uw: float  # W/m2K
    ag: float  # glass area m2
    af: float  # frame area m2
    lg: float  # glass perimeter m
    ug: float  # glass U-value
    uf: float  # frame U-value
    psi: float  # spacer Psi
    total_area: float  # m2
    glass_label: str
    frame_label: str
    spacer_label: str
    ecobonus_eligible: dict  # zone -> eligible boolean
    warnings: list[str]


def _find_item(items, item_id, default_idx=0):
    for item in items:
        if item["id"] == item_id:
            return item
    return items[default_idx] if items else None


def calculate_uw(inp: ThermalInput) -> ThermalResult:
    """Calculate Uw using simplified EN ISO 10077-1 formula."""
    glass = _find_item(GLASS_TYPES, inp.glass_id)
    frame = _find_item(FRAME_TYPES, inp.frame_id)
    spacer = _find_item(SPACER_TYPES, inp.spacer_id)

    h_m = inp.height_mm / 1000
    w_m = inp.width_mm / 1000
    fw = inp.frame_width_mm / 1000  # frame width in m

    total_area = h_m * w_m

    # Glass dimensions (inside frame)
    glass_h = h_m - 2 * fw
    glass_w = w_m - 2 * fw

    if glass_h <= 0 or glass_w <= 0:
        glass_h = max(glass_h, 0.01)
        glass_w = max(glass_w, 0.01)

    ag = glass_h * glass_w  # glass area
    af = total_area - ag     # frame area
    lg = 2 * (glass_h + glass_w)  # glass perimeter

    ug = glass["ug"]
    uf = frame["uf"]
    psi = spacer["psi"]

    denominator = ag + af
    if denominator <= 0:
        denominator = 0.01

    uw = (ag * ug + af * uf + lg * psi) / denominator
    uw = round(uw, 2)

    # Check Ecobonus eligibility per zone
    ecobonus = {}
    for zone, limit in ZONE_LIMITS.items():
        ecobonus[zone] = uw <= limit

    warnings = []
    if not ecobonus.get("E", True):
        warnings.append(f"Uw = {uw} W/m2K supera il limite di 1.30 per Zona E. NON detraibile per Ecobonus.")
    if not ecobonus.get("F", True):
        warnings.append(f"Uw = {uw} W/m2K supera il limite di 1.00 per Zona F.")
    if uw > 3.2:
        warnings.append(f"Uw = {uw} W/m2K supera il limite di tutte le zone climatiche.")

    return ThermalResult(
        uw=uw,
        ag=round(ag, 3),
        af=round(af, 3),
        lg=round(lg, 3),
        ug=ug,
        uf=uf,
        psi=psi,
        total_area=round(total_area, 3),
        glass_label=glass["label"],
        frame_label=frame["label"],
        spacer_label=spacer["label"],
        ecobonus_eligible=ecobonus,
        warnings=warnings,
    )
