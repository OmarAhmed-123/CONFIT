"""
CONFIT Backend - Security Middleware
====================================
Input validation, secure headers, and request sanitization.
"""

from __future__ import annotations

import logging
import re
import secrets
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY HEADERS
# ─────────────────────────────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.stripe.com https://accept.paymob.com https://api.paypal.com; frame-src https://js.stripe.com https://accept.paymob.com https://www.paypal.com https://www.sandbox.paypal.com;",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp, extra_headers: Optional[Dict[str, str]] = None):
        super().__init__(app)
        self.headers = {**SECURITY_HEADERS, **(extra_headers or {})}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for key, value in self.headers.items():
            response.headers[key] = value
        return response


# ─────────────────────────────────────────────────────────────────────────────
# INPUT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

# Patterns for common injection attacks
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|\/\*|\*\/|;|@@|@)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(WAITFOR\s+DELAY)",
    r"(BENCHMARK\s*\()",
    r"(SLEEP\s*\()",
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"expression\s*\(",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"\.\.%2f",
    r"%2e%2e/",
]

# Compile patterns for performance
COMPILED_SQL = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
COMPILED_XSS = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
COMPILED_TRAVERSAL = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]


def detect_sql_injection(value: str) -> bool:
    """Check for SQL injection patterns."""
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in COMPILED_SQL)


def detect_xss(value: str) -> bool:
    """Check for XSS patterns."""
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in COMPILED_XSS)


def detect_path_traversal(value: str) -> bool:
    """Check for path traversal patterns."""
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in COMPILED_TRAVERSAL)


def validate_input(value: Any, field_name: str = "field") -> Optional[str]:
    """
    Validate input for common attack patterns.

    Returns:
        Error message if validation fails, None otherwise
    """
    if not isinstance(value, str):
        return None

    if detect_sql_injection(value):
        logger.warning("sql_injection_attempt field=%s value=%.50s", field_name, value)
        return f"Invalid input in {field_name}"

    if detect_xss(value):
        logger.warning("xss_attempt field=%s value=%.50s", field_name, value)
        return f"Invalid input in {field_name}"

    if detect_path_traversal(value):
        logger.warning("path_traversal_attempt field=%s value=%.50s", field_name, value)
        return f"Invalid input in {field_name}"

    return None


def validate_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Optional[str]:
    """Recursively validate dictionary values."""
    if depth > max_depth:
        return "Maximum nesting depth exceeded"

    for key, value in data.items():
        # Validate key
        if isinstance(key, str):
            error = validate_input(key, f"key_{key}")
            if error:
                return error

        # Validate value
        if isinstance(value, str):
            error = validate_input(value, key)
            if error:
                return error
        elif isinstance(value, dict):
            error = validate_dict(value, depth + 1, max_depth)
            if error:
                return error
        elif isinstance(value, list):
            error = validate_list(value, depth + 1, max_depth)
            if error:
                return error

    return None


