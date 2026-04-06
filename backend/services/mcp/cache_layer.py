"""
CONFIT Backend — MCP Cache Layer
=================================
Redis-backed caching for try-on results and garment data.

Features:
- Result caching keyed by hash(user_image + garment_id + options)
- Garment preloading for popular items
- TTL-based expiry
- Cache hit/miss metrics
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try importing Redis — graceful fallback to in-memory dict
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

# Default TTLs (seconds)
RESULT_TTL = 3600          # 1 hour for completed try-on results
GARMENT_TTL = 86400        # 24 hours for preprocessed garment data
PREVIEW_TTL = 300          # 5 minutes for live preview frames


class TryOnCache:
    """Redis-backed try-on cache with in-memory fallback.

    Usage:
        cache = TryOnCache()
        await cache.connect("redis://localhost:6379/0")

        # Cache a result
        await cache.set_result(cache_key, result_data)

        # Check cache before inference
        cached = await cache.get_result(cache_key)
    """

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0

    async def connect(self, redis_url: str = "redis://localhost:6379/0") -> bool:
        """Connect to Redis. Returns True on success, False falls back to memory."""
        if not REDIS_AVAILABLE:
            logger.info("Redis package not available, using in-memory cache")
            return False
        try:
            self._redis = aioredis.from_url(
                redis_url, decode_responses=False, socket_timeout=5,
            )
            await self._redis.ping()
            logger.info("TryOnCache connected to Redis: %s", redis_url)
            return True
        except Exception as e:
            logger.warning("Redis connection failed (%s), using in-memory cache", e)
            self._redis = None
            return False

    # ── Key Generation ──────────────────────────────────────────────────

    @staticmethod
    def make_result_key(
        user_image_hash: str,
        garment_id: str,
        options_hash: str = "",
    ) -> str:
        """Deterministic cache key for a try-on result."""
        raw = f"tryon:result:{user_image_hash}:{garment_id}:{options_hash}"
        return f"tryon:result:{hashlib.sha256(raw.encode()).hexdigest()[:24]}"

    @staticmethod
    def make_garment_key(garment_id: str) -> str:
        return f"tryon:garment:{garment_id}"

    @staticmethod
    def hash_image(image_base64: str) -> str:
        """Fast hash of a base64 image (first + last 4KB to avoid hashing megabytes)."""
        sample = image_base64[:4096] + image_base64[-4096:] if len(image_base64) > 8192 else image_base64
        return hashlib.sha256(sample.encode()).hexdigest()[:16]

    @staticmethod
    def hash_options(options: Optional[Dict]) -> str:
        if not options:
            return "default"
        return hashlib.md5(json.dumps(options, sort_keys=True).encode()).hexdigest()[:12]

    # ── Result Cache ────────────────────────────────────────────────────

    async def get_result(self, key: str) -> Optional[str]:
        """Get cached try-on result image (base64). Returns None on miss."""
        try:
            if self._redis:
                val = await self._redis.get(key)
                if val:
                    self._hits += 1
                    return val.decode() if isinstance(val, bytes) else val
                self._misses += 1
                return None
            # In-memory fallback
            entry = self._memory_cache.get(key)
            if entry and entry.get("expires", 0) > time.time():
                self._hits += 1
                return entry["value"]
            if entry:
                del self._memory_cache[key]
            self._misses += 1
            return None
        except Exception as e:
            logger.warning("Cache get error: %s", e)
            self._misses += 1
            return None

    async def set_result(self, key: str, value: str, ttl: int = RESULT_TTL) -> None:
        """Cache a try-on result image (base64)."""
        try:
            if self._redis:
                await self._redis.setex(key, ttl, value.encode() if isinstance(value, str) else value)
            else:
                self._memory_cache[key] = {
                    "value": value,
                    "expires": time.time() + ttl,
                }
        except Exception as e:
            logger.warning("Cache set error: %s", e)

    # ── Garment Preload Cache ───────────────────────────────────────────

    async def get_garment(self, garment_id: str) -> Optional[bytes]:
        """Get preprocessed garment data."""
        key = self.make_garment_key(garment_id)
        try:
            if self._redis:
                return await self._redis.get(key)
            entry = self._memory_cache.get(key)
            if entry and entry.get("expires", 0) > time.time():
                return entry["value"]
            return None
        except Exception:
            return None

    async def set_garment(self, garment_id: str, data: bytes, ttl: int = GARMENT_TTL) -> None:
        """Cache preprocessed garment data."""
        key = self.make_garment_key(garment_id)
        try:
            if self._redis:
                await self._redis.setex(key, ttl, data)
            else:
                self._memory_cache[key] = {"value": data, "expires": time.time() + ttl}
        except Exception as e:
            logger.warning("Garment cache set error: %s", e)

    # ── Preview Cache ───────────────────────────────────────────────────

    async def set_preview(self, session_id: str, frame_data: str) -> None:
        """Cache live preview frame (short TTL)."""
        key = f"tryon:preview:{session_id}"
        try:
            if self._redis:
                await self._redis.setex(key, PREVIEW_TTL, frame_data.encode())
            else:
                self._memory_cache[key] = {"value": frame_data, "expires": time.time() + PREVIEW_TTL}
        except Exception:
            pass

    async def get_preview(self, session_id: str) -> Optional[str]:
        """Get cached live preview frame."""
        return await self.get_result(f"tryon:preview:{session_id}")

    # ── Metrics ─────────────────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
            "backend": "redis" if self._redis else "memory",
            "memory_entries": len(self._memory_cache) if not self._redis else None,
        }

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
