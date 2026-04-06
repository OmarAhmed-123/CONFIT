"""
CONFIT Backend - Notification Payload Schemas
=============================================

Pydantic schemas for notification payloads per actor type.
Based on CONFIT spec Section 3.2 and 3.4.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# -------------------------------------------------------------------------
# ENUMS
# -------------------------------------------------------------------------

class ActorTypeEnum(str, Enum):
    """Actor types for notifications."""
    CUSTOMER = "CUSTOMER"
    STORE = "STORE"
    FACTORY = "FACTORY"
    DONOR = "DONOR"
    ADMIN = "ADMIN"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class ChannelEnum(str, Enum):
    """Notification delivery channels."""
    PUSH = "push"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    IN_APP = "in_app"


class TriggerEnum(str, Enum):
    """Notification trigger types."""
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


# -------------------------------------------------------------------------
# BASE SCHEMAS
# -------------------------------------------------------------------------

class NotificationBase(BaseModel):
    """Base notification schema."""
    notification_id: str = Field(..., description="Unique notification ID")
    trigger: TriggerEnum = Field(..., description="Trigger type")
    order_number: str = Field(..., description="Human-readable order number")
    created_at: datetime = Field(..., description="Notification creation timestamp")


class NotificationResponse(NotificationBase):
    """Full notification response for API."""
    actor_type: ActorTypeEnum
    actor_id: str
    receiver_id: str
    order_id: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    read_status: bool = False
    read_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.QUEUED
    channel: Optional[ChannelEnum] = None
    send_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# CUSTOMER NOTIFICATION PAYLOAD
# -------------------------------------------------------------------------

class CustomerNotificationPayload(NotificationBase):
    """
    Customer-friendly notification payload.
    Focuses on customer experience with clear, actionable information.
    """
    # Customer-facing fields
    title: str = Field(..., description="Notification title for customer")
    body: str = Field(..., description="Notification body text")
    
    # Order details (customer-friendly)
    product_name: Optional[str] = Field(None, description="Product name")
    product_image: Optional[str] = Field(None, description="Product image URL")
    quantity: int = Field(1, description="Number of items")
    
    # Store info (for BOPIS)
    store_name: Optional[str] = Field(None, description="Store name for pickup")
    store_address: Optional[str] = Field(None, description="Store address")
    pickup_window: Optional[str] = Field(None, description="Pickup time window")
    
    # Tracking
    tracking_number: Optional[str] = Field(None, description="Tracking number for shipped orders")
    tracking_url: Optional[str] = Field(None, description="Tracking URL")
    
    # Status
    order_status: Optional[str] = Field(None, description="Current order status")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery date/time")
    
    # Action links
    action_url: Optional[str] = Field(None, description="Deep link to order detail")
    action_text: Optional[str] = Field(None, description="Action button text")
    
    # Rejection/Return info
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (if applicable)")
    
    @field_validator('body')
    @classmethod
    def validate_body_length(cls, v: str) -> str:
        """Ensure body is not too long for SMS (70 chars for Arabic)."""
        # For SMS, Arabic is limited to 70 chars per segment
        # This is a soft validation - actual truncation happens in dispatcher
        if len(v) > 500:
            raise ValueError('Body too long for notification')
        return v


class CustomerNotificationList(BaseModel):
    """List of customer notifications."""
    notifications: List[CustomerNotificationPayload]
    total: int
    unread_count: int
    next_cursor: Optional[str] = None


# -------------------------------------------------------------------------
# STORE NOTIFICATION PAYLOAD
# -------------------------------------------------------------------------

class StoreNotificationPayload(NotificationBase):
    """
    Store notification payload with operational information.
    Includes customer name (masked phone!), product SKU, pickup window, location tag.
    """
    # Store operational fields
    title: str = Field(..., description="Notification title for store staff")
    body: str = Field(..., description="Notification body text")
    
    # Customer info (privacy-conscious)
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone_masked: str = Field(
        ...,
        description="Masked customer phone: +20-10***4412",
        pattern=r"^\+[\d]{1,3}-[\d\*]{3,15}\*{3}[\d]{4}$"
    )
    
    # Product details
    product_sku: str = Field(..., description="Product SKU")
    product_name: Optional[str] = Field(None, description="Product name")
    quantity: int = Field(1, description="Quantity ordered")
    
    # Pickup coordination
    pickup_window: Optional[str] = Field(None, description="Scheduled pickup time window")
    pickup_store_id: Optional[str] = Field(None, description="Store ID for pickup")
    location_tag: Optional[str] = Field(None, description="Location tag: 'Cairo, Egypt'")
    
    # Order context
    order_status: str = Field(..., description="Current order status")
    payment_status: Optional[str] = Field(None, description="Payment status")
    
    # Rejection/Return info
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection/return")
    
    # Action
    action_url: Optional[str] = Field(None, description="Deep link to order management")
    
    @field_validator('customer_phone_masked')
    @classmethod
    def validate_masked_phone(cls, v: str) -> str:
        """Ensure phone is properly masked."""
        # Must contain exactly 3 asterisks
        if v.count('*') != 3:
            raise ValueError('Phone must be masked with exactly 3 asterisks')
        return v


class StoreNotificationList(BaseModel):
    """List of store notifications."""
    notifications: List[StoreNotificationPayload]
    total: int
    unread_count: int
    next_cursor: Optional[str] = None


# -------------------------------------------------------------------------
# FACTORY NOTIFICATION PAYLOAD
# -------------------------------------------------------------------------

class FactoryNotificationPayload(NotificationBase):
    """
    Factory notification payload with production information.
    SKU, quantity, production deadline, rejection_reason (if trigger 4 or 8).
    
    Note: Never send full order_id to factory - use order_number (human-readable).
    """
    # Factory operational fields
    title: str = Field(..., description="Notification title for factory staff")
    body: str = Field(..., description="Notification body text")
    
    # Production details
    product_sku: str = Field(..., description="Product SKU to produce")
    product_name: Optional[str] = Field(None, description="Product name")
    quantity: int = Field(1, description="Quantity to produce")
    
    # Production timeline
    production_deadline: Optional[str] = Field(None, description="Production deadline")
    priority: str = Field("normal", description="Production priority: urgent, high, normal, low")
    
    # Rejection info (for triggers 4 and 8)
    rejection_reason: Optional[str] = Field(
        None,
        description="Reason for rejection (midway_rejection or return_initiated)"
    )
    rejection_stage: Optional[str] = Field(
        None,
        description="Stage where rejection occurred"
    )
    
    # Production status
    production_status: Optional[str] = Field(None, description="Current production status")
    
    # Action
    action_url: Optional[str] = Field(None, description="Deep link to production system")


class FactoryNotificationList(BaseModel):
    """List of factory notifications."""
    notifications: List[FactoryNotificationPayload]
    total: int
    unread_count: int
    next_cursor: Optional[str] = None


# -------------------------------------------------------------------------
# DONOR NOTIFICATION PAYLOAD
# -------------------------------------------------------------------------

class DonorNotificationPayload(NotificationBase):
    """
    Donor notification payload for donation impact updates.
    """
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    
    # Donation impact
    item_description: Optional[str] = Field(None, description="Donated item description")
    claim_date: Optional[datetime] = Field(None, description="When item was claimed")
    store_name: Optional[str] = Field(None, description="Store where claimed")
    
    # Impact metrics
    impact_message: Optional[str] = Field(None, description="Impact message for donor")


# -------------------------------------------------------------------------
# PREFERENCE SCHEMAS
# -------------------------------------------------------------------------

class NotificationPreferencesBase(BaseModel):
    """Base notification preferences schema."""
    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = True
    whatsapp_enabled: bool = False
    in_app_enabled: bool = True
    
    categories: Dict[str, bool] = Field(
        default_factory=lambda: {
            "orders": True,
            "styling": True,
            "promotions": True,
            "donor_impact": True,
        },
        description="Category preferences"
    )
    
    language: str = Field("en", pattern="^(en|ar)$", description="Language preference")
    
    dnd_start: Optional[str] = Field(
        None,
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="DND start time (HH:MM)"
    )
    dnd_end: Optional[str] = Field(
        None,
        pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="DND end time (HH:MM)"
    )


class NotificationPreferencesCreate(NotificationPreferencesBase):
    """Schema for creating notification preferences."""
    recipient_id: str
    recipient_type: str = "customer"


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences (partial update)."""
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    
    categories: Optional[Dict[str, bool]] = None
    
    language: Optional[str] = Field(None, pattern="^(en|ar)$")
    
    dnd_start: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    dnd_end: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")


