"""Authentication routes."""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from core.security import (
    exchange_session_id,
    create_session,
    get_current_user,
    delete_session
)
from models.user import UserResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class SessionExchangeRequest(BaseModel):
    """Request body for session exchange."""
    session_id: str


@router.post("/session", response_model=UserResponse)
async def exchange_session(request: SessionExchangeRequest, response: Response):
    """
    Exchange Emergent Auth session_id for user session.
    Called by frontend after Google OAuth redirect.
    """
    try:
        # Exchange session_id with Emergent Auth
        user_data = await exchange_session_id(request.session_id)
        
        # Create/update user and session
        user = await create_session(user_data, response)
        
        logger.info(f"User logged in: {user['email']}")
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session exchange failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante l'autenticazione")


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
