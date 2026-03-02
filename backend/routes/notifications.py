"""Notification & Watchdog API — manual triggers, history, status."""
import logging
from fastapi import APIRouter, Depends
from core.database import db
from core.security import get_current_user
from services.notification_scheduler import run_expiration_check, check_welder_expirations, check_instrument_expirations

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_watchdog_status(user: dict = Depends(get_current_user)):
    """Get the current status: last check, pending alerts, etc."""
    # Last check
    last_log = await db.notification_logs.find_one(
        {}, {"_id": 0}, sort=[("checked_at", -1)]
    )

    # Current alerts (live)
    welder_alerts = await check_welder_expirations()
    instrument_alerts = await check_instrument_expirations()

    return {
        "active": True,
        "last_check": last_log,
        "current_alerts": {
            "welder_count": len(welder_alerts),
            "instrument_count": len(instrument_alerts),
            "total": len(welder_alerts) + len(instrument_alerts),
            "welders": welder_alerts,
            "instruments": instrument_alerts,
        },
    }


@router.post("/check-now")
async def trigger_manual_check(user: dict = Depends(get_current_user)):
    """Manually trigger an expiration check and send emails if needed."""
    result = await run_expiration_check(manual=True)
    # Strip _id if it was added by mongo insert
    result.pop("_id", None)
    return result


@router.get("/history")
async def get_notification_history(user: dict = Depends(get_current_user)):
    """Get last 20 notification checks."""
    logs = await db.notification_logs.find(
        {}, {"_id": 0}
    ).sort("checked_at", -1).to_list(20)
    return {"logs": logs}
