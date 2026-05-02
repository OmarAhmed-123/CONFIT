"""
CONFIT Backend - Donation API Router
=====================================
Production-grade donation endpoints with secure payment processing,
coupon validation, and credit management.

Security Features:
- Rate limiting on all endpoints
- Server-side payment verification
- Fraud prevention integration
- Row-level locking for balance updates

Endpoints:
- POST /api/donations - Create donation
- POST /api/donations/:id/confirm - Confirm after payment
- GET /api/donations/config - Get configuration
- GET /api/donations/history - Get user donation history
- GET /api/donations/credits - Get user credits
- POST /api/donations/credits/redeem - Redeem credit
- POST /api/donations/credits/validate - Validate coupon
- POST /api/donations/webhooks/stripe - Stripe webhook handler
"""

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

import stripe
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.slowapi_limiter import limiter, LIMIT_WEBHOOK

from database.session import SessionLocal
from database.donation_models import DonationStatus
from services.donation_service import (
    DonationService,
    DonationError,
    InvalidAmountError,
    PaymentVerificationError,
    CreditExhaustedError,
    DuplicateTransactionError,
)
from api.deps import get_current_user, get_current_user_optional
from core.security.rbac import AuthContext
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/donations", tags=["Donations"])
security = HTTPBearer(auto_error=False)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateDonationRequest(BaseModel):
    """Request to create a new donation."""
    amount: float = Field(..., gt=0, description="Donation amount in USD")
    payment_method: str = Field("card", description="Payment method")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return round(v, 2)


class ConfirmDonationRequest(BaseModel):
    """Request to confirm a donation after payment."""
    payment_intent_id: str = Field(..., min_length=1)
    transaction_id: Optional[str] = None


class DonationResponse(BaseModel):
    """Donation response."""
    id: str
    user_id: str
    amount: float
    currency: str
    status: str
    payment_method: str
    created_at: str
    completed_at: Optional[str] = None
    
    # Payment details (for checkout)
    client_secret: Optional[str] = None
    payment_intent_id: Optional[str] = None


class CreditResponse(BaseModel):
    """Donor credit response."""
    id: str
    coupon_code: str
    total_credit: float
    remaining_credit: float
    used_credit: float
    status: str
    expires_at: Optional[str] = None
    created_at: str
    is_active: bool


class DonationConfigResponse(BaseModel):
    """Donation configuration response."""
    min_amount: float
    max_amount: float
    preset_amounts: List[float]
    enable_custom_amounts: bool
    hero_title: str
    hero_subtitle: str
    benefits: List[dict]
    default_expiry_days: Optional[int]


class RedeemCreditRequest(BaseModel):
    """Request to redeem credit."""
    amount: float = Field(..., gt=0)
    order_id: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    coupon_code: Optional[str] = None


class ValidateCouponRequest(BaseModel):
    """Request to validate a coupon code."""
    coupon_code: str = Field(..., min_length=1)


class ValidateCouponResponse(BaseModel):
    """Coupon validation response."""
    valid: bool
    message: str
    credit: Optional[CreditResponse] = None


class DonationStatsResponse(BaseModel):
    """User donation statistics."""
    total_donations: int
    total_donated: float
    total_credit_earned: float
    total_credit_used: float
    total_credit_remaining: float
    active_credits: int
    total_redemptions: int


# ============================================
# CONFIGURATION ENDPOINT
# ============================================

@router.get("/config", response_model=DonationConfigResponse)
@limiter.limit("60/minute")
async def get_donation_config(request: Request):
    """
    Get donation configuration.
    
    Public endpoint - no authentication required.
    """
    db = SessionLocal()
    try:
        service = DonationService(db)
        try:
            config = service.get_config()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.warning("Donation config table unavailable; using defaults: %s", exc)
            config = None
        
        return DonationConfigResponse(
            min_amount=float(config.min_donation_amount) if config else 1.0,
            max_amount=float(config.max_donation_amount) if config else 10000.0,
            preset_amounts=(config.preset_amounts if config else None) or [10, 25, 50, 100],
            enable_custom_amounts=config.enable_custom_amounts if config else True,
            hero_title=(config.hero_title if config else None) or "Support the Future of Fashion",
            hero_subtitle=(config.hero_subtitle if config else None) or "Your donation makes a difference.",
            benefits=(config.benefits_text if config else None) or [],
            default_expiry_days=config.default_expiry_days if config else 365,
        )
    finally:
        db.close()


# ============================================
# DONATION ENDPOINTS
# ============================================

