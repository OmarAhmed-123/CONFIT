export type NormalizedRole = 'admin' | 'brand_manager' | 'stylist' | 'user';

const ROLE_ALIASES: Record<string, NormalizedRole> = {
  admin: 'admin',
  brand: 'brand_manager',
  brand_manager: 'brand_manager',
  brand_partner: 'brand_manager',
  customer: 'user',
  shopper: 'user',
  stylist: 'stylist',
  user: 'user',
};

export function normalizeRole(role?: string | null): NormalizedRole {
  if (!role) return 'user';
  return ROLE_ALIASES[role.trim().toLowerCase()] || 'user';
}

export function normalizeRoles(roles?: Array<string | null | undefined>): NormalizedRole[] {
  if (!Array.isArray(roles) || roles.length === 0) {
    return ['user'];
  }

  const normalized = roles.map((role) => normalizeRole(role));
  return Array.from(new Set(normalized));
}

export function hasRole(
  roles: Array<string | null | undefined> | undefined,
  expectedRole: NormalizedRole
): boolean {
  return normalizeRoles(roles).includes(expectedRole);
}

export function getDefaultRouteForRoles(
  roles: Array<string | null | undefined> | undefined
): string {
  const normalizedRoles = normalizeRoles(roles);

  if (normalizedRoles.includes('admin')) return '/admin';
  if (normalizedRoles.includes('brand_manager')) return '/brand-dashboard';
  if (normalizedRoles.includes('stylist')) return '/stylist-dashboard';
  return '/';
}

// ===========================================
// User Object Role Helpers
// ===========================================

interface UserWithRoles {
  id?: string;
  role?: string | string[];
  roles?: string[];
  user_role?: string;
  app_role?: string;
}

/**
 * Extract roles from user object (handles various formats)
 */
export function getUserRoles(user: UserWithRoles | null | undefined): NormalizedRole[] {
  if (!user) return ['user'];

  // Handle array of roles
  if (Array.isArray(user.roles)) {
    return normalizeRoles(user.roles);
  }
  
  if (Array.isArray(user.role)) {
    return normalizeRoles(user.role);
  }

  // Handle single role string
  if (typeof user.role === 'string') {
    return normalizeRoles([user.role]);
  }

  if (typeof user.user_role === 'string') {
    return normalizeRoles([user.user_role]);
  }

  if (typeof user.app_role === 'string') {
    return normalizeRoles([user.app_role]);
  }

  return ['user'];
}

/**
 * Check if user is admin
 */
export function isAdmin(user: UserWithRoles | null | undefined): boolean {
  return getUserRoles(user).includes('admin');
}

/**
 * Check if user is brand manager
 */
export function isBrandManager(user: UserWithRoles | null | undefined): boolean {
  return getUserRoles(user).includes('brand_manager');
}

/**
 * Check if user is store owner (brand_manager or admin)
 */
export function isStoreOwner(user: UserWithRoles | null | undefined): boolean {
  const roles = getUserRoles(user);
  return roles.includes('brand_manager') || roles.includes('admin');
}

/**
 * Check if user is stylist
 */
export function isStylist(user: UserWithRoles | null | undefined): boolean {
  return getUserRoles(user).includes('stylist');
}

/**
 * Check if user has any staff role (admin, brand_manager, stylist)
 */
export function isStaff(user: UserWithRoles | null | undefined): boolean {
  const roles = getUserRoles(user);
  return roles.includes('admin') || roles.includes('brand_manager') || roles.includes('stylist');
}
