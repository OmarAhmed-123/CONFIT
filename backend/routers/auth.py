"""
CONFIT Backend — Authentication Router
========================================
Endpoints for user registration, login, and profile retrieval.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, field_validator

from services.auth_service import AuthService
from utils.auth_deps import get_auth_service


class RefreshTokenRequest(BaseModel):
    """Body expected by SPA clients (e.g. api client)."""

    refresh_token: str = ""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Request / Response Models ──────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    date_of_birth: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD format

    # User type selection (shopper, brand_partner, stylist, admin)
    user_type: str = Field(default="shopper", pattern=r"^(shopper|brand_partner|stylist|admin)$")

    # Optional initial profile fields (USP)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    style_preference: Optional[str] = None
    body_profile: Optional[dict] = None
    budget_range: Optional[dict] = None
    preferred_brands: Optional[list[str]] = None
    occasion_preferences: Optional[list[str]] = None
    marketing_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None

    # Role-specific fields
    # Brand Partner fields
    brand_name: Optional[str] = Field(None, max_length=255)
    brand_description: Optional[str] = Field(None, max_length=1000)
    brand_website: Optional[str] = Field(None, max_length=500)
    brand_logo_url: Optional[str] = Field(None, max_length=1024)

    # Stylist fields
    stylist_bio: Optional[str] = Field(None, max_length=1000)
    stylist_specialties: Optional[list[str]] = None
    stylist_portfolio_url: Optional[str] = Field(None, max_length=500)
    stylist_experience_years: Optional[int] = Field(None, ge=0, le=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    access_token: Optional[str] = None  # OAuth-style alias used by the SPA API client
    refresh_token: Optional[str] = None
    user: Optional[dict] = None
    message: str = ""


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    style_preference: Optional[str] = None
    avatar_url: Optional[str] = None
    body_profile: Optional[dict] = None
    budget_range: Optional[dict] = None
    preferred_brands: Optional[list[str]] = None
    occasion_preferences: Optional[list[str]] = None
    marketing_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/exists")
async def email_exists(email: str, auth_service: AuthService = Depends(get_auth_service)):
    """Check whether an email is registered (for dynamic login/registration UX)."""
    try:
        row = auth_service.get_user_by_email(email)
        return {"exists": bool(row)}
    except Exception:
        # Don't leak server details; treat as not found for UX.
        return {"exists": False}


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    """Register a new user account."""
    # Parse date_of_birth if provided
    dob = None
    if request.date_of_birth:
        try:
            from datetime import datetime
            dob = datetime.strptime(request.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_of_birth format. Use YYYY-MM-DD.")
    
    profile, error = auth_service.register(
        name=request.name,
        email=request.email,
        password=request.password,
        date_of_birth=dob,
        phone=request.phone,
        address=request.address,
        style_preference=request.style_preference,
        body_profile=request.body_profile,
        budget_range=request.budget_range,
        preferred_brands=request.preferred_brands,
        occasion_preferences=request.occasion_preferences,
        marketing_consent=request.marketing_consent,
        data_sharing_consent=request.data_sharing_consent,
        user_type=request.user_type,
        # Brand partner fields
        brand_name=request.brand_name,
        brand_description=request.brand_description,
        brand_website=request.brand_website,
        brand_logo_url=request.brand_logo_url,
        # Stylist fields
        stylist_bio=request.stylist_bio,
        stylist_specialties=request.stylist_specialties,
        stylist_portfolio_url=request.stylist_portfolio_url,
        stylist_experience_years=request.stylist_experience_years,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    access_token = auth_service.create_token(profile.id, profile.email)
    refresh_token = auth_service.create_refresh_token(profile.id, profile.email)

    logger.info(f"New user registered: {profile.email}")
    return AuthResponse(
        success=True,
        token=access_token,
        access_token=access_token,
        refresh_token=refresh_token,
        user=profile.model_dump(),
        message="Account created successfully!",
    )


@router.post("/refresh")
async def refresh_session(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Rotate JWT using a valid refresh token (or the current access token in dev).
    Returns OAuth-style field names for compatibility with the frontend API client.
    """
    raw = (request.refresh_token or "").strip()
    if not raw:
        raise HTTPException(status_code=401, detail="refresh_token required")

    pair = auth_service.refresh_tokens(raw)
    if not pair:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token, refresh_token = pair
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    """Authenticate a user and return a JWT token."""
    profile, access_token, refresh_token, error = auth_service.login(
        email=request.email,
        password=request.password,
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    logger.info("User logged in: %s", profile.email)
    return AuthResponse(
        success=True,
        token=access_token,
        access_token=access_token,
        refresh_token=refresh_token,
        user=profile.model_dump(),
        message="Login successful!",
    )


@router.get("/me", response_model=AuthResponse)
async def get_current_user(
    authorization: str = Header(default=""),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get the current authenticated user profile."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    profile = auth_service.get_user_by_token(token)

    if not profile:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthResponse(
        success=True,
        user=profile.model_dump(),
        message="Profile retrieved successfully",
    )


@router.patch("/me", response_model=AuthResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    authorization: str = Header(default=""),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update user profile details."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    profile = auth_service.get_user_by_token(token)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        return AuthResponse(success=True, user=profile.model_dump(), message="No changes")

    updated_profile = auth_service.update_user(profile.email, updates)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="User not found")

    return AuthResponse(
        success=True,
        user=updated_profile.model_dump(),
        message="Profile updated successfully",
    )


@router.post("/forgot-password")
async def forgot_password(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request a password reset email.
    In development, returns a reset token for testing.
    """
    email_lower = request.email.lower().strip()
    user = auth_service.get_user_by_email(email_lower)
    
    if not user:
        # Don't reveal if email exists or not for security
        return {"success": True, "message": "If the email exists, a reset link will be sent."}
    
    # In production, send email with reset link
    # For development, return a reset token
    import secrets
    reset_token = secrets.token_urlsafe(32)
    
    # Store reset token (in production, this would be in database with expiry)
    # For now, we'll use a simple approach
    logger.info(f"Password reset requested for {email_lower}. Token: {reset_token}")
    
    return {
        "success": True, 
        "message": "If the email exists, a reset link will be sent.",
        # Remove this in production - only for development
        "dev_reset_token": reset_token if os.getenv("ENV", "development") == "development" else None,
    }


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    # In production, validate token from database
    # For now, accept any token in development
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # This is a simplified implementation
    # In production, you'd validate the token and associate it with a user
    return {"success": True, "message": "Password reset successfully. Please login."}


@router.get("/roles")
async def get_user_roles(
    authorization: str = Header(default=""),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get the current user's roles and permissions."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    profile = auth_service.get_user_by_token(token)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from utils.rbac import RBACService
    from database.session import SessionLocal
    
    db = SessionLocal()
    try:
        rbac = RBACService(db)
        roles = rbac.get_user_roles(profile.id)
        permissions = list(rbac.get_user_permissions(profile.id))
        
        return {
            "roles": [r.value for r in roles],
            "permissions": permissions,
        }
    finally:
        db.close()


@router.get("/health")
async def auth_health():
    """Health check for the auth service."""
    return {"status": "ok", "service": "authentication"}
