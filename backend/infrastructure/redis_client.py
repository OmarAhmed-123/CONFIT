"""
CONFIT Backend - Redis Infrastructure
=====================================
Redis client for caching, sessions, and Celery broker.
"""

import os
import json
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

import redis.asyncio as aioredis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.connection import ConnectionPool

from core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# REDIS CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def get_redis_url(db: int = 0) -> str:
    """Get Redis URL for specified database."""
    base_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if "?" in base_url:
        return f"{base_url}&db={db}"
    return f"{base_url}/{db}"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION POOL
# ─────────────────────────────────────────────────────────────────────────────

# Main cache pool (db 0)
cache_pool: ConnectionPool = ConnectionPool.from_url(
    get_redis_url(db=0),
    max_connections=50,
    decode_responses=True,
)

# Session pool (db 3)
session_pool: ConnectionPool = ConnectionPool.from_url(
    get_redis_url(db=3),
    max_connections=20,
    decode_responses=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# REDIS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

async def get_cache_client() -> AsyncRedis:
    """Get Redis cache client."""
    return AsyncRedis(connection_pool=cache_pool)


async def get_session_client() -> AsyncRedis:
    """Get Redis session client."""
    return AsyncRedis(connection_pool=session_pool)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class RedisCache:
    """Redis cache service with serialization support."""
    
    def __init__(self, client: AsyncRedis, prefix: str = "confit"):
        self.client = client
        self.prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.prefix}:{key}"
    
    async def get(
        self,
        key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache."""
        full_key = self._make_key(key)
        value = await self.client.get(full_key)
        
        if value is None:
            return None
        
        if deserialize:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        
        return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache with optional TTL."""
        full_key = self._make_key(key)
        
        if serialize:
            try:
                value = json.dumps(value)
            except (TypeError, ValueError):
                value = str(value)
        
        if ttl is not None:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return await self.client.setex(full_key, ttl, value)
        
        return await self.client.set(full_key, value)
    
    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        full_key = self._make_key(key)
        return await self.client.delete(full_key)
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        full_pattern = self._make_key(pattern)
        keys = []
        
        async for key in self.client.scan_iter(match=full_pattern):
            keys.append(key)
        
        if keys:
            return await self.client.delete(*keys)
        return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        full_key = self._make_key(key)
        return bool(await self.client.exists(full_key))
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration on key."""
        full_key = self._make_key(key)
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        return await self.client.expire(full_key, ttl)
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiry, -2 if doesn't exist)."""
        full_key = self._make_key(key)
        return await self.client.ttl(full_key)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        full_key = self._make_key(key)
        return await self.client.incrby(full_key, amount)
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter."""
        full_key = self._make_key(key)
        return await self.client.decrby(full_key, amount)
    
    # Hash operations
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value."""
        full_key = self._make_key(key)
        return await self.client.hget(full_key, field)
    
    async def hset(
        self,
        key: str,
        field: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> int:
        """Set hash field value."""
        full_key = self._make_key(key)
        result = await self.client.hset(full_key, field, json.dumps(value) if not isinstance(value, str) else value)
        if ttl:
            await self.client.expire(full_key, ttl)
        return result
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        full_key = self._make_key(key)
        return await self.client.hgetall(full_key)
    
    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        full_key = self._make_key(key)
        return await self.client.hdel(full_key, *fields)
    
    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to list head."""
        full_key = self._make_key(key)
        return await self.client.lpush(full_key, *[json.dumps(v) for v in values])
    
    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to list tail."""
        full_key = self._make_key(key)
        return await self.client.rpush(full_key, *[json.dumps(v) for v in values])
    
    async def lpop(self, key: str) -> Optional[str]:
        """Pop value from list head."""
        full_key = self._make_key(key)
        return await self.client.lpop(full_key)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from list tail."""
        full_key = self._make_key(key)
        return await self.client.rpop(full_key)
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """Get list range."""
        full_key = self._make_key(key)
        return await self.client.lrange(full_key, start, end)
    
    # Set operations
    async def sadd(self, key: str, *values: Any) -> int:
        """Add values to set."""
        full_key = self._make_key(key)
        return await self.client.sadd(full_key, *values)
    
    async def srem(self, key: str, *values: Any) -> int:
        """Remove values from set."""
        full_key = self._make_key(key)
        return await self.client.srem(full_key, *values)
    
    async def smembers(self, key: str) -> set:
        """Get all set members."""
        full_key = self._make_key(key)
        return await self.client.smembers(full_key)
    
    async def sismember(self, key: str, value: Any) -> bool:
        """Check if value is in set."""
        full_key = self._make_key(key)
        return bool(await self.client.sismember(full_key, value))
    
    # Sorted set operations
    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members to sorted set."""
        full_key = self._make_key(key)
        return await self.client.zadd(full_key, mapping)
    
    async def zrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        withscores: bool = False
    ) -> List:
        """Get sorted set range."""
        full_key = self._make_key(key)
        return await self.client.zrange(full_key, start, end, withscores=withscores)
    
    async def zrank(self, key: str, member: str) -> Optional[int]:
        """Get member rank in sorted set."""
        full_key = self._make_key(key)
        return await self.client.zrank(full_key, member)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE DECORATOR
# ─────────────────────────────────────────────────────────────────────────────

def cached(
    key_prefix: str,
    ttl: int = 3600,
    key_builder: Optional[callable] = None
):
    """Decorator for caching function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = RedisCache(await get_cache_client())
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{key_prefix}:{':'.join(str(a) for a in args[1:] if a)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────────────────

async def close_redis() -> None:
    """Close Redis connections."""
    await cache_pool.disconnect()
    await session_pool.disconnect()
