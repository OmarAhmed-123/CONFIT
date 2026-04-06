"""
CONFIT Backend - Notification Trigger Registry
==============================================

Implements all 10 lifecycle triggers with actor fan-out.
Each trigger is an async function that fans out to NotificationDispatcher.

Trigger Actor Matrix:
| # | Trigger              | Customer | Store | Factory |
|---|---------------------|----------|-------|---------|
| 1 | Order Placed        |    Y     |   Y   |    Y    |
| 2 | Payment Confirmed   |    Y     |   -   |    Y    |
| 3 | Production Started  |    Y     |   -   |    Y    |
| 4 | Midway Rejection    |    Y     |   Y   |    Y    |
| 5 | Dispatched          |    Y     |   Y   |    -    |
| 6 | Ready for BOPIS     |    Y     |   Y   |    -    |
| 7 | Delivered           |    Y     |   -   |    -    |
| 8 | Return Initiated    |    Y     |   Y   |    Y    |
| 9 | Coupon Redeemed     |    Y     |   Y   |    -    |
|10 | Donor Coupon Claimed|  Donor   |   Y   |    -    |
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ActorType,
    Notification,
    NotificationPreferences,
    Order,
    OrderItem,
    Store,
    User,
)
from services.notification.dispatcher import (
    Channel,
    NotificationDispatcher,
    NotificationPriority,
    NotificationRequest,
    get_dispatcher,
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# TRIGGER ENUMS
# -------------------------------------------------------------------------

class TriggerType(str, Enum):
    """All notification trigger types."""
    ORDER_PLACED = "order_placed"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PRODUCTION_STARTED = "production_started"
    MIDWAY_REJECTION = "midway_rejection"
    DISPATCHED = "dispatched"
    READY_FOR_BOPIS = "ready_for_bopis"
    DELIVERED = "delivered"
    RETURN_INITIATED = "return_initiated"
    COUPON_REDEEMED = "coupon_redeemed"
    DONOR_COUPON_CLAIMED = "donor_coupon_claimed"


class NotificationCategory(str, Enum):
    """Notification categories for preference filtering."""
    ORDERS = "orders"
    STYLING = "styling"
    PROMOTIONS = "promotions"
    DONOR_IMPACT = "donor_impact"


# -------------------------------------------------------------------------
# TRIGGER CONFIGURATION
# -------------------------------------------------------------------------

# Actor fan-out configuration per trigger
TRIGGER_ACTORS: Dict[TriggerType, Set[ActorType]] = {
    TriggerType.ORDER_PLACED: {ActorType.CUSTOMER, ActorType.STORE, ActorType.FACTORY},
    TriggerType.PAYMENT_CONFIRMED: {ActorType.CUSTOMER, ActorType.FACTORY},
    TriggerType.PRODUCTION_STARTED: {ActorType.CUSTOMER, ActorType.FACTORY},
    TriggerType.MIDWAY_REJECTION: {ActorType.CUSTOMER, ActorType.STORE, ActorType.FACTORY},
    TriggerType.DISPATCHED: {ActorType.CUSTOMER, ActorType.STORE},
    TriggerType.READY_FOR_BOPIS: {ActorType.CUSTOMER, ActorType.STORE},
    TriggerType.DELIVERED: {ActorType.CUSTOMER},
    TriggerType.RETURN_INITIATED: {ActorType.CUSTOMER, ActorType.STORE, ActorType.FACTORY},
    TriggerType.COUPON_REDEEMED: {ActorType.CUSTOMER, ActorType.STORE},
    TriggerType.DONOR_COUPON_CLAIMED: {ActorType.DONOR, ActorType.STORE},
}

# Priority per trigger type
TRIGGER_PRIORITY: Dict[TriggerType, NotificationPriority] = {
    TriggerType.ORDER_PLACED: NotificationPriority.HIGH,
    TriggerType.PAYMENT_CONFIRMED: NotificationPriority.HIGH,
    TriggerType.PRODUCTION_STARTED: NotificationPriority.NORMAL,
    TriggerType.MIDWAY_REJECTION: NotificationPriority.URGENT,
    TriggerType.DISPATCHED: NotificationPriority.HIGH,
    TriggerType.READY_FOR_BOPIS: NotificationPriority.HIGH,
    TriggerType.DELIVERED: NotificationPriority.HIGH,
    TriggerType.RETURN_INITIATED: NotificationPriority.HIGH,
    TriggerType.COUPON_REDEEMED: NotificationPriority.NORMAL,
    TriggerType.DONOR_COUPON_CLAIMED: NotificationPriority.NORMAL,
}

# Category mapping for preference filtering
TRIGGER_CATEGORY: Dict[TriggerType, NotificationCategory] = {
    TriggerType.ORDER_PLACED: NotificationCategory.ORDERS,
    TriggerType.PAYMENT_CONFIRMED: NotificationCategory.ORDERS,
    TriggerType.PRODUCTION_STARTED: NotificationCategory.ORDERS,
    TriggerType.MIDWAY_REJECTION: NotificationCategory.ORDERS,
    TriggerType.DISPATCHED: NotificationCategory.ORDERS,
    TriggerType.READY_FOR_BOPIS: NotificationCategory.ORDERS,
    TriggerType.DELIVERED: NotificationCategory.ORDERS,
    TriggerType.RETURN_INITIATED: NotificationCategory.ORDERS,
    TriggerType.COUPON_REDEEMED: NotificationCategory.PROMOTIONS,
    TriggerType.DONOR_COUPON_CLAIMED: NotificationCategory.DONOR_IMPACT,
}

# Channel ladder per priority
PRIORITY_CHANNELS: Dict[NotificationPriority, List[Channel]] = {
    NotificationPriority.HIGH: [Channel.PUSH, Channel.WHATSAPP, Channel.SMS],
    NotificationPriority.URGENT: [Channel.PUSH, Channel.WHATSAPP, Channel.SMS],
    NotificationPriority.NORMAL: [Channel.PUSH, Channel.EMAIL],
    NotificationPriority.LOW: [Channel.IN_APP],
}


# -------------------------------------------------------------------------
# DATA CLASSES
# -------------------------------------------------------------------------

@dataclass
class TriggerContext:
    """Context for a notification trigger."""
    trigger: TriggerType
    order_id: str
    order_number: str
    user_id: str  # Customer user ID
    store_id: Optional[str] = None
    factory_id: Optional[str] = None
    donor_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    # Derived fields (populated during processing)
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    store_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int = 1
    rejection_reason: Optional[str] = None
    pickup_window: Optional[str] = None
    location_tag: Optional[str] = None


@dataclass
class ActorNotification:
    """Notification to be sent to a specific actor."""
    actor_type: ActorType
    actor_id: str
    receiver_id: str  # User ID who should receive (may differ from actor_id for stores)
    title: str
    body: str
    channel: Optional[Channel] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------

def mask_phone(phone: str) -> str:
    """Mask phone number for store payloads: +20-10***4412"""
    if not phone or len(phone) < 8:
        return phone
    # Keep country code and last 4 digits
    return f"{phone[:7]}***{phone[-4:]}"


def generate_idempotency_key(trigger: TriggerType, order_id: str, actor_type: ActorType, actor_id: str) -> str:
    """Generate unique idempotency key for notification."""
    raw = f"{trigger.value}:{order_id}:{actor_type.value}:{actor_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_user_preferences(db: AsyncSession, user_id: str) -> Optional[NotificationPreferences]:
    """Get notification preferences for a user."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.recipient_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def detect_language_from_phone(phone: str) -> str:
    """Detect language from phone number. Egypt (+20) defaults to Arabic."""
    if phone and phone.startswith("+20"):
        return "ar"
    return "en"


