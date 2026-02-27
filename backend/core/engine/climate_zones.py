"""Italian Climate Zones — ENEA/Ecobonus thermal limits.

Source: Draft 2025/2026 (D.M. Requisiti Minimi aggiornamento).
Single point of update when regulations change.
"""
from enum import Enum


class ClimateZone(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


# Maximum Uw (W/m2K) for Ecobonus deduction per climate zone.
# Updated to Draft 2025/2026 restrictive limits.
ZONE_LIMITS: dict[ClimateZone, float] = {
    ClimateZone.A: 2.60,
    ClimateZone.B: 2.60,
    ClimateZone.C: 1.75,
    ClimateZone.D: 1.67,
    ClimateZone.E: 1.30,
    ClimateZone.F: 1.00,
}


def get_limit(zone: ClimateZone | str) -> float:
    """Get the Uw limit for a climate zone."""
    if isinstance(zone, str):
        zone = ClimateZone(zone)
    return ZONE_LIMITS[zone]


def check_compliance(uw: float, zone: ClimateZone | str) -> dict:
    """Check if Uw complies with the zone limit.

    Returns: {"valid": bool, "limit": float, "zone": str, "message": str}
    """
    if isinstance(zone, str):
        zone = ClimateZone(zone)
    limit = ZONE_LIMITS[zone]
    valid = uw <= limit
    if valid:
        message = f"Conforme Ecobonus Zona {zone.value} (Uw {uw} <= {limit} W/m2K)"
    else:
        message = f"NON CONFORME Zona {zone.value}! Uw {uw} supera il limite di {limit} W/m2K"
    return {"valid": valid, "limit": limit, "zone": zone.value, "message": message}
