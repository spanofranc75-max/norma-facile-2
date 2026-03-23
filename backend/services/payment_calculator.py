"""Payment calculator service - Calculates due dates from payment type configuration."""
import calendar
from datetime import date, timedelta


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

        if fine_mese and giorni > 0:
            # Italian "fine mese" convention: N giorni → N/30 calendar months
            # from invoice date, payment due at end of that month.
            # Example: invoice 31/01, "30 FM" → end Feb, "60 FM" → end Mar
            n_months = round(giorni / 30)
            if n_months < 1:
                n_months = 1
            target_month = d0.month + n_months
            target_year = d0.year + (target_month - 1) // 12
            target_month = (target_month - 1) % 12 + 1
            last_day = calendar.monthrange(target_year, target_month)[1]
            target = date(target_year, target_month, last_day)
            if extra_days:
                target = target + timedelta(days=extra_days)
        else:
            target = d0 + timedelta(days=giorni)

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

    quote = pt["quote"]
    # Safety: if total quota sums to 0 (data entry error), distribute evenly
    total_quota = sum(q.get("quota", 0) for q in quote)
    if total_quota == 0:
        even = round(100 / len(quote), 2)
        quote = [{**q, "quota": even} for q in quote]

    return calculate_due_dates(
        invoice_date=data_documento,
        total_amount=totale,
        quote=quote,
        fine_mese=pt.get("fine_mese", False),
        extra_days=pt.get("extra_days") or 0,
    )
