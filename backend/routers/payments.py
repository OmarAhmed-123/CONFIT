"""
CONFIT Backend — Payments & BNPL Router
========================================
BNPL preview, Stripe PaymentIntents (cards + wallets + Klarna via Payment Element),
and pickup confirmation after verified payment.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import (
    Order as OrderModel,
    PickupRecord as PickupRecordModel,
    Store as StoreModel,
    UserRole,
    AppRole,
)
from core.config import settings
from models.production_models import BrandManager as BrandManagerModel
from utils.auth_deps import optional_auth
from services.auth_service import UserProfile
from services.notificationService.service import NotificationService, PickupSelectedData

router = APIRouter(prefix="/api/payments", tags=["Payments"])

logger = logging.getLogger(__name__)


class BNPLPlanRequest(BaseModel):
    total_amount: float = Field(..., ge=0, description="Order total after discounts.")
    installments: int = Field(
        4,
        ge=2,
        le=12,
        description="Number of installments for the BNPL plan.",
    )
    annual_interest_rate: float = Field(
        0.0,
        ge=0.0,
        le=40.0,
        description="Annual percentage rate. Zero for interest-free plans.",
    )
    currency: str = Field("USD", max_length=10)


class BNPLInstallment(BaseModel):
    number: int
    due_date: datetime
    principal: float
    interest: float
    total: float
    remaining_balance: float


class BNPLPlanResponse(BaseModel):
    currency: str
    total_amount: float
    total_interest: float
    effective_apr: float
    installments: List[BNPLInstallment]


class PaymentConfirmRequest(BaseModel):
    """Accepts snake_case or camelCase from web and mobile clients."""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(
        ...,
        min_length=1,
        description="Existing order id",
        validation_alias=AliasChoices("order_id", "orderId"),
    )
    payment_success: bool = Field(False, description="Set true when payment provider confirms success (dev/mock only)")
    payment_intent_id: Optional[str] = Field(
        None,
        description="Stripe PaymentIntent id after client-side confirmation (required when STRIPE_SECRET_KEY is set for pickup)",
        validation_alias=AliasChoices("payment_intent_id", "paymentIntentId"),
    )


class PaymentIntentRequest(BaseModel):
    order_id: str = Field(..., min_length=1, validation_alias=AliasChoices("order_id", "orderId"))


@router.post("/bnpl/plan", response_model=BNPLPlanResponse)
async def calculate_bnpl_plan(payload: BNPLPlanRequest) -> BNPLPlanResponse:
    """
    Calculate a BNPL installment schedule for the given amount.

    This implementation uses a simple amortization formula and is intended
    for front-end preview; providers such as Klarna or Afterpay would supply
    authoritative plans in production.
    """
    principal = payload.total_amount
    n = payload.installments
    r_annual = payload.annual_interest_rate / 100.0
    currency = payload.currency

    if principal == 0 or n == 0:
        return BNPLPlanResponse(
            currency=currency,
            total_amount=0.0,
            total_interest=0.0,
            effective_apr=0.0,
            installments=[],
        )

    # Convert annual rate to per-period rate (monthly-style for simplicity)
    period_rate = r_annual / 12.0

    if period_rate == 0:
        base_payment = round(principal / n, 2)
        remaining = principal
        installments: List[BNPLInstallment] = []
        for i in range(1, n + 1):
            interest = 0.0
            total = base_payment
            remaining = round(remaining - base_payment, 2)
            if remaining < 0:
                total += remaining
                remaining = 0.0
            installments.append(
                BNPLInstallment(
                    number=i,
                    due_date=datetime.now(timezone.utc) + timedelta(days=30 * i),
                    principal=round(total, 2),
                    interest=interest,
                    total=round(total, 2),
                    remaining_balance=max(remaining, 0.0),
                )
            )
        return BNPLPlanResponse(
            currency=currency,
            total_amount=round(principal, 2),
            total_interest=0.0,
            effective_apr=0.0,
            installments=installments,
        )

    # Standard amortization payment calculation
    r = period_rate
    payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    payment = round(payment, 2)

    remaining = principal
    schedule: List[BNPLInstallment] = []
    total_interest_paid = 0.0

    for i in range(1, n + 1):
        interest = round(remaining * r, 2)
        principal_component = round(payment - interest, 2)
        remaining = round(remaining - principal_component, 2)
        total_interest_paid += interest

        # Ensure final payment clears the remaining balance
        if i == n and remaining != 0:
            principal_component += remaining
            payment = principal_component + interest
            remaining = 0.0

        schedule.append(
            BNPLInstallment(
                number=i,
                due_date=datetime.now(timezone.utc) + timedelta(days=30 * i),
                principal=principal_component,
                interest=interest,
                total=round(payment, 2),
                remaining_balance=max(remaining, 0.0),
            )
        )

    effective_apr = payload.annual_interest_rate

    return BNPLPlanResponse(
        currency=currency,
        total_amount=round(principal, 2),
        total_interest=round(total_interest_paid, 2),
        effective_apr=round(effective_apr, 2),
        installments=schedule,
    )


@router.get("/config")
async def payment_public_config():
    """Publishable key + feature flags for storefront (no secrets)."""
    pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    sk = os.getenv("STRIPE_SECRET_KEY", "").strip()
    stripe_enabled = bool(pk and sk)

    paymob_key = os.getenv("PAYMOB_API_KEY", "").strip()
    paymob_iid = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
    paymob_enabled = bool(paymob_key and paymob_iid)
    paymob_iframe_id = os.getenv("PAYMOB_IFRAME_ID", "").strip()
    paymob_iframe_ready = paymob_enabled and bool(paymob_iframe_id)

    # Build Paymob iframe URL if configured
    paymob_iframe_url = None
    if paymob_iframe_ready:
        paymob_iframe_url = f"https://accept.paymob.com/api/acceptance/iframes/{paymob_iframe_id}?payment_token={{payment_key}}"

    # Get integration IDs for different payment methods
    paymob_integration_ids = {
        "card": os.getenv("PAYMOB_INTEGRATION_ID_CARD", paymob_iid) or None,
        "card_3ds": os.getenv("PAYMOB_INTEGRATION_ID_CARD_3DS", paymob_iid) or None,
        "meeza": os.getenv("PAYMOB_INTEGRATION_ID_MEEZA", "").strip() or None,
        "instapay": os.getenv("PAYMOB_INTEGRATION_ID_INSTAPAY", "").strip() or None,
        "valu": os.getenv("PAYMOB_INTEGRATION_ID_VALU", "").strip() or None,
    }

    paypal_cid = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_sec = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    paypal_enabled = bool(paypal_cid and paypal_sec)

    # Fawry configuration
    fawry_merchant_code = os.getenv("FAWRY_MERCHANT_CODE", "").strip()
    fawry_enabled = bool(fawry_merchant_code and os.getenv("FAWRY_SECURITY_KEY", "").strip())

    # Default currency based on region
    default_currency = os.getenv("DEFAULT_CURRENCY", "EGP" if paymob_enabled else "USD")

    # Determine Stripe use case
    stripe_use_case = "all"
    if not stripe_enabled:
        stripe_use_case = "disabled"
    elif paymob_enabled:
        stripe_use_case = "international_customers_only"

    return {
        "stripe_enabled": stripe_enabled,
        "publishable_key": pk if stripe_enabled else None,
        "paymob_enabled": paymob_enabled,
        "paymob_iframe_ready": paymob_iframe_ready,
        "paymob_iframe_url": paymob_iframe_url,
        "paymob_integration_ids": paymob_integration_ids,
        "fawry_enabled": fawry_enabled,
        "fawry_merchant_code": fawry_merchant_code if fawry_enabled else None,
        "paypal_enabled": paypal_enabled,
        "paypal_client_id": paypal_cid if paypal_enabled else None,
        "default_currency": default_currency,
        "stripe_use_case": stripe_use_case,
    }


@router.post("/intent")
async def create_stripe_payment_intent(
    body: PaymentIntentRequest,
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Create a PaymentIntent for Stripe Payment Element (cards, wallets, Klarna where enabled).
    For pickup or shipping orders while payment_status is pending (card checkout).
    """
    sk = os.getenv("STRIPE_SECRET_KEY", "").strip()
    pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    allow_mock = os.getenv("ALLOW_MOCK_PAYMENTS", "").strip().lower() in ("1", "true", "yes")
    if not sk or not pk:
        # Real payments only unless explicitly allowed for local dev.
        if settings.is_production or not allow_mock:
            raise HTTPException(status_code=503, detail="Stripe is not configured")
        return {
            "client_secret": f"pi_mock_{body.order_id}_secret",
            "publishable_key": "pk_test_mock",
            "payment_intent_id": f"pi_mock_{body.order_id}",
            "mode": "mock",
        }

    import stripe

    stripe.api_key = sk

    db: Session = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == body.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if user and getattr(order, "user_id", None) != user.id:
            raise HTTPException(status_code=403, detail="Order ownership mismatch")
        dm = getattr(order, "delivery_method", None)
        if dm not in ("pickup", "shipping"):
            raise HTTPException(
                status_code=400,
                detail="Payment intent is only for pickup or shipping orders awaiting payment",
            )
        if getattr(order, "payment_status", None) != "pending":
            raise HTTPException(status_code=400, detail="Order is not awaiting payment")

        amount_cents = int(round(float(order.total) * 100))
        if amount_cents < 50:
            raise HTTPException(status_code=400, detail="Amount below Stripe minimum ($0.50)")

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                automatic_payment_methods={"enabled": True},
                metadata={
                    "order_id": order.id,
                    "order_number": str(order.order_number or ""),
                },
                description=f"CONFIT {order.order_number}",
            )
        except stripe.error.StripeError as e:
            logger.exception("Stripe PaymentIntent create failed")
            raise HTTPException(status_code=502, detail=str(e)) from e

        return {
            "client_secret": intent.client_secret,
            "publishable_key": pk,
            "payment_intent_id": intent.id,
        }
    finally:
        db.close()


