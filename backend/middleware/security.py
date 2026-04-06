"""
CONFIT Backend — Security Middleware
====================================
Security enhancements for the Discovery & Styling Experience:
- Rate limiting for AI endpoints
- Input validation and sanitization
- Request logging for audit trails
- CORS configuration
- API key protection
"""

import time
import logging
from typing import Callable, Dict, Optional
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ── Rate Limiting ────────────────────────────────────────────────────

class RateLimiter:
    """
    Sliding window rate limiter with per-endpoint limits.
    Protects AI endpoints from abuse.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 500,
        burst_limit: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Track requests: {user_id: [(timestamp, endpoint), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        
        # Endpoint-specific limits
        self._endpoint_limits = {
            "/api/stylist/chat": {"rpm": 30, "burst": 5},
            "/api/brain/recommendations": {"rpm": 20, "burst": 3},
            "/api/brain/track": {"rpm": 100, "burst": 20},
            "/api/outfits": {"rpm": 60, "burst": 10},
        }
    
    def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
    ) -> tuple[bool, Optional[dict]]:
        """
        Check if request is within rate limits.
        Returns (allowed, rate_limit_info).
        """
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        # Get user's request history
        requests = self._requests[user_id]
        
        # Clean old entries
        requests[:] = [
            (ts, ep) for ts, ep in requests
            if ts > hour_ago
        ]
        
        # Count recent requests
        minute_requests = sum(
            1 for ts, ep in requests
            if ts > minute_ago and ep == endpoint
        )
        hour_requests = len(requests)
        burst_requests = sum(
            1 for ts, ep in requests
            if ts > now - timedelta(seconds=10) and ep == endpoint
        )
        
        # Get endpoint-specific limits or defaults
        limits = self._endpoint_limits.get(endpoint, {
            "rpm": self.requests_per_minute,
            "burst": self.burst_limit,
        })
        
        # Check limits
        if burst_requests >= limits["burst"]:
            return False, {
                "reason": "burst_exceeded",
                "retry_after": 10,
                "limit": limits["burst"],
            }
        
        if minute_requests >= limits["rpm"]:
            return False, {
                "reason": "minute_limit_exceeded",
                "retry_after": 60,
                "limit": limits["rpm"],
            }
        
        if hour_requests >= self.requests_per_hour:
            return False, {
                "reason": "hour_limit_exceeded",
                "retry_after": 3600,
                "limit": self.requests_per_hour,
            }
        
        # Record this request
        requests.append((now, endpoint))
        
        return True, None
    
    def get_usage_stats(self, user_id: str) -> dict:
        """Get rate limit usage stats for a user."""
        now = datetime.now(timezone.utc)
        requests = self._requests.get(user_id, [])
        
        minute_requests = sum(
            1 for ts, _ in requests
            if ts > now - timedelta(minutes=1)
        )
        hour_requests = sum(
            1 for ts, _ in requests
            if ts > now - timedelta(hours=1)
        )
        
        return {
            "minute_usage": minute_requests,
            "hour_usage": hour_requests,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
        }


# ── Input Sanitization ───────────────────────────────────────────────

class InputSanitizer:
    """
    Sanitizes user inputs to prevent injection attacks.
    """
    
    # Patterns to detect potential attacks
    SUSPICIOUS_PATTERNS = [
        "<script", "javascript:", "onerror=", "onload=",
        "eval(", "exec(", "import ", "__import__",
        "DROP TABLE", "DELETE FROM", "INSERT INTO",
        "UNION SELECT", "--", "/*", "*/",
    ]
    
    MAX_STRING_LENGTH = 5000
    MAX_MESSAGE_LENGTH = 2000
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = None) -> str:
        """Sanitize a string input."""
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        
        max_len = max_length or cls.MAX_STRING_LENGTH
        
        # Truncate
        if len(value) > max_len:
            value = value[:max_len]
        
        # Remove null bytes
        value = value.replace("\x00", "")
        
        # Strip control characters except newlines and tabs
        value = "".join(
            c for c in value
            if c.isprintable() or c in "\n\t"
        )
        
        return value.strip()
    
    @classmethod
    def check_for_injection(cls, value: str) -> tuple[bool, Optional[str]]:
        """
        Check for potential injection patterns.
        Returns (is_safe, detected_pattern).
        """
        if not isinstance(value, str):
            return True, None
        
        lower = value.lower()
        
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern.lower() in lower:
                return False, pattern
        
        return True, None
    
    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """Sanitize a chat message for the stylist."""
        sanitized = cls.sanitize_string(message, cls.MAX_MESSAGE_LENGTH)
        
        is_safe, pattern = cls.check_for_injection(sanitized)
        if not is_safe:
            logger.warning(
                "Potential injection detected in message: %s",
                pattern
            )
            # Remove the suspicious pattern
            sanitized = sanitized.replace(pattern, "")
        
        return sanitized


# ── Security Middleware ──────────────────────────────────────────────

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for security checks.
    """
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self._protected_endpoints = [
            "/api/stylist",
            "/api/brain",
            "/api/outfits",
            "/api/signals",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security checks."""
        
        # Skip non-API routes
        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)
        
        # Get user ID from auth (if available)
        user_id = self._get_user_id(request)
        
        # Rate limiting for protected endpoints
        if any(path.startswith(ep) for ep in self._protected_endpoints):
            if user_id:
                allowed, rate_info = self.rate_limiter.check_rate_limit(
                    user_id, path
                )
                
                if not allowed:
                    logger.warning(
                        "Rate limit exceeded for user %s on %s: %s",
                        user_id, path, rate_info
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded",
                            "retry_after": rate_info["retry_after"],
                        },
                        headers={
                            "Retry-After": str(rate_info["retry_after"]),
                            "X-RateLimit-Limit": str(rate_info["limit"]),
                        }
                    )
        
        # Log request for audit trail
        start_time = time.time()
        
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Log response time
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "%s %s - %d (%dms) user=%s",
            request.method,
            path,
            response.status_code,
            duration_ms,
            user_id or "anonymous"
        )
        
        return response
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request."""
        # Check Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Would decode JWT in production
            return "user_from_token"
        
        # Check for session cookie
        session = request.cookies.get("session")
        if session:
            return f"session:{session[:8]}"
        
        # Fall back to IP for anonymous users
        return f"ip:{request.client.host}"


# ── Request Validation ───────────────────────────────────────────────

def validate_stylist_request(message: str) -> tuple[bool, str]:
    """
    Validate stylist chat request.
    Returns (is_valid, sanitized_message).
    """
    if not message or not message.strip():
        return False, ""
    
    sanitized = InputSanitizer.sanitize_message(message)
    
    if len(sanitized) < 2:
        return False, ""
    
    return True, sanitized


def validate_outfit_items(items: list) -> tuple[bool, list]:
    """
    Validate outfit items list.
    Returns (is_valid, sanitized_items).
    """
    if not items:
        return True, []
    
    if len(items) > 20:
        return False, []
    
    sanitized = []
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        
        clean_item = {
            "id": str(item.get("id", ""))[:50],
            "name": InputSanitizer.sanitize_string(
                str(item.get("name", "")), 200
            ),
            "category": InputSanitizer.sanitize_string(
                str(item.get("category", "")), 50
            ),
            "price": float(item.get("price", 0)) if item.get("price") else None,
            "image": str(item.get("image", ""))[:500],
            "brand": InputSanitizer.sanitize_string(
                str(item.get("brand", "")), 100
            ),
        }
        
        sanitized.append(clean_item)
    
    return True, sanitized


# ── API Key Protection ────────────────────────────────────────────────

class APIKeyValidator:
    """
    Validates API keys for external services.
    """
    
    @staticmethod
    def validate_groq_key(api_key: str) -> bool:
        """Validate Groq API key format."""
        if not api_key:
            return False
        
        # Groq keys start with 'gsk_'
        if not api_key.startswith("gsk_"):
            return False
        
        # Minimum reasonable length
        if len(api_key) < 20:
            return False
        
        return True
    
    @staticmethod
    def validate_gemini_key(api_key: str) -> bool:
        """Validate Gemini API key format."""
        if not api_key:
            return False
        
        # Gemini keys are typically 39 characters
        if len(api_key) < 30:
            return False
        
        return True
    
    @staticmethod
    def mask_key(api_key: str) -> str:
        """Mask API key for logging."""
        if not api_key or len(api_key) < 8:
            return "***"
        
        return f"{api_key[:4]}...{api_key[-4:]}"


# ── Export ────────────────────────────────────────────────────────────

__all__ = [
    "RateLimiter",
    "InputSanitizer",
    "SecurityMiddleware",
    "validate_stylist_request",
    "validate_outfit_items",
    "APIKeyValidator",
]
