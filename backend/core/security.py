"""Security utilities for authentication."""
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Response
from .database import db
from .config import settings
import logging

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"



def tenant_filter(user: dict) -> dict:
    """Build a MongoDB filter dict that matches the user's tenant.
    
    Resilient: also matches documents that don't have tenant_id yet
    (pre-migration data). This avoids empty results on production
    databases that haven't been fully migrated.
    """
    tid = user.get("tenant_id", "default")
    return {"$or": [{"tenant_id": tid}, {"tenant_id": {"$exists": False}}]}


def tenant_match(user: dict) -> str:
    """Returns the user's tenant_id string — safe for both queries AND inserts.
    
    The startup migration dynamically backfills ALL collections,
    so exact string match is reliable.
    """
    return user.get("tenant_id", "default")



async def exchange_session_id(session_id: str) -> dict:
    """
    Exchange session_id from Emergent Auth for user data and session_token.
    This MUST be called from backend, never from frontend.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            settings.emergent_auth_url,
            headers={"X-Session-ID": session_id}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to exchange session_id: {response.text}")
            raise HTTPException(status_code=401, detail="Autenticazione fallita")
        
        return response.json()


async def create_session(user_data: dict, response: Response) -> dict:
    """
    Create or update user in database and create session.
    Returns user document.
    """
    email = user_data.get("email")
    session_token = user_data.get("session_token")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user data if needed
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "name": user_data.get("name"),
                "picture": user_data.get("picture"),
                "last_login": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        # Backfill tenant_id if missing
        if not existing_user.get("tenant_id"):
            await db.users.update_one(
                {"email": email},
                {"$set": {"tenant_id": "default"}}
            )
    else:
        # Check if this email has a pending invite
        invite = await db.team_invites.find_one({"email": email.lower(), "status": "pending"})

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = {
            "user_id": user_id,
            "email": email,
            "name": user_data.get("name"),
            "picture": user_data.get("picture"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc),
        }

        if invite:
            # Invited user: assign role and link to admin's team
            new_user["role"] = invite["role"]
            new_user["team_owner_id"] = invite["admin_id"]
            # Inherit tenant_id from inviter
            inviter = await db.users.find_one({"user_id": invite["admin_id"]}, {"_id": 0})
            new_user["tenant_id"] = inviter.get("tenant_id", "default") if inviter else "default"
            # Mark invite as accepted
            await db.team_invites.update_one(
                {"_id": invite["_id"]},
                {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc), "accepted_user_id": user_id}},
            )
            logger.info(f"Invited user {email} joined with role {invite['role']}")
        else:
            # First user or uninvited: check if any users exist for this "team"
            total_users = await db.users.count_documents({})
            if total_users == 0:
                new_user["role"] = "admin"  # First user is always admin
            else:
                new_user["role"] = "guest"  # Uninvited users are guests
            new_user["tenant_id"] = "default"

        await db.users.insert_one(new_user)

    # --- Auto-onboarding: ensure admin users get a tenant ---
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if user_doc and user_doc.get("role") == "admin" and user_doc.get("tenant_id", "default") == "default":
        from services.tenant_service import ensure_tenant_for_user
        tenant_id = await ensure_tenant_for_user(user_id, email, user_data.get("name", ""))
    else:
        tenant_id = user_doc.get("tenant_id", "default") if user_doc else "default"
    
    # Retrieve tenant_id from user (after possible backfill)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    tenant_id = user_doc.get("tenant_id", "default") if user_doc else "default"

    # Create session
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_expire_days)
    
    # Policy: max 5 sessioni per utente — elimina solo le più vecchie
    MAX_SESSIONS = 5
    existing = await db.user_sessions.find(
        {"user_id": user_id},
        {"_id": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(100)
    if len(existing) >= MAX_SESSIONS:
        old_ids = [s["_id"] for s in existing[MAX_SESSIONS - 1:]]
        deleted = await db.user_sessions.delete_many({"_id": {"$in": old_ids}})
        logger.info(f"Session cleanup: user={user_id}, deleted={deleted.deleted_count} old sessions, kept={min(len(existing), MAX_SESSIONS - 1)}")
    
    # Create new session with device/metadata
    now = datetime.now(timezone.utc)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "tenant_id": tenant_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": now,
        "last_seen_at": now,
    })
    logger.info(f"Session created: user={user_id}, tenant={tenant_id}, expires={expires_at.isoformat()}")
    
    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=settings.session_expire_days * 24 * 60 * 60
    )
    
    # Get full user data
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    """
    Exchange Google OAuth authorization code for user info.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth non configurato")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })

        if token_response.status_code != 200:
            logger.error(f"Google token exchange failed: {token_response.text}")
            raise HTTPException(status_code=401, detail="Scambio codice Google fallito")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=401, detail="Token di accesso Google mancante")

        # Get user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            logger.error(f"Google userinfo failed: {userinfo_response.text}")
            raise HTTPException(status_code=401, detail="Impossibile ottenere dati utente Google")

        return userinfo_response.json()


