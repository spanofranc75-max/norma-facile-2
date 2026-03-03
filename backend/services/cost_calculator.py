"""Cost Calculator — Computes the real hourly cost for the company.

Formula:
    Costo Totale Annuo = Stipendi Lordi + Contributi + Spese Generali
    Costo Orario Pieno = Costo Totale Annuo / Ore Lavorabili Anno

This "magic number" replaces the naive wage cost with the true cost of 1 hour of work.
"""


def calc_hourly_cost(
    stipendi_lordi: float = 0,
    contributi_inps_inail: float = 0,
    affitto_utenze: float = 0,
    commercialista_software: float = 0,
    altri_costi_fissi: float = 0,
    ore_lavorabili_anno: int = 1600,
) -> dict:
    """Calculate the full hourly cost and return a detailed breakdown.

    Args:
        stipendi_lordi: Annual gross salaries total
        contributi_inps_inail: Annual INPS/INAIL contributions
        affitto_utenze: Annual rent + utilities
        commercialista_software: Annual accountant + software costs
        altri_costi_fissi: Other annual fixed costs (insurance, vehicles, etc.)
        ore_lavorabili_anno: Total workable hours per year (e.g. 1600 * n employees)

    Returns:
        Dict with breakdown and the "magic number" costo_orario_pieno.
    """
    costo_personale = stipendi_lordi + contributi_inps_inail
    spese_generali = affitto_utenze + commercialista_software + altri_costi_fissi
    costo_totale_annuo = costo_personale + spese_generali

    if ore_lavorabili_anno <= 0:
        ore_lavorabili_anno = 1

    costo_orario_pieno = round(costo_totale_annuo / ore_lavorabili_anno, 2)

    # Breakdown percentages
    pct_personale = round((costo_personale / costo_totale_annuo * 100) if costo_totale_annuo > 0 else 0, 1)
    pct_generali = round((spese_generali / costo_totale_annuo * 100) if costo_totale_annuo > 0 else 0, 1)

    return {
        "costo_personale": round(costo_personale, 2),
        "spese_generali": round(spese_generali, 2),
        "costo_totale_annuo": round(costo_totale_annuo, 2),
        "ore_lavorabili_anno": ore_lavorabili_anno,
        "costo_orario_pieno": costo_orario_pieno,
        "pct_personale": pct_personale,
        "pct_generali": pct_generali,
    }


def calc_commessa_margin(
    valore_preventivo: float,
    costi_materiali: float,
    ore_lavorate: float,
    costo_orario_pieno: float,
) -> dict:
    """Calculate the real margin for a commessa including labor at full hourly cost.

    Returns:
        Dict with costo_personale, costo_totale, margine, margine_pct, alert.
    """
    costo_personale = round(ore_lavorate * costo_orario_pieno, 2)
    costo_totale = round(costi_materiali + costo_personale, 2)
    margine = round(valore_preventivo - costo_totale, 2)
    margine_pct = round((margine / valore_preventivo * 100) if valore_preventivo > 0 else 0, 1)

    if margine_pct < 0:
        alert = "rosso"
    elif margine_pct < 10:
        alert = "arancione"
    elif margine_pct < 20:
        alert = "giallo"
    else:
        alert = "verde"

    return {
        "costi_materiali": round(costi_materiali, 2),
        "costo_personale": costo_personale,
        "ore_lavorate": ore_lavorate,
        "costo_orario_pieno": costo_orario_pieno,
        "costo_totale": costo_totale,
        "margine": margine,
        "margine_pct": margine_pct,
        "alert": alert,
    }