class NotificationPreferencesResponse(NotificationPreferencesBase):
    """Response schema for notification preferences."""
    id: str
    recipient_id: str
    recipient_type: str
    version: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# WEBHOOK SCHEMAS
# -------------------------------------------------------------------------

class SendGridEvent(BaseModel):
    """SendGrid event webhook payload."""
    event: str
    sg_message_id: str
    timestamp: int
    email: str
    event_type: str = Field(..., alias="event")
    
    # Delivery events
    response: Optional[str] = None
    smtp_id: Optional[str] = None
    
    # Engagement events
    url: Optional[str] = None
    user_agent: Optional[str] = None


class TwilioStatusCallback(BaseModel):
    """Twilio status callback for SMS/WhatsApp."""
    message_sid: str
    message_status: str
    to: str
    from_number: str = Field(..., alias="from")
    account_sid: str
    error_code: Optional[int] = None
    error_message: Optional[str] = None


class FirebaseDeliveryReceipt(BaseModel):
    """Firebase delivery receipt (via Pub/Sub or app callback)."""
    message_id: str
    status: str
    token: Optional[str] = None
    error: Optional[str] = None
    timestamp: int


# -------------------------------------------------------------------------
# READ RECEIPT SCHEMAS
# -------------------------------------------------------------------------

class MarkReadRequest(BaseModel):
    """Request to mark notification as read."""
    notification_id: str


class MarkAllReadRequest(BaseModel):
    """Request to mark all notifications as read."""
    actor_type: Optional[ActorTypeEnum] = None
    trigger: Optional[TriggerEnum] = None


class MarkReadResponse(BaseModel):
    """Response for mark read operations."""
    success: bool
    updated_count: int
    updated_at: datetime


# -------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------

__all__ = [
    # Enums
    "ActorTypeEnum",
    "NotificationStatus",
    "ChannelEnum",
    "TriggerEnum",
    # Base
    "NotificationBase",
    "NotificationResponse",
    # Customer
    "CustomerNotificationPayload",
    "CustomerNotificationList",
    # Store
    "StoreNotificationPayload",
    "StoreNotificationList",
    # Factory
    "FactoryNotificationPayload",
    "FactoryNotificationList",
    # Donor
    "DonorNotificationPayload",
    # Preferences
    "NotificationPreferencesBase",
    "NotificationPreferencesCreate",
    "NotificationPreferencesUpdate",
    "NotificationPreferencesResponse",
    # Webhooks
    "SendGridEvent",
    "TwilioStatusCallback",
    "FirebaseDeliveryReceipt",
    # Read receipts
    "MarkReadRequest",
    "MarkAllReadRequest",
    "MarkReadResponse",
]
