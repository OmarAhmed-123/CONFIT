"""
CONFIT Backend - Rate Limiting Middleware
=========================================
Advanced rate limiting with different strategies per endpoint type.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Callable, Any
from enum import Enum

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings
from core.constants import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_AUTH,
    RATE_LIMIT_CARE,
    RATE_LIMIT_AI,
    RATE_LIMIT_ADMIN,
    ErrorCode,
)


class RateLimitType(str, Enum):
    """Rate limit types for different endpoint categories."""
    DEFAULT = "default"
    AUTH = "auth"
    CARE = "care"
    AI = "ai"
    ADMIN = "admin"
    PUBLIC = "public"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    requests: int
    window_seconds: int
    burst: int = 0  # Allow burst above limit
    
    @property
    def window_minutes(self) -> float:
        return self.window_seconds / 60


@dataclass
class RateLimitEntry:
    """Entry tracking rate limit state for a client."""
    requests: list = field(default_factory=list)
    blocked_until: Optional[float] = None
    
    def add_request(self, timestamp: float):
        self.requests.append(timestamp)
    
    def clean_old_requests(self, window_start: float):
        self.requests = [t for t in self.requests if t > window_start]
    
    @property
    def request_count(self) -> int:
        return len(self.requests)


# Rate limit configurations by type
RATE_LIMITS: Dict[RateLimitType, RateLimitConfig] = {
    RateLimitType.DEFAULT: RateLimitConfig(
        requests=RATE_LIMIT_DEFAULT["requests"],
        window_seconds=RATE_LIMIT_DEFAULT["window_seconds"],
    ),
    RateLimitType.AUTH: RateLimitConfig(
        requests=RATE_LIMIT_AUTH["requests"],
        window_seconds=RATE_LIMIT_AUTH["window_seconds"],
        burst=3,
    ),
    RateLimitType.CARE: RateLimitConfig(
        requests=RATE_LIMIT_CARE["requests"],
        window_seconds=RATE_LIMIT_CARE["window_seconds"],
    ),
    RateLimitType.AI: RateLimitConfig(
        requests=RATE_LIMIT_AI["requests"],
        window_seconds=RATE_LIMIT_AI["window_seconds"],
    ),
    RateLimitType.ADMIN: RateLimitConfig(
        requests=RATE_LIMIT_ADMIN["requests"],
        window_seconds=RATE_LIMIT_ADMIN["window_seconds"],
    ),
    RateLimitType.PUBLIC: RateLimitConfig(
        requests=100,
        window_seconds=60,
    ),
}


# Endpoint to rate limit type mapping
ENDPOINT_RATE_LIMITS: Dict[str, RateLimitType] = {
    # Authentication endpoints - stricter limits
    "/api/auth/login": RateLimitType.AUTH,
    "/api/auth/register": RateLimitType.AUTH,
    "/api/auth/forgot-password": RateLimitType.AUTH,
    "/api/auth/reset-password": RateLimitType.AUTH,
    "/api/auth/verify-email": RateLimitType.AUTH,
    
    # CARE endpoints - moderate limits
    "/api/care/session": RateLimitType.CARE,
    "/api/care/session/initiate": RateLimitType.CARE,
    "/api/care/vouchers/validate": RateLimitType.CARE,
    
    # AI endpoints - stricter limits due to cost
    "/api/ai/": RateLimitType.AI,
    "/api/stylist/": RateLimitType.AI,
    "/api/try-on/": RateLimitType.AI,
    
    # Admin endpoints - moderate limits
    "/api/admin/": RateLimitType.ADMIN,
    
    # Public endpoints - generous limits
    "/api/products": RateLimitType.PUBLIC,
    "/api/brands": RateLimitType.PUBLIC,
    "/api/health": RateLimitType.PUBLIC,
}


class InMemoryRateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self):
        self._store: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = asyncio.Lock()
    
    async def is_allowed(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int, Optional[float]]:
        """
        Check if request is allowed.
        
        Returns:
            tuple: (is_allowed, remaining_requests, retry_after_seconds, blocked_until)
        """
        async with self._lock:
            now = time.time()
            window_start = now - config.window_seconds
            
            entry = self._store[key]
            
            # Check if currently blocked
            if entry.blocked_until and entry.blocked_until > now:
                retry_after = int(entry.blocked_until - now)
                return False, 0, retry_after, entry.blocked_until
            
            # Clean old requests
            entry.clean_old_requests(window_start)
            
            # Check limit
            if entry.request_count >= config.requests:
                # Calculate retry after
                oldest_request = min(entry.requests) if entry.requests else now
                retry_after = int(oldest_request + config.window_seconds - now)
                
                # Block for a short period
                entry.blocked_until = now + min(60, retry_after)
                
                return False, 0, retry_after, entry.blocked_until
            
            # Allow request
            entry.add_request(now)
            remaining = config.requests - entry.request_count
            
            return True, remaining, 0, None
    
    async def reset(self, key: str):
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "total_keys": len(self._store),
            "total_requests": sum(e.request_count for e in self._store.values()),
            "blocked_clients": sum(1 for e in self._store.values() if e.blocked_until),
        }


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with different limits per endpoint type.
    
    Features:
    - Sliding window rate limiting
    - Different limits for different endpoint types
    - IP-based and user-based limiting
    - Graceful degradation with retry-after headers
    - Whitelist support for internal services
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        limiter: Optional[InMemoryRateLimiter] = None,
    ):
        super().__init__(app)
        self.enabled = enabled and settings.RATE_LIMIT_ENABLED
        self.limiter = limiter or InMemoryRateLimiter()
        
        # Whitelisted IPs (internal services)
        self.whitelisted_ips = {"127.0.0.1", "::1"}
        
        # Whitelisted paths (health checks, etc.)
        self.whitelisted_paths = {"/health", "/metrics", "/docs", "/openapi.json"}
    
    def _get_rate_limit_type(self, path: str) -> RateLimitType:
        """Determine rate limit type for a path."""
        # Check exact matches first
        if path in ENDPOINT_RATE_LIMITS:
            return ENDPOINT_RATE_LIMITS[path]
        
        # Check prefix matches
        for prefix, limit_type in ENDPOINT_RATE_LIMITS.items():
            if path.startswith(prefix):
                return limit_type
        
        return RateLimitType.DEFAULT
    
    def _get_client_key(self, request: Request) -> str:
        """Generate unique key for rate limiting."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        # Combine for key
        if user_id:
            return f"user:{user_id}"
        return f"ip:{client_ip}"
    
    def _is_whitelisted(self, request: Request) -> bool:
        """Check if request is whitelisted."""
        # Check path whitelist
        if request.url.path in self.whitelisted_paths:
            return True
        
        # Check IP whitelist
        client_ip = request.client.host if request.client else ""
        if client_ip in self.whitelisted_ips:
            return True
        
        # Check internal API key
        api_key = request.headers.get("X-Internal-API-Key")
        if api_key and api_key == settings.INTERNAL_API_KEY:
            return True
        
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip if disabled or whitelisted
        if not self.enabled or self._is_whitelisted(request):
            return await call_next(request)
        
        # Get rate limit configuration
        path = request.url.path
        rate_limit_type = self._get_rate_limit_type(path)
        config = RATE_LIMITS[rate_limit_type]
        
        # Get client key
        client_key = f"{rate_limit_type.value}:{self._get_client_key(request)}"
        
        # Check rate limit
        is_allowed, remaining, retry_after, blocked_until = await self.limiter.is_allowed(
            client_key, config
        )
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(config.requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time() + config.window_seconds)),
        }
        
        if not is_allowed:
            headers["Retry-After"] = str(retry_after)
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": ErrorCode.RATE_LIMIT_EXCEEDED,
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers=headers,
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


