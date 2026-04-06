"""
CONFIT Backend - API Dependencies
=================================
FastAPI dependency injection for services and authentication.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import get_async_session
from core.security.jwt_handler import jwt_handler
from core.security.rbac import AuthContext, Role, RBACManager


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE DEPENDENCY
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """Get database session."""
    async for session in get_async_session():
        yield session


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)
rbac_manager = RBACManager()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthContext]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    token = credentials.credentials
    decoded = jwt_handler.validate_access_token(token)
    
    if not decoded or not decoded.valid:
        return None
    
    roles = []
    for r in decoded.roles:
        try:
            roles.append(Role(r))
        except ValueError:
            pass
    
    permissions = set()
    for role in roles:
        permissions.update(rbac_manager.get_permissions(role))
    
    return AuthContext(
        user_id=decoded.user_id,
        email=decoded.email,
        roles=roles,
        permissions=permissions,
        is_authenticated=True,
    )


async def get_current_user(
    current_user: Optional[AuthContext] = Depends(get_current_user_optional),
) -> AuthContext:
    """Get current authenticated user (required)."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_user_id(
    current_user: AuthContext = Depends(get_current_user),
) -> UUID:
    """Get current user ID."""
    return UUID(current_user.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_product_service(
    db: AsyncSession = Depends(get_db),
):
    """Get product service."""
    from application.services.product_service import ProductService
    return ProductService(db)


async def get_checkout_service(
    db: AsyncSession = Depends(get_db),
):
    """Get checkout service."""
    from application.services.checkout_service import CheckoutService
    return CheckoutService(db)


async def get_tryon_service(
    db: AsyncSession = Depends(get_db),
):
    """Get virtual try-on service."""
    from application.services.tryon_service import VirtualTryOnService
    return VirtualTryOnService(db)


async def get_visual_search_service(
    db: AsyncSession = Depends(get_db),
):
    """Get visual search service."""
    from application.services.visual_search_service import VisualSearchService
    return VisualSearchService(db)


async def get_wardrobe_service(
    db: AsyncSession = Depends(get_db),
):
    """Get wardrobe service."""
    from application.services.wardrobe_service import WardrobeService
    return WardrobeService(db)


async def get_recommendation_service(
    db: AsyncSession = Depends(get_db),
):
    """Get recommendation service."""
    from application.services.recommendation_service import RecommendationEngine
    return RecommendationEngine(db)


async def get_brand_service(
    db: AsyncSession = Depends(get_db),
):
    """Get brand service."""
    from application.services.brand_service import BrandService
    return BrandService(db)


# ─────────────────────────────────────────────────────────────────────────────
# PERMISSION DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

from core.security.rbac import Permission


def require_permission(permission: Permission):
    """Require specific permission."""
    async def checker(
        current_user: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}"
            )
        return current_user
    return Depends(checker)


def require_role(role: Role):
    """Require specific role."""
    async def checker(
        current_user: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role.value}"
            )
        return current_user
    return Depends(checker)


def require_admin():
    """Require admin role."""
    return require_role(Role.ADMIN)


def require_brand_manager():
    """Require brand manager role."""
    return require_role(Role.BRAND_MANAGER)
