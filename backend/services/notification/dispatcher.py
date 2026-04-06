"""
CONFIT Backend - Multi-Channel Notification Dispatcher
=====================================================
Routes notifications to multiple channels based on user preferences,
DND hours, and channel availability with fallback support.
"""

import logging
from datetime import datetime, timezone, time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from services.integrations.firebase_client import get_firebase_client
from services.integrations.twilio_whatsapp_client import get_twilio_whatsapp_client
from services.integrations.sms_client import get_sms_client
from services.integrations.sendgrid_client import get_sendgrid_client
from services.integrations.base import IntegrationError

logger = logging.getLogger(__name__)


# # -------------------------------------------------------------------------
# ENUMS
# # -------------------------------------------------------------------------

class Channel(str, Enum):
    """Notification delivery channels."""
    PUSH = "push"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DispatchStatus(str, Enum):
    """Dispatch result status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


# # -------------------------------------------------------------------------
# DATA CLASSES
# # -------------------------------------------------------------------------

@dataclass
class NotificationRequest:
    """Notification request to dispatch."""
    recipient_id: str
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    fcm_tokens: List[str] = field(default_factory=list)
    title: str = ""
    body: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    channels: List[Channel] = field(default_factory=list)
    priority: NotificationPriority = NotificationPriority.NORMAL
    notification_type: str = "general"
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Result of notification dispatch."""
    request_id: str
    status: DispatchStatus
    channels_attempted: List[Channel] = field(default_factory=list)
    channels_succeeded: List[Channel] = field(default_factory=list)
    channels_failed: List[Channel] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    message_ids: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# # -------------------------------------------------------------------------
# NOTIFICATION DISPATCHER
# # -------------------------------------------------------------------------

