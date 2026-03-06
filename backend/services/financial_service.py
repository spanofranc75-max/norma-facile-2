"""
Financial Service — Aggregatore ciclo attivo + passivo per il Cruscotto Artigiano.
Corregge i campi fatture_ricevute (imposta, data_scadenza_pagamento, payment_status).
"""
from datetime import datetime, timezone, timedelta, date
from core.database import db
import logging

logger = logging.getLogger(__name__)


async def get_active_invoices_summary(uid: str, date_start: str, date_end: str):
    """Fatture emesse (ciclo attivo): IVA a debito, incassi, scadenzario clienti."""
    pipeline = [
        {"$match": {
            "user_id": uid,
            "status": {"$in": ["emessa", "pagata", "inviata_sdi", "accettata"]},
            "issue_date": {"$gte": date_start, "$lt": date_end},
        }},
        {"$group": {
            "_id": None,
            "imponibile": {"$sum": {"$ifNull": ["$totals.subtotal", 0]}},
            "totale": {"$sum": {"$ifNull": ["$totals.total_document", 0]}},
            "count": {"$sum": 1},
        }},
    ]
    res = await db.invoices.aggregate(pipeline).to_list(1)
    if not res:
        return {"imponibile": 0, "iva": 0, "totale": 0, "count": 0}
    r = res[0]
    totale = round(r.get("totale", 0), 2)
    imponibile = round(r.get("imponibile", 0), 2)
    return {
        "imponibile": imponibile,
        "iva": round(totale - imponibile, 2),
        "totale": totale,
        "count": r.get("count", 0),
    }


async def get_passive_invoices_summary(uid: str, date_start: str, date_end: str):
    """Fatture ricevute (ciclo passivo): IVA a credito, uscite, scadenzario fornitori.
    Uses correct fields: imposta (not totale_iva), data_documento (string ISO date).
    """
    pipeline = [
        {"$match": {
            "user_id": uid,
            "data_documento": {"$gte": date_start, "$lt": date_end},
        }},
        {"$group": {
            "_id": None,
            "imponibile": {"$sum": {"$ifNull": ["$imponibile", 0]}},
            "iva": {"$sum": {"$ifNull": ["$imposta", 0]}},
            "totale": {"$sum": {"$ifNull": ["$totale_documento", 0]}},
            "count": {"$sum": 1},
        }},
    ]
    res = await db.fatture_ricevute.aggregate(pipeline).to_list(1)
    if not res:
        return {"imponibile": 0, "iva": 0, "totale": 0, "count": 0}
    r = res[0]
    return {
        "imponibile": round(r.get("imponibile", 0), 2),
        "iva": round(r.get("iva", 0), 2),
        "totale": round(r.get("totale", 0), 2),
        "count": r.get("count", 0),
    }


