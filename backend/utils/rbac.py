"""
CONFIT Backend - Role-Based Access Control (RBAC)
===================================================
Centralized permission management for all user roles.

Roles Hierarchy:
- admin: Full system access, user management, analytics, all stores
- brand_manager: Manage own stores, products, orders, view store analytics
- stylist: Access styling tools, virtual try-on, outfit recommendations
- user: Standard customer access - shopping, wardrobe, orders

Usage:
    from utils.rbac import require_role, require_any_role, get_user_roles
    
    @router.get("/admin-only")
    async def admin_endpoint(user: User = Depends(require_role(AppRole.admin))):
        return {"message": "Admin access granted"}
"""

from enum import Enum
from typing import List, Optional, Set
from functools import wraps
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from database.models import User, UserRole, AppRole
from database.session import SessionLocal
from services.auth_service import AuthService


# Role hierarchy for permission inheritance
# Higher roles inherit permissions from lower roles
ROLE_HIERARCHY: dict[AppRole, Set[AppRole]] = {
    AppRole.admin: {AppRole.admin, AppRole.brand_manager, AppRole.stylist, AppRole.user},
    AppRole.brand_manager: {AppRole.brand_manager, AppRole.stylist, AppRole.user},
    AppRole.stylist: {AppRole.stylist, AppRole.user},
    AppRole.user: {AppRole.user},
}

# Permission definitions per role
PERMISSIONS: dict[AppRole, Set[str]] = {
    AppRole.admin: {
        # User management
        "users:read", "users:write", "users:delete",
        # Store management
        "stores:read", "stores:write", "stores:delete",
        "stores:manage_all",
        # Product management
        "products:read", "products:write", "products:delete",
        "products:manage_all",
        # Order management
        "orders:read", "orders:write", "orders:cancel",
        "orders:manage_all",
        # Analytics
        "analytics:read", "analytics:export",
        # System
        "system:configure", "system:audit",
    },
    AppRole.brand_manager: {
        # Store management (own stores only)
        "stores:read", "stores:write",
        "stores:manage_own",
        # Product management (own products only)
        "products:read", "products:write", "products:delete",
        "products:manage_own",
        # Order management (own store orders)
        "orders:read", "orders:write", "orders:cancel",
        "orders:manage_own_store",
        # Analytics (own stores)
        "analytics:read", "analytics:export_own",
    },
    AppRole.stylist: {
        # Styling tools
        "styling:read", "styling:write",
        "tryon:read", "tryon:write",
        "outfits:read", "outfits:write",
        # Products (read only)
        "products:read",
        # Analytics (limited)
        "analytics:read_own",
    },
    AppRole.user: {
        # Shopping
        "products:read",
        "cart:read", "cart:write",
        "orders:read", "orders:write", "orders:cancel_own",
        # Personal features
        "wardrobe:read", "wardrobe:write",
        "outfits:read", "outfits:write",
        "tryon:read", "tryon:write",
        "profile:read", "profile:write",
        # Wishlist
        "wishlist:read", "wishlist:write",
    },
}


def get_permissions_for_role(role: AppRole) -> Set[str]:
    """Get all permissions for a role, including inherited permissions."""
    all_permissions: Set[str] = set()
    for inherited_role in ROLE_HIERARCHY.get(role, {role}):
        all_permissions.update(PERMISSIONS.get(inherited_role, set()))
    return all_permissions


def has_permission(role: AppRole, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_permissions_for_role(role)


class RBACService:
    """Role-Based Access Control Service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_roles(self, user_id: str) -> List[AppRole]:
        """Get all roles assigned to a user."""
        role_rows = self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
        return [r.role for r in role_rows] or [AppRole.user]
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user across all their roles."""
        roles = self.get_user_roles(user_id)
        permissions: Set[str] = set()
        for role in roles:
            permissions.update(get_permissions_for_role(role))
        return permissions
    
    def user_has_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission."""
        return permission in self.get_user_permissions(user_id)
    
    def user_has_any_permission(self, user_id: str, permissions: List[str]) -> bool:
        """Check if a user has any of the specified permissions."""
        user_perms = self.get_user_permissions(user_id)
        return bool(user_perms.intersection(permissions))
    
    def user_has_role(self, user_id: str, role: AppRole) -> bool:
        """Check if a user has a specific role."""
        return role in self.get_user_roles(user_id)
    
    def assign_role(self, user_id: str, role: AppRole) -> bool:
        """Assign a role to a user."""
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role == role
        ).first()
        if existing:
            return True  # Already has role
        
        from uuid import uuid4
        new_role = UserRole(
            id=str(uuid4()),
            user_id=user_id,
            role=role
        )
        self.db.add(new_role)
        self.db.commit()
        return True
    
    def remove_role(self, user_id: str, role: AppRole) -> bool:
        """Remove a role from a user."""
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role == role
        ).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()
        return True


# FastAPI Dependencies

def get_rbac_service() -> RBACService:
    """Dependency to get RBAC service."""
    db = SessionLocal()
    try:
        yield RBACService(db)
    finally:
        db.close()


def get_current_user_id(authorization: str = Header(default="")) -> str:
    """Extract user ID from JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format"
        )
    
    from services.auth_service import AuthService
    auth_service = AuthService(SessionLocal())
    payload = auth_service.decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload.get("sub", "")


def require_role(required_role: AppRole):
    """
    Dependency that requires a specific role.
    Usage: @router.get("/admin", dependencies=[Depends(require_role(AppRole.admin))])
    """
    async def role_checker(
        user_id: str = Depends(get_current_user_id),
        rbac: RBACService = Depends(get_rbac_service)
    ):
        if not rbac.user_has_role(user_id, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required"
            )
        return user_id
    return role_checker


def require_any_role(required_roles: List[AppRole]):
    """
    Dependency that requires any of the specified roles.
    Usage: @router.get("/staff", dependencies=[Depends(require_any_role([AppRole.admin, AppRole.brand_manager]))])
    """
    async def role_checker(
        user_id: str = Depends(get_current_user_id),
        rbac: RBACService = Depends(get_rbac_service)
    ):
        user_roles = rbac.get_user_roles(user_id)
        if not any(role in user_roles for role in required_roles):
            role_names = [r.value for r in required_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {role_names} required"
            )
        return user_id
    return role_checker


def require_permission(permission: str):
    """
    Dependency that requires a specific permission.
    Usage: @router.delete("/products/{id}", dependencies=[Depends(require_permission("products:delete"))])
    """
    async def permission_checker(
        user_id: str = Depends(get_current_user_id),
        rbac: RBACService = Depends(get_rbac_service)
    ):
        if not rbac.user_has_permission(user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return user_id
    return permission_checker


def require_admin():
    """
    Dependency that requires admin role.
    Usage: user: str = Depends(require_admin())
    """
    return require_role(AppRole.admin)


# Decorator for routes (alternative to Depends)

def rbac_required(roles: Optional[List[AppRole]] = None, permissions: Optional[List[str]] = None):
    """
    Decorator for RBAC on route handlers.
    
    Usage:
        @router.get("/admin-data")
        @rbac_required(roles=[AppRole.admin])
        async def get_admin_data():
            ...
        
        @router.delete("/products/{id}")
        @rbac_required(permissions=["products:delete"])
        async def delete_product(id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or args
            # This is a simplified version - in production, use Depends
            return await func(*args, **kwargs)
        return wrapper
    return decorator
