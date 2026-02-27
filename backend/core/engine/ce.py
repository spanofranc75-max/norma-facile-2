"""CE Validator — EN 1090-1, EN 13241, EN 14351-1 mandatory field validation.

Prevents generation of invalid/incomplete legal documents.
"""
from pydantic import BaseModel


class CEValidationResult(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


# Mandatory fields per standard
_EN1090_REQUIRED = {
    "product_type": "Tipo Prodotto obbligatorio per EN 1090-1",
    "execution_class": "Classe di Esecuzione obbligatoria per EN 1090-1 (EXC1-EXC4)",
    "durability": "Durabilita obbligatoria per EN 1090-1",
    "reaction_to_fire": "Reazione al Fuoco obbligatoria per EN 1090-1",
}

_EN13241_REQUIRED = {
    "product_type": "Tipo Prodotto obbligatorio per EN 13241",
    "mechanical_resistance": "Resistenza Meccanica obbligatoria per EN 13241",
    "safe_opening": "Sicurezza Apertura obbligatoria per EN 13241",
    "durability": "Durabilita obbligatoria per EN 13241",
}

_EN14351_REQUIRED = {
    "product_type": "Tipo Prodotto obbligatorio per EN 14351-1",
    "durability": "Durabilita obbligatoria per EN 14351-1",
}


def _is_empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


class CEValidator:
    """Single Source of Truth for CE certification mandatory fields."""

    @staticmethod
    def validate(standard: str, product_type: str, technical_specs: dict, project_name: str = "") -> CEValidationResult:
        """Validate a certification document before PDF generation.

        Args:
            standard: "EN 1090-1" or "EN 13241"
            product_type: Product type string
            technical_specs: dict of technical specifications
            project_name: Project name
        """
        errors = []
        warnings = []

        # Project name always required
        if _is_empty(project_name):
            errors.append("Nome Progetto obbligatorio")

        # Select the right rule set
        if "1090" in standard:
            rules = _EN1090_REQUIRED
        elif "13241" in standard:
            rules = _EN13241_REQUIRED
        else:
            rules = _EN14351_REQUIRED

        # Check product_type at top level
        if _is_empty(product_type) and "product_type" in rules:
            errors.append(rules["product_type"])

        # Check technical_specs fields
        for field, msg in rules.items():
            if field == "product_type":
                continue
            val = technical_specs.get(field)
            if _is_empty(val):
                errors.append(msg)

        # Warnings for recommended fields
        if _is_empty(technical_specs.get("dangerous_substances")):
            warnings.append("Campo 'Sostanze Pericolose' consigliato per completezza DOP")

        # Thermal warning for EN 13241
        if "13241" in standard:
            if technical_specs.get("thermal_enabled") and _is_empty(technical_specs.get("thermal_uw")):
                warnings.append("Calcolo termico abilitato ma Uw non calcolato. Eseguire il calcolo prima di generare il PDF.")

        return CEValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