class NotificationDispatcher:
    """
    Multi-channel notification dispatcher with fallback support.
    
    Features:
    - Routes to multiple channels based on user preferences
    - Respects DND (Do Not Disturb) hours
    - Fallback ladder: Push -> WhatsApp -> SMS -> Email
    - Celery task enqueueing for async processing
    - Channel health monitoring
    
    Egypt-specific:
    - WhatsApp preferred for rich notifications
    - SMS for OTP and critical alerts (local providers)
    - Push for app users
    - Email for receipts and formal communications
    """
    
    # Fallback order (highest to lowest priority)
    FALLBACK_ORDER = [
        Channel.PUSH,
        Channel.WHATSAPP,
        Channel.SMS,
        Channel.EMAIL,
    ]
    
    # DND hours (Egypt timezone: UTC+2 or UTC+3 depending on DST)
    DND_START = time(22, 0)  # 10 PM
    DND_END = time(8, 0)  # 8 AM
    
    # Skip DND for these notification types
    DND_EXCEPTIONS = {
        "security_alert",
        "otp",
        "order_delivery",
        "urgent",
    }
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        celery_app: Optional[Any] = None,
    ):
        self.db = db
        self.celery_app = celery_app
        
        # Lazy-loaded clients
        self._firebase = None
        self._whatsapp = None
        self._sms = None
        self._sendgrid = None
        
        # Channel health status
        self._channel_health: Dict[str, bool] = {
            Channel.PUSH.value: True,
            Channel.WHATSAPP.value: True,
            Channel.SMS.value: True,
            Channel.EMAIL.value: True,
        }
    
    @property
    def firebase(self):
        """Get Firebase FCM client."""
        if self._firebase is None:
            self._firebase = get_firebase_client()
        return self._firebase
    
    @property
    def whatsapp(self):
        """Get Twilio WhatsApp client."""
        if self._whatsapp is None:
            self._whatsapp = get_twilio_whatsapp_client()
        return self._whatsapp
    
    @property
    def sms(self):
        """Get SMS client."""
        if self._sms is None:
            self._sms = get_sms_client()
        return self._sms
    
    @property
    def sendgrid(self):
        """Get SendGrid client."""
        if self._sendgrid is None:
            self._sendgrid = get_sendgrid_client()
        return self._sendgrid
    
    def is_dnd_active(self, notification_type: str) -> bool:
        """
        Check if DND is currently active for this notification type.
        
        DND is active between 10 PM and 8 AM Egypt time.
        Security alerts, OTP, and urgent notifications bypass DND.
        """
        if notification_type in self.DND_EXCEPTIONS:
            return False
        
        # Get current time in Egypt (simplified - use pytz for accuracy)
        now_utc = datetime.now(timezone.utc)
        # Egypt is UTC+2 (winter) or UTC+3 (summer)
        # Simplified: assume UTC+2
        egypt_hour = (now_utc.hour + 2) % 24
        current_time = time(egypt_hour, now_utc.minute)
        
        # Check if within DND window
        if self.DND_START <= current_time or current_time < self.DND_END:
            return True
        
        return False
    
    def get_available_channels(
        self,
        request: NotificationRequest,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Channel]:
        """
        Determine available channels for this notification.
        
        Considers:
        - User preferences
        - Channel health
        - DND hours
        - Contact info availability
        """
        available = []
        
        # Check DND
        if self.is_dnd_active(request.notification_type):
            # During DND, only allow in-app and email
            if request.recipient_email:
                available.append(Channel.EMAIL)
            available.append(Channel.IN_APP)
            return available
        
        # Check each channel
        for channel in request.channels or self.FALLBACK_ORDER:
            # Check channel health
            if not self._channel_health.get(channel.value, True):
                continue
            
            # Check contact info
            if channel == Channel.PUSH and not request.fcm_tokens:
                continue
            if channel == Channel.WHATSAPP and not request.recipient_phone:
                continue
            if channel == Channel.SMS and not request.recipient_phone:
                continue
            if channel == Channel.EMAIL and not request.recipient_email:
                continue
            
            # Check user preferences
            if preferences:
                channel_prefs = preferences.get("channels", {}).get(channel.value, {})
                if not channel_prefs.get("enabled", True):
                    continue
            
            available.append(channel)
        
        return available
    
    async def dispatch(
        self,
        request: NotificationRequest,
        preferences: Optional[Dict[str, Any]] = None,
        use_fallback: bool = True,
    ) -> DispatchResult:
        """
        Dispatch notification to appropriate channels.
        
        Args:
            request: Notification request
            preferences: User notification preferences
            use_fallback: Whether to use fallback channels on failure
            
        Returns:
            DispatchResult with status and details
        """
        request_id = f"notif-{request.recipient_id}-{datetime.now(timezone.utc).timestamp()}"
        
        result = DispatchResult(
            request_id=request_id,
            status=DispatchStatus.SKIPPED,
        )
        
        # Get available channels
        channels = self.get_available_channels(request, preferences)
        
        if not channels:
            logger.warning(
                f"[dispatcher] No available channels for notification to {request.recipient_id}"
            )
            return result
        
        # Sort by fallback order
        ordered_channels = [
            ch for ch in self.FALLBACK_ORDER
            if ch in channels
        ]
        
        # Add in_app at the end (always available)
        if Channel.IN_APP not in ordered_channels:
            ordered_channels.append(Channel.IN_APP)
        
        # Try each channel
        success = False
        for channel in ordered_channels:
            result.channels_attempted.append(channel)
            
            try:
                message_id = await self._send_to_channel(channel, request)
                result.channels_succeeded.append(channel)
                result.message_ids[channel.value] = message_id
                success = True
                
                # For non-urgent notifications, stop after first success
                if request.priority != NotificationPriority.URGENT and use_fallback:
                    break
                    
            except IntegrationError as e:
                result.channels_failed.append(channel)
                result.errors[channel.value] = str(e)
                logger.error(
                    f"[dispatcher] Failed to send via {channel.value}: {e}"
                )
                
                # Mark channel as unhealthy if multiple failures
                # (would need failure counting in production)
                
                # Continue to fallback if enabled
                if not use_fallback:
                    break
        
        # Determine final status
        if result.channels_succeeded:
            if result.channels_failed:
                result.status = DispatchStatus.PARTIAL
            else:
                result.status = DispatchStatus.SUCCESS
        else:
            result.status = DispatchStatus.FAILED
        
        logger.info(
            f"[dispatcher] Dispatch {result.status.value} for {request_id}: "
            f"succeeded={result.channels_succeeded}, failed={result.channels_failed}"
        )
        
        return result
    
    async def _send_to_channel(
        self,
        channel: Channel,
        request: NotificationRequest,
    ) -> str:
        """Send notification via specific channel."""
        
        if channel == Channel.PUSH:
            return await self._send_push(request)
        elif channel == Channel.WHATSAPP:
            return await self._send_whatsapp(request)
        elif channel == Channel.SMS:
            return await self._send_sms(request)
        elif channel == Channel.EMAIL:
            return await self._send_email(request)
        elif channel == Channel.IN_APP:
            return await self._send_in_app(request)
        else:
            raise IntegrationError(
                f"Unknown channel: {channel}",
                provider="dispatcher",
            )
    
    async def _send_push(self, request: NotificationRequest) -> str:
        """Send push notification via Firebase FCM."""
        if not request.fcm_tokens:
            raise IntegrationError(
                "No FCM tokens available",
                provider="firebase",
            )
        
        if len(request.fcm_tokens) == 1:
            return await self.firebase.send_to_token(
                token=request.fcm_tokens[0],
                title=request.title,
                body=request.body,
                data=request.data,
            )
        else:
            result = await self.firebase.send_multicast(
                tokens=request.fcm_tokens,
                title=request.title,
                body=request.body,
                data=request.data,
            )
            return f"multicast:{result['success_count']}/{len(request.fcm_tokens)}"
    
    async def _send_whatsapp(self, request: NotificationRequest) -> str:
        """Send WhatsApp message via Twilio."""
        if not request.recipient_phone:
            raise IntegrationError(
                "No phone number available",
                provider="twilio_whatsapp",
            )
        
        # For OTP, use template
        if request.notification_type == "otp":
            # Would need approved template
            return await self.whatsapp.send_template(
                to_phone=request.recipient_phone,
                template_sid=request.metadata.get("whatsapp_template_sid", ""),
                variables=request.metadata.get("template_variables", {}),
                language_code=request.language,
            )
        
        # For other types, try freeform (only works in 24h window)
        return await self.whatsapp.send_freeform(
            to_phone=request.recipient_phone,
            body=f"*{request.title}*\n\n{request.body}",
        )
    
    async def _send_sms(self, request: NotificationRequest) -> str:
        """Send SMS via local Egyptian provider."""
        if not request.recipient_phone:
            raise IntegrationError(
                "No phone number available",
                provider="sms",
            )
        
        # Use appropriate SMS type
        if request.notification_type == "otp":
            result = await self.sms.send_otp(
                to=request.recipient_phone,
                otp_code=request.data.get("otp_code", ""),
                expiry_minutes=request.data.get("expiry_minutes", 5),
                language=request.language,
            )
        elif request.notification_type == "order_delivery":
            result = await self.sms.send_delivery_alert(
                to=request.recipient_phone,
                order_number=request.data.get("order_number", ""),
                status=request.body,
                tracking_url=request.data.get("tracking_url"),
                language=request.language,
            )
        else:
            result = await self.sms.send(
                to=request.recipient_phone,
                body=f"{request.title}: {request.body}",
            )
        
        if not result.success:
            raise IntegrationError(
                result.error_message or "SMS send failed",
                provider="sms",
            )
        
        return result.message_id or "sms-sent"
    
    async def _send_email(self, request: NotificationRequest) -> str:
        """Send email via SendGrid."""
        if not request.recipient_email:
            raise IntegrationError(
                "No email address available",
                provider="sendgrid",
            )
        
        # Use template if specified
        template_id = request.metadata.get("email_template_id")
        template_data = request.metadata.get("email_template_data", {})
        
        if template_id:
            result = await self.sendgrid.send_email(
                to_email=request.recipient_email,
                subject=request.title,
                template_id=template_id,
                template_data={
                    "title": request.title,
                    "body": request.body,
                    **template_data,
                },
            )
        else:
            # Plain email
            result = await self.sendgrid.send_email(
                to_email=request.recipient_email,
                subject=request.title,
                html_content=f"<h2>{request.title}</h2><p>{request.body}</p>",
                text_content=f"{request.title}\n\n{request.body}",
            )
        
        return result.get("message_id", "email-sent")
    
    async def _send_in_app(self, request: NotificationRequest) -> str:
        """Store in-app notification for user."""
        # This would insert into notifications table
        # and/or push via WebSocket
        notification_id = f"in-app-{datetime.now(timezone.utc).timestamp()}"
        
        # If db available, store notification
        if self.db:
            from sqlalchemy import text
            await self.db.execute(
                text("""
                    INSERT INTO notifications (
                        id, recipient_id, type, title, body, data, created_at
                    ) VALUES (
                        :id, :recipient_id, :type, :title, :body, :data, NOW()
                    )
                """),
                {
                    "id": notification_id,
                    "recipient_id": request.recipient_id,
                    "type": request.notification_type,
                    "title": request.title,
                    "body": request.body,
                    "data": request.data,
                }
            )
            await self.db.commit()
        
        return notification_id
    
    async def dispatch_batch(
        self,
        requests: List[NotificationRequest],
        enqueue: bool = True,
    ) -> List[DispatchResult]:
        """
        Dispatch multiple notifications.
        
        Args:
            requests: List of notification requests
            enqueue: Whether to enqueue via Celery for async processing
            
        Returns:
            List of dispatch results
        """
        if enqueue and self.celery_app:
            # Enqueue via Celery
            from services.notification.celery_tasks import send_notification_batch
            task = send_notification_batch.delay([
                {
                    "recipient_id": r.recipient_id,
                    "recipient_phone": r.recipient_phone,
                    "recipient_email": r.recipient_email,
                    "fcm_tokens": r.fcm_tokens,
                    "title": r.title,
                    "body": r.body,
                    "data": r.data,
                    "channels": [c.value for c in r.channels],
                    "priority": r.priority.value,
                    "notification_type": r.notification_type,
                    "language": r.language,
                }
                for r in requests
            ])
            return [DispatchResult(
                request_id=f"batch-{task.id}",
                status=DispatchStatus.SUCCESS,
                message_ids={"celery_task": task.id},
            )]
        
        # Process synchronously
        results = []
        for request in requests:
            result = await self.dispatch(request)
            results.append(result)
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all notification channels."""
        health = {}
        
        # Check Firebase
        try:
            health[Channel.PUSH.value] = await self.firebase.health_check()
        except Exception as e:
            health[Channel.PUSH.value] = {"healthy": False, "error": str(e)}
        
        # Check WhatsApp
        try:
            health[Channel.WHATSAPP.value] = await self.whatsapp.health_check()
        except Exception as e:
            health[Channel.WHATSAPP.value] = {"healthy": False, "error": str(e)}
        
        # Check SMS
        try:
            health[Channel.SMS.value] = await self.sms.health_check()
        except Exception as e:
            health[Channel.SMS.value] = {"healthy": False, "error": str(e)}
        
        # Check Email
        try:
            health[Channel.EMAIL.value] = await self.sendgrid.health_check()
        except Exception as e:
            health[Channel.EMAIL.value] = {"healthy": False, "error": str(e)}
        
        # Update internal health status
        for channel, status in health.items():
            if isinstance(status, dict):
                self._channel_health[channel] = status.get("healthy", False)
            else:
                self._channel_health[channel] = bool(status)
        
        return health


# # -------------------------------------------------------------------------
# SINGLETON
# # -------------------------------------------------------------------------

_dispatcher: Optional[NotificationDispatcher] = None


def get_dispatcher() -> NotificationDispatcher:
    """Get notification dispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = NotificationDispatcher()
    return _dispatcher
