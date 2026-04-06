"""
CONFIT Backend — Performance Optimizer
======================================
Performance optimizations for the Discovery & Styling Experience:
- Response caching
- Request batching
- Lazy loading
- Query optimization
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


# ── Response Caching ──────────────────────────────────────────────────

class ResponseCache:
    """
    In-memory cache for AI responses and recommendations.
    Uses TTL-based expiration.
    """
    
    def __init__(
        self,
        default_ttl: int = 300,  # 5 minutes
        max_size: int = 1000,
    ):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry["expires_at"] < datetime.now(timezone.utc):
            del self._cache[key]
            return None
        
        self._access_times[key] = datetime.now(timezone.utc)
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set cached value with TTL."""
        ttl = ttl or self.default_ttl
        
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl),
            "created_at": datetime.now(timezone.utc),
        }
        self._access_times[key] = datetime.now(timezone.utc)
    
    def _evict_oldest(self) -> None:
        """Evict least recently used entries."""
        if not self._access_times:
            return
        
        # Remove oldest 10%
        sorted_keys = sorted(
            self._access_times.items(),
            key=lambda x: x[1]
        )
        
        to_remove = max(1, len(sorted_keys) // 10)
        for key, _ in sorted_keys[:to_remove]:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_entries = sum(
            1 for entry in self._cache.values()
            if entry["expires_at"] > now
        )
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size,
        }


# ── Stylist Response Cache ───────────────────────────────────────────

class StylistCache:
    """
    Specialized cache for stylist responses.
    Caches based on message similarity and context.
    """
    
    def __init__(self, cache: ResponseCache = None):
        self._cache = cache or ResponseCache(default_ttl=600)  # 10 minutes
        self._similarity_threshold = 0.8
    
    def _normalize_message(self, message: str) -> str:
        """Normalize message for caching."""
        # Lowercase, remove extra whitespace, basic stemming
        normalized = " ".join(message.lower().split())
        return normalized
    
    def _get_context_key(self, context: Dict[str, Any] = None) -> str:
        """Generate context key."""
        if not context:
            return "default"
        
        relevant = {
            k: v for k, v in context.items()
            if k in ["occasion", "budget", "style_preference", "gender"]
        }
        return json.dumps(relevant, sort_keys=True)
    
    def get_response(
        self,
        message: str,
        context: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached response for similar message."""
        normalized = self._normalize_message(message)
        context_key = self._get_context_key(context)
        
        cache_key = f"stylist:{context_key}:{normalized[:50]}"
        
        return self._cache.get(cache_key)
    
    def set_response(
        self,
        message: str,
        response: Dict[str, Any],
        context: Dict[str, Any] = None,
        ttl: int = 600,
    ) -> None:
        """Cache response for message."""
        normalized = self._normalize_message(message)
        context_key = self._get_context_key(context)
        
        cache_key = f"stylist:{context_key}:{normalized[:50]}"
        
        self._cache.set(cache_key, response, ttl)


# ── Request Batching ─────────────────────────────────────────────────

class RequestBatcher:
    """
    Batches multiple requests for efficient processing.
    Useful for signal tracking and bulk operations.
    """
    
    def __init__(
        self,
        batch_size: int = 50,
        flush_interval: float = 5.0,  # seconds
        processor: Callable = None,
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.processor = processor
        self._batch: List[Dict[str, Any]] = []
        self._last_flush = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()
    
    async def add(self, item: Dict[str, Any]) -> None:
        """Add item to batch."""
        async with self._lock:
            self._batch.append(item)
            
            # Flush if batch is full
            if len(self._batch) >= self.batch_size:
                await self._flush()
    
    async def _flush(self) -> None:
        """Process and clear batch."""
        if not self._batch or not self.processor:
            return
        
        batch = self._batch[:]
        self._batch = []
        self._last_flush = datetime.now(timezone.utc)
        
        try:
            await self.processor(batch)
            logger.debug("Processed batch of %d items", len(batch))
        except Exception as e:
            logger.error("Batch processing error: %s", e)
    
    async def check_flush(self) -> None:
        """Check if interval flush is needed."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_flush).total_seconds()
        
        if elapsed >= self.flush_interval and self._batch:
            async with self._lock:
                await self._flush()


# ── Query Optimization ───────────────────────────────────────────────

class QueryOptimizer:
    """
    Optimizes database queries for styling and outfit operations.
    """
    
    @staticmethod
    def optimize_style_vector_query(query):
        """
        Optimize style vector query with eager loading.
        """
        from sqlalchemy.orm import joinedload
        
        return query.options(
            joinedload("style_profile"),
            joinedload("body_profile"),
            joinedload("budget_profile"),
            joinedload("brand_affinities"),
            joinedload("contextual_preferences"),
        )
    
    @staticmethod
    def optimize_outfit_list_query(query, limit: int = 50):
        """
        Optimize outfit list query.
        """
        # Only select needed columns
        return query.with_entities(
            "id", "title", "occasion", "total_price",
            "currency", "created_at", "updated_at"
        ).limit(limit)
    
    @staticmethod
    def optimize_signals_query(query, days: int = 30):
        """
        Optimize behavior signals query with date filter.
        """
        from datetime import datetime, timezone, timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        return query.filter(
            "created_at" >= cutoff
        ).order_by("created_at.desc")


# ── Decorators ────────────────────────────────────────────────────────

def cached(cache: ResponseCache, ttl: int = None):
    """
    Decorator to cache function results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache._generate_key(func.__name__, *args, **kwargs)
            
            # Check cache
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug("Cache hit for %s", func.__name__)
                return cached_result
            
            # Execute and cache
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def async_cached(cache: ResponseCache, ttl: int = None):
    """
    Decorator to cache async function results.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache._generate_key(func.__name__, *args, **kwargs)
            
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def timed(threshold_ms: int = 1000):
    """
    Decorator to log slow function execution.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start = time.time()
            
            result = await func(*args, **kwargs)
            
            duration_ms = int((time.time() - start) * 1000)
            if duration_ms > threshold_ms:
                logger.warning(
                    "Slow execution: %s took %dms",
                    func.__name__, duration_ms
                )
            
            return result
        
        return wrapper
    return decorator


# ── Global Cache Instance ─────────────────────────────────────────────

_global_cache = ResponseCache()
_stylist_cache = StylistCache(_global_cache)


def get_cache() -> ResponseCache:
    """Get global cache instance."""
    return _global_cache


def get_stylist_cache() -> StylistCache:
    """Get stylist cache instance."""
    return _stylist_cache


# ── Export ────────────────────────────────────────────────────────────

__all__ = [
    "ResponseCache",
    "StylistCache",
    "RequestBatcher",
    "QueryOptimizer",
    "cached",
    "async_cached",
    "timed",
    "get_cache",
    "get_stylist_cache",
]