async def get_monthly_cashflow(uid: str, year: int, month: int):
    """Cash flow reale mensile: incassi effettivi vs pagamenti effettivi."""
    m_start = f"{year}-{month:02d}-01"
    if month == 12:
        m_end = f"{year + 1}-01-01"
    else:
        m_end = f"{year}-{month + 1:02d}-01"

    # Incassi ricevuti (fatture attive pagate)
    inc_pipeline = [
        {"$match": {
            "user_id": uid,
            "payment_status": "pagata",
            "issue_date": {"$gte": m_start, "$lt": m_end},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$totals.total_document"}, "count": {"$sum": 1}}},
    ]
    inc_res = await db.invoices.aggregate(inc_pipeline).to_list(1)
    incassi = round(inc_res[0]["total"], 2) if inc_res else 0
    n_incassi = inc_res[0]["count"] if inc_res else 0

    # Da incassare (fatture attive non pagate in scadenza nel mese)
    # Include invoices where payment_status is null, missing, or explicitly unpaid
    da_inc_pipeline = [
        {"$match": {
            "user_id": uid,
            "status": {"$in": ["emessa", "inviata_sdi", "accettata"]},
            "payment_status": {"$nin": ["pagata"]},
            "due_date": {"$gte": m_start, "$lt": m_end},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$totals.total_document"}, "count": {"$sum": 1}}},
    ]
    da_inc_res = await db.invoices.aggregate(da_inc_pipeline).to_list(1)
    da_incassare = round(da_inc_res[0]["total"], 2) if da_inc_res else 0

    # Pagamenti effettuati (fatture passive pagate)
    pag_pipeline = [
        {"$match": {
            "user_id": uid,
            "payment_status": "pagata",
            "data_documento": {"$gte": m_start, "$lt": m_end},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$totale_documento"}, "count": {"$sum": 1}}},
    ]
    pag_res = await db.fatture_ricevute.aggregate(pag_pipeline).to_list(1)
    pagati = round(pag_res[0]["total"], 2) if pag_res else 0
    n_pagati = pag_res[0]["count"] if pag_res else 0

    # Da pagare (fatture passive non pagate in scadenza nel mese)
    da_pag_pipeline = [
        {"$match": {
            "user_id": uid,
            "payment_status": {"$in": ["non_pagata", "parzialmente_pagata"]},
            "data_scadenza_pagamento": {"$gte": m_start, "$lt": m_end},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$totale_documento"}, "count": {"$sum": 1}}},
    ]
    da_pag_res = await db.fatture_ricevute.aggregate(da_pag_pipeline).to_list(1)
    da_pagare = round(da_pag_res[0]["total"], 2) if da_pag_res else 0

    return {
        "incassi": incassi,
        "n_incassi": n_incassi,
        "da_incassare": da_incassare,
        "pagati": pagati,
        "n_pagati": n_pagati,
        "da_pagare": da_pagare,
        "saldo_reale": round(incassi - pagati, 2),
        "saldo_previsto": round((incassi + da_incassare) - (pagati + da_pagare), 2),
    }


async def get_receivables_aging(uid: str, today_iso: str):
    """Scadenzario crediti clienti per fascia di anzianità."""
    # Include all unpaid invoices (payment_status != "pagata")
    items = await db.invoices.find(
        {"user_id": uid,
         "payment_status": {"$nin": ["pagata"]},
         "status": {"$in": ["emessa", "inviata_sdi", "accettata"]}},
        {"_id": 0, "invoice_id": 1, "document_number": 1, "client_business_name": 1,
         "totals.total_document": 1, "due_date": 1, "issue_date": 1}
    ).sort("due_date", 1).to_list(200)

    today = date.fromisoformat(today_iso)
    aging = {"0_30": 0, "30_60": 0, "60_90": 0, "over_90": 0}
    detail = []

    for inv in items:
        dd = inv.get("due_date") or inv.get("issue_date") or today_iso
        try:
            due = date.fromisoformat(str(dd)[:10])
            days = (today - due).days
        except Exception:
            days = 0

        amount = inv.get("totals", {}).get("total_document", 0) or 0
        if days <= 30:
            aging["0_30"] += amount
        elif days <= 60:
            aging["30_60"] += amount
        elif days <= 90:
            aging["60_90"] += amount
        else:
            aging["over_90"] += amount

        detail.append({
            "id": inv.get("invoice_id"),
            "numero": inv.get("document_number", ""),
            "client_name": inv.get("client_business_name", ""),
            "amount": round(amount, 2),
            "due_date": str(dd)[:10] if dd else None,
            "days_overdue": max(days, 0),
            "urgency": "scaduta" if days > 0 else "in_scadenza",
        })

    return {
        "aging": {k: round(v, 2) for k, v in aging.items()},
        "detail": detail[:20],
        "total": round(sum(aging.values()), 2),
    }


async def get_payables_aging(uid: str, today_iso: str):
    """Scadenzario debiti fornitori per fascia di anzianità.
    Supporta rate multiple da scadenze_pagamento (RIBA 30-60, ecc.)."""
    items = await db.fatture_ricevute.find(
        {"user_id": uid,
         "payment_status": {"$in": ["non_pagata", "parzialmente_pagata"]}},
        {"_id": 0, "fr_id": 1, "numero_documento": 1, "fornitore_nome": 1,
         "totale_documento": 1, "data_scadenza_pagamento": 1, "data_documento": 1,
         "residuo": 1, "scadenze_pagamento": 1}
    ).sort("data_scadenza_pagamento", 1).to_list(200)

    today = date.fromisoformat(today_iso)
    aging = {"0_30": 0, "30_60": 0, "60_90": 0, "over_90": 0}
    scadute = 0
    scadenza_mese = 0
    detail = []

    def _add_to_aging(amount, due_date_str, fr, rata_label=None):
        """Helper: classifica una singola scadenza nei bucket aging."""
        nonlocal scadute, scadenza_mese
        try:
            due = date.fromisoformat(str(due_date_str)[:10]) if due_date_str else today
            days = (today - due).days
        except Exception:
            days = 0

        if days <= 30:
            aging["0_30"] += amount
        elif days <= 60:
            aging["30_60"] += amount
        elif days <= 90:
            aging["60_90"] += amount
        else:
            aging["over_90"] += amount

        if days > 0:
            scadute += amount
        if due_date_str:
            try:
                due_d = date.fromisoformat(str(due_date_str)[:10])
                if due_d.year == today.year and due_d.month == today.month:
                    scadenza_mese += amount
            except Exception:
                pass

        numero = fr.get("numero_documento", "") or fr.get("data_documento", "")
        if rata_label:
            numero = f"{numero} (Rata {rata_label})"

        detail.append({
            "id": fr.get("fr_id"),
            "numero": numero,
            "fornitore": fr.get("fornitore_nome", ""),
            "amount": round(amount, 2),
            "due_date": str(due_date_str)[:10] if due_date_str else None,
            "days_overdue": max(days, 0),
            "urgency": "scaduta" if days > 0 else "in_scadenza",
        })

    for fr in items:
        scadenze = fr.get("scadenze_pagamento") or []
        unpaid_scadenze = [s for s in scadenze if not s.get("pagata")]

        if unpaid_scadenze:
            for s in unpaid_scadenze:
                _add_to_aging(
                    s.get("importo", 0),
                    s.get("data_scadenza", fr.get("data_documento")),
                    fr,
                    rata_label=s.get("rata"),
                )
        else:
            dd = fr.get("data_scadenza_pagamento") or fr.get("data_documento")
            amount = fr.get("residuo") or fr.get("totale_documento", 0) or 0
            _add_to_aging(amount, dd, fr)

    detail.sort(key=lambda x: x.get("due_date") or "9999-12-31")

    return {
        "aging": {k: round(v, 2) for k, v in aging.items()},
        "detail": detail[:30],
        "total": round(sum(aging.values()), 2),
        "scadute": round(scadute, 2),
        "scadenza_mese": round(scadenza_mese, 2),
    }


async def get_cashflow_forecast(uid: str, today_iso: str):
    """Previsione cash flow a 30/60/90 giorni.
    Usa scadenze_pagamento (rate individuali) se disponibili."""
    today = date.fromisoformat(today_iso)
    results = []

    for days, label in [(30, "30 giorni"), (60, "60 giorni"), (90, "90 giorni")]:
        horizon = (today + timedelta(days=days)).isoformat()

        # Entrate attese (fatture clienti non pagate in scadenza)
        ent_pipeline = [
            {"$match": {
                "user_id": uid,
                "payment_status": {"$nin": ["pagata"]},
                "status": {"$in": ["emessa", "inviata_sdi", "accettata"]},
                "due_date": {"$gte": today_iso, "$lte": horizon},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$totals.total_document"}, "count": {"$sum": 1}}},
        ]
        ent_res = await db.invoices.aggregate(ent_pipeline).to_list(1)
        entrate = round(ent_res[0]["total"], 2) if ent_res else 0

        # Uscite previste — iterate through scadenze_pagamento for accuracy
        uscite = 0
        fr_cursor = db.fatture_ricevute.find(
            {"user_id": uid,
             "payment_status": {"$in": ["non_pagata", "parzialmente_pagata"]}},
            {"_id": 0, "totale_documento": 1, "data_scadenza_pagamento": 1,
             "scadenze_pagamento": 1, "residuo": 1}
        )
        async for fr in fr_cursor:
            scadenze = fr.get("scadenze_pagamento") or []
            unpaid = [s for s in scadenze if not s.get("pagata")]
            if unpaid:
                for s in unpaid:
                    sd = s.get("data_scadenza", "")
                    if sd and today_iso <= sd <= horizon:
                        uscite += s.get("importo", 0)
            else:
                sd = fr.get("data_scadenza_pagamento", "")
                if sd and today_iso <= sd <= horizon:
                    uscite += fr.get("residuo") or fr.get("totale_documento", 0)

        results.append({
            "label": label,
            "entrate": entrate,
            "uscite": round(uscite, 2),
            "saldo": round(entrate - uscite, 2),
        })

    return results
