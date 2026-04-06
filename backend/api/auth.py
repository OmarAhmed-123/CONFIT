"""
CONFIT Backend - Authentication API Routes
==========================================
User registration, login, OAuth, and token management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import get_auth_service, get_current_user, get_current_user_optional
from core.slowapi_limiter import limiter, LIMIT_AUTH_ENDPOINT, LIMIT_AUTHENTICATED
from application.services.auth_service import (
    AuthService,
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserDTO,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ResetPasswordConfirmRequest,
    OAuthLoginRequest,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRATION & LOGIN
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def register(
    request: RegisterRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account and return tokens for auto-login."""
    user, error = await auth_service.register(
        email=request.email,
        password=request.password,
        name=request.name,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Auto-login: generate tokens for the newly registered user
    roles = [r.role.value for r in user.roles if not r.is_expired()] if hasattr(user, 'roles') else []
    
    token_pair = await auth_service.jwt_handler.create_token_pair(
        user_id=str(user.id),
        email=user.email.address if hasattr(user.email, 'address') else user.email,
        roles=roles,
    )
    
    # Update last login
    await auth_service.user_repository.update_last_login(
        user_id=user.id,
        ip_address=http_request.client.host if http_request.client else "",
        user_agent=http_request.headers.get("user-agent", ""),
    )
    
    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=auth_service._to_dto(user),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login user",
)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return tokens."""
    response, error = await auth_service.login(
        email=request.email,
        password=request.password,
        device_id=request.device_id,
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("user-agent"),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return response


@router.post(
    "/login/form",
    response_model=LoginResponse,
    summary="Login with form data (OAuth2 compatible)",
)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def login_form(
    http_request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """OAuth2 compatible login endpoint."""
    response, error = await auth_service.login(
        email=form_data.username,
        password=form_data.password,
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("user-agent"),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return response


# ─────────────────────────────────────────────────────────────────────────────
# OAUTH
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/oauth/{provider}",
    summary="Get OAuth authorization URL",
)
async def get_oauth_url(
    provider: str,
    redirect_to: Optional[str] = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get OAuth authorization URL for provider."""
    url = auth_service.get_oauth_url(provider, redirect_to)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' not configured"
        )
    
    return {"authorization_url": url}


@router.post(
    "/oauth/{provider}/callback",
    response_model=LoginResponse,
    summary="Handle OAuth callback",
)
async def oauth_callback(
    provider: str,
    request: OAuthLoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle OAuth callback and authenticate user."""
    response, error = await auth_service.oauth_login(
        provider=provider,
        code=request.code,
        state=request.state,
        ip_address=http_request.client.host if http_request.client else None,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return response


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    summary="Refresh access token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    token_pair, error = await auth_service.refresh_tokens(request.refresh_token)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
        "expires_in": token_pair.expires_in,
    }


@router.post(
    "/logout",
    summary="Logout user",
)
async def logout(
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user and invalidate token."""
    # In production, add token to blacklist
    return {"message": "Successfully logged out"}


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/password/change",
    summary="Change password",
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change user password."""
    from uuid import UUID
    success, error = await auth_service.change_password(
        user_id=UUID(current_user.user_id),
        current_password=request.current_password,
        new_password=request.new_password,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Password changed successfully"}


@router.post(
    "/password/reset",
    summary="Request password reset",
)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def request_password_reset(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Request password reset email."""
    await auth_service.request_password_reset(request.email)
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post(
    "/password/reset/confirm",
    summary="Confirm password reset",
)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def confirm_password_reset(
    request: ResetPasswordConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Confirm password reset with token."""
    success, error = await auth_service.confirm_password_reset(
        token=request.token,
        new_password=request.new_password,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Password reset successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/email/verify/request",
    summary="Request email verification",
)
async def request_email_verification(
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Request email verification."""
    from uuid import UUID
    success, error = await auth_service.request_email_verification(
        UUID(current_user.user_id)
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Verification email sent"}


@router.post(
    "/email/verify/confirm",
    summary="Confirm email verification",
)
async def confirm_email_verification(
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Confirm email with verification token."""
    success, error = await auth_service.verify_email(token)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Email verified successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# USER INFO
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserDTO,
    summary="Get current user",
)
async def get_current_user_info(
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current authenticated user info."""
    from uuid import UUID
    user = await auth_service.get_user_by_id(UUID(current_user.user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