def validate_list(data: List[Any], depth: int = 0, max_depth: int = 10) -> Optional[str]:
    """Recursively validate list values."""
    if depth > max_depth:
        return "Maximum nesting depth exceeded"

    for i, value in enumerate(data):
        if isinstance(value, str):
            error = validate_input(value, f"index_{i}")
            if error:
                return error
        elif isinstance(value, dict):
            error = validate_dict(value, depth + 1, max_depth)
            if error:
                return error
        elif isinstance(value, list):
            error = validate_list(value, depth + 1, max_depth)
            if error:
                return error

    return None


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate request body for injection attacks."""

    # Paths to skip validation (e.g., webhooks with encoded data)
    SKIP_PATHS: Set[str] = {
        "/api/payments/unified/webhooks/paymob",
        "/api/payments/unified/webhooks/paypal",
        "/api/payments/unified/webhooks/stripe",
        "/api/stripe/webhook",
    }

    # Max request body size (1MB)
    MAX_BODY_SIZE = 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip validation for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"},
            )

        # Validate query parameters
        for key, value in request.query_params.items():
            error = validate_input(value, key)
            if error:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": error},
                )

        # Validate path parameters
        for key, value in request.path_params.items():
            error = validate_input(str(value), key)
            if error:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": error},
                )

        # Validate request body for JSON requests
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    if isinstance(body, dict):
                        error = validate_dict(body)
                    elif isinstance(body, list):
                        error = validate_list(body)
                    else:
                        error = None

                    if error:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": error},
                        )
                except Exception:
                    # Let FastAPI handle JSON parsing errors
                    pass

        return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# CSRF PROTECTION
# ─────────────────────────────────────────────────────────────────────────────

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection for state-changing requests.

    Two protection modes:
    1. Cookie-based sessions: require X-CSRF-Token header matching csrf_token cookie
    2. API (Bearer token): CSRF not required but Origin header MUST match allowed origins
    """

    # Paths exempt from CSRF (APIs using other auth / webhook callbacks)
    EXEMPT_PATHS: Set[str] = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/oauth",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/password/reset",
        "/api/payments/bnpl/plan",
        "/api/payments/unified/webhooks",
        "/api/stripe/webhook",
        "/webhooks/",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
    }

    # Safe methods that don't need CSRF
    SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}

    # Allowed origins for Origin header verification
    ALLOWED_ORIGINS: Set[str] = set()

    def __init__(self, app: ASGIApp, secret: Optional[str] = None, allowed_origins: Optional[Set[str]] = None):
        super().__init__(app)
        self.secret = secret or secrets.token_hex(32)
        if allowed_origins:
            self.ALLOWED_ORIGINS = allowed_origins

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    def _verify_origin(self, request: Request) -> bool:
        """Verify Origin header for Bearer-authenticated API requests."""
        origin = request.headers.get("origin", "")
        if not origin:
            # Some API clients don't send Origin; allow if Referer matches instead
            referer = request.headers.get("referer", "")
            if referer:
                # Extract origin from referer
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            else:
                # Neither Origin nor Referer — reject for safety
                return False
        if not self.ALLOWED_ORIGINS:
            # No whitelist configured — allow (dev mode)
            return True
        return origin in self.ALLOWED_ORIGINS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for safe methods and exempt paths
        if request.method in self.SAFE_METHODS or self._is_exempt(request.url.path):
            return await call_next(request)

        # Check for CSRF token in header (cookie-based session protection)
        csrf_token = request.headers.get("X-CSRF-Token")
        cookie_token = request.cookies.get("csrf_token")

        if not csrf_token or not cookie_token:
            # For API endpoints with Bearer auth, CSRF token not required
            # but we verify the Origin header instead
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                if not self._verify_origin(request):
                    logger.warning("csrf_origin_mismatch path=%s origin=%s", request.url.path, request.headers.get("origin"))
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Invalid Origin header"},
                    )
                return await call_next(request)

            logger.warning("csrf_token_missing path=%s", request.url.path)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token required"},
            )

        # Validate tokens match
        if not secrets.compare_digest(csrf_token, cookie_token):
            logger.warning("csrf_token_mismatch path=%s", request.url.path)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid CSRF token"},
            )

        return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST SIZE LIMITS
# ─────────────────────────────────────────────────────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size."""

    # Default max size: 10MB
    DEFAULT_MAX_SIZE = 10 * 1024 * 1024

    # Path-specific limits
    PATH_LIMITS: Dict[str, int] = {
        "/api/upload": 50 * 1024 * 1024,  # 50MB for uploads
        "/api/try-on": 20 * 1024 * 1024,  # 20MB for try-on images
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if not content_length:
            return await call_next(request)

        max_size = self.DEFAULT_MAX_SIZE
        for path, limit in self.PATH_LIMITS.items():
            if request.url.path.startswith(path):
                max_size = limit
                break

        if int(content_length) > max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": f"Request body exceeds maximum size of {max_size // (1024 * 1024)}MB"},
            )

        return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY MIDDLEWARE SETUP
# ─────────────────────────────────────────────────────────────────────────────

def setup_security_middleware(app: FastAPI) -> None:
    """Add all security middleware to FastAPI app."""
    # Order matters: outermost middleware runs first
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(InputValidationMiddleware)
    # CSRF middleware is optional for API-only backends
    # app.add_middleware(CSRFMiddleware)

    logger.info("security_middleware_configured")
