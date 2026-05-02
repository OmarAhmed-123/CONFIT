"""
CONFIT Backend — Authentication Router
========================================
Endpoints for user registration, login, and profile retrieval.
"""

import logging
import os
import socket
import smtplib
from html import escape
from email.message import EmailMessage
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from services.auth_service import AuthService, PASSWORD_RESET_EXPIRATION_MINUTES
from utils.auth_deps import get_auth_service
from core.slowapi_limiter import limiter, LIMIT_AUTH_ENDPOINT
from core.security.audit_log import audit_logger, AuditEventType, AuditOutcome, audit_context_from_request


class RefreshTokenRequest(BaseModel):
    """Body expected by SPA clients (e.g. api client)."""

    refresh_token: str = ""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Request / Response Models ──────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=12, max_length=128)
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


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=24, max_length=2048)
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class AuthResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
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


def _get_frontend_origin(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _email_domain_accepts_mail(email: str) -> bool:
    """Best-effort deliverability check before sending: syntax is validated by Pydantic, then MX/A lookup."""
    domain = email.rsplit("@", 1)[-1].strip().lower()
    if not domain or "." not in domain:
        return False

    try:
        import dns.resolver  # type: ignore

        answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        return any(str(answer.exchange).strip(".") for answer in answers)
    except Exception:
        try:
            socket.getaddrinfo(domain, None)
            return True
        except OSError:
            return False


def _is_configured_secret(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(normalized) and not any(
        placeholder in normalized
        for placeholder in ("your-", "change-me", "example", "placeholder")
    )


def _build_password_reset_message(to_email: str, name: str, reset_link: str) -> EmailMessage:
    safe_name = escape(name or "there")
    safe_link = escape(reset_link, quote=True)
    message = EmailMessage()
    message["Subject"] = "Reset your CONFIT password"
    message["From"] = f"{os.getenv('SMTP_FROM_NAME', 'CONFIT').strip()} <{os.getenv('SMTP_FROM_EMAIL', os.getenv('SMTP_USER', 'noreply@confit.app')).strip()}>"
    message["To"] = to_email
    message.set_content(
        "We received a request to reset your CONFIT password.\n\n"
        f"Open this secure link within {PASSWORD_RESET_EXPIRATION_MINUTES} minutes:\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h2>Reset your CONFIT password</h2>
          <p>Hello {safe_name},</p>
          <p>We received a request to reset your password. This secure link expires in {PASSWORD_RESET_EXPIRATION_MINUTES} minutes.</p>
          <p><a href="{safe_link}" style="display:inline-block;background:#111827;color:#ffffff;padding:12px 18px;border-radius:10px;text-decoration:none">Reset password</a></p>
          <p>If the button does not work, copy and paste this link into your browser:</p>
          <p>{safe_link}</p>
          <p>If you did not request this, you can ignore this email.</p>
        </div>
        """,
        subtype="html",
    )
    return message


def _send_password_reset_email_smtp(to_email: str, name: str, reset_link: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()

    if not smtp_host or not _is_configured_secret(smtp_user) or not _is_configured_secret(smtp_password):
        return False

    message = _build_password_reset_message(to_email, name, reset_link)
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False


async def _send_password_reset_email(to_email: str, name: str, reset_link: str) -> bool:
    """Send a password reset email using SendGrid first, then SMTP fallback."""
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if _is_configured_secret(sendgrid_key) and sendgrid_key.startswith("SG."):
        try:
            from services.integrations.sendgrid_client import get_sendgrid_client

            safe_name = escape(name or "there")
            result = await get_sendgrid_client().send_email(
                to_email=to_email,
                subject="Reset your CONFIT password",
                text_content=(
                    "We received a request to reset your CONFIT password.\n\n"
                    f"Open this secure link within {PASSWORD_RESET_EXPIRATION_MINUTES} minutes:\n"
                    f"{reset_link}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                html_content=(
                    f"<div style='font-family:Arial,sans-serif;line-height:1.6;color:#111827'>"
                    f"<h2>Reset your CONFIT password</h2>"
                    f"<p>Hello {safe_name},</p>"
                    f"<p>This secure link expires in {PASSWORD_RESET_EXPIRATION_MINUTES} minutes.</p>"
                    f"<p><a href='{escape(reset_link, quote=True)}' style='display:inline-block;background:#111827;color:#ffffff;padding:12px 18px;border-radius:10px;text-decoration:none'>Reset password</a></p>"
                    f"<p>{escape(reset_link)}</p>"
                    f"</div>"
                ),
                categories=["auth", "password-reset"],
            )
            return bool(result.get("success"))
        except Exception:
            logger.exception("SendGrid password reset email failed for %s; trying SMTP fallback", to_email)

    sent = await run_in_threadpool(_send_password_reset_email_smtp, to_email, name, reset_link)
    if not sent:
        logger.info("Email provider not configured or failed; password reset link for %s: %s", to_email, reset_link)
    return sent


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
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def register(
    request: Request,
    response: Response,
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    # Parse date_of_birth if provided
    dob = None
    if payload.date_of_birth:
        try:
            from datetime import datetime
            dob = datetime.strptime(payload.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_of_birth format. Use YYYY-MM-DD.")
    
    profile, error = auth_service.register(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        date_of_birth=dob,
        phone=payload.phone,
        address=payload.address,
        style_preference=payload.style_preference,
        body_profile=payload.body_profile,
        budget_range=payload.budget_range,
        preferred_brands=payload.preferred_brands,
        occasion_preferences=payload.occasion_preferences,
        marketing_consent=payload.marketing_consent,
        data_sharing_consent=payload.data_sharing_consent,
        user_type=payload.user_type,
        # Brand partner fields
        brand_name=payload.brand_name,
        brand_description=payload.brand_description,
        brand_website=payload.brand_website,
        brand_logo_url=payload.brand_logo_url,
        # Stylist fields
        stylist_bio=payload.stylist_bio,
        stylist_specialties=payload.stylist_specialties,
        stylist_portfolio_url=payload.stylist_portfolio_url,
        stylist_experience_years=payload.stylist_experience_years,
    )

    if error:
        ctx = audit_context_from_request(request)
        await audit_logger.log(
            event_type=AuditEventType.REGISTER_FAILED,
            actor_id=payload.email.lower().strip(),
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            outcome=AuditOutcome.FAILURE,
            details={"reason": error},
        )
        raise HTTPException(status_code=400, detail=error)

    access_token = auth_service.create_token(profile.id, profile.email)
    refresh_token = auth_service.create_refresh_token(profile.id, profile.email)

    ctx = audit_context_from_request(request)
    await audit_logger.log(
        event_type=AuditEventType.REGISTER,
        actor_id=str(profile.id),
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent"),
        outcome=AuditOutcome.SUCCESS,
        details={"email": profile.email},
    )

    logger.info(f"New user registered: {profile.email}")
    return AuthResponse(
        success=True,
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


@router.post("/logout")
async def logout(response: Response):
    """Stateless JWT logout endpoint for SPA clients."""
    response.delete_cookie("confit_token")
    response.delete_cookie("confit.session-token")
    return {"success": True}


@router.post("/login", response_model=AuthResponse)
@limiter.limit(LIMIT_AUTH_ENDPOINT)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate a user and return a JWT token."""
    from core.security.brute_force import brute_force_protector

    identifier = payload.email.lower().strip()
    locked_out, retry_after = await brute_force_protector.is_locked_out(identifier)
    if locked_out:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {retry_after} seconds."
        )

    profile, access_token, refresh_token, error = auth_service.login(
        email=payload.email,
        password=payload.password,
    )

    if error:
        await brute_force_protector.record_failed_attempt(identifier)
        # Audit log failed login
        ctx = audit_context_from_request(request)
        await audit_logger.log(
            event_type=AuditEventType.LOGIN_FAILED,
            actor_id=identifier,
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            outcome=AuditOutcome.FAILURE,
            details={"reason": error},
        )
        raise HTTPException(status_code=401, detail=error)

    await brute_force_protector.reset(identifier)

    # Audit log successful login
    ctx = audit_context_from_request(request)
    await audit_logger.log(
        event_type=AuditEventType.LOGIN,
        actor_id=str(profile.id),
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent"),
        outcome=AuditOutcome.SUCCESS,
        details={"email": profile.email},
    )

    logger.info("User logged in: %s", profile.email)
    return AuthResponse(
        success=True,
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
    payload: ForgotPasswordRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request a password reset email.
    In development, returns a reset token for testing.
    """
    email_lower = payload.email.lower().strip()
    user, reset_token = auth_service.create_password_reset_token_for_email(email_lower)

    ctx = audit_context_from_request(http_request)

    if not _email_domain_accepts_mail(email_lower):
        await audit_logger.log(
            event_type=AuditEventType.PASSWORD_RESET_REQUEST,
            actor_id=email_lower,
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            outcome=AuditOutcome.FAILURE,
            details={"reason": "Email domain does not accept mail"},
        )
        return {"success": True, "message": "If the email exists, a reset link will be sent."}

    if not user:
        # Don't reveal if email exists or not for security
        await audit_logger.log(
            event_type=AuditEventType.PASSWORD_RESET_REQUEST,
            actor_id=email_lower,
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            outcome=AuditOutcome.FAILURE,
            details={"reason": "User not found"},
        )
        return {"success": True, "message": "If the email exists, a reset link will be sent."}

    if not reset_token:
        return {"success": True, "message": "If the email exists, a reset link will be sent."}

    reset_link = f"{_get_frontend_origin(http_request)}/reset-password?token={quote(reset_token)}"
    email_sent = await _send_password_reset_email(user.email, user.name, reset_link)

    await audit_logger.log(
        event_type=AuditEventType.PASSWORD_RESET_REQUEST,
        actor_id=email_lower,
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent"),
        outcome=AuditOutcome.SUCCESS,
        details={"email_sent": email_sent},
    )

    response = {
        "success": True,
        "message": "If the email exists, a reset link will be sent.",
    }
    if os.getenv("ENV", "development") == "development":
        response["dev_reset_link"] = reset_link
    return response


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    profile, access_token, refresh_token, error = auth_service.reset_password_with_token(
        payload.token,
        payload.new_password,
    )
    if error or not profile or not access_token:
        raise HTTPException(status_code=400, detail=error or "Unable to reset password")

    ctx = audit_context_from_request(http_request)
    await audit_logger.log(
        event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
        actor_id=profile.email,
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent"),
        outcome=AuditOutcome.SUCCESS,
        details={"user_id": profile.id},
    )

    return AuthResponse(
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
        user=profile.model_dump(),
        message="Password reset successfully.",
    )


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
