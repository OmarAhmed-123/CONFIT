from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: Dict[str, Any]
    expires_at: float


class RuntimeCacheService:
    """Small in-memory cache for preview/final result payloads."""

    def __init__(self) -> None:
        self._store: Dict[str, CacheEntry] = {}

    @staticmethod
    def make_key(user_image_b64: str, garment_image_url: str, garment_name: str, mode: str) -> str:
        payload = {
            "u": hashlib.sha256(user_image_b64.encode("utf-8")).hexdigest(),
            "g": garment_image_url,
            "n": garment_name,
            "m": mode,
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._store.get(key)
        if not item:
            return None
        if time.time() >= item.expires_at:
            self._store.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Dict[str, Any], ttl_sec: int) -> None:
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl_sec)

