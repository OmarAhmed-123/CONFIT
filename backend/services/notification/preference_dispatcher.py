"""
CONFIT Backend - Preference-Aware Notification Dispatcher
=========================================================
NotificationService integration that queries and respects user preferences
before every dispatch decision. Implements cache-first strategy with fallbacks.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class DispatchDecision(Enum):
    SEND_IMMEDIATELY = "send_immediately"
    ADD_TO_BATCH = "add_to_batch"
    SKIP_DISABLED = "skip_disabled"
    SKIP_FREQUENCY = "skip_frequency"


class FallbackType(Enum):
    NONE = "none"
    STALE_CACHE = "stale_cache"
    DEFAULTS = "defaults"


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PreferenceCheckResult:
    """Result of preference check before dispatch."""
    decision: DispatchDecision
    reason: str
    effective_settings: Dict[str, Any]
    cache_hit: bool
    cache_age_ms: int
    fallback_used: FallbackType


@dataclass
class NotificationPayload:
    """Notification payload to dispatch."""
    notification_id: str
    notification_type: str  # 'order_updates', 'promotional', etc.
    channel: str  # 'in_app', 'email', 'push', 'toast'
    recipient_id: str
    recipient_type: str  # 'customer' or 'owner'
    title: str
    body: str
    data: Dict[str, Any]
    priority: str = "normal"  # 'low', 'normal', 'high'
    scheduled_for: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# CIRCUIT BREAKER
# ─────────────────────────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for preference service resilience.
    Prevents cascading failures when preference queries fail.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.half_open_successes = 0
    
    def is_open(self) -> bool:
        """Check if circuit is open (should fail-fast)."""
        
        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return False
            return True
        
        return False
    
    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_successes = 0
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count
            )
    
    def record_success(self) -> None:
        """Record a success."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_requests:
                self.state = CircuitState.CLOSED
                self.half_open_successes = 0
                logger.info("Circuit breaker closed after successful recovery")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.reset_timeout


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCE-AWARE DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

