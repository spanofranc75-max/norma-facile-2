"""Payment calculator service - Calculates due dates from payment type configuration."""
import calendar
from datetime import date, timedelta
from typing import Optional


def calculate_due_dates(
    invoice_date: str,
    total_amount: float,
    quote: list,
    fine_mese: bool = False,
    extra_days: int = 0,
) -> list:
    """Calculate payment schedule from payment type configuration.

    Args:
        invoice_date: ISO date string (YYYY-MM-DD)
        total_amount: Total invoice amount
        quote: List of installments [{"giorni": 30, "quota": 50}, ...]
        fine_mese: Apply end-of-month rule
        extra_days: Extra days after end-of-month

    Returns:
        List of dicts: [{"data_scadenza": "YYYY-MM-DD", "importo": float, "pagata": False}, ...]
    """
    if not invoice_date or not quote:
        return []

    try:
        d0 = date.fromisoformat(invoice_date)
    except (ValueError, TypeError):
        return []

    results = []
    for i, q in enumerate(quote):
        giorni = q.get("giorni", 0)
        quota_pct = q.get("quota", 100)

        target = d0 + timedelta(days=giorni)

        if fine_mese:
            last_day = calendar.monthrange(target.year, target.month)[1]
            target = target.replace(day=last_day)
            if extra_days:
                target = target + timedelta(days=extra_days)

        importo = round(total_amount * quota_pct / 100, 2)

        results.append({
            "rata": i + 1,
            "data_scadenza": target.isoformat(),
            "importo": importo,
            "pagata": False,
        })

    return results


async def calc_scadenze_from_supplier(db, fornitore_id: str, user_id: str, data_documento: str, totale: float) -> list:
    """Calculate full payment schedule from supplier's payment type.

    Returns list of installments or empty list if supplier has no payment terms.
    """
    if not fornitore_id or not data_documento:
        return []

    supplier = await db.clients.find_one(
        {"client_id": fornitore_id, "user_id": user_id},
        {"_id": 0, "supplier_payment_type_id": 1, "payment_type_id": 1}
    )
    # Prefer supplier-specific payment terms, fall back to generic
    pt_id = None
    if supplier:
        pt_id = supplier.get("supplier_payment_type_id") or supplier.get("payment_type_id")
    if not pt_id:
        return []

    pt = await db.payment_types.find_one(
        {"payment_type_id": pt_id},
        {"_id": 0, "quote": 1, "fine_mese": 1, "extra_days": 1, "descrizione": 1}
    )
    if not pt or not pt.get("quote"):
        return []

    return calculate_due_dates(
        invoice_date=data_documento,
        total_amount=totale,
        quote=pt["quote"],
        fine_mese=pt.get("fine_mese", False),
        extra_days=pt.get("extra_days") or 0,
    )
