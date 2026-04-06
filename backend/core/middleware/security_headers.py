"""
CONFIT Backend - Security Headers Middleware
============================================
OWASP-recommended security headers for production.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds OWASP-recommended security headers to all responses.
    
    Headers implemented:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    - Cross-Origin-Opener-Policy
    - Cross-Origin-Resource-Policy
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Skip for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/readiness", "/liveness"]:
            return response
        
        # HSTS - Force HTTPS (1 year, include subdomains)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        csp = self._build_csp()
        if csp:
            response.headers["Content-Security-Policy"] = csp
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        # COOP and CORP for cross-origin isolation
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Cache Control for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response
    
    def _build_csp(self) -> str:
        """Build Content Security Policy based on environment."""
        if settings.is_production:
            # Production CSP - strict
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "  # unsafe-inline needed for styled-components
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.stripe.com https://uploads.stripe.com; "
                "frame-src https://js.stripe.com https://hooks.stripe.com https://www.affirm.com https://www.klarna.com https://www.afterpay.com; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "upgrade-insecure-requests"
            )
        else:
            # Development CSP - more permissive
            return (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' http://localhost:* ws://localhost:* https://api.stripe.com; "
                "frame-src https://js.stripe.com; "
                "object-src 'none'"
            )


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS security with origin validation.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        origin = request.headers.get("origin", "")
        
        # Validate origin
        if origin and self._is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-Request-ID, X-Correlation-ID, "
                "X-CSRF-Token, X-Requested-With"
            )
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
            response.headers["Access-Control-Expose-Headers"] = (
                "X-Request-ID, X-Correlation-ID, X-RateLimit-Limit, "
                "X-RateLimit-Remaining, X-RateLimit-Reset"
            )
        elif settings.is_production:
            # In production, reject requests from unknown origins
            logger.warning(f"Rejected CORS request from unknown origin: {origin}")
        
        return response
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        allowed = settings.cors_origins
        if "*" in allowed:
            return True
        return origin in allowed
