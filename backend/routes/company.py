"""Company settings routes."""
from fastapi import APIRouter, Depends, HTTPException
import uuid
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.company import CompanySettings, CompanySettingsUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/company", tags=["company"])


@router.get("/settings", response_model=CompanySettings)
async def get_company_settings(user: dict = Depends(get_current_user)):
    """Get company settings for current user."""
    settings = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not settings:
        # Return empty settings
        return CompanySettings(
            user_id=user["user_id"],
            business_name=user.get("name", ""),
            email=user.get("email", "")
        )
    
    return CompanySettings(**settings)


@router.put("/settings", response_model=CompanySettings)
async def update_company_settings(
    settings_data: CompanySettingsUpdate,
    user: dict = Depends(get_current_user)
):
    """Update company settings."""
    existing = await db.company_settings.find_one(
        {"user_id": user["user_id"]}
    )
    
    now = datetime.now(timezone.utc)
    
    if existing:
        # Update existing
        update_dict = {
            k: v for k, v in settings_data.model_dump().items()
            if v is not None
        }
        
        # Handle nested bank_details
        if settings_data.bank_details:
            update_dict["bank_details"] = settings_data.bank_details.model_dump()
        
        # Handle bank_accounts list
        if settings_data.bank_accounts is not None:
            update_dict["bank_accounts"] = settings_data.bank_accounts
        
        # Handle figure_aziendali list
        if settings_data.figure_aziendali is not None:
            update_dict["figure_aziendali"] = settings_data.figure_aziendali
        
        update_dict["updated_at"] = now
        
        await db.company_settings.update_one(
            {"user_id": user["user_id"]},
            {"$set": update_dict}
        )
    else:
        # Create new
        settings_id = f"settings_{uuid.uuid4().hex[:12]}"
        settings_doc = {
            "settings_id": settings_id,
            "user_id": user["user_id"],
            **{k: v for k, v in settings_data.model_dump().items() if v is not None},
            "updated_at": now
        }
        
        # Handle nested bank_details
        if settings_data.bank_details:
            settings_doc["bank_details"] = settings_data.bank_details.model_dump()
        
        # Handle bank_accounts list
        if settings_data.bank_accounts is not None:
            settings_doc["bank_accounts"] = settings_data.bank_accounts
        
        # Handle figure_aziendali list
        if settings_data.figure_aziendali is not None:
            settings_doc["figure_aziendali"] = settings_data.figure_aziendali
        
        await db.company_settings.insert_one(settings_doc)
    
    updated = await db.company_settings.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    logger.info(f"Company settings updated for user {user['user_id']}")
    return CompanySettings(**updated)
