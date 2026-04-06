/**
 * Next.js Middleware for Route Protection
 * Handles authentication and role-based access control at the middleware level
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that don't require authentication
const PUBLIC_ROUTES = [
  '/',
  '/login',
  '/register',
  '/forgot-password',
  '/auth/callback',
  '/auth/error',
  '/brands',
  '/discover',
  '/stores',
  '/terms',
  '/privacy',
];

// Routes that require specific roles
const ROLE_PROTECTED_ROUTES: Record<string, string[]> = {
  '/admin': ['admin'],
  '/brand-dashboard': ['admin', 'brand_manager'],
  '/store-dashboard': ['admin', 'brand_manager'],
  '/stylist-dashboard': ['admin', 'stylist'],
  '/analytics': ['admin', 'brand_manager'],
  '/notification-analytics': ['admin', 'brand_manager'],
  '/security': ['admin'],
  '/payment-debug': ['admin'],
  '/ai-stylist': ['admin', 'brand_manager', 'stylist'],
  '/stylist': ['admin', 'brand_manager', 'stylist'],
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
  '/care',
];

function isPublicRoute(pathname: string): boolean {
  // Check exact match
  if (PUBLIC_ROUTES.includes(pathname)) {
    return true;
  }
  
  // Check prefix for dynamic routes
  // Product pages are public
  if (pathname.startsWith('/product/')) {
    return true;
  }
  
  // API routes (except /api/auth/me) are handled by their own auth
  if (pathname.startsWith('/api/')) {
    return true;
  }
  
  // Static files
  if (pathname.includes('.') || pathname.startsWith('/_next')) {
    return true;
  }
  
  return false;
}

function getRequiredRoles(pathname: string): string[] | null {
  for (const [route, roles] of Object.entries(ROLE_PROTECTED_ROUTES)) {
    if (pathname.startsWith(route)) {
      return roles;
    }
  }
  return null;
}

function requiresAuth(pathname: string): boolean {
  if (AUTH_REQUIRED_ROUTES.some(route => pathname.startsWith(route))) {
    return true;
  }
  return getRequiredRoles(pathname) !== null;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip public routes
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }
  
  // Check for auth token in cookies
  const sessionToken = request.cookies.get('confit.session-token')?.value;
  const accessToken = request.cookies.get('confit_token')?.value;
  
  // For routes requiring authentication
  if (requiresAuth(pathname)) {
    if (!sessionToken && !accessToken) {
      // Redirect to login with return URL
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
    
    // Role-based protection is handled client-side via useRBAC hook
    // and server-side via API endpoints using require_role dependency
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
};
