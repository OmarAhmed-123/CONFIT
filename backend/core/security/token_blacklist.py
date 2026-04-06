"""
CONFIT Backend - Token Blacklist for JWT Rotation
==================================================
Redis-based token blacklist for secure logout and token rotation.

Uses Redis Sorted Set for automatic cleanup:
- Key: "jwt:blacklist"
- Score: token expiry timestamp (Unix epoch)
- Member: JTI (JWT ID)
- Auto-cleanup via ZREMRANGEBYSCORE removes expired entries
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Set, List, Dict, Any
from uuid import UUID

from infrastructure.redis_client import get_cache_client


logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    Redis-based token blacklist for JWT revocation.
    
    Features:
    - O(1) token lookup using Sorted Set
    - Automatic cleanup via ZREMRANGEBYSCORE (cron task)
    - Support for user-wide revocation
    - Family-based refresh token tracking
    
    Redis Structure:
    - jwt:blacklist (Sorted Set) - score=expiry_ts, member=jti
    - jwt:blacklist:meta:{jti} (Hash) - user_id, reason, blacklisted_at
    - jwt:user_tokens:{user_id} (Set) - user's active JTIs
    - jwt:token_family:{family_id} (Hash) - refresh token family info
    """
    
    # Main blacklist key (Sorted Set)
    BLACKLIST_KEY = "jwt:blacklist"
    META_PREFIX = "jwt:blacklist:meta"
    USER_PREFIX = "jwt:user_tokens"
    FAMILY_PREFIX = "jwt:token_family"
    
    def __init__(self, redis_client=None):
        self._redis = redis_client
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_cache_client()
        return self._redis
    
    # ─────────────────────────────────────────────────────────────────────────
    # TOKEN BLACKLIST
    # ─────────────────────────────────────────────────────────────────────────
    
    async def blacklist_token(
        self,
        jti: str,
        exp: datetime,
        user_id: str = "",
        reason: str = "logout",
    ) -> bool:
        """
        Add token to blacklist using Redis Sorted Set.
        
        Args:
            jti: JWT ID (unique token identifier)
            exp: Token expiration datetime (used as score for auto-cleanup)
            user_id: User ID who owns the token
            reason: Reason for blacklisting
            
        Returns:
            True if successful
        """
        redis = await self._get_redis()
        
        # Calculate expiry timestamp (Unix epoch) as score
        now = datetime.now(timezone.utc)
        expiry_ts = exp.timestamp() if isinstance(exp, datetime) else exp
        
        if expiry_ts <= now.timestamp():
            # Token already expired, no need to blacklist
            return True
        
        # Add to Sorted Set with expiry timestamp as score
        # ZADD jwt:blacklist expiry_ts jti
        await redis.zadd(
            self.BLACKLIST_KEY,
            {jti: expiry_ts}
        )
        
        # Store metadata in separate hash
        meta_key = f"{self.META_PREFIX}:{jti}"
        await redis.hset(meta_key, mapping={
            "user_id": user_id,
            "reason": reason,
            "blacklisted_at": now.isoformat(),
            "expires_at": exp.isoformat() if isinstance(exp, datetime) else exp,
        })
        # Set TTL on metadata to match token expiry
        ttl = int(expiry_ts - now.timestamp())
        await redis.expire(meta_key, ttl)
        
        # Add to user's token set for user-wide revocation
        if user_id:
            user_key = f"{self.USER_PREFIX}:{user_id}"
            await redis.sadd(user_key, jti)
            await redis.expire(user_key, ttl)
        
        logger.info(
            f"Token blacklisted: {jti[:8]}... for user {user_id} "
            f"(reason: {reason}, expires: {exp.isoformat() if isinstance(exp, datetime) else exp})"
        )
        
        return True
    
    # Alias for backward compatibility
    async def add_token(
        self,
        jti: str,
        expires_at: datetime,
        user_id: str,
        reason: str = "logout",
    ) -> bool:
        """Alias for blacklist_token (backward compatibility)."""
        return await self.blacklist_token(jti, expires_at, user_id, reason)
    
    async def is_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted using Sorted Set.
        
        Args:
            jti: JWT ID to check
            
        Returns:
            True if token is blacklisted
        """
        redis = await self._get_redis()
        # Check if JTI exists in sorted set
        # ZSCORE returns the score (expiry timestamp) if member exists
        score = await redis.zscore(self.BLACKLIST_KEY, jti)
        return score is not None
    
    async def get_blacklist_reason(self, jti: str) -> Optional[str]:
        """Get reason for token blacklisting."""
        redis = await self._get_redis()
        meta_key = f"{self.META_PREFIX}:{jti}"
        reason = await redis.hget(meta_key, "reason")
        return reason
    
    async def get_blacklist_metadata(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get full metadata for a blacklisted token."""
        redis = await self._get_redis()
        meta_key = f"{self.META_PREFIX}:{jti}"
        data = await redis.hgetall(meta_key)
        if data:
            return {
                "user_id": data.get("user_id", ""),
                "reason": data.get("reason", "unknown"),
                "blacklisted_at": data.get("blacklisted_at"),
                "expires_at": data.get("expires_at"),
            }
        return None
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired tokens from blacklist (cron task).
        
        Uses ZREMRANGEBYSCORE to remove entries with score (expiry_ts)
        less than current timestamp.
        
        Returns:
            Number of entries removed
        """
        redis = await self._get_redis()
        now_ts = datetime.now(timezone.utc).timestamp()
        
        # Remove all entries with score < now
        # ZREMRANGEBYSCORE jwt:blacklist -inf now_ts
        removed = await redis.zremrangebyscore(
            self.BLACKLIST_KEY,
            "-inf",
            now_ts
        )
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired tokens from blacklist")
        
        return removed
    
    async def get_blacklist_size(self) -> int:
        """Get current number of blacklisted tokens."""
        redis = await self._get_redis()
        return await redis.zcard(self.BLACKLIST_KEY)
    
    # ─────────────────────────────────────────────────────────────────────────
    # USER-WIDE REVOCATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def revoke_all_user_tokens(
        self,
        user_id: str,
        reason: str = "security_breach",
    ) -> int:
        """
        Revoke all tokens for a user.
        
        Use cases:
        - Password change
        - Security breach detection
        - Account suspension
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            
        Returns:
            Number of tokens revoked
        """
        redis = await self._get_redis()
        user_key = f"{self.USER_PREFIX}:{user_id}"
        
        # Get all user's tokens
        jtis = await redis.smembers(user_key)
        
        if not jtis:
            return 0
        
        # Add all to blacklist using Sorted Set
        now = datetime.now(timezone.utc)
        default_expiry = now + timedelta(hours=24)  # 24 hours default
        expiry_ts = default_expiry.timestamp()
        
        for jti in jtis:
            # Check if already blacklisted
            if await redis.zscore(self.BLACKLIST_KEY, jti) is None:
                # Add to sorted set
                await redis.zadd(self.BLACKLIST_KEY, {jti: expiry_ts})
                
                # Store metadata
                meta_key = f"{self.META_PREFIX}:{jti}"
                await redis.hset(meta_key, mapping={
                    "user_id": user_id,
                    "reason": reason,
                    "blacklisted_at": now.isoformat(),
                    "expires_at": default_expiry.isoformat(),
                })
                await redis.expire(meta_key, 24 * 3600)
        
        # Clear user's token set
        await redis.delete(user_key)
        
        logger.warning(f"Revoked {len(jtis)} tokens for user {user_id} (reason: {reason})")
        
        return len(jtis)
    
    # ─────────────────────────────────────────────────────────────────────────
    # REFRESH TOKEN FAMILY TRACKING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_token_family(
        self,
        family_id: str,
        refresh_jti: str,
        user_id: str,
        expires_at: datetime,
    ) -> bool:
        """
        Create a new token family for refresh token rotation.
        
        Token families detect token reuse attacks:
        - When a refresh token is used, it's invalidated
        - If an invalidated token is reused, the entire family is revoked
        
        Args:
            family_id: Unique family identifier
            refresh_jti: Initial refresh token JTI
            user_id: User ID
            expires_at: Token expiration
            
        Returns:
            True if successful
        """
        redis = await self._get_redis()
        
        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        
        if ttl <= 0:
            return False
        
        family_key = f"{self.FAMILY_PREFIX}:{family_id}"
        
        # Store family info
        await redis.hset(family_key, mapping={
            "user_id": user_id,
            "valid_jti": refresh_jti,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await redis.expire(family_key, ttl)
        
        return True
    
    async def rotate_refresh_token(
        self,
        family_id: str,
        old_jti: str,
        new_jti: str,
    ) -> tuple[bool, bool]:
        """
        Rotate refresh token within a family.
        
        Args:
            family_id: Token family ID
            old_jti: Previous refresh token JTI
            new_jti: New refresh token JTI
            
        Returns:
            Tuple of (success, security_breach_detected)
        """
        redis = await self._get_redis()
        family_key = f"{self.FAMILY_PREFIX}:{family_id}"
        
        # Check if family exists
        if not await redis.exists(family_key):
            return False, False
        
        # Get current valid JTI
        valid_jti = await redis.hget(family_key, "valid_jti")
        
        if not valid_jti:
            return False, False
        
        # Check if old token matches valid token
        if old_jti != valid_jti:
            # SECURITY BREACH: Token reuse detected!
            # Revoke entire family
            user_id = await redis.hget(family_key, "user_id")
            await self.revoke_all_user_tokens(
                user_id,
                reason="token_reuse_detected"
            )
            await redis.delete(family_key)
            
            logger.critical(
                f"Token reuse detected! Family {family_id}, "
                f"expected {valid_jti[:8]}... got {old_jti[:8]}..."
            )
            
            return False, True
        
        # Blacklist old token
        await self.add_token(old_jti, datetime.now(timezone.utc) + timedelta(days=7), 
                            await redis.hget(family_key, "user_id"), "rotated")
        
        # Update family with new valid JTI
        await redis.hset(family_key, "valid_jti", new_jti)
        
        return True, False
    
    async def invalidate_family(self, family_id: str) -> bool:
        """Invalidate an entire token family."""
        redis = await self._get_redis()
        family_key = f"{self.FAMILY_PREFIX}:{family_id}"
        
        if await redis.exists(family_key):
            valid_jti = await redis.hget(family_key, "valid_jti")
            if valid_jti:
                await self.add_token(valid_jti, datetime.now(timezone.utc) + timedelta(days=7),
                                    await redis.hget(family_key, "user_id") or "", "family_invalidation")
            
            await redis.delete(family_key)
            return True
        
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

token_blacklist = TokenBlacklist()
