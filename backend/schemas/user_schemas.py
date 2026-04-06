"""CONFIT Backend — User Schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator

from schemas.base import BaseSchema


# ── Request Schemas ─────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = Field(None, max_length=64)
    marketing_consent: Optional[bool] = False
    
    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    avatar_url: Optional[str] = Field(None, max_length=1024)
    style_preference: Optional[str] = Field(None, max_length=255)
    body_profile: Optional[Dict[str, Any]] = None
    budget_range: Optional[Dict[str, Any]] = None
    preferred_brands: Optional[List[str]] = None
    occasion_preferences: Optional[Dict[str, Any]] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserStyleUpdate(BaseModel):
    """Schema for updating style preference."""
    style_preference: str
    style_vector: Optional[Dict[str, float]] = None


class UserBodyProfileUpdate(BaseModel):
    """Schema for updating body profile."""
    height_cm: Optional[int] = Field(None, ge=100, le=250)
    weight_kg: Optional[int] = Field(None, ge=30, le=300)
    body_type: Optional[str] = None
    measurements: Optional[Dict[str, float]] = None


# ── Response Schemas ─────────────────────────────────────────────────────

class UserResponse(BaseSchema):
    """Schema for user response."""
    id: str
    name: str
    email: str
    phone: Optional[str]
    avatar_url: Optional[str]
    style_preference: Optional[str]
    created_at: datetime


class UserDetailResponse(UserResponse):
    """Detailed user response with profile data."""
    body_profile: Optional[Dict[str, Any]]
    budget_range: Optional[Dict[str, Any]]
    preferred_brands: Optional[List[str]]
    occasion_preferences: Optional[Dict[str, Any]]
    marketing_consent: Optional[bool]
    data_sharing_consent: Optional[bool]


class UserListResponse(BaseModel):
    """Paginated user list response."""
    total: int
    users: List[UserResponse]


class AuthTokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
