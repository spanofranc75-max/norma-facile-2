"""Thermal transmittance calculator — Thin wrapper over core.engine.thermal.

Backward-compatible: existing imports from services.thermal_calc still work.
All logic lives in core.engine.thermal (Single Source of Truth).
"""
from core.engine.thermal import (
    ThermalValidator,
    ThermalInput,
    ThermalResult,
    GLASS_TYPES,
    FRAME_TYPES,
    SPACER_TYPES,
)
from core.engine.climate_zones import ZONE_LIMITS as _ENGINE_LIMITS

# Re-export for backward compatibility (dict[str, float] format)
ZONE_LIMITS = {z.value: lim for z, lim in _ENGINE_LIMITS.items()}


def calculate_uw(inp: ThermalInput) -> ThermalResult:
    """Backward-compatible wrapper. Delegates to ThermalValidator."""
    return ThermalValidator.calculate(inp)