async def create_session_from_google(user_data: dict, response: Response) -> dict:
    """
    Create or update user from Google OAuth data and create session.
    """
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email mancante dai dati Google")

    # Generate a session token
    session_token = uuid.uuid4().hex

    # Reuse the same user creation/update logic
    google_user_data = {
        "email": email,
        "name": user_data.get("name", ""),
        "picture": user_data.get("picture", ""),
        "session_token": session_token,
    }

    return await create_session(google_user_data, response)


async def verify_session(session_token: str) -> dict:
    """
    Verify session token and return user data (includes tenant_id).
    Also updates last_seen_at and silently extends sessions approaching expiry.
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Token di sessione mancante")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Sessione non valida")
    
    # Check expiry with timezone awareness
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    if expires_at < now:
        logger.info(f"Session expired: user={session_doc['user_id']}, expired_at={expires_at.isoformat()}")
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    
    # Silent session refresh: if session expires within 2 days, extend it
    remaining = (expires_at - now).total_seconds()
    update_fields = {"last_seen_at": now}
    if remaining < 2 * 86400:  # Less than 2 days left
        new_expiry = now + timedelta(days=settings.session_expire_days)
        update_fields["expires_at"] = new_expiry
        logger.info(f"Session auto-renewed: user={session_doc['user_id']}, new_expiry={new_expiry.isoformat()}")
    
    # Update last_seen_at (fire-and-forget, don't block response)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": update_fields}
    )
    
    # Get user
    user = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    
    # Ensure tenant_id is always present
    if "tenant_id" not in user:
        user["tenant_id"] = session_doc.get("tenant_id", "default")
    
    return user


async def get_current_user(request: Request) -> dict:
    """
    Get current authenticated user from cookies or Authorization header.
    WARNING: Don't use FastAPI's HTTPAuthorizationCredentials - it breaks cookie auth.
    """
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    # Fallback to query param — short-lived download token
    if not session_token:
        dl_token = request.query_params.get("token")
        if dl_token:
            dl_doc = await db.download_tokens.find_one({"token": dl_token}, {"_id": 0})
            if dl_doc:
                # Consume token (one-time use)
                await db.download_tokens.delete_one({"token": dl_token})
                expires = dl_doc.get("expires_at")
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                if expires and expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires and expires > datetime.now(timezone.utc):
                    user = await db.users.find_one(
                        {"user_id": dl_doc["user_id"]}, {"_id": 0}
                    )
                    if user:
                        if "tenant_id" not in user:
                            user["tenant_id"] = "default"
                        return user
            raise HTTPException(status_code=401, detail="Token di download non valido o scaduto")
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    return await verify_session(session_token)


async def create_download_token(user_id: str) -> str:
    """Create a short-lived one-time download token (60 seconds)."""
    token = uuid.uuid4().hex
    await db.download_tokens.insert_one({
        "token": token,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=60),
        "created_at": datetime.now(timezone.utc),
    })
    return token


async def delete_session(request: Request, response: Response) -> bool:
    """
    Delete user session and clear cookie.
    """
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    
    return True
