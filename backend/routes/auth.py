"""Authentication routes."""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from core.security import exchange_google_code, create_session, get_current_user, delete_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/auth/callback")
async def google_callback(payload: GoogleCallbackRequest, response: Response):
    """Handle Google OAuth callback - exchange code for session."""
    user_data = await exchange_google_code(payload.code, payload.redirect_uri)
    user = await create_session(user_data, response)
    
    # Also return session token in response body for localStorage fallback
    from core.database import db
    session = await db.user_sessions.find_one({"user_id": user["user_id"]}, {"_id": 0})
    session_token = session["session_token"] if session else None
    
    logger.info(f"User logged in: {user.get('email')}")
    return {"user": user, "session_token": session_token}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user."""
    await delete_session(request, response)
    return {"message": "Logout effettuato"}


@router.get("/auth/me")
async def get_me(request: Request):
    """Get current user."""
    user = await get_current_user(request)
    return user


@router.post("/auth/download-token")
async def create_download_token_endpoint(request: Request):
    """Create a short-lived download token."""
    from core.security import create_download_token
    user = await get_current_user(request)
    token = await create_download_token(user["user_id"])
    return {"token": token}

