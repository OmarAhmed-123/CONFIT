"""
CONFIT Backend - Notification Webhook Endpoints
================================================

Webhook endpoints for delivery status callbacks from providers.
Handles SendGrid, Twilio, and Firebase delivery receipts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from core.slowapi_limiter import limiter, LIMIT_WEBHOOK
from database.models import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# -------------------------------------------------------------------------
# WEBHOOK SIGNATURE VERIFICATION
# -------------------------------------------------------------------------

def _verify_sendgrid_signature(request: Request, body: bytes) -> bool:
    """Verify SendGrid webhook signature using ECDSA (or HMAC fallback).

    SendGrid signs webhooks with the Event Webhook Signing Key.
    When the signing key is not configured, we fall back to checking
    a shared HMAC secret for basic integrity.
    """
    # Try ECDSA verification first (SendGrid Event Webhook)
    sg_key = os.getenv("SENDGRID_WEBHOOK_SIGNING_KEY")
    if sg_key:
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization, hashes
            from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
            import base64

            public_key = serialization.load_pem_public_key(
                sg_key.encode() if b"-----BEGIN" in sg_key.encode() else
                b"-----BEGIN PUBLIC KEY-----\n" + sg_key.encode() + b"\n-----END PUBLIC KEY-----"
            )
            timestamp = request.headers.get("X-Twilio-Callback-Url", "")
            signature_b64 = request.headers.get("X-Sendgrid-Signature", "")
            if not signature_b64:
                return False
            # Verify ECDSA signature over the raw body
            payload_str = body.decode("utf-8", errors="replace")
            try:
                public_key.verify(
                    base64.b64decode(signature_b64),
                    payload_str.encode("utf-8"),
                    ec.ECDSA(hashes.SHA256()),
                )
                return True
            except Exception:
                return False
        except ImportError:
            pass
        except Exception as e:
            logger.warning("SendGrid ECDSA verification failed: %s", e)

    # Fallback: HMAC-SHA256 verification
    hmac_secret = os.getenv("SENDGRID_WEBHOOK_HMAC_SECRET")
    if hmac_secret:
        expected = hmac.new(hmac_secret.encode(), body, hashlib.sha256).hexdigest()
        received = request.headers.get("X-Sendgrid-Hmac-SHA256", "")
        if not received:
            return False
        return hmac.compare_digest(expected, received)

    # No verification key configured — reject in production
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.error("SendGrid webhook verification key not configured in production!")
        return False
    # Dev: allow unverified
    logger.warning("SendGrid webhook received without signature verification (dev mode)")
    return True


def _verify_twilio_signature(request: Request, body: bytes) -> bool:
    """Verify Twilio webhook signature using HMAC-SHA1."""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not auth_token:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            logger.error("TWILIO_AUTH_TOKEN not configured in production!")
            return False
        logger.warning("Twilio webhook received without signature verification (dev mode)")
        return True

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    # Build the URL that Twilio signed
    url = str(request.url)
    # If behind a proxy, use the original URL
    proto = request.headers.get("X-Forwarded-Proto")
    host = request.headers.get("X-Forwarded-Host")
    if proto and host:
        url = f"{proto}://{host}{request.url.path}"

    # Twilio signs: URL + POST params sorted alphabetically
    import urllib.parse
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        params = urllib.parse.parse_qs(body.decode("utf-8", errors="replace"))
        sorted_params = sorted(params.items())
        concat = url + "".join(f"{k}{v[0]}" for k, v in sorted_params)
    else:
        concat = url + body.decode("utf-8", errors="replace")

    expected = hmac.new(
        auth_token.encode(),
        concat.encode(),
        hashlib.sha1,
    ).digest()
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(expected_b64, signature)


def _verify_firebase_token(request: Request) -> bool:
    """Verify Firebase webhook via Bearer token or shared secret."""
    fb_secret = os.getenv("FIREBASE_WEBHOOK_SECRET")
    if not fb_secret:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            logger.error("FIREBASE_WEBHOOK_SECRET not configured in production!")
            return False
        logger.warning("Firebase webhook received without verification (dev mode)")
        return True

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return hmac.compare_digest(token, fb_secret)

    # Also check custom header
    custom_token = request.headers.get("X-Firebase-Token", "")
    if custom_token:
        return hmac.compare_digest(custom_token, fb_secret)

    return False


# -------------------------------------------------------------------------
# WEBHOOK PAYLOAD SCHEMAS
# -------------------------------------------------------------------------

class SendGridEventPayload(BaseModel):
    """SendGrid event webhook payload."""
    event: str
    sg_message_id: str
    timestamp: int
    email: str
    smtp_id: Optional[str] = None
    response: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    type: Optional[str] = None  # For typed events
    
    # Additional fields
    message_id: Optional[str] = None
    notification_id: Optional[str] = None


class TwilioStatusPayload(BaseModel):
    """Twilio status callback payload."""
    MessageSid: str
    MessageStatus: str
    To: str
    From: str
    AccountSid: str
    ErrorCode: Optional[str] = None
    ErrorMessage: Optional[str] = None
    
    # Custom fields we add
    notification_id: Optional[str] = None


class FirebaseDeliveryPayload(BaseModel):
    """Firebase delivery receipt payload."""
    message_id: str
    status: str
    token: Optional[str] = None
    error: Optional[str] = None
    timestamp: int
    notification_id: Optional[str] = None


# -------------------------------------------------------------------------
# STATUS MAPPING
# -------------------------------------------------------------------------

SENDGRID_STATUS_MAP = {
    "delivered": "DELIVERED",
    "processed": "SENT",
    "bounce": "FAILED",
    "dropped": "FAILED",
    "deferred": "QUEUED",
    "open": "DELIVERED",
    "click": "DELIVERED",
}

TWILIO_STATUS_MAP = {
    "delivered": "DELIVERED",
    "sent": "SENT",
    "queued": "QUEUED",
    "failed": "FAILED",
    "undelivered": "FAILED",
    "accepted": "QUEUED",
    "scheduled": "QUEUED",
    "read": "READ",  # WhatsApp read receipts
}

FIREBASE_STATUS_MAP = {
    "SUCCESS": "DELIVERED",
    "FAILURE": "FAILED",
    "TIMEOUT": "FAILED",
    "INVALID_TOKEN": "FAILED",
}


# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------

async def update_notification_status(
    db: AsyncSession,
    notification_id: str,
    status: str,
    provider_message_id: Optional[str] = None,
    error: Optional[str] = None,
) -> Optional[Notification]:
    """Update notification status in database."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        logger.warning(f"Notification not found: {notification_id}")
        return None
    
    notification.status = status
    
    if status == "DELIVERED":
        notification.delivery_status = "delivered"
        notification.ack_received_at = datetime.now(timezone.utc)
    elif status == "FAILED":
        notification.delivery_status = "failed"
    elif status == "READ":
        notification.read_status = True
        notification.read_at = datetime.now(timezone.utc)
    
    if provider_message_id:
        notification.provider_message_id = provider_message_id
    
    notification.last_emitted_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(notification)
    
    logger.info(f"Updated notification {notification_id} status to {status}")
    return notification


