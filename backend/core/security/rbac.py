"""
CONFIT Backend - Role-Based Access Control (RBAC)
==================================================
Authorization system with roles, permissions, and resource access control.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from functools import wraps

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ─────────────────────────────────────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────────────────────────────────────

class Permission(str, Enum):
    """System permissions."""
    
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_MANAGE = "user:manage"
    
    # Product permissions
    PRODUCT_READ = "product:read"
    PRODUCT_WRITE = "product:write"
    PRODUCT_DELETE = "product:delete"
    PRODUCT_MANAGE = "product:manage"
    
    # Order permissions
    ORDER_READ = "order:read"
    ORDER_WRITE = "order:write"
    ORDER_CANCEL = "order:cancel"
    ORDER_MANAGE = "order:manage"
    
    # Brand permissions
    BRAND_READ = "brand:read"
    BRAND_WRITE = "brand:write"
    BRAND_DELETE = "brand:delete"
    BRAND_MANAGE = "brand:manage"
    BRAND_ANALYTICS = "brand:analytics"
    
    # Wardrobe permissions
    WARDROBE_READ = "wardrobe:read"
    WARDROBE_WRITE = "wardrobe:write"
    WARDROBE_DELETE = "wardrobe:delete"
    
    # Try-on permissions
    TRYLON_USE = "tryon:use"
    TRYLON_MANAGE = "tryon:manage"
    
    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    ADMIN_USERS = "admin:users"
    ADMIN_PRODUCTS = "admin:products"
    ADMIN_ORDERS = "admin:orders"
    ADMIN_ANALYTICS = "admin:analytics"
    ADMIN_SETTINGS = "admin:settings"
    
    # Payment permissions
    PAYMENT_PROCESS = "payment:process"
    PAYMENT_REFUND = "payment:refund"
    PAYMENT_MANAGE = "payment:manage"
    
    # Notification permissions
    NOTIFICATION_SEND = "notification:send"
    NOTIFICATION_MANAGE = "notification:manage"
    NOTIFICATION_ANALYTICS = "notification:analytics"


# ─────────────────────────────────────────────────────────────────────────────
# ROLES
# ─────────────────────────────────────────────────────────────────────────────

class Role(str, Enum):
    """System roles."""
    ADMIN = "admin"
    ANALYTICS = "analytics"
    STORE_OWNER = "store_owner"
    FACTORY_OWNER = "factory_owner"
    BRAND_MANAGER = "brand_manager"
    STYLIST = "stylist"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


# Role-Permission mappings
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Admin has all permissions
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE, Permission.USER_MANAGE,
        Permission.PRODUCT_READ, Permission.PRODUCT_WRITE, Permission.PRODUCT_DELETE, Permission.PRODUCT_MANAGE,
        Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.ORDER_CANCEL, Permission.ORDER_MANAGE,
        Permission.BRAND_READ, Permission.BRAND_WRITE, Permission.BRAND_DELETE, Permission.BRAND_MANAGE, Permission.BRAND_ANALYTICS,
        Permission.WARDROBE_READ, Permission.WARDROBE_WRITE, Permission.WARDROBE_DELETE,
        Permission.TRYLON_USE, Permission.TRYLON_MANAGE,
        Permission.ADMIN_ACCESS, Permission.ADMIN_USERS, Permission.ADMIN_PRODUCTS, Permission.ADMIN_ORDERS, Permission.ADMIN_ANALYTICS, Permission.ADMIN_SETTINGS,
        Permission.PAYMENT_PROCESS, Permission.PAYMENT_REFUND, Permission.PAYMENT_MANAGE,
    },
    Role.ANALYTICS: {
        Permission.ADMIN_ACCESS,
        Permission.ADMIN_ANALYTICS,
        Permission.BRAND_ANALYTICS,
        Permission.NOTIFICATION_ANALYTICS,
        Permission.ORDER_READ,
        Permission.PRODUCT_READ,
        Permission.USER_READ,
    },
    Role.STORE_OWNER: {
        Permission.USER_READ,
        Permission.PRODUCT_READ,
        Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.ORDER_MANAGE,
        Permission.BRAND_READ,
        Permission.NOTIFICATION_SEND, Permission.NOTIFICATION_MANAGE, Permission.NOTIFICATION_ANALYTICS,
        Permission.PAYMENT_PROCESS,
    },
    Role.FACTORY_OWNER: {
        Permission.USER_READ,
        Permission.PRODUCT_READ, Permission.PRODUCT_WRITE,
        Permission.ORDER_READ, Permission.ORDER_MANAGE,
        Permission.BRAND_READ, Permission.BRAND_WRITE,
        Permission.NOTIFICATION_SEND, Permission.NOTIFICATION_MANAGE, Permission.NOTIFICATION_ANALYTICS,
        Permission.PAYMENT_PROCESS,
    },
    Role.BRAND_MANAGER: {
        Permission.USER_READ,
        Permission.PRODUCT_READ, Permission.PRODUCT_WRITE, Permission.PRODUCT_DELETE, Permission.PRODUCT_MANAGE,
        Permission.ORDER_READ, Permission.ORDER_MANAGE,
        Permission.BRAND_READ, Permission.BRAND_WRITE, Permission.BRAND_ANALYTICS,
        Permission.TRYLON_USE,
        Permission.PAYMENT_PROCESS,
        Permission.NOTIFICATION_ANALYTICS,
    },
    Role.STYLIST: {
        Permission.USER_READ,
        Permission.PRODUCT_READ,
        Permission.ORDER_READ,
        Permission.BRAND_READ,
        Permission.WARDROBE_READ, Permission.WARDROBE_WRITE,
        Permission.TRYLON_USE,
    },
    Role.MODERATOR: {
        Permission.USER_READ,
        Permission.PRODUCT_READ,
        Permission.ORDER_READ,
        Permission.BRAND_READ,
        Permission.WARDROBE_READ,
        Permission.TRYLON_USE,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.PRODUCT_READ,
        Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.ORDER_CANCEL,
        Permission.BRAND_READ,
        Permission.WARDROBE_READ, Permission.WARDROBE_WRITE, Permission.WARDROBE_DELETE,
        Permission.TRYLON_USE,
        Permission.PAYMENT_PROCESS,
    },
    Role.GUEST: {
        Permission.PRODUCT_READ,
        Permission.BRAND_READ,
        Permission.ORDER_WRITE,
        Permission.PAYMENT_PROCESS,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# RBAC MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class RBACManager:
    """Role-Based Access Control manager."""
    
    def __init__(self):
        self._role_permissions = ROLE_PERMISSIONS.copy()
        self._custom_permissions: Dict[str, Set[Permission]] = {}
    
    def get_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role."""
        return self._role_permissions.get(role, set())
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has a specific permission."""
        return permission in self.get_permissions(role)
    
    def has_any_permission(self, role: Role, permissions: List[Permission]) -> bool:
        """Check if role has any of the specified permissions."""
        role_permissions = self.get_permissions(role)
        return any(p in role_permissions for p in permissions)
    
    def has_all_permissions(self, role: Role, permissions: List[Permission]) -> bool:
        """Check if role has all specified permissions."""
        role_permissions = self.get_permissions(role)
        return all(p in role_permissions for p in permissions)
    
    def add_permission_to_role(self, role: Role, permission: Permission) -> None:
        """Add permission to role (for dynamic permission assignment)."""
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].add(permission)
    
    def remove_permission_from_role(self, role: Role, permission: Permission) -> None:
        """Remove permission from role."""
        if role in self._role_permissions:
            self._role_permissions[role].discard(permission)
    
    def get_roles_with_permission(self, permission: Permission) -> List[Role]:
        """Get all roles that have a specific permission."""
        return [
            role for role, perms in self._role_permissions.items()
            if permission in perms
        ]
    
    def validate_role_transition(
        self,
        current_role: Role,
        new_role: Role,
        actor_role: Role
    ) -> bool:
        """Validate if actor can change user's role."""
        # Only admin can assign admin role
        if new_role == Role.ADMIN and actor_role != Role.ADMIN:
            return False
        
        # Brand managers can only assign brand_manager, stylist, user roles
        if actor_role == Role.BRAND_MANAGER:
            return new_role in [Role.BRAND_MANAGER, Role.STYLIST, Role.USER]
        
        # Admins can assign any role
        if actor_role == Role.ADMIN:
            return True
        
        return False


