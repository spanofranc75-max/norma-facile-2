"""Norma Router — Maps ProductType to required validators and mandatory fields.

The frontend asks: 'What is required for a Cancello?' -> Router returns the list.
"""
from enum import Enum
from pydantic import BaseModel


class ProductType(str, Enum):
    CANCELLO = "cancello"
    PORTONE = "portone"
    FINESTRA = "finestra"
    PORTAFINESTRA = "portafinestra"
    TETTOIA = "tettoia"
    SCALA = "scala"
    SOPPALCO = "soppalco"
    RINGHIERA = "ringhiera"
    PENSILINA = "pensilina"
    RECINZIONE = "recinzione"


class RegulationStandard(str, Enum):
    EN_1090 = "EN 1090-1"
    EN_13241 = "EN 13241"
    EN_14351 = "EN 14351-1"


class RouteResult(BaseModel):
    product_type: str
    standards: list[str]
    validators: list[str]
    mandatory_fields: list[dict]
    optional_validators: list[str]
    notes: str


# ── Routing Table ────────────────────────────────────────────────

_GATE_ROUTE = {
    "standards": [RegulationStandard.EN_13241],
    "validators": ["CEValidator"],
    "mandatory_fields": [
        {"field": "product_type", "label": "Tipo Prodotto"},
        {"field": "mechanical_resistance", "label": "Resistenza Meccanica"},
        {"field": "safe_opening", "label": "Sicurezza di Apertura"},
        {"field": "durability", "label": "Durabilita"},
    ],
    "optional_validators": ["ThermalValidator"],
    "notes": "EN 13241 per cancelli e portoni. Calcolo termico opzionale per Ecobonus.",
}

_WINDOW_ROUTE = {
    "standards": [RegulationStandard.EN_14351],
    "validators": ["CEValidator", "ThermalValidator"],
    "mandatory_fields": [
        {"field": "product_type", "label": "Tipo Prodotto"},
        {"field": "durability", "label": "Durabilita"},
        {"field": "thermal_uw", "label": "Trasmittanza Termica Uw"},
    ],
    "optional_validators": [],
    "notes": "EN 14351-1 per finestre e portefinestre. Calcolo termico OBBLIGATORIO.",
}

_STRUCTURAL_ROUTE = {
    "standards": [RegulationStandard.EN_1090],
    "validators": ["CEValidator"],
    "mandatory_fields": [
        {"field": "product_type", "label": "Tipo Prodotto"},
        {"field": "execution_class", "label": "Classe di Esecuzione (EXC1-EXC4)"},
        {"field": "durability", "label": "Durabilita"},
        {"field": "reaction_to_fire", "label": "Reazione al Fuoco"},
    ],
    "optional_validators": [],
    "notes": "EN 1090-1 per strutture in acciaio. Classe di esecuzione obbligatoria.",
}

ROUTING_TABLE: dict[ProductType, dict] = {
    ProductType.CANCELLO: _GATE_ROUTE,
    ProductType.PORTONE: _GATE_ROUTE,
    ProductType.FINESTRA: _WINDOW_ROUTE,
    ProductType.PORTAFINESTRA: _WINDOW_ROUTE,
    ProductType.TETTOIA: _STRUCTURAL_ROUTE,
    ProductType.SCALA: _STRUCTURAL_ROUTE,
    ProductType.SOPPALCO: _STRUCTURAL_ROUTE,
    ProductType.RINGHIERA: _STRUCTURAL_ROUTE,
    ProductType.PENSILINA: _STRUCTURAL_ROUTE,
    ProductType.RECINZIONE: _STRUCTURAL_ROUTE,
}


class NormaRouter:
    """Routes product types to the correct regulation standards and validators."""

    @staticmethod
    def route(product_type: str) -> RouteResult:
        """Given a product type, return the required standards and fields."""
        try:
            pt = ProductType(product_type.lower())
        except ValueError:
            # Default to structural for unknown types
            pt = ProductType.TETTOIA

        entry = ROUTING_TABLE[pt]
        return RouteResult(
            product_type=pt.value,
            standards=[s.value for s in entry["standards"]],
            validators=entry["validators"],
            mandatory_fields=entry["mandatory_fields"],
            optional_validators=entry["optional_validators"],
            notes=entry["notes"],
        )

    @staticmethod
    def get_all_product_types() -> list[dict]:
        """Return all supported product types with their routing info."""
        results = []
        for pt in ProductType:
            entry = ROUTING_TABLE[pt]
            results.append({
                "id": pt.value,
                "label": pt.value.replace("_", " ").title(),
                "standards": [s.value for s in entry["standards"]],
                "has_thermal": "ThermalValidator" in entry["validators"],
            })
        return results
