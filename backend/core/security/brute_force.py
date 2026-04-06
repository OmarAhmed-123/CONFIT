"""
CONFIT Backend - Brute Force Lockout
====================================
Redis-based failed login counter with automatic lockout.
5 failed logins → 15 minute lockout.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes
COUNTER_WINDOW_SECONDS = 15 * 60  # Count failures within this window


class BruteForceProtector:
    """
    Track failed login attempts and enforce lockout.

    Uses Redis for distributed counter storage, with an in-memory
    fallback when Redis is unavailable.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        # In-memory fallback: {key: [(timestamp, ), ...]}
        self._memory_store: dict[str, list[float]] = {}

    def _key(self, identifier: str) -> str:
        return f"bruteforce:{identifier}"

    def _lockout_key(self, identifier: str) -> str:
        return f"bruteforce:lockout:{identifier}"

    async def record_failed_attempt(self, identifier: str) -> Tuple[int, bool]:
        """
        Record a failed login attempt.

        Returns:
            (failed_count, is_locked_out): Number of recent failures and whether
            the account is now locked out.
        """
        now = time.time()
        key = self._key(identifier)
        lockout_key = self._lockout_key(identifier)

        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.zadd(key, {str(now): now})
                # Remove entries outside the window
                pipe.zremrangebyscore(key, 0, now - COUNTER_WINDOW_SECONDS)
                pipe.zcard(key)
                # Set lockout if threshold reached
                results = await pipe.execute()
                failed_count = results[2]
                if failed_count >= MAX_FAILED_ATTEMPTS:
                    await self._redis.setex(lockout_key, LOCKOUT_DURATION_SECONDS, "1")
                    logger.warning(
                        "brute_force_lockout identifier=%s attempts=%d",
                        identifier, failed_count,
                    )
                    return failed_count, True
                return failed_count, False
            except Exception as e:
                logger.warning("Redis brute force check failed, using memory fallback: %s", e)

        # In-memory fallback
        if key not in self._memory_store:
            self._memory_store[key] = []
        self._memory_store[key].append(now)
        # Prune old entries
        self._memory_store[key] = [
            t for t in self._memory_store[key]
            if t > now - COUNTER_WINDOW_SECONDS
        ]
        failed_count = len(self._memory_store[key])
        if failed_count >= MAX_FAILED_ATTEMPTS:
            logger.warning(
                "brute_force_lockout identifier=%s attempts=%d (memory)",
                identifier, failed_count,
            )
            return failed_count, True
        return failed_count, False

    async def is_locked_out(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if the identifier is currently locked out.

        Returns:
            (is_locked_out, retry_after_seconds): Lockout status and seconds remaining.
        """
        lockout_key = self._lockout_key(identifier)

        if self._redis:
            try:
                ttl = await self._redis.ttl(lockout_key)
                if ttl and ttl > 0:
                    return True, ttl
                return False, None
            except Exception:
                pass

        # In-memory: check if we have enough recent failures to imply lockout
        key = self._key(identifier)
        now = time.time()
        entries = self._memory_store.get(key, [])
        entries = [t for t in entries if t > now - COUNTER_WINDOW_SECONDS]
        self._memory_store[key] = entries
        if len(entries) >= MAX_FAILED_ATTEMPTS:
            oldest = min(entries)
            retry_after = int(oldest + LOCKOUT_DURATION_SECONDS - now)
            if retry_after > 0:
                return True, retry_after
        return False, None

    async def reset(self, identifier: str) -> None:
        """Reset failed attempt counter (e.g., after successful login)."""
        key = self._key(identifier)
        lockout_key = self._lockout_key(identifier)

        if self._redis:
            try:
                await self._redis.delete(key, lockout_key)
                return
            except Exception:
                pass

        self._memory_store.pop(key, None)


# Global instance (initialized with Redis in app lifespan)
brute_force_protector = BruteForceProtector()


def init_brute_force_protector(redis_client) -> None:
    """Initialize the global protector with a Redis client."""
    global brute_force_protector
    brute_force_protector = BruteForceProtector(redis_client=redis_client)


__all__ = [
    "BruteForceProtector",
    "brute_force_protector",
    "init_brute_force_protector",
    "MAX_FAILED_ATTEMPTS",
    "LOCKOUT_DURATION_SECONDS",
]