# ─────────────────────────────────────────────────────────────────────────────
# AUTH CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthContext:
    """Authentication context for request."""
    user_id: str
    email: str
    roles: List[Role] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    is_authenticated: bool = True
    is_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, roles: List[Role]) -> bool:
        """Check if user has any of the specified roles."""
        return any(r in self.roles for r in roles)
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return Role.ADMIN in self.roles
    
    def is_brand_manager(self) -> bool:
        """Check if user is a brand manager."""
        return Role.BRAND_MANAGER in self.roles
    
    def is_store_owner(self) -> bool:
        """Check if user is a store owner."""
        return Role.STORE_OWNER in self.roles
    
    def is_factory_owner(self) -> bool:
        """Check if user is a factory owner."""
        return Role.FACTORY_OWNER in self.roles
    
    def can_access_analytics(self) -> bool:
        """Check if user can access analytics."""
        return self.has_permission(Permission.NOTIFICATION_ANALYTICS) or self.is_admin()


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)
rbac_manager = RBACManager()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthContext]:
    """Get current authenticated user from JWT token."""
    if not credentials:
        return None
    
    from core.security.jwt_handler import jwt_handler
    
    token = credentials.credentials
    decoded = jwt_handler.validate_access_token(token)
    
    if not decoded or not decoded.valid:
        return None
    
    # Convert string roles to Role enum
    roles = []
    for r in decoded.roles:
        try:
            roles.append(Role(r))
        except ValueError:
            pass
    
    # Collect all permissions
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


