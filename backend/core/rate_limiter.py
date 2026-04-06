"""
CONFIT Backend - Rate Limiting Module
=====================================
Centralized rate limiting using slowapi + Redis.

Features:
- User-based rate limiting (per tier)
- IP-based rate limiting for anonymous users
- Redis-backed for distributed rate limiting
- Customizable limits per endpoint
"""

import os
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Optional, Tuple

from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = logging.getLogger(__name__)

# Redis URL for distributed rate limiting
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_user_id_or_ip(request: Request) -> str:
    """
    Get user ID from request or fall back to IP address.
    
    Used as the key function for rate limiting.
    """
    # Try to get user ID from auth context
    user = getattr(request.state, "user", None)
    if user and user.get("id"):
        return f"user:{user['id']}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_tier_limit(request: Request, endpoint: str) -> Tuple[int, int]:
    """
    Get rate limit based on user tier and endpoint.
    
    Returns:
        (limit, window_seconds)
    """
    user = getattr(request.state, "user", {})
    tier = user.get("tier", "free")
    
    # Limits per tier per endpoint type
    limits = {
        "muse": {
            "free": (20, 3600),      # 20/hour
            "club": (100, 3600),     # 100/hour
            "icon": (500, 3600),     # 500/hour
        },
        "mirror": {
            "free": (10, 86400),     # 10/day
            "club": (50, 86400),     # 50/day
            "icon": (200, 86400),    # 200/day
        },
        "visualsearch": {
            "free": (30, 86400),     # 30/day
            "club": (100, 86400),    # 100/day
            "icon": (500, 86400),    # 500/day
        },
        "wardrobe": {
            "free": (50, 86400),     # 50 items/day
            "club": (200, 86400),    # 200 items/day
            "icon": (1000, 86400),   # 1000 items/day
        },
        "default": {
            "free": (60, 3600),      # 60/hour
            "club": (300, 3600),     # 300/hour
            "icon": (1000, 3600),    # 1000/hour
        },
    }
    
    endpoint_limits = limits.get(endpoint, limits["default"])
    return endpoint_limits.get(tier, endpoint_limits["free"])


# Create the limiter instance
limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["60/hour"],
    storage_uri=REDIS_URL,
    strategy="fixed-window",  # or "moving-window" for more accurate
    headers_enabled=True,  # Include X-RateLimit-* headers
)


def rate_limit(
    endpoint: str,
    key_func: Optional[Callable] = None
) -> Callable:
    """
    Decorator for rate limiting endpoints.
    
    Usage:
        @rate_limit("muse")
        async def muse_chat(...):
            ...
    
    Args:
        endpoint: Endpoint type for tier-based limits
        key_func: Optional custom key function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            # Get request from args if not provided
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request is None:
                # No request context, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get limit for this user/endpoint
            limit, window = get_tier_limit(request, endpoint)
            
            # Create rate limit string
            limit_str = f"{limit}/{window}seconds"
            
            # Apply rate limit
            key = key_func(request) if key_func else get_user_id_or_ip(request)
            
            # Check with limiter
            if not limiter.test_request(request, limit_str, key):
                # Rate limit exceeded
                raise RateLimitExceeded(
                    detail=f"Rate limit exceeded. Limit: {limit} per {window} seconds."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class RateLimitMiddleware:
    """
    Custom middleware for rate limiting with Redis backend.
    
    Provides more control than SlowAPIMiddleware.
    """
    
    def __init__(self, app, limiter: Limiter = None):
        self.app = app
        self.limiter = limiter or limiter
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for health checks and static files
        path = scope.get("path", "")
        if path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            await self.app(scope, receive, send)
            return
        
        if path.startswith("/static/") or path.startswith("/api/static/"):
            await self.app(scope, receive, send)
            return
        
        # Get rate limit for endpoint
        endpoint = self._get_endpoint_type(path)
        if endpoint:
            limit, window = get_tier_limit(request, endpoint)
            limit_str = f"{limit}/{window}seconds"
            
            try:
                # Check rate limit
                if not self.limiter.test_request(request, limit_str):
                    # Rate limit exceeded
                    response = self._rate_limit_response(limit, window)
                    await response(scope, receive, send)
                    return
            except Exception as e:
                logger.warning(f"Rate limit check failed: {e}")
        
        await self.app(scope, receive, send)
    
    def _get_endpoint_type(self, path: str) -> Optional[str]:
        """Determine endpoint type from path."""
        if "/muse" in path:
            return "muse"
        elif "/mirror" in path:
            return "mirror"
        elif "/visual-search" in path:
            return "visualsearch"
        elif "/wardrobe" in path:
            return "wardrobe"
        return None
    
    def _rate_limit_response(self, limit: int, window: int):
        """Create rate limit exceeded response."""
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Limit: {limit} requests per {window} seconds.",
                "retry_after": window,
            },
            headers={
                "Retry-After": str(window),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(datetime.now(timezone.utc).timestamp()) + window),
            }
        )


def setup_rate_limiting(app):
    """
    Set up rate limiting for a FastAPI app.
    
    Usage:
        from fastapi import FastAPI
        from core.rate_limiter import setup_rate_limiting
        
        app = FastAPI()
        setup_rate_limiting(app)
    """
    # Add limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting configured with Redis backend")


# ==========================================
# Convenience Functions
# ==========================================

async def check_rate_limit_redis(
    redis_client,
    key: str,
    limit: int,
    window_seconds: int
) -> Tuple[bool, int, int]:
    """
    Check rate limit using Redis directly.
    
    Args:
        redis_client: Redis client instance
        key: Rate limit key (e.g., "muse:user:123")
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        (is_allowed, remaining_requests, retry_after_seconds)
    """
    try:
        current = redis_client.get(key)
        
        if current is None:
            # First request, set counter
            redis_client.setex(key, window_seconds, 1)
            return True, limit - 1, 0
        
        count = int(current)
        
        if count >= limit:
            # Rate limit exceeded
            ttl = redis_client.ttl(key)
            return False, 0, max(ttl, 1)
        
        # Increment counter
        redis_client.incr(key)
        return True, limit - count - 1, 0
        
    except Exception as e:
        logger.warning(f"Redis rate limit check failed: {e}")
        # On error, allow the request
        return True, limit, 0


async def increment_rate_limit(redis_client, key: str, window_seconds: int = 3600) -> None:
    """
    Increment rate limit counter.
    
    Used for custom rate limiting logic.
    """
    try:
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, window_seconds, 1)
        else:
            redis_client.incr(key)
    except Exception as e:
        logger.warning(f"Failed to increment rate limit: {e}")


def get_rate_limit_headers(
    limit: int,
    remaining: int,
    reset_timestamp: int
) -> dict:
    """Generate rate limit headers for response."""
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_timestamp),
    }


# ==========================================
# Tier-Based Limits Configuration
# ==========================================

TIER_LIMITS = {
    "free": {
        "muse_hourly": 20,
        "mirror_daily": 10,
        "visualsearch_daily": 30,
        "wardrobe_items": 50,
    },
    "club": {
        "muse_hourly": 100,
        "mirror_daily": 50,
        "visualsearch_daily": 100,
        "wardrobe_items": 200,
    },
    "icon": {
        "muse_hourly": 500,
        "mirror_daily": 200,
        "visualsearch_daily": 500,
        "wardrobe_items": 1000,
    },
}


def get_tier_limits(tier: str) -> dict:
    """Get all limits for a tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])
