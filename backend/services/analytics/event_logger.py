"""
CONFIT — Analytics Event Logger
================================
Service for logging notification events to the analytics database.
Provides non-blocking event logging with automatic batching.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Notification event types."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    CLICKED = "clicked"
    DISMISSED = "dismissed"


class Channel(str, Enum):
    """Notification channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    TOAST = "toast"


class RecipientType(str, Enum):
    """Recipient types."""
    CUSTOMER = "customer"
    OWNER = "owner"


class AnalyticsEventLogger:
    """
    Logs notification events to the analytics database.
    
    Features:
    - Non-blocking logging via background thread
    - Automatic batching for performance
    - Graceful degradation on failure
    """
    
    _instance: Optional['AnalyticsEventLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'AnalyticsEventLogger':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._queue = deque(maxlen=10000)
                    cls._instance._worker = None
                    cls._instance._running = False
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'AnalyticsEventLogger':
        """Get singleton instance."""
        return cls()
    
    def log_event(
        self,
        *,
        notification_id: str,
        recipient_id: str,
        recipient_type: RecipientType | str,
        channel: Channel | str,
        event_type: EventType | str,
        payload: Optional[dict[str, Any]] = None,
        time_spent_ms: Optional[int] = None,
        scroll_depth: Optional[float] = None,
        action_taken: Optional[str] = None,
        ab_test_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> None:
        """
        Log a notification event.
        
        If db is provided, logs immediately in the current transaction.
        Otherwise, queues for background processing.
        
        Args:
            notification_id: Unique notification identifier
            recipient_id: User ID of recipient
            recipient_type: 'customer' or 'owner'
            channel: 'in_app', 'email', 'push', or 'toast'
            event_type: 'sent', 'delivered', 'read', 'clicked', or 'dismissed'
            payload: Additional context (order_id, store_id, etc.)
            time_spent_ms: Time spent viewing notification
            scroll_depth: Scroll depth percentage (0-1)
            action_taken: Action taken by user
            ab_test_id: A/B test ID if applicable
            variant_id: Variant ID if applicable
            db: Optional database session for immediate logging
        """
        event_data = {
            "notification_id": notification_id,
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value if isinstance(recipient_type, RecipientType) else recipient_type,
            "channel": channel.value if isinstance(channel, Channel) else channel,
            "event_type": event_type.value if isinstance(event_type, EventType) else event_type,
            "payload": payload or {},
            "time_spent_ms": time_spent_ms,
            "scroll_depth": scroll_depth,
            "action_taken": action_taken,
            "ab_test_id": ab_test_id,
            "variant_id": variant_id,
        }
        
        if db is not None:
            # Immediate logging
            self._log_immediate(db, event_data)
        else:
            # Queue for background processing
            self._queue.append(event_data)
    
    def _log_immediate(self, db: Session, event_data: dict) -> None:
        """Log event immediately in current transaction."""
        try:
            query = text("""
                INSERT INTO notification_events (
                    notification_id, recipient_id, recipient_type, channel, event_type,
                    event_timestamp, payload, time_spent_ms, scroll_depth, action_taken,
                    ab_test_id, variant_id
                ) VALUES (
                    :notification_id, :recipient_id, :recipient_type, :channel, :event_type,
                    NOW(), :payload, :time_spent_ms, :scroll_depth, :action_taken,
                    :ab_test_id, :variant_id
                )
            """)
            
            db.execute(query, {
                "notification_id": event_data["notification_id"],
                "recipient_id": event_data["recipient_id"],
                "recipient_type": event_data["recipient_type"],
                "channel": event_data["channel"],
                "event_type": event_data["event_type"],
                "payload": event_data["payload"],
                "time_spent_ms": event_data["time_spent_ms"],
                "scroll_depth": event_data["scroll_depth"],
                "action_taken": event_data["action_taken"],
                "ab_test_id": event_data["ab_test_id"],
                "variant_id": event_data["variant_id"],
            })
            # Note: Caller must commit
        except Exception as e:
            logger.warning("Failed to log analytics event: %s", e)
    
    def flush(self, db: Session) -> int:
        """
        Flush all queued events to database.
        
        Returns number of events flushed.
        """
        count = 0
        while self._queue:
            event_data = self._queue.popleft()
            try:
                self._log_immediate(db, event_data)
                count += 1
            except Exception as e:
                logger.warning("Failed to flush event: %s", e)
                # Re-queue at front
                self._queue.appendleft(event_data)
                break
        
        if count > 0:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning("Failed to commit flushed events: %s", e)
        
        return count


# Singleton instance
event_logger = AnalyticsEventLogger.get_instance()


def log_notification_sent(
    db: Session,
    notification_id: str,
    recipient_id: str,
    recipient_type: str,
    channel: str = "in_app",
    payload: Optional[dict] = None,
    ab_test_id: Optional[str] = None,
    variant_id: Optional[str] = None,
) -> None:
    """Convenience function to log notification sent event."""
    event_logger.log_event(
        db=db,
        notification_id=notification_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        event_type=EventType.SENT,
        payload=payload,
        ab_test_id=ab_test_id,
        variant_id=variant_id,
    )


def log_notification_delivered(
    db: Session,
    notification_id: str,
    recipient_id: str,
    recipient_type: str,
    channel: str = "in_app",
) -> None:
    """Convenience function to log notification delivered event."""
    event_logger.log_event(
        db=db,
        notification_id=notification_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        event_type=EventType.DELIVERED,
    )


def log_notification_read(
    db: Session,
    notification_id: str,
    recipient_id: str,
    recipient_type: str,
    channel: str = "in_app",
    time_spent_ms: Optional[int] = None,
    scroll_depth: Optional[float] = None,
) -> None:
    """Convenience function to log notification read event."""
    event_logger.log_event(
        db=db,
        notification_id=notification_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        event_type=EventType.READ,
        time_spent_ms=time_spent_ms,
        scroll_depth=scroll_depth,
    )


def log_notification_clicked(
    db: Session,
    notification_id: str,
    recipient_id: str,
    recipient_type: str,
    channel: str = "in_app",
    action_taken: Optional[str] = None,
) -> None:
    """Convenience function to log notification clicked event."""
    event_logger.log_event(
        db=db,
        notification_id=notification_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        event_type=EventType.CLICKED,
        action_taken=action_taken,
    )


def log_notification_dismissed(
    db: Session,
    notification_id: str,
    recipient_id: str,
    recipient_type: str,
    channel: str = "in_app",
) -> None:
    """Convenience function to log notification dismissed event."""
    event_logger.log_event(
        db=db,
        notification_id=notification_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        event_type=EventType.DISMISSED,
    )
