"""Safety Validator — D.Lgs. 81/2008 POS risk association logic.

Maps work activities to required risks, machines, and PPE.
Single Source of Truth for safety compliance rules.
"""


# Risk -> required DPI associations
RISK_DPI_MAP: dict[str, list[str]] = {
    "saldatura": ["maschera_saldatura", "guanti_pelle", "grembiule_saldatura", "scarpe_antinfortunistiche", "occhiali"],
    "saldatura_tig": ["maschera_saldatura", "guanti_pelle", "grembiule_saldatura", "scarpe_antinfortunistiche"],
    "taglio_plasma": ["occhiali", "guanti_pelle", "scarpe_antinfortunistiche", "tappi_auricolari", "grembiule_saldatura"],
    "molatura": ["occhiali", "visiera", "guanti_antitaglio", "tappi_auricolari", "scarpe_antinfortunistiche"],
    "foratura": ["occhiali", "guanti_antitaglio", "scarpe_antinfortunistiche"],
    "taglio_flessibile": ["occhiali", "visiera", "guanti_antitaglio", "tappi_auricolari", "scarpe_antinfortunistiche"],
    "piegatura": ["guanti_antitaglio", "scarpe_antinfortunistiche"],
    "lavoro_quota": ["casco", "imbracatura", "scarpe_antinfortunistiche"],
    "movimentazione": ["casco", "guanti_antitaglio", "scarpe_antinfortunistiche"],
    "montaggio_cantiere": ["casco", "scarpe_antinfortunistiche", "guanti_antitaglio", "occhiali"],
    "verniciatura": ["maschera_ffp2", "guanti_chimici", "occhiali", "tuta_lavoro"],
    "sabbiatura": ["maschera_ffp2", "visiera", "guanti_antitaglio", "tuta_lavoro", "tappi_auricolari"],
    "spazi_confinati": ["maschera_ffp2", "casco", "imbracatura", "scarpe_antinfortunistiche"],
}

# Risk -> typical machines
RISK_MACHINE_MAP: dict[str, list[str]] = {
    "saldatura": ["saldatrice_mig", "saldatrice_elettrodo"],
    "saldatura_tig": ["saldatrice_tig"],
    "taglio_plasma": ["plasma"],
    "molatura": ["smerigliatrice"],
    "foratura": ["trapano_colonna", "trapano_portatile"],
    "taglio_flessibile": ["smerigliatrice"],
    "piegatura": ["pressa_piegatrice"],
    "lavoro_quota": ["ponteggio", "piattaforma_aerea"],
    "movimentazione": ["carroponte", "muletto"],
    "montaggio_cantiere": ["trapano_portatile", "compressore"],
}


class SafetyValidator:
    """Single Source of Truth for POS safety compliance (D.Lgs. 81/2008)."""

    @staticmethod
    def get_required_dpi(selected_risks: list[str]) -> list[str]:
        """Given selected risks, return all required DPI (deduplicated)."""
        dpi = set()
        for risk_id in selected_risks:
            dpi.update(RISK_DPI_MAP.get(risk_id, []))
        return sorted(dpi)

    @staticmethod
    def get_suggested_machines(selected_risks: list[str]) -> list[str]:
        """Given selected risks, return suggested machines (deduplicated)."""
        machines = set()
        for risk_id in selected_risks:
            machines.update(RISK_MACHINE_MAP.get(risk_id, []))
        return sorted(machines)

    @staticmethod
    def validate_pos(selected_risks: list[str], selected_dpi: list[str]) -> dict:
        """Validate a POS document: check if all required DPI are selected.

        Returns: {"valid": bool, "missing_dpi": list[str], "warnings": list[str]}
        """
        required = set()
        for risk_id in selected_risks:
            required.update(RISK_DPI_MAP.get(risk_id, []))

        selected_set = set(selected_dpi)
        missing = sorted(required - selected_set)

        warnings = []
        if missing:
            warnings.append(f"DPI mancanti per le lavorazioni selezionate: {', '.join(missing)}")
        if not selected_risks:
            warnings.append("Nessuna lavorazione selezionata. Il POS richiede almeno una lavorazione.")

        return {
            "valid": len(missing) == 0 and len(selected_risks) > 0,
            "missing_dpi": missing,
            "required_dpi": sorted(required),
            "warnings": warnings,
        }