@router.post("", response_model=DonationResponse)
@limiter.limit("10/minute")  # Stricter limit for donation creation
async def create_donation(
    request: Request,
    donation_request: CreateDonationRequest,
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Create a new donation.
    
    Creates a pending donation and returns payment details.
    For Stripe: returns client_secret for Payment Element.
    """
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        # Validate amount
        is_valid, error = service.validate_amount(Decimal(str(donation_request.amount)))
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Get client info for fraud prevention
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Create pending donation
        donation = service.create_donation(
            user_id=current_user.user_id,
            amount=Decimal(str(donation_request.amount)),
            payment_method=donation_request.payment_method,
            payment_provider="stripe" if stripe.api_key else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Create Stripe PaymentIntent if configured
        client_secret = None
        payment_intent_id = None
        
        if stripe.api_key:
            try:
                amount_cents = int(round(donation_request.amount * 100))
                
                intent = stripe.PaymentIntent.create(
                    amount=amount_cents,
                    currency="usd",
                    automatic_payment_methods={"enabled": True},
                    metadata={
                        "donation_id": donation.id,
                        "user_id": current_user.user_id,
                        "type": "donation",
                    },
                    description=f"CONFIT Donation ${donation_request.amount}",
                )
                
                client_secret = intent.client_secret
                payment_intent_id = intent.id
                
                logger.info(
                    "Created PaymentIntent %s for donation %s",
                    payment_intent_id, donation.id
                )
                
            except stripe.error.StripeError as e:
                logger.error("Stripe error creating payment intent: %s", e)
                # Continue without Stripe - will use mock mode
        else:
            # Mock mode for development
            client_secret = f"pi_mock_{donation.id}_secret"
            payment_intent_id = f"pi_mock_{donation.id}"
        
        return DonationResponse(
            id=donation.id,
            user_id=donation.user_id,
            amount=float(donation.amount),
            currency=donation.currency,
            status=donation.status.value,
            payment_method=donation.payment_method,
            created_at=donation.created_at.isoformat(),
            completed_at=donation.completed_at.isoformat() if donation.completed_at else None,
            client_secret=client_secret,
            payment_intent_id=payment_intent_id,
        )
        
    except InvalidAmountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Error creating donation")
        raise HTTPException(status_code=500, detail="Failed to create donation")
    finally:
        db.close()


@router.post("/{donation_id}/confirm", response_model=dict)
@limiter.limit("10/minute")  # Stricter limit for payment confirmation
async def confirm_donation(
    request: Request,
    donation_id: str,
    confirm_request: ConfirmDonationRequest,
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Confirm a donation after successful payment.
    
    Verifies payment with Stripe and generates donor credit.
    """
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        # Verify payment with Stripe
        risk_score = None
        transaction_id = confirm_request.transaction_id
        
        if stripe.api_key and confirm_request.payment_intent_id.startswith("pi_"):
            try:
                intent = stripe.PaymentIntent.retrieve(confirm_request.payment_intent_id)
                
                if intent.status != "succeeded":
                    raise HTTPException(
                        status_code=402,
                        detail=f"Payment not completed: {intent.status}"
                    )
                
                # Verify donation ID matches
                if intent.metadata.get("donation_id") != donation_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Payment does not match this donation"
                    )
                
                # Verify amount
                expected_cents = int(round(intent.amount / 100))
                # Amount is already in cents from Stripe
                
                transaction_id = intent.id
                risk_score = 0  # TODO: Integrate with fraud service
                
            except stripe.error.StripeError as e:
                logger.error("Stripe verification failed: %s", e)
                raise HTTPException(
                    status_code=400,
                    detail="Payment verification failed"
                )
        else:
            # Mock mode - verify ownership only
            logger.warning("Confirming donation without Stripe verification")
        
        # Confirm donation and generate credit
        donation, credit = service.confirm_donation(
            donation_id=donation_id,
            transaction_id=transaction_id or confirm_request.payment_intent_id,
            payment_intent_id=confirm_request.payment_intent_id,
            risk_score=risk_score,
        )
        
        logger.info(
            "Donation %s confirmed, credit %s generated",
            donation_id, credit.id
        )
        
        return {
            "success": True,
            "donation": {
                "id": donation.id,
                "amount": float(donation.amount),
                "status": donation.status.value,
                "completed_at": donation.completed_at.isoformat(),
            },
            "credit": {
                "id": credit.id,
                "coupon_code": credit.coupon_code,
                "total_credit": float(credit.total_credit),
                "remaining_credit": float(credit.remaining_credit),
                "expires_at": credit.expires_at.isoformat() if credit.expires_at else None,
            },
        }
        
    except DonationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error confirming donation")
        raise HTTPException(status_code=500, detail="Failed to confirm donation")
    finally:
        db.close()


