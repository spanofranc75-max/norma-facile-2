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

# Check interval: every 12 hours
CHECK_INTERVAL_SECONDS = 12 * 60 * 60
ALERT_THRESHOLD_DAYS = 30

_scheduler_task = None


async def _get_notification_recipients() -> list[str]:
    """Get email addresses of users who should receive notifications (admin + ufficio_tecnico)."""
    users = await db.users.find(
        {"role": {"$in": ["admin", "ufficio_tecnico"]}},
        {"_id": 0, "email": 1, "name": 1},
    ).to_list(50)
    return [u["email"] for u in users if u.get("email")]


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
                    status = "SCADUTA" if delta < 0 else f"scade tra {delta} giorni"
                    alerts.append({
                        "type": "welder_qualification",
                        "welder_name": w.get("name", "N/A"),
                        "stamp_id": w.get("stamp_id", ""),
                        "qualification": f"{q.get('standard', '')} - {q.get('process', '')}",
                        "expiry_date": exp_str,
                        "days_remaining": delta,
                        "status_label": status,
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
                status = "SCADUTA" if delta < 0 else f"scade tra {delta} giorni"
                alerts.append({
                    "type": "instrument_calibration",
                    "instrument_name": inst.get("name", "N/A"),
                    "serial_number": inst.get("serial_number", ""),
                    "next_calibration_date": next_cal,
                    "days_remaining": delta,
                    "status_label": status,
                })
        except (ValueError, TypeError):
            continue
    return alerts


def _build_alert_email_html(welder_alerts: list, instrument_alerts: list) -> str:
    """Build a professional HTML email for expiration alerts."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(welder_alerts) + len(instrument_alerts)

    rows_welders = ""
    for a in sorted(welder_alerts, key=lambda x: x["days_remaining"]):
        color = "#ef4444" if a["days_remaining"] < 0 else "#f59e0b" if a["days_remaining"] <= 7 else "#eab308"
        rows_welders += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['welder_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['stamp_id']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['qualification']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['expiry_date']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;color:{color};font-weight:600;">{a['status_label']}</td>
        </tr>"""

    rows_instruments = ""
    for a in sorted(instrument_alerts, key=lambda x: x["days_remaining"]):
        color = "#ef4444" if a["days_remaining"] < 0 else "#f59e0b" if a["days_remaining"] <= 7 else "#eab308"
        rows_instruments += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['instrument_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['serial_number']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{a['next_calibration_date']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;color:{color};font-weight:600;">{a['status_label']}</td>
        </tr>"""

    welder_section = ""
    if welder_alerts:
        welder_section = f"""
        <h3 style="color:#1e293b;margin:24px 0 12px;">Qualifiche Saldatori ({len(welder_alerts)})</h3>
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
        instrument_section = f"""
        <h3 style="color:#1e293b;margin:24px 0 12px;">Calibrazioni Strumenti ({len(instrument_alerts)})</h3>
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

    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:700px;margin:0 auto;background:#f8fafc;padding:40px 20px;">
        <div style="background:white;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <div style="text-align:center;margin-bottom:24px;">
                <h1 style="color:#f59e0b;font-size:24px;margin:0;">Allarme Scadenze - NormaFacile</h1>
                <p style="color:#64748b;font-size:13px;margin-top:4px;">Controllo automatico del {now_str}</p>
            </div>
            <div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:16px;margin-bottom:20px;text-align:center;">
                <p style="color:#92400e;font-weight:700;font-size:18px;margin:0;">
                    {total} scadenz{'a' if total == 1 else 'e'} rilevat{'a' if total == 1 else 'e'}
                </p>
            </div>
            {welder_section}
            {instrument_section}
            <div style="margin-top:24px;text-align:center;">
                <a href="{settings.domain_url}/dashboard" 
                   style="display:inline-block;background:#0055FF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
                    Vai a NormaFacile
                </a>
            </div>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:20px;">
            {settings.sender_name} - Notifica automatica (Il Cane da Guardia)
        </p>
    </div>"""
    return html


async def _send_alert_email(recipients: list[str], welder_alerts: list, instrument_alerts: list) -> bool:
    """Send the notification email via Resend."""
    try:
        import resend
        if not settings.resend_api_key:
            logger.warning("[WATCHDOG] Resend API key not configured, skip email")
            return False
        resend.api_key = settings.resend_api_key

        html = _build_alert_email_html(welder_alerts, instrument_alerts)
        total = len(welder_alerts) + len(instrument_alerts)

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": recipients,
            "subject": f"[NormaFacile] {total} scadenz{'a' if total == 1 else 'e'} in arrivo",
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
    logger.info(f"[WATCHDOG] Avvio controllo scadenze ({source})...")

    welder_alerts = await check_welder_expirations()
    instrument_alerts = await check_instrument_expirations()
    total = len(welder_alerts) + len(instrument_alerts)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "welder_alerts": welder_alerts,
        "instrument_alerts": instrument_alerts,
        "total_alerts": total,
        "email_sent": False,
    }

    if total > 0:
        recipients = await _get_notification_recipients()
        if recipients:
            result["email_sent"] = await _send_alert_email(recipients, welder_alerts, instrument_alerts)
            result["recipients"] = recipients
        else:
            logger.warning("[WATCHDOG] No recipients found (no admin/ufficio_tecnico users with email)")

    # Save check result to DB
    await db.notification_logs.insert_one({
        "checked_at": datetime.now(timezone.utc),
        "source": source,
        "total_alerts": total,
        "welder_count": len(welder_alerts),
        "instrument_count": len(instrument_alerts),
        "email_sent": result["email_sent"],
        "recipients": result.get("recipients", []),
    })

    logger.info(f"[WATCHDOG] Controllo completato: {total} alert trovati, email_sent={result['email_sent']}")
    return result


async def _scheduler_loop():
    """Background loop that periodically checks expirations."""
    logger.info("[WATCHDOG] Scheduler avviato (intervallo: 12h)")
    # Wait 60s after startup before first check
    await asyncio.sleep(60)
    while True:
        try:
            await run_expiration_check(manual=False)
        except Exception as e:
            logger.error(f"[WATCHDOG] Errore nel controllo programmato: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler():
    """Start the background scheduler as an asyncio task."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("[WATCHDOG] Background task creato")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("[WATCHDOG] Background task cancellato")
