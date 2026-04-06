"""
CONFIT Backend - Preference Cache Manager
=========================================
Redis-based cache management for notification preferences with:
- TTL-based caching
- Stale cache fallback
- Pub/Sub invalidation
- Circuit breaker integration
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import json
import logging
import asyncio

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


logger = logging.getLogger(__name__)


class CacheStrategy:
    """Cache strategy configuration."""
    
    # TTL settings
    PREFERENCE_CACHE_TTL = 300  # 5 minutes
    DEVICE_CACHE_TTL = 86400   # 24 hours
    STALE_CACHE_TTL = None      # No expiration (manual cleanup)
    
    # Key prefixes
    PREF_PREFIX = "notif:prefs"
    DEVICE_PREFIX = "notif:devices"
    LOCK_PREFIX = "notif:locks"
    
    # Pub/Sub channels
    INVALIDATION_CHANNEL = "preference:invalidate"
    UPDATE_CHANNEL = "preference:updated"


class PreferenceCacheManager:
    """
    Manages preference caching with Redis.
    
    Features:
    - Multi-layer caching (hot + stale)
    - Automatic invalidation via Pub/Sub
    - Distributed locking for concurrent updates
    - Circuit breaker integration
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        db: AsyncSession,
        circuit_breaker: Optional[Any] = None
    ):
        self.redis = redis_client
        self.db = db
        self.circuit_breaker = circuit_breaker
        self._pubsub = None
        self._local_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._running = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # CACHE READ OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_preferences(
        self,
        recipient_id: str,
        recipient_type: str,
        use_stale_fallback: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], bool, int]:
        """
        Get preferences from cache.
        
        Returns:
            Tuple of (preferences, cache_hit, cache_age_ms)
        """
        
        cache_key = self._build_pref_key(recipient_id, recipient_type)
        
        # Try local cache first (fastest)
        local_result = self._get_from_local_cache(cache_key)
        if local_result:
            prefs, cached_at = local_result
            age_ms = int((datetime.utcnow() - cached_at).total_seconds() * 1000)
            return prefs, True, age_ms
        
        # Try Redis cache
        try:
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                prefs = data.get('preferences', {})
                cached_at = datetime.fromisoformat(data.get('cached_at', datetime.utcnow().isoformat()))
                age_ms = int((datetime.utcnow() - cached_at).total_seconds() * 1000)
                
                # Update local cache
                self._set_local_cache(cache_key, prefs)
                
                return prefs, True, age_ms
            
        except redis.RedisError as e:
            logger.warning("Redis read failed: %s", str(e))
        
        # Try stale cache if enabled
        if use_stale_fallback:
            stale_prefs = await self._get_stale_cache(cache_key)
            if stale_prefs:
                logger.info("Using stale cache for %s:%s", recipient_type, recipient_id)
                return stale_prefs, True, -1  # -1 indicates stale
        
        return None, False, 0
    
    async def get_or_query(
        self,
        recipient_id: str,
        recipient_type: str,
        query_timeout: float = 0.5
    ) -> Tuple[Dict[str, Any], bool, int, bool]:
        """
        Get preferences from cache or query database.
        
        Returns:
            Tuple of (preferences, cache_hit, cache_age_ms, used_fallback)
        """
        
        # Try cache first
        prefs, cache_hit, age_ms = await self.get_preferences(recipient_id, recipient_type)
        
        if cache_hit:
            return prefs, True, age_ms, False
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.is_open():
            logger.warning("Circuit breaker open, using fallback")
            fallback = await self._get_fallback_preferences(recipient_id, recipient_type)
            return fallback, False, 0, True
        
        # Query database with timeout
        try:
            async with asyncio.timeout(query_timeout):
                prefs = await self._query_preferences(recipient_id, recipient_type)
                
                # Cache the result
                await self.set_preferences(recipient_id, recipient_type, prefs)
                
                return prefs, False, 0, False
                
        except asyncio.TimeoutError:
            logger.warning("Database query timeout for %s:%s", recipient_type, recipient_id)
            
            # Use stale cache or defaults
            fallback = await self._get_fallback_preferences(recipient_id, recipient_type)
            return fallback, False, 0, True
            
        except Exception as e:
            logger.error("Database query failed: %s", str(e))
            
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            
            fallback = await self._get_fallback_preferences(recipient_id, recipient_type)
            return fallback, False, 0, True
    
    # ─────────────────────────────────────────────────────────────────────────
    # CACHE WRITE OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def set_preferences(
        self,
        recipient_id: str,
        recipient_type: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Set preferences in cache with TTL."""
        
        cache_key = self._build_pref_key(recipient_id, recipient_type)
        
        cache_data = {
            'preferences': preferences,
            'cached_at': datetime.utcnow().isoformat(),
            'recipient_id': recipient_id,
            'recipient_type': recipient_type,
        }
        
        try:
            # Set hot cache with TTL
            await self.redis.setex(
                cache_key,
                CacheStrategy.PREFERENCE_CACHE_TTL,
                json.dumps(cache_data)
            )
            
            # Also store in stale cache (no TTL)
            await self.redis.set(
                f"{cache_key}:stale",
                json.dumps(cache_data)
            )
            
            # Update local cache
            self._set_local_cache(cache_key, preferences)
            
            logger.debug(
                "Cached preferences for %s:%s",
                recipient_type, recipient_id
            )
            
        except redis.RedisError as e:
            logger.warning("Redis write failed: %s", str(e))
    
    async def invalidate(
        self,
        recipient_id: str,
        recipient_type: str,
        publish: bool = True
    ) -> None:
        """Invalidate preference cache and publish event."""
        
        cache_key = self._build_pref_key(recipient_id, recipient_type)
        
        try:
            # Delete hot cache
            await self.redis.delete(cache_key)
            
            # Clear local cache
            self._clear_local_cache(cache_key)
            
            # Publish invalidation event
            if publish:
                await self._publish_invalidation(recipient_id, recipient_type)
            
            logger.info(
                "Invalidated cache for %s:%s",
                recipient_type, recipient_id
            )
            
        except redis.RedisError as e:
            logger.warning("Cache invalidation failed: %s", str(e))
    
    async def invalidate_all_devices(
        self,
        user_id: str
    ) -> None:
        """Invalidate cache for all user's devices."""
        
        # This would typically be called when user logs out or changes password
        pattern = f"{CacheStrategy.PREF_PREFIX}:*:{user_id}"
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info("Invalidated %d cache entries for user %s", len(keys), user_id)
        except redis.RedisError as e:
            logger.warning("Batch invalidation failed: %s", str(e))
    
    # ─────────────────────────────────────────────────────────────────────────
    # DISTRIBUTED LOCKING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def acquire_lock(
        self,
        recipient_id: str,
        recipient_type: str,
        device_id: str,
        ttl: int = 30
    ) -> bool:
        """
        Acquire distributed lock for preference update.
        Prevents concurrent updates from multiple devices.
        """
        
        lock_key = f"{CacheStrategy.LOCK_PREFIX}:{recipient_type}:{recipient_id}"
        lock_value = f"{device_id}:{datetime.utcnow().timestamp()}"
        
        try:
            acquired = await self.redis.set(
                lock_key,
                lock_value,
                nx=True,  # Only set if not exists
                ex=ttl
            )
            
            if acquired:
                logger.debug(
                    "Lock acquired for %s:%s by %s",
                    recipient_type, recipient_id, device_id
                )
            
            return bool(acquired)
            
        except redis.RedisError as e:
            logger.warning("Lock acquisition failed: %s", str(e))
            return False
    
    async def release_lock(
        self,
        recipient_id: str,
        recipient_type: str,
        device_id: str
    ) -> bool:
        """Release distributed lock."""
        
        lock_key = f"{CacheStrategy.LOCK_PREFIX}:{recipient_type}:{recipient_id}"
        
        try:
            # Only release if we own the lock
            lock_value = await self.redis.get(lock_key)
            
            if lock_value and device_id in lock_value.decode():
                await self.redis.delete(lock_key)
                logger.debug(
                    "Lock released for %s:%s by %s",
                    recipient_type, recipient_id, device_id
                )
                return True
            
            return False
            
        except redis.RedisError as e:
            logger.warning("Lock release failed: %s", str(e))
            return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # PUB/SUB LISTENER
    # ─────────────────────────────────────────────────────────────────────────
    
    async def start_listener(self) -> None:
        """Start listening for cache invalidation events."""
        
        self._running = True
        self._pubsub = self.redis.pubsub()
        
        try:
            await self._pubsub.subscribe(CacheStrategy.INVALIDATION_CHANNEL)
            
            logger.info("Started cache invalidation listener")
            
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] == 'message':
                    await self._handle_invalidation_message(message)
                    
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop_listener()
    
    async def stop_listener(self) -> None:
        """Stop listening for cache invalidation events."""
        
        self._running = False
        
        if self._pubsub:
            await self._pubsub.unsubscribe(CacheStrategy.INVALIDATION_CHANNEL)
            await self._pubsub.close()
            self._pubsub = None
        
        logger.info("Stopped cache invalidation listener")
    
    async def _handle_invalidation_message(self, message: dict) -> None:
        """Handle incoming invalidation message."""
        
        try:
            data = json.loads(message['data'])
            recipient_id = data['recipient_id']
            recipient_type = data['recipient_type']
            
            cache_key = self._build_pref_key(recipient_id, recipient_type)
            
            # Clear local cache
            self._clear_local_cache(cache_key)
            
            logger.debug(
                "Received invalidation for %s:%s",
                recipient_type, recipient_id
            )
            
        except Exception as e:
            logger.error("Failed to handle invalidation message: %s", str(e))
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _build_pref_key(self, recipient_id: str, recipient_type: str) -> str:
        return f"{CacheStrategy.PREF_PREFIX}:{recipient_type}:{recipient_id}"
    
    def _get_from_local_cache(self, key: str) -> Optional[Tuple[Dict[str, Any], datetime]]:
        """Get from in-memory local cache."""
        
        if key in self._local_cache:
            prefs, cached_at = self._local_cache[key]
            
            # Check if local cache is still valid (1 minute TTL)
            if datetime.utcnow() - cached_at < timedelta(minutes=1):
                return prefs, cached_at
            
            # Expired, remove it
            del self._local_cache[key]
        
        return None
    
    def _set_local_cache(self, key: str, preferences: Dict[str, Any]) -> None:
        """Set in-memory local cache."""
        self._local_cache[key] = (preferences, datetime.utcnow())
    
    def _clear_local_cache(self, key: str) -> None:
        """Clear from in-memory local cache."""
        if key in self._local_cache:
            del self._local_cache[key]
    
    async def _get_stale_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get preferences from stale cache (no TTL)."""
        
        try:
            stale_data = await self.redis.get(f"{cache_key}:stale")
            
            if stale_data:
                data = json.loads(stale_data)
                return data.get('preferences')
                
        except redis.RedisError as e:
            logger.warning("Stale cache read failed: %s", str(e))
        
        return None
    
    async def _get_fallback_preferences(
        self,
        recipient_id: str,
        recipient_type: str
    ) -> Dict[str, Any]:
        """Get fallback preferences when all else fails."""
        
        # Try stale cache
        cache_key = self._build_pref_key(recipient_id, recipient_type)
        stale = await self._get_stale_cache(cache_key)
        
        if stale:
            return stale
        
        # Return defaults
        return self._get_default_preferences()
    
    async def _query_preferences(
        self,
        recipient_id: str,
        recipient_type: str
    ) -> Dict[str, Any]:
        """Query preferences from database."""
        
        result = await self.db.execute(
            text("""
                SELECT * FROM get_effective_preferences(
                    :recipient_id, :recipient_type
                )
            """),
            {
                'recipient_id': recipient_id,
                'recipient_type': recipient_type
            }
        )
        
        row = result.fetchone()
        
        if row:
            return row[0]
        
        return self._get_default_preferences()
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default preferences for new users."""
        return {
            'global_enabled': True,
            'channels': {
                'in_app': {'enabled': True, 'frequency': 'real_time'},
                'email': {'enabled': True, 'frequency': 'real_time'},
                'push': {'enabled': True, 'frequency': 'real_time'},
                'toast': {'enabled': True, 'frequency': 'real_time'}
            },
            'notification_types': {},
            'batch_settings': {},
            'is_default': True
        }
    
    async def _publish_invalidation(
        self,
        recipient_id: str,
        recipient_type: str
    ) -> None:
        """Publish cache invalidation event."""
        
        try:
            await self.redis.publish(
                CacheStrategy.INVALIDATION_CHANNEL,
                json.dumps({
                    'recipient_id': recipient_id,
                    'recipient_type': recipient_type,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
        except redis.RedisError as e:
            logger.warning("Failed to publish invalidation: %s", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FAILURE HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class PreferenceFailureHandler:
    """
    Handles failures in preference operations with retry logic,
    fallback strategies, and user notification.
    """
    
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 10.0
    
    def __init__(
        self,
        cache_manager: PreferenceCacheManager,
        notification_service: Optional[Any] = None
    ):
        self.cache_manager = cache_manager
        self.notification_service = notification_service
        self._pending_retries: Dict[str, Dict[str, Any]] = {}
    
    async def handle_query_failure(
        self,
        recipient_id: str,
        recipient_type: str,
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle preference query failure.
        Returns fallback preferences.
        """
        
        logger.warning(
            "Preference query failed for %s:%s: %s",
            recipient_type, recipient_id, str(error)
        )
        
        # Get fallback preferences
        fallback = await self.cache_manager._get_fallback_preferences(
            recipient_id, recipient_type
        )
        
        # Log the failure for monitoring
        await self._log_failure(
            recipient_id, recipient_type, 'query', error
        )
        
        return fallback
    
    async def handle_update_failure(
        self,
        recipient_id: str,
        recipient_type: str,
        device_id: str,
        update: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle preference update failure.
        Queues for retry and returns current state.
        """
        
        logger.warning(
            "Preference update failed for %s:%s: %s",
            recipient_type, recipient_id, str(error)
        )
        
        # Queue for retry
        operation_id = f"{recipient_id}:{device_id}:{datetime.utcnow().timestamp()}"
        
        self._pending_retries[operation_id] = {
            'recipient_id': recipient_id,
            'recipient_type': recipient_type,
            'device_id': device_id,
            'update': update,
            'error': str(error),
            'retry_count': 0,
            'queued_at': datetime.utcnow(),
        }
        
        # Log the failure
        await self._log_failure(
            recipient_id, recipient_type, 'update', error
        )
        
        # Return current state from cache
        prefs, _, _ = await self.cache_manager.get_preferences(
            recipient_id, recipient_type
        )
        
        return {
            'success': False,
            'queued_for_retry': True,
            'operation_id': operation_id,
            'current_state': prefs,
            'error_message': self._get_user_message(error)
        }
    
    async def retry_pending_operations(self) -> int:
        """
        Retry all pending operations.
        Returns count of successful retries.
        """
        
        successful = 0
        
        for op_id, operation in list(self._pending_retries.items()):
            if operation['retry_count'] >= self.MAX_RETRIES:
                # Max retries exceeded, remove
                del self._pending_retries[op_id]
                continue
            
            # Calculate delay with exponential backoff
            delay = min(
                self.BASE_RETRY_DELAY * (2 ** operation['retry_count']),
                self.MAX_RETRY_DELAY
            )
            
            # Check if enough time has passed
            elapsed = (datetime.utcnow() - operation['queued_at']).total_seconds()
            if elapsed < delay:
                continue
            
            # Attempt retry
            try:
                # This would call the actual update service
                # For now, just increment retry count
                operation['retry_count'] += 1
                operation['queued_at'] = datetime.utcnow()
                
                # If successful, remove from pending
                # successful += 1
                # del self._pending_retries[op_id]
                
            except Exception as e:
                logger.error("Retry failed for %s: %s", op_id, str(e))
        
        return successful
    
    async def schedule_retry(
        self,
        operation_id: str,
        delay: Optional[float] = None
    ) -> None:
        """Schedule a retry for a specific operation."""
        
        if operation_id not in self._pending_retries:
            return
        
        operation = self._pending_retries[operation_id]
        
        if delay is None:
            delay = min(
                self.BASE_RETRY_DELAY * (2 ** operation['retry_count']),
                self.MAX_RETRY_DELAY
            )
        
        # Schedule retry (would typically use a task queue)
        # For now, just update the queued_at time
        operation['queued_at'] = datetime.utcnow()
    
    def get_pending_count(self) -> int:
        """Get count of pending retry operations."""
        return len(self._pending_retries)
    
    async def _log_failure(
        self,
        recipient_id: str,
        recipient_type: str,
        operation_type: str,
        error: Exception
    ) -> None:
        """Log failure for monitoring and alerting."""
        
        logger.error(
            "Preference operation failed",
            extra={
                'recipient_id': recipient_id,
                'recipient_type': recipient_type,
                'operation_type': operation_type,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def _get_user_message(self, error: Exception) -> str:
        """Get user-friendly error message."""
        
        error_type = type(error).__name__
        
        messages = {
            'TimeoutError': 'The request took too long. Please try again.',
            'ConnectionError': 'Unable to connect to the server. Please check your connection.',
            'NetworkError': 'Network error occurred. Your changes will be saved when connection is restored.',
            'RateLimitError': 'Too many requests. Please wait a moment before trying again.',
            'ConflictError': 'Your settings were updated on another device. Please review.',
            'ValidationError': 'Invalid settings. Please check your inputs.',
        }
        
        return messages.get(error_type, 'An error occurred. Please try again.')


# ─────────────────────────────────────────────────────────────────────────────
# BATCH PROCESSOR FOR DIGEST/SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

class BatchProcessor:
    """
    Processes batched notifications for daily digest and weekly summary.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        redis: redis.Redis,
        dispatcher: Optional[Any] = None
    ):
        self.db = db
        self.redis = redis
        self.dispatcher = dispatcher
    
    async def process_due_batches(self) -> int:
        """Process all batches that are due for delivery."""
        
        result = await self.db.execute(
            text("""
                SELECT id, recipient_id, recipient_type, channel, frequency,
                       notifications, count
                FROM notification_batches
                WHERE status = 'pending' AND scheduled_for <= NOW()
                FOR UPDATE SKIP LOCKED
            """)
        )
        
        batches = result.fetchall()
        processed = 0
        
        for batch in batches:
            batch_id = batch[0]
            
            try:
                # Mark as processing
                await self.db.execute(
                    text("""
                        UPDATE notification_batches
                        SET status = 'processing'
                        WHERE id = :id
                    """),
                    {'id': batch_id}
                )
                await self.db.commit()
                
                # Create and send digest
                # (Implementation would call actual notification dispatcher)
                
                # Mark as sent
                await self.db.execute(
                    text("""
                        UPDATE notification_batches
                        SET status = 'sent', sent_at = NOW()
                        WHERE id = :id
                    """),
                    {'id': batch_id}
                )
                await self.db.commit()
                
                processed += 1
                
            except Exception as e:
                logger.error("Failed to process batch %s: %s", batch_id, str(e))
                
                await self.db.execute(
                    text("""
                        UPDATE notification_batches
                        SET status = 'failed'
                        WHERE id = :id
                    """),
                    {'id': batch_id}
                )
                await self.db.commit()
        
        return processed
    
    async def cleanup_old_batches(self, days: int = 30) -> int:
        """Clean up old batch records."""
        
        result = await self.db.execute(
            text("""
                DELETE FROM notification_batches
                WHERE status IN ('sent', 'failed')
                  AND sent_at < NOW() - INTERVAL '%s days'
            """) % days
        )
        await self.db.commit()
        
        deleted = result.rowcount
        logger.info("Cleaned up %d old batch records", deleted)
        
        return deleted