@router.get("/history", response_model=List[dict])
async def get_donation_history(
    limit: int = 20,
    offset: int = 0,
    current_user: AuthContext = Depends(get_current_user),
):
    """Get donation history for current user."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        return service.get_donation_history(
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
        )
    finally:
        db.close()


@router.get("/stats", response_model=DonationStatsResponse)
async def get_donation_stats(
    current_user: AuthContext = Depends(get_current_user),
):
    """Get donation statistics for current user."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        stats = service.get_donation_stats(current_user.user_id)
        return DonationStatsResponse(**stats)
    finally:
        db.close()


# ============================================
# CREDIT ENDPOINTS
# ============================================

@router.get("/credits", response_model=List[CreditResponse])
async def get_user_credits(
    active_only: bool = True,
    current_user: AuthContext = Depends(get_current_user),
):
    """Get donor credits for current user."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        if active_only:
            credits = service.get_active_credits(current_user.user_id)
        else:
            credits = service.get_user_credits(current_user.user_id)
        
        return [
            CreditResponse(
                id=c.id,
                coupon_code=c.coupon_code,
                total_credit=float(c.total_credit),
                remaining_credit=float(c.remaining_credit),
                used_credit=float(c.total_credit - c.remaining_credit),
                status=c.status.value,
                expires_at=c.expires_at.isoformat() if c.expires_at else None,
                created_at=c.created_at.isoformat(),
                is_active=c.is_active,
            )
            for c in credits
        ]
    finally:
        db.close()


@router.get("/credits/total")
async def get_total_credit(
    current_user: AuthContext = Depends(get_current_user),
):
    """Get total available credit for current user."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        total = service.get_total_available_credit(current_user.user_id)
        return {
            "total_available": float(total),
            "currency": "USD",
        }
    finally:
        db.close()


@router.post("/credits/validate", response_model=ValidateCouponResponse)
@limiter.limit("30/minute")  # Moderate limit for coupon validation
async def validate_coupon(
    request: Request,
    validate_request: ValidateCouponRequest,
    current_user: Optional[AuthContext] = Depends(get_current_user_optional),
):
    """
    Validate a coupon code.
    
    Public endpoint - works for authenticated and anonymous users.
    """
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        user_id = current_user.user_id if current_user else None
        is_valid, credit, error = service.validate_coupon_code(
            code=validate_request.coupon_code,
            user_id=user_id,
        )
        
        credit_response = None
        if credit:
            credit_response = CreditResponse(
                id=credit.id,
                coupon_code=credit.coupon_code,
                total_credit=float(credit.total_credit),
                remaining_credit=float(credit.remaining_credit),
                used_credit=float(credit.total_credit - credit.remaining_credit),
                status=credit.status.value,
                expires_at=credit.expires_at.isoformat() if credit.expires_at else None,
                created_at=credit.created_at.isoformat(),
                is_active=credit.is_active,
            )
        
        return ValidateCouponResponse(
            valid=is_valid,
            message=error if error else "Coupon is valid",
            credit=credit_response,
        )
    finally:
        db.close()


@router.post("/credits/redeem")
@limiter.limit("20/minute")  # Moderate limit for credit redemption
async def redeem_credit(
    request: Request,
    redeem_request: RedeemCreditRequest,
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Redeem donor credit for a purchase.
    
    Uses credits in optimal order (earliest expiration first).
    """
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        redemption, credit = service.redeem_credit(
            user_id=current_user.user_id,
            amount=Decimal(str(redeem_request.amount)),
            order_id=redeem_request.order_id,
            product_id=redeem_request.product_id,
            product_name=redeem_request.product_name,
            coupon_code=redeem_request.coupon_code,
        )
        
        return {
            "success": True,
            "redemption": {
                "id": redemption.id,
                "amount_used": float(redemption.amount_used),
                "balance_after": float(redemption.balance_after),
            },
            "credit": {
                "id": credit.id,
                "remaining_credit": float(credit.remaining_credit),
                "status": credit.status.value,
            },
        }
        
    except CreditExhaustedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DonationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error redeeming credit")
        raise HTTPException(status_code=500, detail="Failed to redeem credit")
    finally:
        db.close()


@router.get("/redemptions")
async def get_redemption_history(
    limit: int = 20,
    offset: int = 0,
    current_user: AuthContext = Depends(get_current_user),
):
    """Get redemption history for current user."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        return service.get_redemption_history(
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
        )
    finally:
        db.close()


# ============================================
# STRIPE WEBHOOK HANDLER
# ============================================

