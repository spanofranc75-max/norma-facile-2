"""
NormaFacile - Notification Scheduler ("Il Cane da Guardia")
Background service that monitors expirations and sends email alerts.
Checks:
- Welder qualification expiry (≤30 days)
- Instrument calibration expiry (≤30 days)
"""
import asyncio
import logging
from datetime import date, datetime, timezone
from core.database import db
from core.config import settings

logger = logging.getLogger(__name__)

# Check interval: once per day (24h)
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
ALERT_THRESHOLD_DAYS = 30
# Minimum hours between email sends (prevents flood on hot-reload restarts)
MIN_HOURS_BETWEEN_EMAILS = 23

_scheduler_task = None


async def _get_notification_recipients() -> list[str]:
    """Get email addresses of users who should receive notifications.
    Respects per-user notification_preferences (opt-out, custom email).
    """
    users = await db.users.find(
        {"role": {"$in": ["admin", "ufficio_tecnico"]}},
        {"_id": 0, "email": 1, "name": 1, "notification_preferences": 1},
    ).to_list(50)
    recipients = []
    for u in users:
        prefs = u.get("notification_preferences") or {}
        # Default is enabled
        if not prefs.get("email_alerts_enabled", True):
            continue
        email = prefs.get("alert_email") or u.get("email")
        if email:
            recipients.append(email)
    return recipients


async def check_welder_expirations() -> list[dict]:
    """Find welder qualifications expiring within threshold."""
    alerts = []
    today = date.today()
    welders = await db.welders.find({"is_active": True}, {"_id": 0}).to_list(500)

    for w in welders:
        for q in w.get("qualifications", []):
            exp_str = q.get("expiry_date", "")
            if not exp_str:
                continue
            try:
                exp = date.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
                delta = (exp - today).days
                if delta <= ALERT_THRESHOLD_DAYS:
                    if delta < 0:
                        urgency = "scaduto"
                    elif delta <= 1:
                        urgency = "critico"
                    elif delta <= 7:
                        urgency = "urgente"
                    else:
                        urgency = "alert"
                    status = "SCADUTA" if delta < 0 else f"scade tra {delta} giorni"
                    alerts.append({
                        "type": "welder_qualification",
                        "welder_name": w.get("name", "N/A"),
                        "stamp_id": w.get("stamp_id", ""),
                        "qualification": f"{q.get('standard', '')} - {q.get('process', '')}",
                        "expiry_date": exp_str,
                        "days_remaining": delta,
                        "status_label": status,
                        "urgency": urgency,
                    })
            except (ValueError, TypeError):
                continue
    return alerts


async def check_instrument_expirations() -> list[dict]:
    """Find instruments with calibration expiring within threshold."""
    alerts = []
    today = date.today()
    instruments = await db.instruments.find(
        {"status": {"$nin": ["fuori_uso"]}},
        {"_id": 0},
    ).to_list(500)

    for inst in instruments:
        next_cal = inst.get("next_calibration_date", "")
        if not next_cal:
            continue
        try:
            exp = date.fromisoformat(next_cal) if isinstance(next_cal, str) else next_cal
            delta = (exp - today).days
            if delta <= ALERT_THRESHOLD_DAYS:
                if delta < 0:
                    urgency = "scaduto"
                elif delta <= 1:
                    urgency = "critico"
                elif delta <= 7:
                    urgency = "urgente"
                else:
                    urgency = "alert"
                status = "SCADUTA" if delta < 0 else f"scade tra {delta} giorni"
                alerts.append({
                    "type": "instrument_calibration",
                    "instrument_name": inst.get("name", "N/A"),
                    "serial_number": inst.get("serial_number", ""),
                    "next_calibration_date": next_cal,
                    "days_remaining": delta,
                    "status_label": status,
                    "urgency": urgency,
                })
        except (ValueError, TypeError):
            continue
    return alerts


