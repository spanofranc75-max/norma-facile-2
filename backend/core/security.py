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


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    """
    Exchange Google OAuth authorization code for user data.
    Replaces the old Emergent exchange_session_id.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Exchange code for tokens
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        )

        if token_response.status_code != 200:
            logger.error(f"Google token exchange failed: {token_response.text}")
            raise HTTPException(status_code=401, detail="Autenticazione Google fallita")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=401, detail="Token Google non ricevuto")

        # Step 2: Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            logger.error(f"Google userinfo failed: {userinfo_response.text}")
            raise HTTPException(status_code=401, detail="Impossibile ottenere dati utente da Google")

        userinfo = userinfo_response.json()

        return {
            "email": userinfo.get("email"),
            "name": userinfo.get("name"),
            "picture": userinfo.get("picture"),
            "google_id": userinfo.get("id"),
        }


async def create_session(user_data: dict, response: Response) -> dict:
    """
    Create or update user in database and create session.
    Returns user document.
    """
    email = user_data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email non trovata nei dati utente")

    # Generate our own session token (no longer from Emergent)
    session_token = uuid.uuid4().hex + uuid.uuid4().hex

    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})

    if existing_user:
        user_id = existing_user["user_id"]
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "name": user_data.get("name"),
                "picture": user_data.get("picture"),
                "last_login": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }}
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
            new_user["role"] = invite["role"]
            new_user["team_owner_id"] = invite["admin_id"]
            await db.team_invites.update_one(
                {"_id": invite["_id"]},
                {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc), "accepted_user_id": user_id}},
            )
            logger.info(f"Invited user {email} joined with role {invite['role']}")
        else:
            total_users = await db.users.count_documents({})
            if total_users == 0:
                new_user["role"] = "admin"
            else:
                new_user["role"] = "guest"

        await db.users.insert_one(new_user)

    # Create session
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_expire_days)

    # Remove old sessions for this user
    await db.user_sessions.delete_many({"user_id": user_id})

    # Create new session
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc)
    })

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

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user


async def verify_session(session_token: str) -> dict:
    """Verify session token and return user data."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token di sessione mancante")

    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )

    if not session_doc:
        raise HTTPException(status_code=401, detail="Sessione non valida")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessione scaduta")

    user = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )

    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato")

    return user


async def get_current_user(request: Request) -> dict:
    """Get current authenticated user from cookies or Authorization header."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

    if not session_token:
        dl_token = request.query_params.get("token")
        if dl_token:
            dl_doc = await db.download_tokens.find_one({"token": dl_token}, {"_id": 0})
            if dl_doc:
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
    """Delete user session and clear cookie."""
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

