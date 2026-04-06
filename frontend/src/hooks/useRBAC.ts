/**
 * CONFIT Frontend - Role-Based Access Control Hook
 * ================================================
 * Provides role and permission checking for UI components and routes.
 */

import { useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { normalizeRoles } from '@/lib/auth/roles';

// Role enum matching backend
export enum AppRole {
  ADMIN = 'admin',
  BRAND_MANAGER = 'brand_manager',
  STYLIST = 'stylist',
  USER = 'user',
}

// Permission definitions (synced with backend)
export const PERMISSIONS = {
  // Admin permissions
  USERS_READ: 'users:read',
  USERS_WRITE: 'users:write',
  USERS_DELETE: 'users:delete',
  
  // Store permissions
  STORES_READ: 'stores:read',
  STORES_WRITE: 'stores:write',
  STORES_DELETE: 'stores:delete',
  STORES_MANAGE_ALL: 'stores:manage_all',
  STORES_MANAGE_OWN: 'stores:manage_own',
  
  // Product permissions
  PRODUCTS_READ: 'products:read',
  PRODUCTS_WRITE: 'products:write',
  PRODUCTS_DELETE: 'products:delete',
  PRODUCTS_MANAGE_ALL: 'products:manage_all',
  PRODUCTS_MANAGE_OWN: 'products:manage_own',
  
  // Order permissions
  ORDERS_READ: 'orders:read',
  ORDERS_WRITE: 'orders:write',
  ORDERS_CANCEL: 'orders:cancel',
  ORDERS_CANCEL_OWN: 'orders:cancel_own',
  ORDERS_MANAGE_ALL: 'orders:manage_all',
  ORDERS_MANAGE_OWN_STORE: 'orders:manage_own_store',
  
  // Analytics permissions
  ANALYTICS_READ: 'analytics:read',
  ANALYTICS_EXPORT: 'analytics:export',
  ANALYTICS_EXPORT_OWN: 'analytics:export_own',
  ANALYTICS_READ_OWN: 'analytics:read_own',
  
  // Styling permissions
  STYLING_READ: 'styling:read',
  STYLING_WRITE: 'styling:write',
  TRYON_READ: 'tryon:read',
  TRYON_WRITE: 'tryon:write',
  OUTFITS_READ: 'outfits:read',
  OUTFITS_WRITE: 'outfits:write',
  
  // User permissions
  CART_READ: 'cart:read',
  CART_WRITE: 'cart:write',
  WARDROBE_READ: 'wardrobe:read',
  WARDROBE_WRITE: 'wardrobe:write',
  PROFILE_READ: 'profile:read',
  PROFILE_WRITE: 'profile:write',
  WISHLIST_READ: 'wishlist:read',
  WISHLIST_WRITE: 'wishlist:write',
  
  // System
  SYSTEM_CONFIGURE: 'system:configure',
  SYSTEM_AUDIT: 'system:audit',
} as const;

// Role hierarchy for permission inheritance
const ROLE_HIERARCHY: Record<AppRole, AppRole[]> = {
  [AppRole.ADMIN]: [AppRole.ADMIN, AppRole.BRAND_MANAGER, AppRole.STYLIST, AppRole.USER],
  [AppRole.BRAND_MANAGER]: [AppRole.BRAND_MANAGER, AppRole.STYLIST, AppRole.USER],
  [AppRole.STYLIST]: [AppRole.STYLIST, AppRole.USER],
  [AppRole.USER]: [AppRole.USER],
};

// Permission sets per role
const ROLE_PERMISSIONS: Record<AppRole, Set<string>> = {
  [AppRole.ADMIN]: new Set([
    PERMISSIONS.USERS_READ, PERMISSIONS.USERS_WRITE, PERMISSIONS.USERS_DELETE,
    PERMISSIONS.STORES_READ, PERMISSIONS.STORES_WRITE, PERMISSIONS.STORES_DELETE, PERMISSIONS.STORES_MANAGE_ALL,
    PERMISSIONS.PRODUCTS_READ, PERMISSIONS.PRODUCTS_WRITE, PERMISSIONS.PRODUCTS_DELETE, PERMISSIONS.PRODUCTS_MANAGE_ALL,
    PERMISSIONS.ORDERS_READ, PERMISSIONS.ORDERS_WRITE, PERMISSIONS.ORDERS_CANCEL, PERMISSIONS.ORDERS_MANAGE_ALL,
    PERMISSIONS.ANALYTICS_READ, PERMISSIONS.ANALYTICS_EXPORT,
    PERMISSIONS.SYSTEM_CONFIGURE, PERMISSIONS.SYSTEM_AUDIT,
    PERMISSIONS.STYLING_READ, PERMISSIONS.STYLING_WRITE, PERMISSIONS.TRYON_READ, PERMISSIONS.TRYON_WRITE,
  ]),
  [AppRole.BRAND_MANAGER]: new Set([
    PERMISSIONS.STORES_READ, PERMISSIONS.STORES_WRITE, PERMISSIONS.STORES_MANAGE_OWN,
    PERMISSIONS.PRODUCTS_READ, PERMISSIONS.PRODUCTS_WRITE, PERMISSIONS.PRODUCTS_DELETE, PERMISSIONS.PRODUCTS_MANAGE_OWN,
    PERMISSIONS.ORDERS_READ, PERMISSIONS.ORDERS_WRITE, PERMISSIONS.ORDERS_CANCEL, PERMISSIONS.ORDERS_MANAGE_OWN_STORE,
    PERMISSIONS.ANALYTICS_READ, PERMISSIONS.ANALYTICS_EXPORT_OWN,
    PERMISSIONS.STYLING_READ, PERMISSIONS.TRYON_READ,
  ]),
  [AppRole.STYLIST]: new Set([
    PERMISSIONS.STYLING_READ, PERMISSIONS.STYLING_WRITE,
    PERMISSIONS.TRYON_READ, PERMISSIONS.TRYON_WRITE,
    PERMISSIONS.OUTFITS_READ, PERMISSIONS.OUTFITS_WRITE,
    PERMISSIONS.PRODUCTS_READ,
    PERMISSIONS.ANALYTICS_READ_OWN,
  ]),
  [AppRole.USER]: new Set([
    PERMISSIONS.PRODUCTS_READ,
    PERMISSIONS.CART_READ, PERMISSIONS.CART_WRITE,
    PERMISSIONS.ORDERS_READ, PERMISSIONS.ORDERS_WRITE, PERMISSIONS.ORDERS_CANCEL_OWN,
    PERMISSIONS.WARDROBE_READ, PERMISSIONS.WARDROBE_WRITE,
    PERMISSIONS.OUTFITS_READ, PERMISSIONS.OUTFITS_WRITE,
    PERMISSIONS.TRYON_READ, PERMISSIONS.TRYON_WRITE,
    PERMISSIONS.PROFILE_READ, PERMISSIONS.PROFILE_WRITE,
    PERMISSIONS.WISHLIST_READ, PERMISSIONS.WISHLIST_WRITE,
  ]),
};

export interface RBACResult {
  /** User's roles */
  roles: AppRole[];
  /** All permissions the user has */
  permissions: Set<string>;
  /** Check if user has a specific role */
  hasRole: (role: AppRole) => boolean;
  /** Check if user has any of the specified roles */
  hasAnyRole: (roles: AppRole[]) => boolean;
  /** Check if user has a specific permission */
  hasPermission: (permission: string) => boolean;
  /** Check if user has any of the specified permissions */
  hasAnyPermission: (permissions: string[]) => boolean;
  /** Check if user can access a specific feature */
  canAccess: (feature: string) => boolean;
  /** Is admin */
  isAdmin: boolean;
  /** Is brand manager */
  isBrandManager: boolean;
  /** Is stylist */
  isStylist: boolean;
  /** Is regular user */
  isUser: boolean;
}

/**
 * Hook for Role-Based Access Control
 * 
 * Usage:
 * ```tsx
 * const rbac = useRBAC();
 * 
 * if (rbac.hasPermission(PERMISSIONS.PRODUCTS_DELETE)) {
 *   // Show delete button
 * }
 * 
 * if (rbac.isAdmin) {
 *   // Show admin panel
 * }
 * ```
 */
export function useRBAC(): RBACResult {
  const { user } = useAuth();
  
  const roles = useMemo(() => {
    return normalizeRoles(user?.roles).map((role) => role as AppRole);
  }, [user?.roles]);
  
  const permissions = useMemo(() => {
    const allPermissions = new Set<string>();
    for (const role of roles) {
      for (const inheritedRole of ROLE_HIERARCHY[role] ?? [role]) {
        const rolePerms = ROLE_PERMISSIONS[inheritedRole];
        if (rolePerms) {
          for (const perm of rolePerms) {
            allPermissions.add(perm);
          }
        }
      }
    }
    return allPermissions;
  }, [roles]);
  
  const hasRole = (role: AppRole): boolean => {
    return roles.includes(role);
  };
  
  const hasAnyRole = (checkRoles: AppRole[]): boolean => {
    return checkRoles.some(role => roles.includes(role));
  };
  
  const hasPermission = (permission: string): boolean => {
    return permissions.has(permission);
  };
  
  const hasAnyPermission = (checkPermissions: string[]): boolean => {
    return checkPermissions.some(perm => permissions.has(perm));
  };
  
  const canAccess = (feature: string): boolean => {
    // Feature to permission mapping
    const featurePermissions: Record<string, string[]> = {
      'admin-panel': [PERMISSIONS.SYSTEM_CONFIGURE],
      'store-dashboard': [PERMISSIONS.STORES_MANAGE_OWN, PERMISSIONS.STORES_MANAGE_ALL],
      'product-management': [PERMISSIONS.PRODUCTS_WRITE],
      'order-management': [PERMISSIONS.ORDERS_READ],
      'analytics-dashboard': [PERMISSIONS.ANALYTICS_READ],
      'styling-tools': [PERMISSIONS.STYLING_READ],
      'virtual-tryon': [PERMISSIONS.TRYON_READ],
      'wardrobe': [PERMISSIONS.WARDROBE_READ],
      'wishlist': [PERMISSIONS.WISHLIST_READ],
      'cart': [PERMISSIONS.CART_READ],
      'profile': [PERMISSIONS.PROFILE_READ],
    };
    
    const requiredPerms = featurePermissions[feature];
    if (!requiredPerms) return true; // Unknown features are accessible by default
    return hasAnyPermission(requiredPerms);
  };
  
  return {
    roles,
    permissions,
    hasRole,
    hasAnyRole,
    hasPermission,
    hasAnyPermission,
    canAccess,
    isAdmin: hasRole(AppRole.ADMIN),
    isBrandManager: hasRole(AppRole.BRAND_MANAGER),
    isStylist: hasRole(AppRole.STYLIST),
    isUser: hasRole(AppRole.USER),
  };
}

/**
 * Component wrapper for role-based rendering
 * 
 * Usage:
 * ```tsx
 * <RequireRole role={AppRole.ADMIN}>
 *   <AdminPanel />
 * </RequireRole>
 * ```
 */
export function RequireRole({ 
  role, 
  children, 
  fallback = null 
}: { 
  role: AppRole | AppRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const rbac = useRBAC();
  const roles = Array.isArray(role) ? role : [role];
  
  if (rbac.hasAnyRole(roles)) {
    return children;
  }
  return fallback;
}

/**
 * Component wrapper for permission-based rendering
 * 
 * Usage:
 * ```tsx
 * <RequirePermission permission={PERMISSIONS.PRODUCTS_DELETE}>
 *   <DeleteButton />
 * </RequirePermission>
 * ```
 */
export function RequirePermission({ 
  permission, 
  children, 
  fallback = null 
}: { 
  permission: string | string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const rbac = useRBAC();
  const permissions = Array.isArray(permission) ? permission : [permission];
  
  if (rbac.hasAnyPermission(permissions)) {
    return children;
  }
  return fallback;
}
