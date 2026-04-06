'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useRBAC, AppRole } from '@/hooks/useRBAC';
import { Loader2 } from 'lucide-react';

// Route configuration with required roles
const PROTECTED_ROUTES: Record<string, { roles?: AppRole[]; permissions?: string[] }> = {
  '/admin': { roles: [AppRole.ADMIN] },
  '/brand-dashboard': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER] },
  '/store-dashboard': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER] },
  '/stylist-dashboard': { roles: [AppRole.ADMIN, AppRole.STYLIST] },
  '/analytics': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER] },
  '/notification-analytics': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER] },
  '/security': { roles: [AppRole.ADMIN] },
  '/payment-debug': { roles: [AppRole.ADMIN] },
  '/ai-stylist': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER, AppRole.STYLIST] },
  '/stylist': { roles: [AppRole.ADMIN, AppRole.BRAND_MANAGER, AppRole.STYLIST] },
  '/wardrobe': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/orders': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/profile': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/wishlist': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/try-on': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/outfits': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/cart': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
  '/checkout': { roles: [AppRole.USER, AppRole.STYLIST, AppRole.BRAND_MANAGER, AppRole.ADMIN] },
};

// Routes that require authentication but no specific role
const AUTH_REQUIRED_ROUTES = [
  '/profile',
  '/orders',
  '/wardrobe',
  '/wishlist',
  '/cart',
  '/checkout',
  '/try-on',
  '/outfits',
  '/notifications',
  '/notification-preferences',
];

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Protected Route Wrapper
 * Wraps children with authentication and role-based access control
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const safePathname = pathname || '/';
  const { isAuthenticated, isLoading } = useAuth();
  const rbac = useRBAC();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    if (isLoading) return;

    // Check if route requires authentication
    const routeConfig = PROTECTED_ROUTES[safePathname];
    const requiresAuth = routeConfig || AUTH_REQUIRED_ROUTES.includes(safePathname);

    if (requiresAuth && !isAuthenticated) {
      // Redirect to login with return URL
      router.replace(`/login?redirect=${encodeURIComponent(safePathname)}`);
      return;
    }

    // Check role requirements
    if (routeConfig?.roles && routeConfig.roles.length > 0) {
      const hasRequiredRole = rbac.hasAnyRole(routeConfig.roles);
      if (!hasRequiredRole) {
        // Redirect to unauthorized page or home
        router.replace('/?error=unauthorized');
        return;
      }
    }

    // Check permission requirements
    if (routeConfig?.permissions && routeConfig.permissions.length > 0) {
      const hasRequiredPermission = rbac.hasAnyPermission(routeConfig.permissions);
      if (!hasRequiredPermission) {
        router.replace('/?error=unauthorized');
        return;
      }
    }

    setIsChecking(false);
  }, [isAuthenticated, isLoading, rbac, router, safePathname]);

  // Show loading state while checking
  if (isLoading || isChecking) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Higher-order component for protecting pages
 * Usage: export default withAuth(MyPage)
 */
export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function ProtectedComponent(props: P) {
    return (
      <ProtectedRoute>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

/**
 * Higher-order component for role-protected pages
 * Usage: export default withRole(MyAdminPage, [AppRole.ADMIN])
 */
export function withRole<P extends object>(
  Component: React.ComponentType<P>,
  requiredRoles: AppRole[]
) {
  return function RoleProtectedComponent(props: P) {
    const rbac = useRBAC();
    const router = useRouter();

    useEffect(() => {
      if (!rbac.hasAnyRole(requiredRoles)) {
        router.replace('/?error=unauthorized');
      }
    }, [rbac, router]);

    if (!rbac.hasAnyRole(requiredRoles)) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <h1 className="text-2xl font-bold">Access Denied</h1>
          <p className="text-muted-foreground">You don't have permission to access this page.</p>
        </div>
      );
    }

    return <Component {...props} />;
  };
}

export default ProtectedRoute;
