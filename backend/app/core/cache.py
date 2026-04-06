"""
CONFIT Backend — Caching Layer
==============================
High-performance caching with Redis and in-memory fallback.

Features:
- Redis caching with automatic fallback
- Decorator-based caching for API endpoints
- Cache invalidation strategies
- TTL management
- Compression support
"""

import json
import hashlib
import pickle
import logging
import asyncio
from typing import Optional, Any, Callable, Dict, List
from functools import wraps
from datetime import timedelta
import gzip

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class CacheBackend:
    """Abstract cache backend interface."""
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    async def delete_pattern(self, pattern: str) -> int:
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        raise NotImplementedError
    
    async def clear(self) -> bool:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """In-memory LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    def _is_expired(self, expiry: float) -> bool:
        import time
        return time.time() > expiry
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                return None
            
            return value
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        import time
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                # Remove oldest/expired entries
                expired = [k for k, (v, e) in self._cache.items() if self._is_expired(e)]
                if expired:
                    for k in expired:
                        del self._cache[k]
                else:
                    # Remove oldest
                    oldest = next(iter(self._cache))
                    del self._cache[oldest]
            
            expiry = time.time() + ttl
            self._cache[key] = (value, expiry)
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (simple wildcard support)."""
        import fnmatch
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys() 
                if fnmatch.fnmatch(k, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key not in self._cache:
                return False
            _, expiry = self._cache[key]
            return not self._is_expired(expiry)
    
    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True


class RedisCache(CacheBackend):
    """Redis cache backend with compression support."""
    
    def __init__(self, redis_url: str, prefix: str = "confit:"):
        self._redis_url = redis_url
        self._prefix = prefix
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    async def _get_client(self) -> Optional[redis.Redis]:
        if not REDIS_AVAILABLE:
            return None
        
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=False
                )
                # Test connection
                await self._client.ping()
                self._connected = True
                logger.info(f"Connected to Redis: {self._redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
                return None
        
        return self._client if self._connected else None
    
    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize and compress value."""
        data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        # Compress if larger than 1KB
        if len(data) > 1024:
            data = gzip.compress(data)
            return b"gz:" + data
        return b"py:" + data
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize and decompress value."""
        if data.startswith(b"gz:"):
            data = gzip.decompress(data[3:])
            return pickle.loads(data)
        elif data.startswith(b"py:"):
            return pickle.loads(data[3:])
        else:
            # Try JSON fallback
            return json.loads(data.decode("utf-8"))
    
    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        if client is None:
            return None
        
        try:
            data = await client.get(self._make_key(key))
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            data = self._serialize(value)
            await client.setex(self._make_key(key), ttl, data)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            await client.delete(self._make_key(key))
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        client = await self._get_client()
        if client is None:
            return 0
        
        try:
            keys = []
            async for key in client.scan_iter(match=self._make_key(pattern)):
                keys.append(key)
            
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            return await client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def clear(self) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            keys = []
            async for key in client.scan_iter(match=f"{self._prefix}*"):
                keys.append(key)
            
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


class CacheManager:
    """
    Unified cache manager with Redis primary and in-memory fallback.
    """
    
    _instance: Optional['CacheManager'] = None
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        prefix: str = "confit:",
        default_ttl: int = 3600,
    ):
        self._primary: Optional[RedisCache] = None
        self._fallback = InMemoryCache()
        self._default_ttl = default_ttl
        
        if redis_url and REDIS_AVAILABLE:
            self._primary = RedisCache(redis_url, prefix)
        
        CacheManager._instance = self
    
    @classmethod
    def get_instance(cls) -> 'CacheManager':
        if cls._instance is None:
            raise RuntimeError("CacheManager not initialized")
        return cls._instance
    
    async def get(self, key: str) -> Optional[Any]:
        # Try primary (Redis)
        if self._primary:
            value = await self._primary.get(key)
            if value is not None:
                # Replicate to fallback
                await self._fallback.set(key, value, self._default_ttl)
                return value
        
        # Fallback to in-memory
        return await self._fallback.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl = ttl or self._default_ttl
        results = []
        
        # Set in both backends
        if self._primary:
            results.append(await self._primary.set(key, value, ttl))
        results.append(await self._fallback.set(key, value, ttl))
        
        return any(results)
    
    async def delete(self, key: str) -> bool:
        results = []
        if self._primary:
            results.append(await self._primary.delete(key))
        results.append(await self._fallback.delete(key))
        return any(results)
    
    async def delete_pattern(self, pattern: str) -> int:
        total = 0
        if self._primary:
            total += await self._primary.delete_pattern(pattern)
        total += await self._fallback.delete_pattern(pattern)
        return total
    
    async def exists(self, key: str) -> bool:
        if self._primary and await self._primary.exists(key):
            return True
        return await self._fallback.exists(key)
    
    async def clear(self) -> bool:
        results = []
        if self._primary:
            results.append(await self._primary.clear())
        results.append(await self._fallback.clear())
        return all(results)


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    skip_args: Optional[List[int]] = None,
):
    """
    Decorator for caching async function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        skip_args: Indices of arguments to skip in key generation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip specified arguments (e.g., request objects)
            key_args = args
            if skip_args:
                key_args = tuple(
                    arg for i, arg in enumerate(args) 
                    if i not in skip_args
                )
            
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*key_args, **kwargs)}"
            
            # Try to get from cache
            cache = CacheManager.get_instance()
            cached_value = await cache.get(key)
            
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(key, result, ttl)
            logger.debug(f"Cache miss: {key}")
            
            return result
        
        return wrapper
    return decorator


# Cache invalidation helpers
async def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user."""
    cache = CacheManager.get_instance()
    return await cache.delete_pattern(f"*:user:{user_id}:*")


async def invalidate_product_cache(product_id: str):
    """Invalidate all cache entries for a product."""
    cache = CacheManager.get_instance()
    return await cache.delete_pattern(f"*:product:{product_id}:*")


async def invalidate_brand_cache(brand_id: str):
    """Invalidate all cache entries for a brand."""
    cache = CacheManager.get_instance()
    return await cache.delete_pattern(f"*:brand:{brand_id}:*")


# Pre-configured cache TTLs
class CacheTTL:
    """Pre-defined TTL values for different data types."""
    
    PRODUCTS_LIST = 300  # 5 minutes
    PRODUCT_DETAIL = 600  # 10 minutes
    USER_PROFILE = 1800  # 30 minutes
    BRAND_DATA = 3600  # 1 hour
    RECOMMENDATIONS = 900  # 15 minutes
    SEARCH_RESULTS = 120  # 2 minutes
    STATIC_CONTENT = 86400  # 24 hours
    RATE_LIMIT = 60  # 1 minute