class PreferenceAwareDispatcher:
    """
    Notification dispatcher that queries and respects user preferences
    before every dispatch decision.
    
    Features:
    - Cache-first strategy with 5-minute TTL
    - Fallback to stale cache or defaults on DB failure
    - Circuit breaker for resilience
    - Preference hierarchy evaluation (global → type → channel → frequency)
    """
    
    PREFERENCE_CACHE_TTL = 300  # 5 minutes
    PREFERENCE_QUERY_TIMEOUT = 0.5  # 500ms max for preference query
    CIRCUIT_BREAKER_THRESHOLD = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT = 60
    
    def __init__(
        self,
        db: AsyncSession,
        redis: redis.Redis,
        event_publisher: Optional[Any] = None
    ):
        self.db = db
        self.redis = redis
        self.event_publisher = event_publisher
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=self.CIRCUIT_BREAKER_RESET_TIMEOUT
        )
    
    async def check_preferences(
        self,
        recipient_id: str,
        recipient_type: str,
        notification_type: str,
        channel: str
    ) -> PreferenceCheckResult:
        """
        Query current preferences and determine dispatch decision.
        Implements cache-first strategy with fallback to defaults.
        """
        
        cache_key = self._build_cache_key(recipient_id, recipient_type)
        cache_hit = False
        cache_age_ms = 0
        fallback_used = FallbackType.NONE
        prefs = None
        
        # Step 1: Try cache first (fastest path)
        cached = await self._get_from_cache(cache_key)
        if cached:
            cache_hit = True
            cache_age_ms = int(
                (datetime.utcnow() - cached.get('cached_at', datetime.utcnow())).total_seconds() * 1000
            )
            prefs = cached.get('preferences', {})
        
        # Step 2: Query database if cache miss
        if not prefs:
            try:
                async with asyncio.timeout(self.PREFERENCE_QUERY_TIMEOUT):
                    prefs = await self._query_preferences(recipient_id, recipient_type)
                    # Cache the result
                    await self._set_cache(cache_key, prefs)
            except asyncio.TimeoutError:
                logger.warning(
                    "Preference query timeout for %s:%s",
                    recipient_type, recipient_id
                )
                fallback_used = FallbackType.STALE_CACHE
                prefs = await self._get_fallback_preferences(cache_key)
            except Exception as e:
                logger.error(
                    "Preference query failed: %s",
                    str(e),
                    extra={
                        'recipient_id': recipient_id,
                        'recipient_type': recipient_type
                    }
                )
                self.circuit_breaker.record_failure()
                fallback_used = FallbackType.STALE_CACHE
                prefs = await self._get_fallback_preferences(cache_key)
        
        # Step 4: Evaluate preference hierarchy
        decision, reason = self._evaluate_hierarchy(prefs, notification_type, channel)
        
        return PreferenceCheckResult(
            decision=decision,
            reason=reason,
            effective_settings=prefs,
            cache_hit=cache_hit,
            cache_age_ms=cache_age_ms,
            fallback_used=fallback_used
        )
    
    async def dispatch(
        self,
        payload: NotificationPayload
    ) -> bool:
        """
        Main dispatch method that respects preferences.
        Returns True if notification was sent/queued, False otherwise.
        """
        
        # Circuit breaker check
        if self.circuit_breaker.is_open():
            logger.warning(
                "Circuit breaker open, queuing notification %s for retry",
                payload.notification_id
            )
            await self._queue_for_retry(payload)
            return False
        
        # Check preferences
        pref_check = await self.check_preferences(
            payload.recipient_id,
            payload.recipient_type,
            payload.notification_type,
            payload.channel
        )
        
        # Log the check for analytics
        await self._log_preference_check(pref_check, payload)
        
        if pref_check.decision == DispatchDecision.SKIP_DISABLED:
            logger.info(
                "Notification %s skipped due to preference: %s",
                payload.notification_id,
                pref_check.reason,
                extra={
                    'recipient_id': payload.recipient_id,
                    'notification_type': payload.notification_type,
                    'channel': payload.channel,
                    'reason': pref_check.reason
                }
            )
            return False
        
        if pref_check.decision == DispatchDecision.SKIP_FREQUENCY:
            logger.info(
                "Notification %s skipped due to frequency: %s",
                payload.notification_id,
                pref_check.reason
            )
            return False
        
        if pref_check.decision == DispatchDecision.ADD_TO_BATCH:
            await self._add_to_batch(payload, pref_check.effective_settings)
            return True
        
        # Dispatch immediately
        await self._send_immediately(payload)
        
        # Record success for circuit breaker
        self.circuit_breaker.record_success()
        
        return True
    
    def _evaluate_hierarchy(
        self,
        prefs: Dict[str, Any],
        notification_type: str,
        channel: str
    ) -> Tuple[DispatchDecision, str]:
        """
        Evaluate the full preference hierarchy.
        Returns (decision, reason) tuple.
        """
        
        # Level 1: Global toggle
        if not prefs.get('global_enabled', True):
            return DispatchDecision.SKIP_DISABLED, "Global notifications disabled"
        
        # Level 2: Notification type toggle
        type_settings = prefs.get('notification_types', {}).get(notification_type, {})
        if not type_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Notification type '{notification_type}' disabled"
        
        # Level 3: Channel toggle
        channel_settings = prefs.get('channels', {}).get(channel, {})
        if not channel_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Channel '{channel}' disabled globally"
        
        # Level 4: Type-channel override
        type_channel_settings = type_settings.get('channels', {}).get(channel, {})
        if not type_channel_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Type '{notification_type}' disabled for channel '{channel}'"
        
        # Level 5: Frequency check
        frequency = channel_settings.get('frequency', 'real_time')
        
        if frequency == 'disabled':
            return DispatchDecision.SKIP_FREQUENCY, f"Frequency set to 'disabled' for channel '{channel}'"
        
        if frequency == 'real_time':
            return DispatchDecision.SEND_IMMEDIATELY, "All checks passed - send immediately"
        
        # Batch frequency (daily_digest, weekly_summary)
        return DispatchDecision.ADD_TO_BATCH, f"Queued for {frequency}"
    
    def _build_cache_key(self, recipient_id: str, recipient_type: str) -> str:
        return f"notif:prefs:{recipient_type}:{recipient_id}"
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get preferences from Redis cache."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("Cache read failed: %s", str(e))
        return None
    
    async def _set_cache(self, key: str, prefs: Dict[str, Any]) -> None:
        """Set preferences in Redis cache."""
        try:
            cache_data = {
                'preferences': prefs,
                'cached_at': datetime.utcnow().isoformat()
            }
            await self.redis.setex(
                key,
                self.PREFERENCE_CACHE_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning("Cache write failed: %s", str(e))
    
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
    
    async def _get_fallback_preferences(self, cache_key: str) -> Dict[str, Any]:
        """
        Get fallback preferences when DB query fails.
        Priority: stale cache → defaults
        """
        
        # Try stale cache (ignore TTL)
        try:
            stale_key = f"{cache_key}:stale"
            data = await self.redis.get(stale_key)
            if data:
                logger.info("Using stale cache for preferences")
                return json.loads(data).get('preferences', {})
        except Exception:
            pass
        
        # Return defaults
        logger.info("Using default preferences as fallback")
        return self._get_default_preferences()
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Default preferences when user has no custom settings."""
        return {
            'global_enabled': True,
            'channels': {
                'in_app': {'enabled': True, 'frequency': 'real_time'},
                'email': {'enabled': True, 'frequency': 'real_time'},
                'push': {'enabled': True, 'frequency': 'real_time'},
                'toast': {'enabled': True, 'frequency': 'real_time'}
            },
            'notification_types': {},
            'batch_settings': {}
        }
    
    async def _add_to_batch(
        self,
        payload: NotificationPayload,
        prefs: Dict[str, Any]
    ) -> None:
        """Add notification to batch queue for digest/summary."""
        
        channel_settings = prefs.get('channels', {}).get(payload.channel, {})
        frequency = channel_settings.get('frequency', 'daily_digest')
        batch_settings = prefs.get('batch_settings', {})
        
        # Determine scheduled time based on frequency
        if frequency == 'daily_digest':
            digest_settings = batch_settings.get('daily_digest', {})
            preferred_time = digest_settings.get('preferred_time', '18:00')
            scheduled_for = self._get_next_daily_digest_time(preferred_time)
        elif frequency == 'weekly_summary':
            weekly_settings = batch_settings.get('weekly_summary', {})
            preferred_day = weekly_settings.get('preferred_day', 'sunday')
            preferred_time = weekly_settings.get('preferred_time', '10:00')
            scheduled_for = self._get_next_weekly_summary_time(preferred_day, preferred_time)
        else:
            scheduled_for = datetime.utcnow() + timedelta(hours=1)
        
        # Insert into batch table
        await self.db.execute(
            text("""
                INSERT INTO notification_batches (
                    recipient_id, recipient_type, channel, frequency,
                    notifications, count, scheduled_for
                ) VALUES (
                    :recipient_id, :recipient_type, :channel, :frequency,
                    :notifications, 1, :scheduled_for
                )
                ON CONFLICT (recipient_id, recipient_type, channel, frequency, scheduled_for)
                DO UPDATE SET
                    notifications = notification_batches.notifications || :notifications,
                    count = notification_batches.count + 1
            """),
            {
                'recipient_id': payload.recipient_id,
                'recipient_type': payload.recipient_type,
                'channel': payload.channel,
                'frequency': frequency,
                'notifications': json.dumps([{
                    'notification_id': payload.notification_id,
                    'notification_type': payload.notification_type,
                    'title': payload.title,
                    'body': payload.body,
                    'data': payload.data,
                    'created_at': datetime.utcnow().isoformat()
                }]),
                'scheduled_for': scheduled_for,
            }
        )
        await self.db.commit()
        
        logger.info(
            "Added notification %s to %s batch for %s",
            payload.notification_id, frequency, payload.recipient_id
        )
    
    def _get_next_daily_digest_time(self, preferred_time: str) -> datetime:
        """Get next scheduled time for daily digest."""
        now = datetime.utcnow()
        hour, minute = map(int, preferred_time.split(':'))
        
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if scheduled <= now:
            scheduled += timedelta(days=1)
        
        return scheduled
    
    def _get_next_weekly_summary_time(
        self,
        preferred_day: str,
        preferred_time: str
    ) -> datetime:
        """Get next scheduled time for weekly summary."""
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        now = datetime.utcnow()
        target_day = day_map.get(preferred_day.lower(), 6)
        hour, minute = map(int, preferred_time.split(':'))
        
        days_ahead = target_day - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        scheduled += timedelta(days=days_ahead)
        
        return scheduled
    
    async def _send_immediately(self, payload: NotificationPayload) -> None:
        """Send notification immediately via appropriate channel."""
        
        # This would integrate with actual notification providers
        # (SendGrid, Firebase, etc.)
        
        if payload.channel == 'email':
            await self._send_email(payload)
        elif payload.channel == 'push':
            await self._send_push(payload)
        elif payload.channel == 'in_app':
            await self._send_in_app(payload)
        elif payload.channel == 'toast':
            await self._send_toast(payload)
        
        # Log the dispatch
        await self._log_dispatch(payload)
    
    async def _send_email(self, payload: NotificationPayload) -> None:
        """Send email notification."""
        # Integration with email provider (SendGrid, SES, etc.)
        logger.info(
            "Sending email notification %s to %s",
            payload.notification_id, payload.recipient_id
        )
    
    async def _send_push(self, payload: NotificationPayload) -> None:
        """Send push notification."""
        # Integration with push provider (Firebase, APNS)
        logger.info(
            "Sending push notification %s to %s",
            payload.notification_id, payload.recipient_id
        )
    
    async def _send_in_app(self, payload: NotificationPayload) -> None:
        """Send in-app notification via WebSocket."""
        # Integration with WebSocket hub
        logger.info(
            "Sending in-app notification %s to %s",
            payload.notification_id, payload.recipient_id
        )
    
    async def _send_toast(self, payload: NotificationPayload) -> None:
        """Send toast notification."""
        # Integration with real-time toast system
        logger.info(
            "Sending toast notification %s to %s",
            payload.notification_id, payload.recipient_id
        )
    
    async def _log_dispatch(self, payload: NotificationPayload) -> None:
        """Log notification dispatch for analytics."""
        
        await self.db.execute(
            text("""
                INSERT INTO notification_events (
                    notification_id, recipient_id, recipient_type, channel,
                    event_type, payload
                ) VALUES (
                    :notification_id, :recipient_id, :recipient_type, :channel,
                    'sent', :payload
                )
            """),
            {
                'notification_id': payload.notification_id,
                'recipient_id': payload.recipient_id,
                'recipient_type': payload.recipient_type,
                'channel': payload.channel,
                'payload': json.dumps({
                    'notification_type': payload.notification_type,
                    'title': payload.title,
                    'priority': payload.priority,
                })
            }
        )
        await self.db.commit()
    
    async def _log_preference_check(
        self,
        pref_check: PreferenceCheckResult,
        payload: NotificationPayload
    ) -> None:
        """Log preference check for analytics."""
        
        logger.debug(
            "Preference check for notification %s: decision=%s, reason=%s, cache_hit=%s, fallback=%s",
            payload.notification_id,
            pref_check.decision.value,
            pref_check.reason,
            pref_check.cache_hit,
            pref_check.fallback_used.value
        )
    
    async def _queue_for_retry(self, payload: NotificationPayload) -> None:
        """Queue notification for retry when service recovers."""
        
        await self.db.execute(
            text("""
                INSERT INTO notification_sync_queue (
                    recipient_id, recipient_type, device_id, operation_type,
                    payload, sync_version, status
                ) VALUES (
                    :recipient_id, :recipient_type, :device_id, 'update',
                    :payload, :sync_version, 'pending'
                )
            """),
            {
                'recipient_id': payload.recipient_id,
                'recipient_type': payload.recipient_type,
                'device_id': 'system',
                'payload': json.dumps({
                    'notification_id': payload.notification_id,
                    'notification_type': payload.notification_type,
                    'channel': payload.channel,
                    'title': payload.title,
                    'body': payload.body,
                    'data': payload.data,
                }),
                'sync_version': f"retry:{datetime.utcnow().timestamp()}",
            }
        )
        await self.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# CACHE INVALIDATION LISTENER
# ─────────────────────────────────────────────────────────────────────────────

class PreferenceCacheListener:
    """
    Listens for preference invalidation events and refreshes local cache.
    Runs as a background task on each service instance.
    """
    
    def __init__(self, redis: redis.Redis):
        self.redis = redis
        self.pubsub = None
        self._running = False
    
    async def start(self) -> None:
        """Start listening for invalidation events."""
        self._running = True
        self.pubsub = self.redis.pubsub()
        
        try:
            await self.pubsub.subscribe('preference:invalidate')
            
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] == 'message':
                    await self._handle_invalidation(message)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self.pubsub:
            await self.pubsub.unsubscribe('preference:invalidate')
            await self.pubsub.close()
    
    async def _handle_invalidation(self, message: dict) -> None:
        """Handle a cache invalidation event."""
        try:
            data = json.loads(message['data'])
            recipient_id = data['recipient_id']
            recipient_type = data['recipient_type']
            
            cache_key = f"notif:prefs:{recipient_type}:{recipient_id}"
            
            # Delete cache entry
            await self.redis.delete(cache_key)
            
            logger.info(
                "Received cache invalidation event for %s:%s",
                recipient_type, recipient_id
            )
        except Exception as e:
            logger.error("Failed to handle invalidation: %s", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class BatchProcessor:
    """
    Processes batched notifications (daily digest, weekly summary).
    """
    
    def __init__(
        self,
        db: AsyncSession,
        redis: redis.Redis,
        dispatcher: PreferenceAwareDispatcher
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
            recipient_id = batch[1]
            recipient_type = batch[2]
            channel = batch[3]
            frequency = batch[4]
            notifications = batch[5]
            count = batch[6]
            
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
                
                # Create digest notification
                digest_payload = self._create_digest_payload(
                    recipient_id, recipient_type, channel, frequency,
                    notifications, count
                )
                
                # Send the digest
                await self.dispatcher._send_immediately(digest_payload)
                
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
                logger.error(
                    "Failed to process batch %s: %s",
                    batch_id, str(e)
                )
                
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
    
    def _create_digest_payload(
        self,
        recipient_id: str,
        recipient_type: str,
        channel: str,
        frequency: str,
        notifications: List[Dict],
        count: int
    ) -> NotificationPayload:
        """Create a digest notification from batched items."""
        
        if frequency == 'daily_digest':
            title = f"Your Daily Digest ({count} notifications)"
            body = f"You have {count} notifications from today."
        else:
            title = f"Your Weekly Summary ({count} notifications)"
            body = f"You have {count} notifications from this week."
        
        return NotificationPayload(
            notification_id=f"digest-{datetime.utcnow().timestamp()}",
            notification_type='digest',
            channel=channel,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            title=title,
            body=body,
            data={
                'notifications': notifications[:10],  # Include first 10
                'total_count': count,
                'frequency': frequency,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def should_send_notification(
    db: AsyncSession,
    redis: redis.Redis,
    recipient_id: str,
    recipient_type: str,
    notification_type: str,
    channel: str
) -> Tuple[bool, str]:
    """
    Convenience function to check if a notification should be sent.
    
    Returns: (should_send: bool, reason: str)
    """
    
    dispatcher = PreferenceAwareDispatcher(db, redis)
    result = await dispatcher.check_preferences(
        recipient_id, recipient_type, notification_type, channel
    )
    
    if result.decision in (DispatchDecision.SEND_IMMEDIATELY, DispatchDecision.ADD_TO_BATCH):
        return True, result.reason
    
    return False, result.reason