async def resolve_channels(
    prefs: Optional[NotificationPreferences],
    priority: NotificationPriority,
    category: NotificationCategory,
) -> List[Channel]:
    """Resolve available channels based on preferences and priority."""
    # Get base channels from priority
    channels = list(PRIORITY_CHANNELS.get(priority, [Channel.IN_APP]))
    
    if not prefs:
        return channels
    
    # Filter by category preference
    categories = prefs.categories or {}
    if not categories.get(category.value, True):
        # Category disabled - only in-app
        return [Channel.IN_APP]
    
    # Filter by channel preferences
    filtered = []
    for ch in channels:
        if ch == Channel.PUSH and not prefs.push_enabled:
            continue
        if ch == Channel.EMAIL and not prefs.email_enabled:
            continue
        if ch == Channel.SMS and not prefs.sms_enabled:
            continue
        if ch == Channel.WHATSAPP and not prefs.whatsapp_enabled:
            continue
        filtered.append(ch)
    
    # Always add in-app as fallback
    if Channel.IN_APP not in filtered:
        filtered.append(Channel.IN_APP)
    
    return filtered


# -------------------------------------------------------------------------
# NOTIFICATION SERVICE
# -------------------------------------------------------------------------

class NotificationTriggerService:
    """
    Service for triggering notifications across multiple actors.
    
    Handles:
    - Actor fan-out based on trigger type
    - Preference filtering
    - DND scheduling
    - Idempotent notification creation
    """
    
    def __init__(self, db: AsyncSession, dispatcher: Optional[NotificationDispatcher] = None):
        self.db = db
        self.dispatcher = dispatcher or get_dispatcher()
    
    async def _enrich_context(self, ctx: TriggerContext) -> TriggerContext:
        """Enrich trigger context with data from database."""
        # Fetch order
        order = await self.db.get(Order, ctx.order_id)
        if order:
            ctx.order_number = order.order_number or ctx.order_number
            
            # Fetch customer
            customer = await self.db.get(User, ctx.user_id)
            if customer:
                ctx.customer_phone = customer.phone
                ctx.customer_email = customer.email
                ctx.customer_name = customer.name
                # Detect language from phone
                ctx.additional_data["language"] = await detect_language_from_phone(customer.phone or "")
            
            # Fetch store
            if ctx.store_id:
                store = await self.db.get(Store, ctx.store_id)
                if store:
                    ctx.store_name = store.name
                    ctx.location_tag = f"{store.city}, {store.country}"
            
            # Fetch first order item for SKU
            result = await self.db.execute(
                select(OrderItem).where(OrderItem.order_id == ctx.order_id).limit(1)
            )
            item = result.scalar_one_or_none()
            if item:
                ctx.product_sku = item.product_id or "N/A"
                ctx.product_name = item.name
                ctx.quantity = item.quantity
        
        return ctx
    
    async def _create_notification_record(
        self,
        actor_type: ActorType,
        actor_id: str,
        receiver_id: str,
        trigger: TriggerType,
        order_id: str,
        message: str,
        metadata: Dict[str, Any],
        idempotency_key: str,
        channel: Optional[Channel] = None,
        send_at: Optional[datetime] = None,
    ) -> Optional[Notification]:
        """Create notification record in database (idempotent)."""
        # Check for existing notification
        result = await self.db.execute(
            select(Notification).where(Notification.idempotency_key == idempotency_key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.debug(f"Notification already exists for key: {idempotency_key[:16]}...")
            return existing
        
        notification = Notification(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            receiver_id=receiver_id,
            actor_type=actor_type,
            actor_id=actor_id,
            order_id=order_id,
            trigger=trigger.value,
            message=message,
            metadata_json=metadata,
            read_status=False,
            idempotency_key=idempotency_key,
            status="QUEUED",
            channel=channel.value if channel else None,
            send_at=send_at,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification
    
    async def _dispatch_to_actor(
        self,
        actor_type: ActorType,
        actor_id: str,
        receiver_id: str,
        ctx: TriggerContext,
        prefs: Optional[NotificationPreferences],
    ) -> Optional[Notification]:
        """Dispatch notification to a specific actor."""
        trigger = ctx.trigger
        priority = TRIGGER_PRIORITY.get(trigger, NotificationPriority.NORMAL)
        category = TRIGGER_CATEGORY.get(trigger, NotificationCategory.ORDERS)
        
        # Resolve channels
        channels = await resolve_channels(prefs, priority, category)
        if not channels:
            return None
        
        # Build message based on actor type
        title, body, metadata = self._build_actor_payload(actor_type, ctx)
        
        # Generate idempotency key
        idempotency_key = generate_idempotency_key(trigger, ctx.order_id, actor_type, actor_id)
        
        # Check DND and calculate send_at
        send_at = None
        if prefs and prefs.dnd_start and prefs.dnd_end:
            # Would need proper timezone-aware DND check
            # For now, just note DND is configured
            metadata["dnd_configured"] = True
        
        # Create notification record
        notification = await self._create_notification_record(
            actor_type=actor_type,
            actor_id=actor_id,
            receiver_id=receiver_id,
            trigger=trigger,
            order_id=ctx.order_id,
            message=f"{title}\n{body}",
            metadata=metadata,
            idempotency_key=idempotency_key,
            channel=channels[0] if channels else None,
            send_at=send_at,
        )
        
        if not notification:
            return None
        
        # Get language from preferences or context
        language = prefs.language if prefs else ctx.additional_data.get("language", "en")
        
        # Dispatch via dispatcher
        request = NotificationRequest(
            recipient_id=receiver_id,
            recipient_phone=ctx.customer_phone if actor_type == ActorType.CUSTOMER else None,
            recipient_email=ctx.customer_email if actor_type == ActorType.CUSTOMER else None,
            title=title,
            body=body,
            data=metadata,
            channels=channels,
            priority=priority,
            notification_type=trigger.value,
            language=language,
            metadata={"notification_id": notification.id},
        )
        
        result = await self.dispatcher.dispatch(request, use_fallback=True)
        
        # Update notification status
        if result.status.value == "success":
            notification.status = "SENT"
            notification.channel = result.channels_succeeded[0].value if result.channels_succeeded else None
        elif result.status.value == "partial":
            notification.status = "SENT"
            notification.channel = result.channels_succeeded[0].value if result.channels_succeeded else None
        else:
            notification.status = "FAILED"
        
        notification.last_emitted_at = datetime.now(timezone.utc)
        notification.delivery_attempts += 1
        
        await self.db.flush()
        return notification
    
    def _build_actor_payload(
        self,
        actor_type: ActorType,
        ctx: TriggerContext,
    ) -> tuple[str, str, Dict[str, Any]]:
        """Build notification payload for specific actor type."""
        if actor_type == ActorType.CUSTOMER:
            return self._build_customer_payload(ctx)
        elif actor_type == ActorType.STORE:
            return self._build_store_payload(ctx)
        elif actor_type == ActorType.FACTORY:
            return self._build_factory_payload(ctx)
        elif actor_type == ActorType.DONOR:
            return self._build_donor_payload(ctx)
        else:
            return self._build_admin_payload(ctx)
    
    def _build_customer_payload(self, ctx: TriggerContext) -> tuple[str, str, Dict[str, Any]]:
        """Build customer-friendly notification payload."""
        trigger_messages = {
            TriggerType.ORDER_PLACED: (
                "Order Placed",
                f"Your order #{ctx.order_number} has been placed successfully.",
            ),
            TriggerType.PAYMENT_CONFIRMED: (
                "Payment Confirmed",
                f"Payment for order #{ctx.order_number} confirmed. We'll start preparing your items.",
            ),
            TriggerType.PRODUCTION_STARTED: (
                "Production Started",
                f"Your order #{ctx.order_number} is now in production.",
            ),
            TriggerType.MIDWAY_REJECTION: (
                "Order Update",
                f"There's an issue with your order #{ctx.order_number}. Reason: {ctx.rejection_reason or 'N/A'}",
            ),
            TriggerType.DISPATCHED: (
                "Order Dispatched",
                f"Your order #{ctx.order_number} is on its way!",
            ),
            TriggerType.READY_FOR_BOPIS: (
                "Ready for Pickup",
                f"Your order #{ctx.order_number} is ready for pickup at {ctx.store_name or 'the store'}.",
            ),
            TriggerType.DELIVERED: (
                "Order Delivered",
                f"Your order #{ctx.order_number} has been delivered. Enjoy!",
            ),
            TriggerType.RETURN_INITIATED: (
                "Return Initiated",
                f"Your return request for order #{ctx.order_number} has been received.",
            ),
            TriggerType.COUPON_REDEEMED: (
                "Coupon Redeemed",
                f"Your coupon has been applied to order #{ctx.order_number}.",
            ),
            TriggerType.DONOR_COUPON_CLAIMED: (
                "Donation Impact",
                f"Your donated item has been claimed! Thank you for your generosity.",
            ),
        }
        
        title, body = trigger_messages.get(ctx.trigger, ("Notification", f"Update on order #{ctx.order_number}"))
        
        metadata = {
            "order_id": ctx.order_id,
            "order_number": ctx.order_number,
            "trigger": ctx.trigger.value,
            "product_name": ctx.product_name,
            "store_name": ctx.store_name,
        }
        
        return title, body, metadata
    
    def _build_store_payload(self, ctx: TriggerContext) -> tuple[str, str, Dict[str, Any]]:
        """Build store notification payload with masked phone and SKU."""
        masked_phone = mask_phone(ctx.customer_phone or "")
        
        trigger_messages = {
            TriggerType.ORDER_PLACED: (
                "New Order",
                f"New order #{ctx.order_number} from customer {ctx.customer_name or 'Unknown'} ({masked_phone}). SKU: {ctx.product_sku}, Qty: {ctx.quantity}.",
            ),
            TriggerType.MIDWAY_REJECTION: (
                "Order Rejected",
                f"Order #{ctx.order_number} rejected midway. Reason: {ctx.rejection_reason or 'N/A'}. Customer: {masked_phone}.",
            ),
            TriggerType.DISPATCHED: (
                "Order Dispatched",
                f"Order #{ctx.order_number} dispatched to customer {masked_phone}.",
            ),
            TriggerType.READY_FOR_BOPIS: (
                "BOPIS Ready",
                f"Order #{ctx.order_number} ready for pickup. Customer: {ctx.customer_name or 'Unknown'} ({masked_phone}). Pickup window: {ctx.pickup_window or 'N/A'}. Location: {ctx.location_tag or 'N/A'}.",
            ),
            TriggerType.RETURN_INITIATED: (
                "Return Request",
                f"Return requested for order #{ctx.order_number}. Customer: {masked_phone}. Reason: {ctx.rejection_reason or 'N/A'}.",
            ),
            TriggerType.COUPON_REDEEMED: (
                "Coupon Used",
                f"Coupon redeemed for order #{ctx.order_number}. Customer: {masked_phone}.",
            ),
            TriggerType.DONOR_COUPON_CLAIMED: (
                "Donor Coupon Claimed",
                f"Donor coupon claimed at your store. Order #{ctx.order_number}.",
            ),
        }
        
        title, body = trigger_messages.get(ctx.trigger, ("Store Notification", f"Update on order #{ctx.order_number}"))
        
        metadata = {
            "order_number": ctx.order_number,  # Never send full order_id to factory
            "customer_name": ctx.customer_name,
            "customer_phone_masked": masked_phone,
            "product_sku": ctx.product_sku,
            "quantity": ctx.quantity,
            "pickup_window": ctx.pickup_window,
            "location_tag": ctx.location_tag,
            "trigger": ctx.trigger.value,
        }
        
        return title, body, metadata
    
    def _build_factory_payload(self, ctx: TriggerContext) -> tuple[str, str, Dict[str, Any]]:
        """Build factory notification payload with SKU and production deadline."""
        trigger_messages = {
            TriggerType.ORDER_PLACED: (
                "New Production Order",
                f"New order #{ctx.order_number}. SKU: {ctx.product_sku}, Qty: {ctx.quantity}.",
            ),
            TriggerType.PAYMENT_CONFIRMED: (
                "Production Approved",
                f"Order #{ctx.order_number} payment confirmed. Start production. SKU: {ctx.product_sku}.",
            ),
            TriggerType.PRODUCTION_STARTED: (
                "Production Started",
                f"Production started for order #{ctx.order_number}. SKU: {ctx.product_sku}.",
            ),
            TriggerType.MIDWAY_REJECTION: (
                "Production Issue",
                f"Order #{ctx.order_number} rejected. SKU: {ctx.product_sku}. Reason: {ctx.rejection_reason or 'N/A'}.",
            ),
            TriggerType.RETURN_INITIATED: (
                "Return Processing",
                f"Return requested for order #{ctx.order_number}. SKU: {ctx.product_sku}. Reason: {ctx.rejection_reason or 'N/A'}.",
            ),
        }
        
        title, body = trigger_messages.get(ctx.trigger, ("Factory Notification", f"Update on order #{ctx.order_number}"))
        
        metadata = {
            "order_number": ctx.order_number,  # Human-readable, not full order_id
            "product_sku": ctx.product_sku,
            "quantity": ctx.quantity,
            "rejection_reason": ctx.rejection_reason,
            "trigger": ctx.trigger.value,
        }
        
        return title, body, metadata
    
    def _build_donor_payload(self, ctx: TriggerContext) -> tuple[str, str, Dict[str, Any]]:
        """Build donor notification payload."""
        title = "Your Donation Made an Impact!"
        body = f"Your donated item has been claimed through a coupon. Thank you for your generosity!"
        
        metadata = {
            "order_number": ctx.order_number,
            "store_name": ctx.store_name,
            "trigger": ctx.trigger.value,
        }
        
        return title, body, metadata
    
    def _build_admin_payload(self, ctx: TriggerContext) -> tuple[str, str, Dict[str, Any]]:
        """Build admin notification payload."""
        title = f"Admin Alert: {ctx.trigger.value.replace('_', ' ').title()}"
        body = f"Order #{ctx.order_number} - {ctx.trigger.value}"
        
        metadata = {
            "order_id": ctx.order_id,
            "order_number": ctx.order_number,
            "trigger": ctx.trigger.value,
            "user_id": ctx.user_id,
        }
        
        return title, body, metadata
    
    async def trigger_notification(
        self,
        ctx: TriggerContext,
    ) -> List[Notification]:
        """
        Trigger notifications for all relevant actors.
        
        Args:
            ctx: Trigger context with order and actor info
            
        Returns:
            List of created notifications
        """
        # Enrich context with DB data
        ctx = await self._enrich_context(ctx)
        
        # Get actors for this trigger
        actors = TRIGGER_ACTORS.get(ctx.trigger, {ActorType.CUSTOMER})
        
        notifications = []
        
        for actor_type in actors:
            # Determine actor_id and receiver_id
            actor_id, receiver_id = await self._resolve_actor_ids(actor_type, ctx)
            if not actor_id or not receiver_id:
                continue
            
            # Get preferences for receiver
            prefs = await get_user_preferences(self.db, receiver_id)
            
            # Dispatch to actor
            notification = await self._dispatch_to_actor(
                actor_type=actor_type,
                actor_id=actor_id,
                receiver_id=receiver_id,
                ctx=ctx,
                prefs=prefs,
            )
            
            if notification:
                notifications.append(notification)
        
        await self.db.commit()
        logger.info(f"Triggered {len(notifications)} notifications for {ctx.trigger.value}")
        return notifications
    
    async def _resolve_actor_ids(
        self,
        actor_type: ActorType,
        ctx: TriggerContext,
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve actor_id and receiver_id for an actor type."""
        if actor_type == ActorType.CUSTOMER:
            return ctx.user_id, ctx.user_id
        elif actor_type == ActorType.STORE:
            # Store notifications go to store owner/manager
            # For now, use store_id as actor_id
            # In production, would look up store owner user_id
            return ctx.store_id, ctx.store_id  # Placeholder - needs store owner lookup
        elif actor_type == ActorType.FACTORY:
            # Factory notifications go to factory manager
            return ctx.factory_id, ctx.factory_id
        elif actor_type == ActorType.DONOR:
            return ctx.donor_id, ctx.donor_id
        elif actor_type == ActorType.ADMIN:
            # Admin notifications could go to admin user(s)
            return "admin", "admin"  # Placeholder
        
        return None, None


# -------------------------------------------------------------------------
# TRIGGER FUNCTIONS (Public API)
# -------------------------------------------------------------------------

async def on_order_placed(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    store_id: Optional[str] = None,
    factory_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Order Placed - notifies customer, store, factory."""
    ctx = TriggerContext(
        trigger=TriggerType.ORDER_PLACED,
        order_id=order_id,
        order_number=order_id,  # Will be enriched
        user_id=user_id,
        store_id=store_id,
        factory_id=factory_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_payment_confirmed(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    factory_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Payment Confirmed - notifies customer, factory."""
    ctx = TriggerContext(
        trigger=TriggerType.PAYMENT_CONFIRMED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        factory_id=factory_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_production_started(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    factory_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Production Started - notifies customer, factory."""
    ctx = TriggerContext(
        trigger=TriggerType.PRODUCTION_STARTED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        factory_id=factory_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_midway_rejection(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    rejection_reason: str,
    store_id: Optional[str] = None,
    factory_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Midway Rejection - notifies customer, store, factory."""
    ctx = TriggerContext(
        trigger=TriggerType.MIDWAY_REJECTION,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        store_id=store_id,
        factory_id=factory_id,
        additional_data={"rejection_reason": rejection_reason},
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_dispatched(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    store_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Dispatched - notifies customer, store."""
    ctx = TriggerContext(
        trigger=TriggerType.DISPATCHED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        store_id=store_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_ready_for_bopis(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    store_id: str,
    pickup_window: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Ready for BOPIS - notifies customer, store."""
    ctx = TriggerContext(
        trigger=TriggerType.READY_FOR_BOPIS,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        store_id=store_id,
        additional_data={"pickup_window": pickup_window},
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_delivered(
    db: AsyncSession,
    order_id: str,
    user_id: str,
) -> List[Notification]:
    """Trigger: Delivered - notifies customer only."""
    ctx = TriggerContext(
        trigger=TriggerType.DELIVERED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_return_initiated(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    reason: str,
    store_id: Optional[str] = None,
    factory_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Return Initiated - notifies customer, store, factory."""
    ctx = TriggerContext(
        trigger=TriggerType.RETURN_INITIATED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        store_id=store_id,
        factory_id=factory_id,
        additional_data={"rejection_reason": reason},
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_coupon_redeemed(
    db: AsyncSession,
    order_id: str,
    user_id: str,
    store_id: Optional[str] = None,
) -> List[Notification]:
    """Trigger: Coupon Redeemed - notifies customer, store."""
    ctx = TriggerContext(
        trigger=TriggerType.COUPON_REDEEMED,
        order_id=order_id,
        order_number=order_id,
        user_id=user_id,
        store_id=store_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


async def on_donor_coupon_claimed(
    db: AsyncSession,
    order_id: str,
    donor_id: str,
    store_id: str,
) -> List[Notification]:
    """Trigger: Donor Coupon Claimed - notifies donor, store."""
    ctx = TriggerContext(
        trigger=TriggerType.DONOR_COUPON_CLAIMED,
        order_id=order_id,
        order_number=order_id,
        user_id=donor_id,  # Donor is the "user" in this context
        donor_id=donor_id,
        store_id=store_id,
    )
    service = NotificationTriggerService(db)
    return await service.trigger_notification(ctx)


# -------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------

__all__ = [
    # Enums
    "TriggerType",
    "NotificationCategory",
    # Data classes
    "TriggerContext",
    "ActorNotification",
    # Service
    "NotificationTriggerService",
    # Trigger functions
    "on_order_placed",
    "on_payment_confirmed",
    "on_production_started",
    "on_midway_rejection",
    "on_dispatched",
    "on_ready_for_bopis",
    "on_delivered",
    "on_return_initiated",
    "on_coupon_redeemed",
    "on_donor_coupon_claimed",
    # Helpers
    "mask_phone",
    "generate_idempotency_key",
    "get_user_preferences",
    "detect_language_from_phone",
    "resolve_channels",
    # Configuration
    "TRIGGER_ACTORS",
    "TRIGGER_PRIORITY",
    "TRIGGER_CATEGORY",
    "PRIORITY_CHANNELS",
]