@router.post("/confirm")
async def confirm_payment_success(
    request: PaymentConfirmRequest,
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Confirm successful payment: verify Stripe PaymentIntent when configured, then finalize.

    Pickup: create pickup record + brand notifications. Shipping: mark paid only.
    """
    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    allow_mock = os.getenv("ALLOW_MOCK_PAYMENTS", "").strip().lower() in ("1", "true", "yes")

    db: Session = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == request.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if user and getattr(order, "user_id", None) != user.id:
            raise HTTPException(status_code=403, detail="Order ownership mismatch")

        is_pickup = getattr(order, "delivery_method", None) == "pickup"
        pending = getattr(order, "payment_status", None) == "pending"

        if pending and stripe_secret:
            if not request.payment_intent_id:
                raise HTTPException(
                    status_code=400,
                    detail="payment_intent_id is required when Stripe is configured",
                )
            import stripe

            stripe.api_key = stripe_secret
            try:
                pi = stripe.PaymentIntent.retrieve(request.payment_intent_id)
            except stripe.error.StripeError as e:
                logger.warning("Stripe retrieve failed: %s", e)
                raise HTTPException(status_code=400, detail="Could not verify payment") from e
            if pi.status != "succeeded":
                raise HTTPException(status_code=402, detail=f"Payment not completed: {pi.status}")
            meta = pi.metadata or {}
            if meta.get("order_id") and meta["order_id"] != order.id:
                raise HTTPException(status_code=400, detail="Payment does not match this order")
            if pi.amount != int(round(float(order.total) * 100)):
                raise HTTPException(status_code=400, detail="Payment amount does not match order")
        elif pending and not stripe_secret:
            if settings.is_production or not allow_mock:
                raise HTTPException(
                    status_code=503,
                    detail="Stripe must be configured in production; payment cannot be confirmed without verification.",
                )
            logger.warning("Stripe not configured — using dev payment_success flag for order %s", request.order_id)
            if not request.payment_success:
                with db.begin():
                    order_fail = db.query(OrderModel).filter(OrderModel.id == request.order_id).first()
                    if order_fail:
                        order_fail.payment_status = "failed"
                return {"success": False, "reason": "payment_success=false"}
        elif not pending:
            return {"success": True, "order_id": order.id}

        if not is_pickup:
            with db.begin():
                order_ship = db.query(OrderModel).filter(OrderModel.id == request.order_id).first()
                if order_ship:
                    order_ship.payment_status = "success"
            return {"success": True, "order_id": order.id}

        # Pickup: payment verified (Stripe) or mock (payment_success)
        if not getattr(order, "pickup_store_id", None) or not getattr(order, "pickup_time", None):
            raise HTTPException(status_code=400, detail="Order missing pickup fields")

        # Single transaction: create pickup + notification rows, commit once, then emit.
        with db.begin():
            order = db.query(OrderModel).filter(OrderModel.id == request.order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")

            order.payment_status = "success"

            # 1) create pickup record
            existing_pickup = (
                db.query(PickupRecordModel)
                .filter(PickupRecordModel.order_id == order.id)
                .first()
            )
            if not existing_pickup:
                pickup_id = f"pickup-{uuid.uuid4().hex[:12]}"
                db.add(
                    PickupRecordModel(
                        id=pickup_id,
                        order_id=order.id,
                        store_id=order.pickup_store_id,
                        pickup_time=order.pickup_time,
                        status="scheduled",
                    )
                )

            # 2) select notification receivers (store brand owners/managers)
            store = db.query(StoreModel).filter(StoreModel.id == order.pickup_store_id).first()
            if not store:
                raise HTTPException(status_code=400, detail="Invalid pickup store on order")

            managers = (
                db.query(BrandManagerModel)
                .filter(BrandManagerModel.brand_id == store.brand_id, BrandManagerModel.is_active == True)  # noqa: E712
                .all()
            )
            owners = [m for m in managers if (m.role or "").lower() == "owner"]
            target = owners or managers
            receiver_ids: list[str] = [str(m.user_id) for m in target]

            if not receiver_ids:
                receiver_ids = [
                    str(r.user_id)
                    for r in db.query(UserRole).filter(UserRole.role == AppRole.brand_manager).all()
                ]

            if not receiver_ids:
                raise HTTPException(status_code=500, detail="No brand managers found for store")

            service = NotificationService(db)
            created: list[tuple[str, str, str, dict]] = []
            for receiver_id in receiver_ids:
                data = PickupSelectedData(
                    order_id=str(order.id),
                    customer_user_id=str(order.user_id),
                    pickup_store_id=str(order.pickup_store_id),
                    pickup_time=str(order.pickup_time),
                    receiver_id=str(receiver_id),
                )
                row, payload = service.create_pickup_notification_row(data=data, reject_if_exists=True)
                if row is not None and payload is not None:
                    created.append((receiver_id, str(order.pickup_store_id), row.id, payload))

        # 3) emit after commit (ACK/retry handled by hub)
        from services.notificationService.realtime import realtime_hub

        for receiver_id, store_id, notif_id, payload in created:
            await realtime_hub.publish_notification(
                receiver_id=receiver_id,
                store_id=store_id,
                notification_id=notif_id,
                payload=payload,
            )

        return {"success": True, "order_id": request.order_id}
    finally:
        db.close()