async def get_current_user_required(
    current_user: Optional[AuthContext] = Depends(get_current_user),
) -> AuthContext:
    """Get current authenticated user (required)."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_permission(permission: Permission):
    """Dependency that requires a specific permission."""
    async def permission_checker(
        current_user: AuthContext = Depends(get_current_user_required),
    ) -> AuthContext:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}"
            )
        return current_user
    return Depends(permission_checker)


def require_role(role: Role):
    """Dependency that requires a specific role."""
    async def role_checker(
        current_user: AuthContext = Depends(get_current_user_required),
    ) -> AuthContext:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role.value}"
            )
        return current_user
    return Depends(role_checker)


def require_any_role(roles: List[Role]):
    """Dependency that requires any of the specified roles."""
    async def role_checker(
        current_user: AuthContext = Depends(get_current_user_required),
    ) -> AuthContext:
        if not current_user.has_any_role(roles):
            raise HTTPException(
                status_code=403,
                detail=f"One of these roles required: {[r.value for r in roles]}"
            )
        return current_user
    return Depends(role_checker)


def require_admin():
    """Dependency that requires admin role."""
    return require_role(Role.ADMIN)


def optional_auth(
    current_user: Optional[AuthContext] = Depends(get_current_user),
) -> Optional[AuthContext]:
    """Optional authentication - returns None if not authenticated."""
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE OWNERSHIP
# ─────────────────────────────────────────────────────────────────────────────

def check_resource_ownership(
    current_user: AuthContext,
    resource_user_id: str,
    allow_admin: bool = True,
) -> bool:
    """Check if user owns a resource or is admin."""
    if current_user.user_id == resource_user_id:
        return True
    
    if allow_admin and current_user.is_admin():
        return True
    
    return False


def require_ownership(
    resource_user_id_getter: Callable[[Request], str],
    allow_admin: bool = True,
):
    """
    Dependency that requires resource ownership.
    
    Usage:
        @app.get("/users/{user_id}/profile")
        async def get_profile(
            request: Request,
            current_user: AuthContext = Depends(
                require_ownership(lambda r: r.path_params["user_id"])
            ),
        ):
            ...
    """
    async def ownership_checker(
        request: Request,
        current_user: AuthContext = Depends(get_current_user_required),
    ) -> AuthContext:
        resource_user_id = resource_user_id_getter(request)
        
        if not check_resource_ownership(current_user, resource_user_id, allow_admin):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this resource"
            )
        return current_user
    
    return Depends(ownership_checker)