async def check_itt_expirations() -> list[dict]:
    """Find ITT verbali expiring within threshold."""
    alerts = []
    today = date.today()
    verbali = await db.verbali_itt.find(
        {"stato": {"$nin": ["annullato", "chiuso"]}},
        {"_id": 0},
    ).to_list(500)

    for v in verbali:
        exp_str = v.get("data_scadenza") or v.get("scadenza") or v.get("data_prossima_verifica", "")
        if not exp_str:
            continue
        try:
            if isinstance(exp_str, str):
                exp = date.fromisoformat(exp_str)
            elif hasattr(exp_str, 'date'):
                exp = exp_str.date() if hasattr(exp_str, 'date') else exp_str
            else:
                exp = exp_str
            delta = (exp - today).days
            if delta <= ALERT_THRESHOLD_DAYS:
                if delta < 0:
                    urgency = "scaduto"
                elif delta <= 1:
                    urgency = "critico"
                elif delta <= 7:
                    urgency = "urgente"
                else:
                    urgency = "alert"
                status = "SCADUTO" if delta < 0 else f"scade tra {delta} giorni"
                alerts.append({
                    "type": "itt_verbale",
                    "verbale_numero": v.get("numero", v.get("verbale_id", "N/A")),
                    "descrizione": v.get("descrizione", v.get("tipo", "Verbale ITT")),
                    "commessa": v.get("commessa_id", ""),
                    "data_scadenza": str(exp),
                    "days_remaining": delta,
                    "status_label": status,
                    "urgency": urgency,
                })
        except (ValueError, TypeError):
            continue
    return alerts



async def check_payment_expirations() -> dict:
    """Find upcoming and overdue payment deadlines for all users."""
    from datetime import timedelta
    today_d = date.today()
    today_iso = today_d.isoformat()
    week_ahead = (today_d + timedelta(days=7)).isoformat()

    result = {"in_scadenza": [], "scadute_fornitori": [], "clienti_ritardo": []}

    # --- Fatture passive: scadenze prossimi 7gg + scadute ---
    fatture_p = await db.fatture_ricevute.find(
        {"payment_status": {"$nin": ["pagata"]}},
        {"_id": 0, "fr_id": 1, "user_id": 1, "numero_documento": 1, "fornitore_nome": 1,
         "totale_documento": 1, "residuo": 1, "scadenze_pagamento": 1, "data_scadenza_pagamento": 1}
    ).to_list(5000)

    for f in fatture_p:
        scadenze = f.get("scadenze_pagamento") or []
        if scadenze:
            for s in scadenze:
                if s.get("pagata"):
                    continue
                scad = s.get("data_scadenza", "")
                imp = s.get("importo", 0)
                if not scad or not imp:
                    continue
                try:
                    days = (today_d - date.fromisoformat(scad)).days
                except ValueError:
                    continue
                entry = {
                    "user_id": f.get("user_id"), "fornitore": f.get("fornitore_nome", ""),
                    "numero": f.get("numero_documento", ""), "importo": imp,
                    "data_scadenza": scad, "giorni": abs(days),
                }
                if days > 0:
                    result["scadute_fornitori"].append(entry)
                elif scad <= week_ahead:
                    result["in_scadenza"].append(entry)
        else:
            scad = f.get("data_scadenza_pagamento", "")
            imp = f.get("residuo") or f.get("totale_documento", 0)
            if not scad or not imp:
                continue
            try:
                days = (today_d - date.fromisoformat(scad)).days
            except ValueError:
                continue
            entry = {
                "user_id": f.get("user_id"), "fornitore": f.get("fornitore_nome", ""),
                "numero": f.get("numero_documento", ""), "importo": imp,
                "data_scadenza": scad, "giorni": abs(days),
            }
            if days > 0:
                result["scadute_fornitori"].append(entry)
            elif scad <= week_ahead:
                result["in_scadenza"].append(entry)

    # --- Fatture attive: clienti in ritardo >30gg ---
    invoices = await db.invoices.find(
        {"payment_status": {"$nin": ["pagata", "paid"]}},
        {"_id": 0, "invoice_id": 1, "user_id": 1, "number": 1, "client_name": 1,
         "totals": 1, "scadenze_pagamento": 1, "due_date": 1}
    ).to_list(5000)

    for inv in invoices:
        scadenze = inv.get("scadenze_pagamento") or []
        if scadenze:
            for s in scadenze:
                if s.get("pagata"):
                    continue
                scad = s.get("data_scadenza", "")
                imp = s.get("importo", 0)
                if not scad:
                    continue
                try:
                    days = (today_d - date.fromisoformat(scad)).days
                except ValueError:
                    continue
                if days > 30:
                    result["clienti_ritardo"].append({
                        "user_id": inv.get("user_id"), "cliente": inv.get("client_name", ""),
                        "numero": inv.get("number", ""), "importo": imp,
                        "data_scadenza": scad, "giorni": days,
                    })
        else:
            scad = inv.get("due_date", "")
            tot = (inv.get("totals") or {}).get("total_document", 0)
            if not scad or not tot:
                continue
            try:
                days = (today_d - date.fromisoformat(scad)).days
            except ValueError:
                continue
            if days > 30:
                result["clienti_ritardo"].append({
                    "user_id": inv.get("user_id"), "cliente": inv.get("client_name", ""),
                    "numero": inv.get("number", ""), "importo": tot,
                    "data_scadenza": scad, "giorni": days,
                })

    return result


