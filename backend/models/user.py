"""User models."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    name: str
    picture: Optional[str] = None


class UserCreate(UserBase):
    """Model for creating a user."""
    pass


class User(UserBase):
    """Full user model with ID and timestamps."""
    model_config = ConfigDict(extra="ignore")
    
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserResponse(BaseModel):
    """User response model for API."""
    model_config = ConfigDict(extra="ignore")
    
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: Optional[str] = "admin"  # Default admin for backward compat
    is_demo: Optional[bool] = False