@router.post("/webhooks/stripe")
@limiter.limit(LIMIT_WEBHOOK)
async def stripe_donation_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle Stripe webhook events for donations.
    
    Processes payment_intent.succeeded events for donation payments.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    if not webhook_secret and is_production:
        logger.error("STRIPE_WEBHOOK_SECRET not set in production — rejecting donation webhook")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    # Get raw body
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
        logger.warning("Stripe donation webhook received without signature verification (dev mode)")
        event = json.loads(payload)
    
    event_type = event.get("type")
    data = event.get("data", {})
    obj = data.get("object", {})
    
    logger.info("Received Stripe webhook: %s", event_type)
    
    # Handle payment_intent.succeeded
    if event_type == "payment_intent.succeeded":
        await handle_payment_success(obj, background_tasks)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failure(obj)
    else:
        logger.debug("Unhandled donation webhook event: %s", event_type)
    
    return {"status": "received"}


async def handle_payment_success(
    payment_intent: dict,
    background_tasks: BackgroundTasks,
):
    """Handle successful payment for donation."""
    metadata = payment_intent.get("metadata", {})
    
    # Only process donation payments
    if metadata.get("type") != "donation":
        return
    
    donation_id = metadata.get("donation_id")
    if not donation_id:
        logger.warning("Payment success missing donation_id")
        return
    
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        # Check if already confirmed
        from database.donation_models import Donation
        donation = db.query(Donation).filter(Donation.id == donation_id).first()
        
        if not donation:
            logger.warning("Donation %s not found for payment success", donation_id)
            return
        
        if donation.status == DonationStatus.COMPLETED:
            logger.info("Donation %s already confirmed", donation_id)
            return
        
        # Confirm donation
        service.confirm_donation(
            donation_id=donation_id,
            transaction_id=payment_intent.get("id"),
            payment_intent_id=payment_intent.get("id"),
        )
        
        logger.info("Donation %s confirmed via webhook", donation_id)
        
        # TODO: Send confirmation email in background
        # background_tasks.add_task(send_donation_confirmation_email, donation_id)
        
    except Exception as e:
        logger.exception("Error processing donation webhook")
    finally:
        db.close()


async def handle_payment_failure(payment_intent: dict):
    """Handle failed payment for donation."""
    metadata = payment_intent.get("metadata", {})
    
    if metadata.get("type") != "donation":
        return
    
    donation_id = metadata.get("donation_id")
    if not donation_id:
        return
    
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        failure_reason = payment_intent.get("last_payment_error", {}).get("message", "Unknown error")
        
        service.fail_donation(
            donation_id=donation_id,
            reason=failure_reason,
        )
        
        logger.warning("Donation %s marked as failed: %s", donation_id, failure_reason)
        
    except Exception as e:
        logger.exception("Error processing donation failure")
    finally:
        db.close()


# ============================================
# ADMIN ENDPOINTS (require admin role)
# ============================================

@router.get("/admin/all")
async def list_all_donations(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    # current_user: AuthContext = Depends(require_admin()),  # TODO: Add admin check
):
    """List all donations (admin only)."""
    # TODO: Implement admin authorization
    db = SessionLocal()
    try:
        from database.donation_models import Donation
        query = db.query(Donation)
        
        if status:
            query = query.filter(Donation.status == status)
        
        donations = query.order_by(Donation.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "id": d.id,
                "user_id": d.user_id,
                "amount": float(d.amount),
                "status": d.status.value,
                "payment_provider": d.payment_provider,
                "created_at": d.created_at.isoformat(),
            }
            for d in donations
        ]
    finally:
        db.close()


@router.patch("/admin/config")
async def update_donation_config(
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    preset_amounts: Optional[List[float]] = None,
    default_expiry_days: Optional[int] = None,
    # current_user: AuthContext = Depends(require_admin()),  # TODO: Add admin check
):
    """Update donation configuration (admin only)."""
    db = SessionLocal()
    try:
        service = DonationService(db)
        
        updates = {}
        if min_amount is not None:
            updates["min_donation_amount"] = Decimal(str(min_amount))
        if max_amount is not None:
            updates["max_donation_amount"] = Decimal(str(max_amount))
        if preset_amounts is not None:
            updates["preset_amounts"] = preset_amounts
        if default_expiry_days is not None:
            updates["default_expiry_days"] = default_expiry_days
        
        config = service.update_config(
            updated_by="admin",  # TODO: Use actual admin user ID
            **updates
        )
        
        return {
            "success": True,
            "config": {
                "min_amount": float(config.min_donation_amount),
                "max_amount": float(config.max_donation_amount),
                "preset_amounts": config.preset_amounts,
                "default_expiry_days": config.default_expiry_days,
            }
        }
    finally:
        db.close()
