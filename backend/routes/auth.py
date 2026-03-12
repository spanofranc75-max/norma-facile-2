"""Authentication routes."""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from core.security import (
    exchange_google_code,
    create_session,
    get_current_user,
    delete_session
)
from models.user import UserResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCallbackRequest(BaseModel):
    """Request body for Google OAuth callback."""
    code: str
    redirect_uri: str


@router.post("/callback", response_model=UserResponse)
async def google_callback(request: GoogleCallbackRequest, response: Response):
    """
    Handle Google OAuth callback.
    Frontend sends the 'code' received from Google redirect.
    """
    try:
        user_data = await exchange_google_code(request.code, request.redirect_uri)
        user = await create_session(user_data, response)
        logger.info(f"User logged in: {user['email']}")
        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante l'autenticazione")


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(**user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user."""
    await delete_session(request, response)
    return {"message": "Logout effettuato con successo"}


@router.post("/download-token")
async def get_download_token(user: dict = Depends(get_current_user)):
    """Generate a short-lived one-time token for iframe file downloads."""
    from core.security import create_download_token
    token = await create_download_token(user["user_id"])
    return {"token": token}