class CareRateLimiter:
    """
    Specialized rate limiter for CARE endpoints.
    
    Features:
    - OTP attempt limiting
    - Session creation limits
    - Voucher validation limits
    """
    
    def __init__(self, limiter: Optional[InMemoryRateLimiter] = None):
        self.limiter = limiter or InMemoryRateLimiter()
        
        # OTP-specific limits
        self.otp_config = RateLimitConfig(
            requests=5,  # 5 OTP requests
            window_seconds=300,  # per 5 minutes
        )
        
        # Session limits
        self.session_config = RateLimitConfig(
            requests=10,  # 10 session initiations
            window_seconds=3600,  # per hour
        )
        
        # Voucher validation limits
        self.voucher_config = RateLimitConfig(
            requests=20,  # 20 validations
            window_seconds=300,  # per 5 minutes
        )
    
    async def check_otp_limit(self, session_id: str) -> tuple[bool, int]:
        """Check OTP request limit for a session."""
        key = f"otp:{session_id}"
        is_allowed, remaining, _, _ = await self.limiter.is_allowed(
            key, self.otp_config
        )
        return is_allowed, remaining
    
    async def check_session_limit(self, ip_address: str) -> tuple[bool, int]:
        """Check session creation limit for an IP."""
        key = f"session:{ip_address}"
        is_allowed, remaining, _, _ = await self.limiter.is_allowed(
            key, self.session_config
        )
        return is_allowed, remaining
    
    async def check_voucher_limit(self, ip_address: str) -> tuple[bool, int]:
        """Check voucher validation limit for an IP."""
        key = f"voucher:{ip_address}"
        is_allowed, remaining, _, _ = await self.limiter.is_allowed(
            key, self.voucher_config
        )
        return is_allowed, remaining


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()
care_rate_limiter = CareRateLimiter(rate_limiter)


def setup_rate_limiting(app):
    """Setup rate limiting middleware for the application."""
    app.add_middleware(
        RateLimitingMiddleware,
        enabled=settings.RATE_LIMIT_ENABLED,
        limiter=rate_limiter,
    )
    
    return rate_limiter
