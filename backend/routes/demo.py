"""Demo Mode routes — reset, status, and demo login."""
from fastapi import APIRouter, Depends, HTTPException, Response
from core.database import db
from core.security import get_current_user, create_download_token, tenant_match
from datetime import datetime, timezone, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_USER_ID = "demo_user"
DEMO_SESSION_TOKEN = "demo_session_token_normafacile"


async def _is_demo_user(user_id: str) -> bool:
    """Check if user is the demo user."""
    return user_id == DEMO_USER_ID


@router.post("/reset")
async def reset_demo_data(user: dict = Depends(get_current_user)):
    """Reset all demo data to initial state. Admin only.
    SEED GUARD: Only touches documents with user_id == DEMO_USER_ID.
    Will never write to or delete real user data."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")

    from scripts.demo_seed_data import get_all_demo_collections, DEMO_USER_ID

    # ── SEED GUARD: verify all seed docs are for demo_user only ──
    seed = get_all_demo_collections()
    for coll_name, docs in seed.items():
        for doc in docs:
            if doc.get("user_id") and doc["user_id"] != DEMO_USER_ID:
                logger.error(f"[SEED GUARD] BLOCKED: seed doc in {coll_name} has user_id='{doc['user_id']}' (expected '{DEMO_USER_ID}')")
                raise HTTPException(
                    status_code=400,
                    detail=f"Seed guard: trovato user_id non-demo in {coll_name}. Reset bloccato."
                )

    # Delete ONLY demo data (strict filter)
    collections_cleaned = 0
    for coll_name in await db.list_collection_names():
        result = await db[coll_name].delete_many({"user_id": DEMO_USER_ID})
        if result.deleted_count > 0:
            collections_cleaned += 1
            logger.info(f"Demo reset: deleted {result.deleted_count} docs from {coll_name}")

    await db.user_sessions.delete_many({"user_id": DEMO_USER_ID})
    await db.onboarding.delete_many({"user_id": DEMO_USER_ID})

    # Re-seed demo data
    docs_created = 0
    for coll_name, docs in seed.items():
        if docs:
            await db[coll_name].insert_many(docs)
            docs_created += len(docs)
            logger.info(f"Demo seed: inserted {len(docs)} docs into {coll_name}")

    # Create demo session
    await db.user_sessions.insert_one({
        "session_token": DEMO_SESSION_TOKEN,
        "user_id": DEMO_USER_ID,
        "tenant_id": "default",
        "email": "demo@normafacile.it",
        "name": "Marco Rossi",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=365),
    })

    logger.info(f"[SEED GUARD OK] Demo data reset complete: {docs_created} docs in {len(seed)} collections")

    return {
        "message": "Demo data reset completato",
        "collections_cleaned": collections_cleaned,
        "docs_created": docs_created,
    }


@router.post("/login")
async def demo_login(response: Response):
    """Quick login for demo mode — no credentials needed."""
    # Check if demo user exists
    user = await db.users.find_one({"user_id": DEMO_USER_ID}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Demo non configurata. Esegui prima il reset.")

    # Ensure session exists
    session = await db.user_sessions.find_one({"session_token": DEMO_SESSION_TOKEN})
    if not session:
        await db.user_sessions.insert_one({
            "session_token": DEMO_SESSION_TOKEN,
            "user_id": DEMO_USER_ID,
            "tenant_id": user.get("tenant_id", "default"),
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=365),
        })

    # Set cookie
    response.set_cookie(
        key="session_token",
        value=DEMO_SESSION_TOKEN,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400 * 365,
    )

    return {
        "message": "Login demo effettuato",
        "user": {
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "is_demo": True,
        }
    }


@router.get("/status")
async def demo_status():
    """Check if demo mode is available and has data."""
    user = await db.users.find_one({"user_id": DEMO_USER_ID}, {"_id": 0, "user_id": 1, "is_demo": 1})
    if not user:
        return {"available": False, "message": "Demo non configurata"}

    commesse_count = await db.commesse.count_documents({"user_id": DEMO_USER_ID})
    return {
        "available": True,
        "commesse_count": commesse_count,
        "demo_user_id": DEMO_USER_ID,
    }
