"""Onboarding routes — tracks first-time user progress."""
from fastapi import APIRouter, Depends
from core.database import db
from core.security import get_current_user
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])

STEPS = [
    "company_configured",
    "first_client",
    "first_preventivo",
    "first_commessa",
]


async def _detect_steps(user_id: str, tenant_id: str = "default") -> dict:
    """Auto-detect which onboarding steps are completed."""
    company = await db.company_settings.find_one(
        {"user_id": user_id, "tenant_id": tenant_id},
        {"_id": 0, "business_name": 1, "partita_iva": 1, "vat_number": 1}
    )
    has_company = bool(
        company
        and company.get("business_name")
        and (company.get("partita_iva") or company.get("vat_number"))
    )

    has_client = await db.clients.count_documents({"user_id": user_id, "tenant_id": tenant_id}) > 0
    has_preventivo = await db.preventivi.count_documents({"user_id": user_id, "tenant_id": tenant_id}) > 0
    has_commessa = await db.commesse.count_documents({"user_id": user_id, "tenant_id": tenant_id}) > 0

    return {
        "company_configured": has_company,
        "first_client": has_client,
        "first_preventivo": has_preventivo,
        "first_commessa": has_commessa,
    }


@router.get("/status")
async def get_onboarding_status(user: dict = Depends(get_current_user)):
    """Return current onboarding status with auto-detected steps."""
    user_id = user["user_id"]
    tenant_id = user["tenant_id"]

    # Check if user has dismissed onboarding
    record = await db.onboarding.find_one(
        {"user_id": user_id, "tenant_id": tenant_id}, {"_id": 0}
    )

    dismissed = bool(record and record.get("dismissed"))
    completed_at = record.get("completed_at") if record else None

    # Auto-detect steps
    steps = await _detect_steps(user_id, tenant_id)
    all_done = all(steps.values())
    completed_count = sum(1 for v in steps.values() if v)

    # Auto-complete onboarding if all steps done
    if all_done and not completed_at:
        await db.onboarding.update_one(
            {"user_id": user_id, "tenant_id": tenant_id},
            {"$set": {
                "user_id": user_id, "tenant_id": tenant_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        completed_at = datetime.now(timezone.utc).isoformat()

    return {
        "steps": steps,
        "completed_count": completed_count,
        "total_steps": len(STEPS),
        "all_completed": all_done,
        "dismissed": dismissed,
        "completed_at": completed_at,
        "show_onboarding": not dismissed and not all_done,
    }


@router.post("/dismiss")
async def dismiss_onboarding(user: dict = Depends(get_current_user)):
    """Dismiss onboarding checklist (user chose to skip)."""
    await db.onboarding.update_one(
        {"user_id": user["user_id"], "tenant_id": user["tenant_id"]},
        {"$set": {
            "user_id": user["user_id"], "tenant_id": user["tenant_id"],
            "dismissed": True,
            "dismissed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"message": "Onboarding nascosto"}
