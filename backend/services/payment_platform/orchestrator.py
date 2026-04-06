"""
Unified payment orchestration — ledger row + provider session.

Provider Priority for Egypt (EGP):
  1. Paymob (cards, Meeza, Instapay, Valu BNPL)
  2. Fawry (COD, cards, wallets, kiosk)
  3. Stripe (international customers only)

Stripe is deprioritized for Egypt - only used when:
  - billing_country != 'EG' OR currency != 'EGP'
"""

from __future__ import annotations

import logging
import os
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import stripe
from sqlalchemy.orm import Session

from database.models import Order as OrderModel
from database.payment_platform_models import Payment, PaymentStatus, PaymentTransaction

logger = logging.getLogger(__name__)


def _amount_cents(order: OrderModel) -> int:
    return int(round(float(order.total) * 100))


def _normalize_currency_iso(code: str) -> str:
    return (code or "USD").strip().upper()


def _storefront_default_currency() -> str:
    return _normalize_currency_iso(os.getenv("STOREFRONT_DEFAULT_CURRENCY", "EGP"))


def _coerce_user_uuid(user_id: Optional[str]) -> Optional[str]:
    if not user_id:
        return None
    try:
        uuid.UUID(str(user_id))
        return str(user_id)
    except ValueError:
        return None


def _stripe_keys() -> tuple[str, str]:
    sk = os.getenv("STRIPE_SECRET_KEY", "").strip()
    pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    return sk, pk


def _stripe_use_case() -> str:
    """Get Stripe use case setting."""
    return os.getenv("STRIPE_USE_CASE", "international_customers_only").lower()


def _should_use_stripe(billing_country: Optional[str], currency: str) -> bool:
    """
    Determine if Stripe should be used based on Egypt routing rules.
    
    Stripe is only used for:
      - International customers (billing_country != 'EG')
      - Non-EGP currency transactions
    """
    use_case = _stripe_use_case()
    
    if use_case == "disabled":
        return False
    
    if use_case == "international_customers_only":
        # Only use Stripe for non-Egypt customers or non-EGP currency
        is_egypt = (billing_country or "EG").upper() == "EG"
        is_egp = currency.upper() == "EGP"
        
        if is_egypt and is_egp:
            logger.warning(
                "Stripe routing blocked for Egypt/EGP transaction - use Paymob or Fawry instead"
            )
            return False
        return True
    
    # Default: allow Stripe for all (legacy behavior)
    return True


