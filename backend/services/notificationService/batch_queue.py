"""
CONFIT Backend — Batch Notification Queue Service
=================================================
Manages queuing and processing of batch notifications (daily digest, weekly summary).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database.models import NotificationQueue, NotificationPreferences, Notification
from database.session import SessionLocal

logger = logging.getLogger(__name__)


class BatchType(str, Enum):
    DAILY_DIGEST = "daily_digest"
    WEEKLY_SUMMARY = "weekly_summary"


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class BatchQueueService:
    """
    Service for managing batch notification queue.
    Handles queuing, scheduling, and processing of digest notifications.
    """

    @staticmethod
    def queue_notification(
        db: Session,
        recipient_id: str,
        recipient_type: str,
        notification_type: str,
        channel: str,
        payload: Dict[str, Any],
        batch_type: BatchType,
    ) -> NotificationQueue:
        """
        Queue a notification for batch delivery.
        Calculates the scheduled_for timestamp based on batch type.
        """
        # Calculate scheduled time
        now = datetime.now(timezone.utc)
        
        if batch_type == BatchType.DAILY_DIGEST:
            # Schedule for next day at 9 AM UTC
            scheduled_for = (now + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
        else:  # WEEKLY_SUMMARY
            # Schedule for next Monday at 9 AM UTC
            days_until_monday = (7 - now.weekday()) % 7 or 7
            scheduled_for = (now + timedelta(days=days_until_monday)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        queue_item = NotificationQueue(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            batch_type=batch_type.value,
            notification_payload=payload,
            notification_type=notification_type,
            channel=channel,
            scheduled_for=scheduled_for,
            status=QueueStatus.PENDING.value,
        )

        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)

        logger.info(
            "Queued %s notification for user %s (scheduled: %s)",
            batch_type.value,
            recipient_id,
            scheduled_for.isoformat(),
        )

        return queue_item

    @staticmethod
    def get_pending_batch(
        db: Session,
        recipient_id: str,
        recipient_type: str,
        batch_type: BatchType,
    ) -> List[NotificationQueue]:
        """
        Get all pending notifications for a user's batch.
        """
        return (
            db.query(NotificationQueue)
            .filter(
                NotificationQueue.recipient_id == recipient_id,
                NotificationQueue.recipient_type == recipient_type,
                NotificationQueue.batch_type == batch_type.value,
                NotificationQueue.status == QueueStatus.PENDING.value,
            )
            .order_by(NotificationQueue.created_at.asc())
            .all()
        )

    @staticmethod
    def process_due_batches(db: Session) -> int:
        """
        Process all batch notifications that are due.
        Called by the scheduler.
        Returns count of processed batches.
        """
        now = datetime.now(timezone.utc)

        # Find all due pending items
        due_items = (
            db.query(NotificationQueue)
            .filter(
                NotificationQueue.status == QueueStatus.PENDING.value,
                NotificationQueue.scheduled_for <= now,
            )
            .all()
        )

        if not due_items:
            return 0

        # Group by recipient for batch processing
        grouped: Dict[str, List[NotificationQueue]] = {}
        for item in due_items:
            key = f"{item.recipient_id}:{item.recipient_type}:{item.batch_type}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)

        processed_count = 0

        for group_key, items in grouped.items():
            recipient_id = items[0].recipient_id
            recipient_type = items[0].recipient_type
            batch_type = items[0].batch_type

            try:
                # Mark as processing
                for item in items:
                    item.status = QueueStatus.PROCESSING.value
                db.commit()

                # Build digest content
                digest_content = BatchQueueService._build_digest(db, items)

                # Send the batch notification
                success = BatchQueueService._send_batch_notification(
                    db,
                    recipient_id,
                    recipient_type,
                    batch_type,
                    digest_content,
                )

                # Update status
                for item in items:
                    item.status = QueueStatus.SENT.value if success else QueueStatus.FAILED.value
                    item.processed_at = now
                db.commit()

                if success:
                    processed_count += 1
                    logger.info(
                        "Processed %s for user %s (%d notifications)",
                        batch_type,
                        recipient_id,
                        len(items),
                    )

            except Exception as e:
                logger.error(
                    "Failed to process %s for user %s: %s",
                    batch_type,
                    recipient_id,
                    e,
                )
                # Mark as failed
                for item in items:
                    item.status = QueueStatus.FAILED.value
                    item.processed_at = now
                db.commit()

        return processed_count

    @staticmethod
    def _build_digest(db: Session, items: List[NotificationQueue]) -> Dict[str, Any]:
        """
        Build digest content from queued notifications.
        """
        notifications = []
        for item in items:
            notifications.append({
                "type": item.notification_type,
                "channel": item.channel,
                "payload": item.notification_payload,
                "queued_at": item.created_at.isoformat() if item.created_at else None,
            })

        return {
            "count": len(notifications),
            "notifications": notifications,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _send_batch_notification(
        db: Session,
        recipient_id: str,
        recipient_type: str,
        batch_type: str,
        digest_content: Dict[str, Any],
    ) -> bool:
        """
        Send a batch notification (digest/summary).
        Creates a single notification record with aggregated content.
        """
        try:
            # Determine title based on batch type
            if batch_type == BatchType.DAILY_DIGEST.value:
                title = "Daily Digest"
                message = f"You have {digest_content['count']} notifications from today."
            else:
                title = "Weekly Summary"
                message = f"You have {digest_content['count']} notifications from this week."

            # Create notification record
            notification = Notification(
                id=f"batch-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{recipient_id[:8]}",
                receiver_id=recipient_id,
                order_id="",  # Batch notifications aren't tied to specific orders
                message=message,
                metadata_json={
                    "type": "batch_digest",
                    "batch_type": batch_type,
                    "title": title,
                    "digest": digest_content,
                },
                read_status=False,
                idempotency_key=f"batch-{batch_type}-{recipient_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            )

            db.add(notification)
            db.commit()

            # Emit via realtime hub if available
            try:
                from services.notificationService.realtime import realtime_hub
                import asyncio

                async def emit():
                    await realtime_hub.emit_to_user(
                        recipient_id,
                        {
                            "type": "notification.batch",
                            "data": {
                                "id": notification.id,
                                "title": title,
                                "message": message,
                                "batch_type": batch_type,
                                "count": digest_content["count"],
                            },
                        },
                    )

                # Run in event loop if available
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(emit())
                    else:
                        loop.run_until_complete(emit())
                except RuntimeError:
                    pass  # No event loop available

            except ImportError:
                pass  # realtime_hub not available

            return True

        except Exception as e:
            logger.error("Failed to send batch notification: %s", e)
            return False

    @staticmethod
    def cleanup_old_processed_items(db: Session, days: int = 30) -> int:
        """
        Remove processed queue items older than specified days.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        deleted = (
            db.query(NotificationQueue)
            .filter(
                NotificationQueue.status.in_([
                    QueueStatus.SENT.value,
                    QueueStatus.FAILED.value,
                ]),
                NotificationQueue.processed_at < cutoff,
            )
            .delete()
        )
        db.commit()

        if deleted > 0:
            logger.info("Cleaned up %d old processed queue items", deleted)

        return deleted


def should_queue_for_batch(
    db: Session,
    recipient_id: str,
    recipient_type: str,
    frequency: str,
) -> bool:
    """
    Determine if a notification should be queued for batch delivery
    based on user preferences and frequency setting.
    """
    if frequency in ("daily_digest", "weekly_summary"):
        # Check if batch is enabled in preferences
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.recipient_id == recipient_id,
            NotificationPreferences.recipient_type == recipient_type,
        ).first()

        if prefs and prefs.batch_options:
            batch_opts = prefs.batch_options
            if batch_opts.get("enabled", False):
                return True

    return False