def _build_payment_alert_html(payment_data: dict) -> str:
    """Build HTML email for payment deadline alerts."""
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    in_scadenza = payment_data["in_scadenza"]
    scadute = payment_data["scadute_fornitori"]
    clienti = payment_data["clienti_ritardo"]

    def fmt_eur(v):
        return f"{v:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")

    def fmt_date(d):
        p = d.split("-")
        return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else d

    def make_table(rows, cols, color_bg):
        if not rows:
            return ""
        header = "".join(f'<th style="padding:6px 10px;text-align:left;font-size:12px;">{c}</th>' for c in cols)
        body = ""
        for r in rows:
            cells = "".join(f'<td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{v}</td>' for v in r)
            body += f"<tr>{cells}</tr>"
        total = sum(row_data.get("importo", 0) for row_data in [])  # computed outside
        return f"""
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <thead><tr style="background:{color_bg};">{header}</tr></thead>
            <tbody>{body}</tbody>
        </table>"""

    sections = ""

    if in_scadenza:
        tot = sum(s["importo"] for s in in_scadenza)
        rows_html = ""
        for s in sorted(in_scadenza, key=lambda x: x["data_scadenza"]):
            rows_html += f"""<tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['fornitore']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['numero']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;text-align:right;font-family:monospace;">{fmt_eur(s['importo'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{fmt_date(s['data_scadenza'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#d97706;font-weight:600;">{s['giorni']}gg</td>
            </tr>"""
        sections += f"""
        <div style="margin-bottom:20px;">
            <h3 style="color:#92400e;font-size:14px;margin:0 0 8px;">IN SCADENZA ENTRO 7 GIORNI ({len(in_scadenza)})</h3>
            <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:#fef3c7;">
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Fornitore</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Fattura</th>
                    <th style="padding:6px 10px;text-align:right;font-size:11px;">Importo</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Scadenza</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Giorni</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <p style="text-align:right;font-size:13px;font-weight:700;color:#92400e;margin:4px 0;">Totale: {fmt_eur(tot)}</p>
        </div>"""

    if scadute:
        tot = sum(s["importo"] for s in scadute)
        rows_html = ""
        for s in sorted(scadute, key=lambda x: -x["giorni"]):
            rows_html += f"""<tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['fornitore']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['numero']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;text-align:right;font-family:monospace;">{fmt_eur(s['importo'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{fmt_date(s['data_scadenza'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#dc2626;font-weight:600;">{s['giorni']}gg ritardo</td>
            </tr>"""
        sections += f"""
        <div style="margin-bottom:20px;">
            <h3 style="color:#dc2626;font-size:14px;margin:0 0 8px;">SCADUTE NON PAGATE — FORNITORI ({len(scadute)})</h3>
            <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:#fee2e2;">
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Fornitore</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Fattura</th>
                    <th style="padding:6px 10px;text-align:right;font-size:11px;">Importo</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Scadenza</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Ritardo</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <p style="text-align:right;font-size:13px;font-weight:700;color:#dc2626;margin:4px 0;">Totale: {fmt_eur(tot)}</p>
        </div>"""

    if clienti:
        tot = sum(s["importo"] for s in clienti)
        rows_html = ""
        for s in sorted(clienti, key=lambda x: -x["giorni"]):
            rows_html += f"""<tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['cliente']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{s['numero']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;text-align:right;font-family:monospace;">{fmt_eur(s['importo'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;">{fmt_date(s['data_scadenza'])}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#ca8a04;font-weight:600;">{s['giorni']}gg ritardo</td>
            </tr>"""
        sections += f"""
        <div style="margin-bottom:20px;">
            <h3 style="color:#ca8a04;font-size:14px;margin:0 0 8px;">CLIENTI IN RITARDO &gt;30gg ({len(clienti)})</h3>
            <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:#fef9c3;">
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Cliente</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Fattura</th>
                    <th style="padding:6px 10px;text-align:right;font-size:11px;">Importo</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Scadenza</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Ritardo</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <p style="text-align:right;font-size:13px;font-weight:700;color:#ca8a04;margin:4px 0;">Totale: {fmt_eur(tot)}</p>
        </div>"""

    total = len(in_scadenza) + len(scadute) + len(clienti)
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:700px;margin:0 auto;background:#f8fafc;padding:30px 16px;">
        <div style="background:white;border-radius:12px;padding:28px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <h1 style="color:#1e293b;font-size:20px;margin:0 0 4px;">Scadenziario — Riepilogo del {now_str}</h1>
            <p style="color:#64748b;font-size:12px;margin:0 0 20px;">Norma Facile 2.0 — Alert automatico pagamenti</p>
            <div style="background:#f1f5f9;border-radius:8px;padding:12px;text-align:center;margin-bottom:20px;">
                <span style="font-size:16px;font-weight:700;color:#334155;">{total} scadenz{'a' if total == 1 else 'e'} che richied{'e' if total == 1 else 'ono'} attenzione</span>
            </div>
            {sections}
            <div style="text-align:center;margin-top:20px;">
                <a href="{settings.domain_url}/scadenziario"
                   style="display:inline-block;background:#0055FF;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;">
                    Apri Scadenziario
                </a>
            </div>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:11px;margin-top:16px;">
            NormaFacile 2.0 — Notifica automatica
        </p>
    </div>"""
    return html


async def send_payment_alert(manual: bool = False) -> dict:
    """Check payment expirations and send alert email if needed."""
    payment_data = await check_payment_expirations()
    total = len(payment_data["in_scadenza"]) + len(payment_data["scadute_fornitori"]) + len(payment_data["clienti_ritardo"])

    result = {
        "in_scadenza": len(payment_data["in_scadenza"]),
        "scadute_fornitori": len(payment_data["scadute_fornitori"]),
        "clienti_ritardo": len(payment_data["clienti_ritardo"]),
        "total": total,
        "email_sent": False,
    }

    if total == 0:
        logger.info("[WATCHDOG] Nessuna scadenza pagamento urgente, skip email")
        return result

    recipients = await _get_notification_recipients()
    if not recipients:
        logger.warning("[WATCHDOG] No recipients for payment alert")
        return result

    try:
        import resend
        if not settings.resend_api_key:
            logger.warning("[WATCHDOG] Resend not configured, skip payment alert")
            return result
        resend.api_key = settings.resend_api_key

        html = _build_payment_alert_html(payment_data)
        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": recipients,
            "subject": f"Scadenziario Norma Facile — {total} scadenz{'a' if total == 1 else 'e'} [{datetime.now(timezone.utc).strftime('%d/%m/%Y')}]",
            "html": html,
        }
        resend.Emails.send(params)
        result["email_sent"] = True
        result["recipients"] = recipients
        logger.info(f"[WATCHDOG] Payment alert sent to {recipients}: {total} scadenze")
    except Exception as e:
        logger.error(f"[WATCHDOG] Failed to send payment alert: {e}")

    return result



def _build_alert_email_html(welder_alerts: list, instrument_alerts: list, itt_alerts: list = None) -> str:
    """Build a professional HTML email for expiration alerts with urgency levels."""
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    itt_alerts = itt_alerts or []
    total = len(welder_alerts) + len(instrument_alerts) + len(itt_alerts)

    def urgency_color(a):
        u = a.get("urgency", "alert")
        if u == "scaduto":
            return "#dc2626"
        if u == "critico":
            return "#ea580c"
        if u == "urgente":
            return "#d97706"
        return "#eab308"

    def urgency_badge(a):
        u = a.get("urgency", "alert")
        colors = {"scaduto": ("#dc2626", "#fef2f2"), "critico": ("#ea580c", "#fff7ed"),
                  "urgente": ("#d97706", "#fffbeb"), "alert": ("#eab308", "#fefce8")}
        fg, bg = colors.get(u, ("#eab308", "#fefce8"))
        labels = {"scaduto": "SCADUTO", "critico": "1 GIORNO", "urgente": "7 GIORNI", "alert": "30 GIORNI"}
        return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{labels.get(u, "ALERT")}</span>'

    rows_welders = ""
    for a in sorted(welder_alerts, key=lambda x: x["days_remaining"]):
        rows_welders += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['welder_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['stamp_id']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['qualification']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['expiry_date']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{urgency_badge(a)}</td>
        </tr>"""

    rows_instruments = ""
    for a in sorted(instrument_alerts, key=lambda x: x["days_remaining"]):
        rows_instruments += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['instrument_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['serial_number']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['next_calibration_date']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{urgency_badge(a)}</td>
        </tr>"""

    rows_itt = ""
    for a in sorted(itt_alerts, key=lambda x: x["days_remaining"]):
        rows_itt += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['verbale_numero']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['descrizione']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['data_scadenza']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{urgency_badge(a)}</td>
        </tr>"""

    welder_section = ""
    if welder_alerts:
        n_crit = sum(1 for a in welder_alerts if a.get("urgency") in ("scaduto", "critico"))
        welder_section = f"""
        <h3 style="color:#1e293b;margin:24px 0 12px;">Qualifiche Saldatori ({len(welder_alerts)}{f' — {n_crit} critiche' if n_crit else ''})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <thead>
                <tr style="background:#f1f5f9;">
                    <th style="padding:8px 12px;text-align:left;">Saldatore</th>
                    <th style="padding:8px 12px;text-align:left;">Punzone</th>
                    <th style="padding:8px 12px;text-align:left;">Qualifica</th>
                    <th style="padding:8px 12px;text-align:left;">Scadenza</th>
                    <th style="padding:8px 12px;text-align:left;">Stato</th>
                </tr>
            </thead>
            <tbody>{rows_welders}</tbody>
        </table>"""

    instrument_section = ""
    if instrument_alerts:
        n_crit = sum(1 for a in instrument_alerts if a.get("urgency") in ("scaduto", "critico"))
        instrument_section = f"""
        <h3 style="color:#1e293b;margin:24px 0 12px;">Calibrazioni Strumenti ({len(instrument_alerts)}{f' — {n_crit} critiche' if n_crit else ''})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <thead>
                <tr style="background:#f1f5f9;">
                    <th style="padding:8px 12px;text-align:left;">Strumento</th>
                    <th style="padding:8px 12px;text-align:left;">N. Serie</th>
                    <th style="padding:8px 12px;text-align:left;">Prossima Taratura</th>
                    <th style="padding:8px 12px;text-align:left;">Stato</th>
                </tr>
            </thead>
            <tbody>{rows_instruments}</tbody>
        </table>"""

    itt_section = ""
    if itt_alerts:
        n_crit = sum(1 for a in itt_alerts if a.get("urgency") in ("scaduto", "critico"))
        itt_section = f"""
        <h3 style="color:#1e293b;margin:24px 0 12px;">Verbali ITT ({len(itt_alerts)}{f' — {n_crit} critici' if n_crit else ''})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <thead>
                <tr style="background:#f1f5f9;">
                    <th style="padding:8px 12px;text-align:left;">N. Verbale</th>
                    <th style="padding:8px 12px;text-align:left;">Descrizione</th>
                    <th style="padding:8px 12px;text-align:left;">Scadenza</th>
                    <th style="padding:8px 12px;text-align:left;">Stato</th>
                </tr>
            </thead>
            <tbody>{rows_itt}</tbody>
        </table>"""

    # Count by urgency
    all_alerts = welder_alerts + instrument_alerts + itt_alerts
    n_scaduti = sum(1 for a in all_alerts if a.get("urgency") == "scaduto")
    n_critici = sum(1 for a in all_alerts if a.get("urgency") == "critico")
    n_urgenti = sum(1 for a in all_alerts if a.get("urgency") == "urgente")

    urgency_summary = ""
    if n_scaduti > 0:
        urgency_summary += f'<span style="background:#fef2f2;color:#dc2626;padding:4px 12px;border-radius:6px;font-weight:700;font-size:13px;margin:0 4px;">{n_scaduti} SCADUT{"O" if n_scaduti == 1 else "I"}</span>'
    if n_critici > 0:
        urgency_summary += f'<span style="background:#fff7ed;color:#ea580c;padding:4px 12px;border-radius:6px;font-weight:700;font-size:13px;margin:0 4px;">{n_critici} CRITIC{"O" if n_critici == 1 else "I"}</span>'
    if n_urgenti > 0:
        urgency_summary += f'<span style="background:#fffbeb;color:#d97706;padding:4px 12px;border-radius:6px;font-weight:700;font-size:13px;margin:0 4px;">{n_urgenti} URGENT{"E" if n_urgenti == 1 else "I"}</span>'

    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:700px;margin:0 auto;background:#f8fafc;padding:40px 20px;">
        <div style="background:white;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <div style="text-align:center;margin-bottom:24px;">
                <h1 style="color:#1e293b;font-size:22px;margin:0;">Allarme Scadenze — NormaFacile 2.0</h1>
                <p style="color:#64748b;font-size:13px;margin-top:4px;">Controllo automatico del {now_str}</p>
            </div>
            <div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:16px;margin-bottom:20px;text-align:center;">
                <p style="color:#92400e;font-weight:700;font-size:18px;margin:0 0 8px;">
                    {total} scadenz{'a' if total == 1 else 'e'} rilevat{'a' if total == 1 else 'e'}
                </p>
                <div>{urgency_summary}</div>
            </div>
            {welder_section}
            {instrument_section}
            {itt_section}
            <div style="margin-top:24px;text-align:center;">
                <a href="{settings.domain_url}/dashboard"
                   style="display:inline-block;background:#0055FF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
                    Vai a NormaFacile
                </a>
            </div>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:20px;">
            {settings.sender_name} — Il Cane da Guardia (Notifica automatica)
        </p>
    </div>"""
    return html


async def _send_alert_email(recipients: list[str], welder_alerts: list, instrument_alerts: list, itt_alerts: list = None) -> bool:
    """Send the notification email via Resend."""
    try:
        import resend
        if not settings.resend_api_key:
            logger.warning("[WATCHDOG] Resend API key not configured, skip email")
            return False
        resend.api_key = settings.resend_api_key

        itt_alerts = itt_alerts or []
        html = _build_alert_email_html(welder_alerts, instrument_alerts, itt_alerts)
        total = len(welder_alerts) + len(instrument_alerts) + len(itt_alerts)

        # Count critical items for subject line
        all_a = welder_alerts + instrument_alerts + itt_alerts
        n_crit = sum(1 for a in all_a if a.get("urgency") in ("scaduto", "critico"))
        urgency_tag = f" [{n_crit} CRITICHE]" if n_crit else ""

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": recipients,
            "subject": f"[NormaFacile] {total} scadenz{'a' if total == 1 else 'e'} in arrivo{urgency_tag}",
            "html": html,
        }
        resend.Emails.send(params)
        logger.info(f"[WATCHDOG] Alert email sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"[WATCHDOG] Failed to send alert email: {e}")
        return False


async def run_expiration_check(manual: bool = False) -> dict:
    """Run the full expiration check. Returns summary of findings."""
    source = "manuale" if manual else "automatico"

    # Skip automatic checks if we sent an email recently (prevents flood on hot-reload)
    if not manual:
        last_log = await db.notification_logs.find_one(
            {"email_sent": True},
            sort=[("checked_at", -1)],
        )
        if last_log and last_log.get("checked_at"):
            checked_at = last_log["checked_at"]
            if isinstance(checked_at, datetime) and checked_at.tzinfo is None:
                checked_at = checked_at.replace(tzinfo=timezone.utc)
            hours_ago = (datetime.now(timezone.utc) - checked_at).total_seconds() / 3600
            if hours_ago < MIN_HOURS_BETWEEN_EMAILS:
                logger.info(f"[WATCHDOG] Skip: ultima email inviata {hours_ago:.1f}h fa (min {MIN_HOURS_BETWEEN_EMAILS}h)")
                return {"skipped": True, "hours_since_last": round(hours_ago, 1)}

    logger.info(f"[WATCHDOG] Avvio controllo scadenze ({source})...")

    welder_alerts = await check_welder_expirations()
    instrument_alerts = await check_instrument_expirations()
    itt_alerts = await check_itt_expirations()
    payment_result = await send_payment_alert(manual=manual)
    total = len(welder_alerts) + len(instrument_alerts) + len(itt_alerts)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "welder_alerts": welder_alerts,
        "instrument_alerts": instrument_alerts,
        "itt_alerts": itt_alerts,
        "payment_alerts": payment_result,
        "total_alerts": total + payment_result.get("total", 0),
        "email_sent": False,
    }

    if total > 0:
        recipients = await _get_notification_recipients()
        if recipients:
            result["email_sent"] = await _send_alert_email(recipients, welder_alerts, instrument_alerts, itt_alerts)
            result["recipients"] = recipients
        else:
            logger.warning("[WATCHDOG] No recipients found (no admin/ufficio_tecnico users with email)")

    # Save check result to DB
    await db.notification_logs.insert_one({
        "checked_at": datetime.now(timezone.utc),
        "source": source,
        "total_alerts": result["total_alerts"],
        "welder_count": len(welder_alerts),
        "instrument_count": len(instrument_alerts),
        "itt_count": len(itt_alerts),
        "payment_count": payment_result.get("total", 0),
        "email_sent": result["email_sent"] or payment_result.get("email_sent", False),
        "payment_email_sent": payment_result.get("email_sent", False),
        "recipients": result.get("recipients", []),
    })

    logger.info(f"[WATCHDOG] Controllo completato: {result['total_alerts']} alert, welder_email={result['email_sent']}, payment_email={payment_result.get('email_sent', False)}")
    return result


async def _scheduler_loop():
    """Background loop that periodically checks expirations and performs auto-backups."""
    logger.info("[WATCHDOG] Scheduler avviato (intervallo: 24h, 1 volta al giorno)")
    # Wait 5 min after startup before first check (avoids flood on hot-reload)
    await asyncio.sleep(300)
    while True:
        try:
            await run_expiration_check(manual=False)
        except Exception as e:
            logger.error(f"[WATCHDOG] Errore nel controllo programmato: {e}")
        # Auto-backup (runs after expiration check)
        try:
            await _run_auto_backup()
        except Exception as e:
            logger.error(f"[WATCHDOG] Errore nel backup automatico: {e}")
        # Cleanup expired sessions and download tokens
        try:
            await _cleanup_expired_auth()
        except Exception as e:
            logger.error(f"[WATCHDOG] Errore nel cleanup sessioni: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def _cleanup_expired_auth():
    """Remove expired sessions and one-time download tokens. Runs daily."""
    now = datetime.now(timezone.utc)

    # Expired sessions
    result = await db.user_sessions.delete_many({"expires_at": {"$lt": now}})
    if result.deleted_count:
        logger.info(f"[WATCHDOG] Cleanup: {result.deleted_count} sessioni scadute rimosse")

    # Expired download tokens (should self-clean via one-time use, but catch stragglers)
    result = await db.download_tokens.delete_many({"expires_at": {"$lt": now}})
    if result.deleted_count:
        logger.info(f"[WATCHDOG] Cleanup: {result.deleted_count} download token scaduti rimossi")



async def _run_auto_backup():
    """Perform automatic backup for all admin users, keeping last 7 backups."""
    import json as _json

    admins = await db.users.find(
        {"role": {"$in": ["admin"]}},
        {"_id": 0, "user_id": 1, "email": 1},
    ).to_list(10)

    for admin in admins:
        uid = admin["user_id"]
        # Check last backup date — skip if already done today
        last = await db.backup_log.find_one(
            {"user_id": uid, "auto": True},
            sort=[("date", -1)],
        )
        if last:
            last_date = last.get("date")
            if isinstance(last_date, datetime):
                if last_date.date() == datetime.now(timezone.utc).date():
                    continue

        # Perform backup
        from routes.backup import BACKUP_COLLECTIONS, _serialize
        now = datetime.now(timezone.utc)
        backup_data = {}
        total_records = 0
        stats = {}
        for coll_name in BACKUP_COLLECTIONS:
            try:
                docs = await db[coll_name].find({"user_id": uid}, {"_id": 0}).to_list(None)
                backup_data[coll_name] = docs
                stats[coll_name] = len(docs)
                total_records += len(docs)
            except Exception:
                backup_data[coll_name] = []
                stats[coll_name] = 0

        backup = {
            "metadata": {
                "date": now.isoformat(),
                "version": "2.0",
                "app": "Norma Facile 2.0",
                "user_id": uid,
                "auto": True,
            },
            "data": backup_data,
            "stats": stats,
        }

        json_bytes = _json.dumps(backup, default=_serialize, ensure_ascii=False).encode("utf-8")
        date_str = now.strftime("%Y%m%d_%H%M")
        filename = f"auto_backup_{date_str}.json"

        await db.backup_log.insert_one({
            "user_id": uid,
            "date": now,
            "filename": filename,
            "total_records": total_records,
            "stats": stats,
            "size_bytes": len(json_bytes),
            "auto": True,
        })

        # Cleanup: keep only last 7 auto-backups
        old_backups = await db.backup_log.find(
            {"user_id": uid, "auto": True},
            sort=[("date", -1)],
        ).skip(7).to_list(100)
        if old_backups:
            old_ids = [b["_id"] for b in old_backups]
            await db.backup_log.delete_many({"_id": {"$in": old_ids}})

        logger.info(f"[BACKUP] Auto-backup completato per {uid}: {total_records} record, {len(json_bytes)} bytes")


def start_scheduler():
    """Start the background scheduler as an asyncio task."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop(), name="notification_scheduler")
        _scheduler_task.add_done_callback(
            lambda t: logger.error(f"[WATCHDOG] Scheduler crashed: {t.exception()}") if not t.cancelled() and t.exception() else None
        )
        logger.info("[WATCHDOG] Background task creato")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("[WATCHDOG] Background task cancellato")
