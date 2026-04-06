"""
Redis-backed cache with in-memory fallback for sales analytics.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class SalesCacheBackend:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[Any, float]] = {}
        self._redis = None
        redis_url = os.getenv("REDIS_URL")
        if redis and redis_url:
            try:
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    def get(self, key: str) -> Optional[Any]:
        if self._redis:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw)
            return None
        current = self._memory.get(key)
        if not current:
            return None
        value, expires = current
        if time.time() >= expires:
            self._memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        if self._redis:
            self._redis.setex(key, ttl, json.dumps(value, default=str))
            return
        self._memory[key] = (value, time.time() + ttl)

    def invalidate_store(self, store_id: str) -> int:
        pattern = f"*:{store_id}:*"
        if self._redis:
            deleted = 0
            for key in self._redis.scan_iter(match=pattern, count=200):
                deleted += self._redis.delete(key)
            return int(deleted)
        keys = [k for k in self._memory.keys() if f":{store_id}:" in k]
        for key in keys:
            self._memory.pop(key, None)
        return len(keys)
