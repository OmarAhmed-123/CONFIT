"""
CONFIT Backend - Authentication Dependencies
===========================================
FastAPI dependencies for JWT-based auth. Use Depends(get_auth_service)
in routers; the service is backed by the database session.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.auth_service import AuthService, UserProfile
from database.models import UserRole, AppRole


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Return an AuthService bound to the request's DB session."""
    return AuthService(db)


async def require_auth(
    authorization: str = Header(default=""),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserProfile:
    """
    FastAPI dependency - validates the JWT and returns the UserProfile.
    Raises 401 if missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    profile = auth_service.get_user_by_token(token)
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return profile


async def optional_auth(
    authorization: str = Header(default=""),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserProfile | None:
    """Returns UserProfile if valid token present, else None."""
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None

    return auth_service.get_user_by_token(token)


async def require_admin(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Require an authenticated admin user."""
    role_row = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if not role_row or role_row.role != AppRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Backward-compatible aliases used by utils.__init__ and validation scripts.
get_current_user = require_auth
get_optional_user = optional_auth
