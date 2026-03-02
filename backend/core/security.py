"""Security utilities for authentication."""
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Response
from .database import db
from .config import settings
import logging

logger = logging.getLogger(__name__)


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
    
    # Get full user data
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user


async def verify_session(session_token: str) -> dict:
    """
    Verify session token and return user data.
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
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    
    # Get user
    user = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    
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
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    
    return await verify_session(session_token)


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
