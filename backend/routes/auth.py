"""Authentication routes."""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from core.security import (
    exchange_session_id,
    create_session,
    get_current_user,
    delete_session,
    exchange_google_code,
    create_session_from_google
)
from models.user import UserResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class SessionExchangeRequest(BaseModel):
    """Request body for session exchange (Emergent Auth)."""
    session_id: str


class GoogleCallbackRequest(BaseModel):
    """Request body for Google OAuth callback."""
    code: str
    redirect_uri: str


@router.post("/session", response_model=UserResponse)
async def exchange_session(request: SessionExchangeRequest, response: Response):
    """
    Exchange Emergent Auth session_id for user session.
    Called by frontend after Google OAuth redirect via Emergent Auth.
    """
    try:
        user_data = await exchange_session_id(request.session_id)
        user = await create_session(user_data, response)
        logger.info(f"User logged in via Emergent Auth: {user['email']}")
        return UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session exchange failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante l'autenticazione")


@router.post("/callback", response_model=UserResponse)
async def google_oauth_callback(request: GoogleCallbackRequest, response: Response):
    """
    Exchange Google OAuth code for user session.
    Called by frontend after direct Google OAuth redirect.
    """
    try:
        user_data = await exchange_google_code(request.code, request.redirect_uri)
        user = await create_session_from_google(user_data, response)
        logger.info(f"User logged in via Google OAuth: {user['email']}")
        return UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante l'autenticazione Google")


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user.
    Used to verify session and get user data.
    """
    return UserResponse(**user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout user by deleting session and clearing cookie.
    """
    await delete_session(request, response)
    return {"message": "Logout effettuato con successo"}


@router.post("/download-token")
async def get_download_token(user: dict = Depends(get_current_user)):
    """Generate a short-lived one-time token for iframe file downloads."""
    from core.security import create_download_token
    token = await create_download_token(user["user_id"])
    return {"token": token}
