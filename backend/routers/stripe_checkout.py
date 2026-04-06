"""
CONFIT Backend — Stripe Checkout Router
=======================================
Creates Stripe Checkout Sessions for external redirect payment flow.
Payment happens on Stripe's hosted page, not embedded in CONFIT.
"""

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import Order as OrderModel
from utils.auth_deps import optional_auth
from services.auth_service import UserProfile
from core.config import settings
from core.slowapi_limiter import limiter, LIMIT_WEBHOOK

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Stripe Checkout"])

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


# ===========================================
# Request/Response Models
# ===========================================

class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe Checkout Session."""
    order_id: str = Field(..., min_length=1)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    """Response with Stripe Checkout Session details."""
    session_id: str
    checkout_url: str
    publishable_key: str


# ===========================================
# Create Checkout Session Endpoint
# ===========================================

@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Create a Stripe Checkout Session.
    
    This creates a hosted payment page on Stripe's domain.
    The user is redirected to Stripe to complete payment.
    After payment, Stripe redirects back to CONFIT.
    
    Flow:
    1. Frontend calls this endpoint with order_id
    2. Backend creates Stripe Checkout Session
    3. Backend returns checkout_url
    4. Frontend redirects user to checkout_url (Stripe's domain)
    5. User completes payment on Stripe
    6. Stripe redirects user to success_url
    7. Stripe sends webhook to backend with payment status
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    
    db: Session = SessionLocal()
    try:
        # Fetch order
        order = db.query(OrderModel).filter(OrderModel.id == request.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify ownership
        if user and getattr(order, "user_id", None) != user.id:
            raise HTTPException(status_code=403, detail="Order ownership mismatch")
        
        # Check order status
        if getattr(order, "payment_status", None) != "pending":
            raise HTTPException(status_code=400, detail="Order is not awaiting payment")
        
        # Build line items from order
        line_items = []
        for item in order.items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item.name,
                        "images": [item.image_url] if item.image_url else [],
                    },
                    "unit_amount": int(round(item.price * 100)),  # Cents
                },
                "quantity": item.quantity,
            })
        
        # Add shipping if applicable
        if order.shipping > 0:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Shipping",
                    },
                    "unit_amount": int(round(order.shipping * 100)),
                },
                "quantity": 1,
            })
        
        # Add tax
        if order.tax > 0:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Tax",
                    },
                    "unit_amount": int(round(order.tax * 100)),
                },
                "quantity": 1,
            })
        
        # Build URLs
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = request.success_url or f"{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.cancel_url or f"{base_url}/checkout/cancel"
        
        # Create Checkout Session
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(order.user_id),
                metadata={
                    "order_id": order.id,
                    "order_number": str(order.order_number or ""),
                },
                payment_intent_data={
                    "metadata": {
                        "order_id": order.id,
                        "order_number": str(order.order_number or ""),
                    },
                    "description": f"CONFIT Order {order.order_number}",
                },
                # Enable Stripe's BNPL options
                payment_method_options={
                    "card": {
                        "request_three_d_secure": "automatic",
                    },
                },
            )
            
            logger.info("Created Stripe Checkout Session %s for order %s", session.id, order.id)
            
            return CheckoutSessionResponse(
                session_id=session.id,
                checkout_url=session.url,
                publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
            )
            
        except stripe.error.StripeError as e:
            logger.exception("Stripe Checkout Session creation failed")
            raise HTTPException(status_code=502, detail=str(e))
            
    finally:
        db.close()


# ===========================================
# Stripe Webhook Handler
# ===========================================

@router.post("/webhooks/stripe")
@limiter.limit(LIMIT_WEBHOOK)
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    This endpoint receives webhook notifications from Stripe when
    payment events occur (successful payment, failed payment, etc.).
    
    Stripe signs webhooks - we verify the signature to ensure
    the request is genuinely from Stripe.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    if not webhook_secret and is_production:
        logger.error("STRIPE_WEBHOOK_SECRET not set in production — rejecting webhook")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify webhook signature
    if webhook_secret:
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                webhook_secret,
            )
        except stripe.error.SignatureVerificationError as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Parse without verification (development only)
        import json
        logger.warning("Stripe webhook received without signature verification (dev mode)")
        event = json.loads(payload)
    
    event_type = event.get("type")
    data = event.get("data", {})
    obj = data.get("object", {})
    
    logger.info("Received Stripe webhook: %s", event_type)
    
    # Handle specific events
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(obj)
    elif event_type == "payment_intent.succeeded":
        await handle_payment_intent_succeeded(obj)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_intent_failed(obj)
    elif event_type == "charge.refunded":
        await handle_charge_refunded(obj)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)
    
    return {"status": "received"}


async def handle_checkout_completed(session: dict):
    """Handle completed checkout session."""
    metadata = session.get("metadata", {})
    order_id = metadata.get("order_id")
    payment_intent_id = session.get("payment_intent")
    
    if not order_id:
        logger.warning("Checkout session missing order_id in metadata")
        return
    
    db = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if order:
            order.payment_status = "success"
            db.commit()
            logger.info("Order %s marked as paid via checkout session", order_id)
    finally:
        db.close()


async def handle_payment_intent_succeeded(payment_intent: dict):
    """Handle successful payment intent."""
    metadata = payment_intent.get("metadata", {})
    order_id = metadata.get("order_id")
    
    if not order_id:
        return
    
    db = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if order and order.payment_status != "success":
            order.payment_status = "success"
            db.commit()
            logger.info("Order %s marked as paid via payment intent", order_id)
    finally:
        db.close()


async def handle_payment_intent_failed(payment_intent: dict):
    """Handle failed payment intent."""
    metadata = payment_intent.get("metadata", {})
    order_id = metadata.get("order_id")
    
    if not order_id:
        return
    
    db = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if order:
            order.payment_status = "failed"
            db.commit()
            logger.info("Order %s marked as failed", order_id)
    finally:
        db.close()


async def handle_charge_refunded(charge: dict):
    """Handle refunded charge."""
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    db = SessionLocal()
    try:
        # Find order by payment intent ID stored in metadata
        # This would require storing the payment_intent_id on the order
        # For now, log the refund
        logger.info("Charge refunded for payment intent: %s", payment_intent_id)
    finally:
        db.close()