def extract_notification_id(message_id: str) -> Optional[str]:
    """Extract notification ID from provider message ID."""
    # Message IDs may contain notification ID as part of the ID
    # Format: "notif-{uuid}" or embedded in provider ID
    if message_id.startswith("notif-"):
        return message_id
    return None


# -------------------------------------------------------------------------
# SENDGRID WEBHOOK
# -------------------------------------------------------------------------

@router.post(
    "/sendgrid",
    summary="SendGrid event webhook",
    description="Handle SendGrid delivery and engagement events.",
)
@limiter.limit(LIMIT_WEBHOOK)
async def handle_sendgrid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Handle SendGrid event webhook.
    
    Events: delivered, processed, bounce, dropped, deferred, open, click
    """
    try:
        body = await request.body()

        # Verify SendGrid webhook signature
        if not _verify_sendgrid_signature(request, body):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid SendGrid webhook signature",
            )

        events = json.loads(body)
        
        if not isinstance(events, list):
            events = [events]
        
        processed = 0
        for event in events:
            event_type = event.get("event", "unknown")
            sg_message_id = event.get("sg_message_id", "")
            
            # Get notification ID from metadata or parse from message ID
            notification_id = event.get("notification_id") or extract_notification_id(sg_message_id)
            
            if notification_id:
                status = SENDGRID_STATUS_MAP.get(event_type, "SENT")
                
                # Schedule background update
                background_tasks.add_task(
                    update_notification_status,
                    db,
                    notification_id,
                    status,
                    sg_message_id,
                    event.get("response") or event.get("reason"),
                )
                processed += 1
            
            logger.debug(f"SendGrid event: {event_type} for message {sg_message_id}")
        
        return {"status": "success", "processed": processed}
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid SendGrid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    except Exception as e:
        logger.error(f"SendGrid webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# -------------------------------------------------------------------------
# TWILIO WEBHOOK
# -------------------------------------------------------------------------

@router.post(
    "/twilio",
    summary="Twilio status callback",
    description="Handle Twilio SMS and WhatsApp delivery status callbacks.",
)
@limiter.limit(LIMIT_WEBHOOK)
async def handle_twilio_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Handle Twilio status callback.
    
    Status values: queued, accepted, scheduled, sent, delivered, 
                   undelivered, failed, read (WhatsApp)
    """
    try:
        # Verify Twilio webhook signature
        raw_body = await request.body()
        if not _verify_twilio_signature(request, raw_body):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Twilio webhook signature",
            )

        form_data = await request.form()
        
        message_sid = form_data.get("MessageSid", "")
        message_status = form_data.get("MessageStatus", "")
        to_phone = form_data.get("To", "")
        from_phone = form_data.get("From", "")
        error_code = form_data.get("ErrorCode")
        error_message = form_data.get("ErrorMessage")
        
        # Get notification ID from custom parameter
        notification_id = form_data.get("notification_id") or extract_notification_id(message_sid)
        
        if notification_id:
            status = TWILIO_STATUS_MAP.get(message_status, "SENT")
            
            error = None
            if error_code:
                error = f"{error_code}: {error_message}"
            
            background_tasks.add_task(
                update_notification_status,
                db,
                notification_id,
                status,
                message_sid,
                error,
            )
        
        logger.debug(
            f"Twilio status: {message_status} for message {message_sid} to {to_phone}"
        )
        
        return {"status": "success", "message_sid": message_sid}
    
    except Exception as e:
        logger.error(f"Twilio webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# -------------------------------------------------------------------------
# FIREBASE WEBHOOK
# -------------------------------------------------------------------------

@router.post(
    "/firebase",
    summary="Firebase delivery receipt",
    description="Handle Firebase FCM delivery receipts.",
)
@limiter.limit(LIMIT_WEBHOOK)
async def handle_firebase_webhook(
    request: Request,
    payload: FirebaseDeliveryPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Handle Firebase FCM delivery receipt.
    
    Status values: SUCCESS, FAILURE, TIMEOUT, INVALID_TOKEN
    """
    # Verify Firebase webhook token
    if not _verify_firebase_token(request):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Firebase webhook token",
        )

    try:
        notification_id = payload.notification_id or extract_notification_id(payload.message_id)
        
        if notification_id:
            status = FIREBASE_STATUS_MAP.get(payload.status, "SENT")
            
            error = payload.error
            if status == "FAILED" and not error:
                error = f"Firebase delivery failed with status: {payload.status}"
            
            background_tasks.add_task(
                update_notification_status,
                db,
                notification_id,
                status,
                payload.message_id,
                error,
            )
        
        logger.debug(
            f"Firebase status: {payload.status} for message {payload.message_id}"
        )
        
        return {"status": "success", "message_id": payload.message_id}
    
    except Exception as e:
        logger.error(f"Firebase webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# -------------------------------------------------------------------------
# GENERIC WEBHOOK (for testing)
# -------------------------------------------------------------------------

@router.post(
    "/delivery",
    summary="Generic delivery receipt",
    description="Generic delivery receipt endpoint for testing.",
)
async def handle_generic_delivery(
    notification_id: str,
    status: str,
    provider_message_id: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Handle generic delivery receipt (for testing)."""
    if status not in ["QUEUED", "SENT", "DELIVERED", "READ", "FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be QUEUED, SENT, DELIVERED, READ, or FAILED",
        )
    
    notification = await update_notification_status(
        db,
        notification_id,
        status,
        provider_message_id,
        error,
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification not found: {notification_id}",
        )
    
    return {
        "status": "success",
        "notification_id": notification_id,
        "new_status": status,
    }


# -------------------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Webhook health check",
    description="Check webhook endpoint health.",
)
async def webhook_health() -> Dict[str, Any]:
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "endpoints": {
            "sendgrid": "/webhooks/sendgrid",
            "twilio": "/webhooks/twilio",
            "firebase": "/webhooks/firebase",
            "delivery": "/webhooks/delivery",
        },
    }


# -------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------

__all__ = [
    "router",
    "handle_sendgrid_webhook",
    "handle_twilio_webhook",
    "handle_firebase_webhook",
    "update_notification_status",
]
