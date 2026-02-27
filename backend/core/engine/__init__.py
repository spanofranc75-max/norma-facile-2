"""Norma Core Engine — Single Source of Truth for Italian building regulations.

All compliance logic lives here. If the law changes, update ONE file.
"""
from core.engine.climate_zones import ClimateZone, ZONE_LIMITS
from core.engine.thermal import ThermalValidator, ThermalInput, ThermalResult
from core.engine.safety import SafetyValidator
from core.engine.ce import CEValidator, CEValidationResult

__all__ = [
    "ClimateZone", "ZONE_LIMITS",
    "ThermalValidator", "ThermalInput", "ThermalResult",
    "SafetyValidator",
    "CEValidator", "CEValidationResult",
]