async def create_payment_session(
    db: Session,
    *,
    order_id: str,
    provider: str,
    user_id: Optional[str],
    idempotency_key: Optional[str],
    billing: Optional[Dict[str, str]] = None,
    paypal_return_url: Optional[str] = None,
    paypal_cancel_url: Optional[str] = None,
) -> Dict[str, Any]:
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise ValueError("ORDER_NOT_FOUND")
    if getattr(order, "payment_status", None) != "pending":
        raise ValueError("ORDER_NOT_PAYABLE")

    cents = _amount_cents(order)
    if cents < 50 and provider == "stripe":
        raise ValueError("AMOUNT_BELOW_STRIPE_MIN")

    if idempotency_key:
        existing = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
        if existing and existing.client_payload:
            return dict(existing.client_payload)

    pay = Payment(
        order_id=order.id,
        user_id=_coerce_user_uuid(user_id),
        provider=provider,
        status=PaymentStatus.pending.value,
        amount_cents=cents,
        currency="usd",
        idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex}",
    )
    db.add(pay)
    db.flush()

    billing = billing or {}
    billing_country = billing.get("country")
    currency = billing.get("currency", "EGP")

    if provider == "stripe":
        # Check if Stripe should be used based on Egypt routing rules
        if not _should_use_stripe(billing_country, currency):
            db.rollback()
            raise ValueError("STRIPE_NOT_AVAILABLE_FOR_EGYPT_EGP - Use Paymob or Fawry instead")
        
        sk, pk = _stripe_keys()
        if not sk or not pk:
            db.rollback()
            raise ValueError("STRIPE_NOT_CONFIGURED")
        stripe.api_key = sk
        try:
            intent = stripe.PaymentIntent.create(
                amount=cents,
                currency="usd",
                automatic_payment_methods={"enabled": True},
                metadata={"order_id": order.id, "order_number": str(order.order_number or ""), "payment_id": pay.id},
                description=f"CONFIT {order.order_number}",
                idempotency_key=f"{pay.idempotency_key}:pi",
            )
        except stripe.error.StripeError as e:
            db.rollback()
            raise ValueError(f"STRIPE_ERROR:{e}") from e
        pay.external_payment_id = intent.id
        pay.status = PaymentStatus.processing.value
        out = {
            "payment_record_id": pay.id,
            "client_secret": intent.client_secret,
            "publishable_key": pk,
            "payment_intent_id": intent.id,
            "provider": "stripe",
        }
        pay.client_payload = out
        db.add(
            PaymentTransaction(
                payment_id=pay.id,
                kind="payment_intent_created",
                amount_cents=cents,
                currency="usd",
                provider_reference=intent.id,
                payload={"id": intent.id},
            )
        )
        db.commit()
        return out

    if provider == "paymob":
        from services.payment_platform.providers import paymob_provider as pm

        storefront_cur = _storefront_default_currency()
        paymob_cur = _normalize_currency_iso(billing.get("currency") or storefront_cur)
        strict = os.getenv("PAYMOB_STRICT_CURRENCY_MATCH", "").lower() in ("1", "true", "yes")
        if strict and paymob_cur != storefront_cur:
            db.rollback()
            raise ValueError("PAYMOB_CURRENCY_MISMATCH")
        billing = {**billing, "currency": paymob_cur}

        try:
            tok = await pm.auth_token()
            reg = await pm.register_order(
                auth_tok=tok,
                amount_cents=cents,
                currency=paymob_cur,
                merchant_order_id=order.id,
            )
            paymob_oid = int(reg.get("id"))
            iframe_tok = await pm.create_payment_key(
                auth_tok=tok,
                amount_cents=cents,
                currency=paymob_cur,
                paymob_order_id=paymob_oid,
                billing=billing,
            )
        except Exception as e:
            db.rollback()
            logger.exception("Paymob session failed")
            raise ValueError(f"PAYMOB_ERROR:{e}") from e
        pay.external_payment_id = str(paymob_oid)
        pay.currency = paymob_cur.lower()
        pay.status = PaymentStatus.processing.value
        iframe_base = os.getenv("PAYMOB_IFRAME_URL", "https://accept.paymob.com/api/acceptance/iframes")
        iframe_id = os.getenv("PAYMOB_IFRAME_ID", "").strip()
        iframe_url = f"{iframe_base}/{iframe_id}?payment_token={iframe_tok}" if iframe_id else None
        out = {
            "payment_record_id": pay.id,
            "provider": "paymob",
            "iframe_token": iframe_tok,
            "paymob_order_id": paymob_oid,
            "iframe_url": iframe_url,
        }
        pk = os.getenv("PAYMOB_PUBLIC_KEY", "").strip()
        if pk:
            out["public_key"] = pk
        pay.client_payload = out
        db.add(
            PaymentTransaction(
                payment_id=pay.id,
                kind="paymob_payment_key",
                amount_cents=cents,
                currency=paymob_cur,
                provider_reference=str(paymob_oid),
                payload={"order_id": paymob_oid},
            )
        )
        db.commit()
        return out

    if provider == "paypal":
        from services.payment_platform.providers import paypal_provider as pp

        if not paypal_return_url or not paypal_cancel_url:
            db.rollback()
            raise ValueError("PAYPAL_URLS_REQUIRED")
        paypal_cur = _normalize_currency_iso(os.getenv("PAYPAL_CHECKOUT_CURRENCY", "USD"))
        storefront_cur = _storefront_default_currency()
        if paypal_cur != storefront_cur:
            db.rollback()
            raise ValueError("PAYPAL_CURRENCY_MISMATCH")
        amt = str(Decimal(order.total).quantize(Decimal("0.01")))
        try:
            po = await pp.create_order(
                amount_value=amt,
                currency=paypal_cur,
                merchant_ref=order.id,
                return_url=paypal_return_url,
                cancel_url=paypal_cancel_url,
            )
        except Exception as e:
            db.rollback()
            logger.exception("PayPal order failed")
            raise ValueError(f"PAYPAL_ERROR:{e}") from e
        pid = str(po.get("id"))
        pay.external_payment_id = pid
        pay.currency = paypal_cur.lower()
        pay.status = PaymentStatus.processing.value
        approve = pp.extract_approve_link(po)
        out = {
            "payment_record_id": pay.id,
            "provider": "paypal",
            "paypal_order_id": pid,
            "approve_url": approve,
        }
        pay.client_payload = out
        db.add(
            PaymentTransaction(
                payment_id=pay.id,
                kind="paypal_order_created",
                amount_cents=cents,
                currency=paypal_cur,
                provider_reference=pid,
                payload=po,
            )
        )
        db.commit()
        return out

    db.rollback()
    raise ValueError("UNKNOWN_PROVIDER")


def mark_payment_succeeded(db: Session, payment: Payment, extra: Optional[dict] = None) -> None:
    if payment.status == PaymentStatus.succeeded.value:
        return
    order = db.query(OrderModel).filter(OrderModel.id == payment.order_id).first()
    if order:
        order.payment_status = "success"
    payment.status = PaymentStatus.succeeded.value
    db.add(
        PaymentTransaction(
            payment_id=payment.id,
            kind="captured",
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            provider_reference=payment.external_payment_id,
            payload=extra or {},
        )
    )
    db.commit()
    db.refresh(payment)

    from services.payment_platform.post_payment_workflow import schedule_post_payment_success

    schedule_post_payment_success(
        str(payment.order_id),
        payment.id,
        str(payment.provider),
    )


def mark_payment_failed(db: Session, payment: Payment, reason: str) -> None:
    if payment.status == PaymentStatus.succeeded.value:
        logger.info("mark_payment_failed ignored: payment already succeeded id=%s", payment.id)
        return
    if payment.status == PaymentStatus.failed.value:
        return
    order = db.query(OrderModel).filter(OrderModel.id == payment.order_id).first()
    if order and getattr(order, "payment_status", None) == "pending":
        order.payment_status = "failed"
    payment.status = PaymentStatus.failed.value
    db.commit()

    from services.payment_platform.event_bus import DomainEvent, bus
    import asyncio

    async def _pub():
        await bus.publish(
            DomainEvent("payment_failed", {"order_id": payment.order_id, "payment_id": payment.id, "reason": reason})
        )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_pub())
        else:
            asyncio.run(_pub())
    except RuntimeError:
        asyncio.run(_pub())
