"""
CONFIT Backend - Rate Limiting Middleware
=========================================
Token bucket rate limiting with Redis backend.
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from infrastructure.redis_client import get_cache_client


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMIT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitConfig:
    """Rate limit configuration."""
    
    # Default limits (requests per minute)
    DEFAULT_LIMIT = 60
    AUTH_LIMIT = 10  # Stricter for auth endpoints
    API_LIMIT = 120  # Higher for API endpoints
    SEARCH_LIMIT = 30  # Moderate for search
    TRYON_LIMIT = 5  # Strict for resource-intensive operations
    
    # Window size in seconds
    WINDOW_SIZE = 60
    
    # Whitelisted paths (no rate limiting)
    WHITELISTED_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
    
    # Path-specific limits
    PATH_LIMITS = {
        "/auth/login": AUTH_LIMIT,
        "/auth/register": AUTH_LIMIT,
        "/auth/password": AUTH_LIMIT,
        "/auth/oauth": AUTH_LIMIT,
        "/visual-search": SEARCH_LIMIT,
        "/try-on": TRYON_LIMIT,
        "/recommendations": SEARCH_LIMIT,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN BUCKET ALGORITHM
# ─────────────────────────────────────────────────────────────────────────────

class TokenBucket:
    """Token bucket rate limiter using Redis."""
    
    PREFIX = "ratelimit"
    
    def __init__(
        self,
        redis_client,
        key: str,
        limit: int,
        window: int = 60,
    ):
        self.redis = redis_client
        self.key = f"{self.PREFIX}:{key}"
        self.limit = limit
        self.window = window
    
    async def is_allowed(self) -> Tuple[bool, int, int]:
        """
        Check if request is allowed.
        
        Returns:
            Tuple of (is_allowed, remaining_tokens, retry_after)
        """
        now = time.time()
        window_start = now - self.window
        
        # Use Redis transaction for atomicity
        async with self.redis.pipeline() as pipe:
            # Remove old entries
            await pipe.zremrangebyscore(self.key, 0, window_start)
            
            # Count current entries
            await pipe.zcard(self.key)
            
            # Execute
            results = await pipe.execute()
            
            current_count = results[1]
            
            if current_count < self.limit:
                # Add new entry
                await self.redis.zadd(self.key, {str(now): now})
                await self.redis.expire(self.key, self.window)
                
                return True, self.limit - current_count - 1, 0
            else:
                # Calculate retry after
                oldest = await self.redis.zrange(self.key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + self.window - now) + 1
                else:
                    retry_after = self.window
                
                return False, 0, retry_after


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMIT MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self._redis = None
    
    async def get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_cache_client()
        return self._redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        
        # Skip whitelisted paths
        if request.url.path in self.config.WHITELISTED_PATHS:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get rate limit for path
        limit = self._get_limit_for_path(request.url.path)
        
        # Check rate limit
        redis = await self.get_redis()
        bucket = TokenBucket(
            redis_client=redis,
            key=client_id,
            limit=limit,
            window=self.config.WINDOW_SIZE,
        )
        
        allowed, remaining, retry_after = await bucket.is_allowed()
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + self.config.WINDOW_SIZE),
        }
        
        if not allowed:
            headers["Retry-After"] = str(retry_after)
            
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "limit": limit,
                    "retry_after": retry_after,
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please try again later.",
                        "retry_after": retry_after,
                    }
                },
                headers=headers,
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try to get authenticated user ID
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Hash the token for privacy
            token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            return f"user:{token_hash}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"

        # Check for X-Forwarded-For header (behind proxy)
        # Only trust this header when running behind a known proxy (checked via TRUSTED_PROXY env).
        # Blindly trusting client-supplied X-Forwarded-For allows rate-limit bypass.
        import os
        trusted_proxy = os.getenv("TRUSTED_PROXY_IPS", "").strip()
        if trusted_proxy and client_ip in [p.strip() for p in trusted_proxy.split(",")]:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

        return f"ip:{client_ip}"
    
    def _get_limit_for_path(self, path: str) -> int:
        """Get rate limit for specific path."""
        # Check for exact match
        if path in self.config.PATH_LIMITS:
            return self.config.PATH_LIMITS[path]
        
        # Check for prefix match
        for prefix, limit in self.config.PATH_LIMITS.items():
            if path.startswith(prefix):
                return limit
        
        # Return default limit
        return self.config.DEFAULT_LIMIT


# ─────────────────────────────────────────────────────────────────────────────
# DECORATOR FOR ENDPOINT-SPECIFIC RATE LIMITING
# ─────────────────────────────────────────────────────────────────────────────

def rate_limit(
    limit: int = RateLimitConfig.DEFAULT_LIMIT,
    window: int = 60,
    key_func: Optional[Callable] = None,
):
    """
    Decorator for endpoint-specific rate limiting.
    
    Usage:
        @router.get("/endpoint")
        @rate_limit(limit=10, window=60)
        async def endpoint():
            ...
    """
    def decorator(func):
        async def wrapper(*args, request: Request = None, **kwargs):
            # Get request from args if not in kwargs
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request is None:
                return await func(*args, **kwargs)
            
            # Get client ID
            if key_func:
                client_id = key_func(request)
            else:
                client_ip = request.client.host if request.client else "unknown"
                client_id = f"ip:{client_ip}"
            
            # Check rate limit
            redis = await get_cache_client()
            bucket = TokenBucket(
                redis_client=redis,
                key=f"{client_id}:{request.url.path}",
                limit=limit,
                window=window,
            )
            
            allowed, remaining, retry_after = await bucket.is_allowed()
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
