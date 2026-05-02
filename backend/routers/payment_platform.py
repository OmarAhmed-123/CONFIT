"""
Unified payment API (FastAPI source of truth): Stripe + Paymob + PayPal.
Legacy routes /api/payments/intent and /confirm remain unchanged.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import Order as OrderModel
from database.payment_platform_models import Invoice, Payment, PaymentEvent, PaymentStatus
from services.auth_service import UserProfile
from services.payment_platform.event_bus import bus
from services.payment_platform import orchestrator as orch
from services.payment_platform.providers import paymob_provider as pm
from services.payment_platform.providers import paypal_provider as pp
from services.payment_platform.providers import fawry_provider as fw
from utils.auth_deps import optional_auth
from core.slowapi_limiter import limiter, LIMIT_PAYMENT, LIMIT_WEBHOOK

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments — Unified"])


async def _log_payment_success(payload: Dict[str, Any]) -> None:
    logger.info("event payment_success order=%s payment=%s", payload.get("order_id"), payload.get("payment_id"))


async def _log_payment_failed(payload: Dict[str, Any]) -> None:
    logger.warning("event payment_failed order=%s reason=%s", payload.get("order_id"), payload.get("reason"))


async def _log_invoice(payload: Dict[str, Any]) -> None:
    logger.info("event invoice_created invoice=%s order=%s", payload.get("invoice_id"), payload.get("order_id"))


bus.subscribe("payment_success", _log_payment_success)
bus.subscribe("payment_failed", _log_payment_failed)
bus.subscribe("invoice_created", _log_invoice)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UnifiedSessionBody(BaseModel):
    order_id: str = Field(..., min_length=1)
    provider: str = Field(..., pattern="^(stripe|paymob|paypal|fawry|valu|cash_on_delivery)$")
    billing: Optional[Dict[str, str]] = None
    paypal_return_url: Optional[str] = None
    paypal_cancel_url: Optional[str] = None
    # Fawry-specific
    payment_method: Optional[str] = None  # CARD, CASH_ON_DELIVERY, WALLET, FAWRY_REF_NUMBER
    # Valu-specific
    tenor: Optional[int] = None  # 6, 9, 12, 18, 24 months


@router.post("/api/payments/unified/session")
@limiter.limit(LIMIT_PAYMENT)
async def create_unified_session(
    request: Request,
    body: UnifiedSessionBody,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    if not user:
        raise HTTPException(401, "Authentication required")
    idem = request.headers.get("x-idempotency-key") or request.headers.get("X-Idempotency-Key")
    uid = str(user.id)
    order = db.query(OrderModel).filter(OrderModel.id == body.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if str(order.user_id) != str(user.id):
        raise HTTPException(403, "Order ownership mismatch")
    try:
        out = await orch.create_payment_session(
            db,
            order_id=body.order_id,
            provider=body.provider,
            user_id=uid,
            idempotency_key=idem,
            billing=body.billing,
            paypal_return_url=body.paypal_return_url,
            paypal_cancel_url=body.paypal_cancel_url,
        )
    except ValueError as e:
        code = str(e)
        if code == "ORDER_NOT_FOUND":
            raise HTTPException(404, "Order not found") from e
        if code == "ORDER_NOT_PAYABLE":
            raise HTTPException(400, "Order is not payable") from e
        if code == "STRIPE_NOT_CONFIGURED":
            raise HTTPException(503, "Stripe is not configured") from e
        if code == "AMOUNT_BELOW_STRIPE_MIN":
            raise HTTPException(400, "Amount below Stripe minimum") from e
        if code == "PAYPAL_URLS_REQUIRED":
            raise HTTPException(400, "paypal_return_url and paypal_cancel_url required for PayPal") from e
        if code.startswith("STRIPE_ERROR:"):
            raise HTTPException(502, code) from e
        if code.startswith("PAYMOB_ERROR:"):
            if "403 Forbidden" in code or "401 Unauthorized" in code:
                raise HTTPException(
                    503,
                    "Paymob credentials were rejected. Check PAYMOB_API_KEY, integration id, iframe id, and account mode before retrying.",
                ) from e
            raise HTTPException(502, code) from e
        if code.startswith("PAYPAL_ERROR:"):
            raise HTTPException(502, code) from e
        if code.startswith("FAWRY_ERROR:"):
            raise HTTPException(502, code) from e
        if code.startswith("VALU_ERROR:"):
            raise HTTPException(502, code) from e
        if code == "STRIPE_NOT_AVAILABLE_FOR_EGYPT_EGP - Use Paymob or Fawry instead":
            raise HTTPException(400, "Stripe not available for Egypt/EGP transactions. Use Paymob or Fawry instead") from e
        raise HTTPException(400, code) from e

    return out


@router.post("/api/payments/unified/webhooks/paymob")
@limiter.limit(LIMIT_WEBHOOK)
async def webhook_paymob(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    obj_raw = form.get("obj") or form.get("object")
    hmac_v = form.get("hmac") or form.get("HMAC")
    if not obj_raw or not hmac_v:
        raise HTTPException(400, "Missing obj or hmac")
    try:
        obj = json.loads(obj_raw) if isinstance(obj_raw, str) else dict(obj_raw)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "Invalid obj JSON") from e

    if not pm.verify_callback_hmac(obj, str(hmac_v)):
        raise HTTPException(403, "Invalid HMAC")

    tid = str(obj.get("id", ""))
    fp = f"paymob:{tid}"
    if db.query(PaymentEvent).filter(PaymentEvent.provider_event_fingerprint == fp).first():
        return {"received": True, "duplicate": True}

    success = str(obj.get("success", "")).lower() == "true"
    order_nested = obj.get("order") or {}
    paymob_oid = str(order_nested.get("id", ""))
    pay = db.query(Payment).filter(Payment.external_payment_id == paymob_oid, Payment.provider == "paymob").first()
    if not pay:
        logger.warning("Paymob webhook: no payment row for paymob order %s", paymob_oid)
        raise HTTPException(404, "Payment not found")

    ev = PaymentEvent(
        payment_id=pay.id,
        event_type="paymob_transaction",
        provider_event_fingerprint=fp,
        payload=obj,
        processed_ok=False,
    )
    db.add(ev)
    db.flush()

    if success:
        orch.mark_payment_succeeded(db, pay, {"transaction": tid})
    else:
        orch.mark_payment_failed(db, pay, "paymob_declined")
    db.query(PaymentEvent).filter(PaymentEvent.id == ev.id).update({"processed_ok": True})
    db.commit()
    return {"received": True}


@router.post("/api/payments/unified/webhooks/paypal")
@limiter.limit(LIMIT_WEBHOOK)
async def webhook_paypal(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(400, "Invalid JSON body") from exc
    headers = {k.lower(): v for k, v in request.headers.items()}
    hdr = {
        "paypal-transmission-id": headers.get("paypal-transmission-id", ""),
        "paypal-transmission-time": headers.get("paypal-transmission-time", ""),
        "paypal-cert-url": headers.get("paypal-cert-url", ""),
        "paypal-auth-algo": headers.get("paypal-auth-algo", ""),
        "paypal-transmission-sig": headers.get("paypal-transmission-sig", ""),
    }
    try:
        signature_ok = await pp.verify_webhook_signature(hdr, body)
    except Exception as exc:
        logger.warning("PayPal webhook signature verification failed: %s", exc)
        raise HTTPException(403, "Invalid PayPal webhook signature") from exc
    if not signature_ok:
        raise HTTPException(403, "Invalid PayPal webhook signature")

    et = body.get("event_type", "")
    resource = body.get("resource") or {}
    eid = str(body.get("id", ""))
    fp = f"paypal:{eid}"
    if db.query(PaymentEvent).filter(PaymentEvent.provider_event_fingerprint == fp).first():
        return {"received": True, "duplicate": True}

    ev = PaymentEvent(
        payment_id=None,
        event_type=et,
        provider_event_fingerprint=fp,
        payload=body,
        processed_ok=False,
    )
    db.add(ev)
    db.flush()

    if et == "PAYMENT.CAPTURE.COMPLETED":
        supp = resource.get("supplementary_data") or {}
        rel = supp.get("related_ids") or {}
        paypal_order_id = str(rel.get("order_id") or "")
        pay = None
        if paypal_order_id:
            pay = db.query(Payment).filter(Payment.external_payment_id == paypal_order_id, Payment.provider == "paypal").first()
        if pay:
            ev.payment_id = pay.id
            orch.mark_payment_succeeded(db, pay, {"webhook": et, "capture_id": resource.get("id")})
            db.query(PaymentEvent).filter(PaymentEvent.id == ev.id).update({"processed_ok": True})
        else:
            logger.warning("PayPal webhook: no payment for order_id %s", paypal_order_id)
    db.commit()
    return {"received": True}


@router.post("/api/payments/unified/webhooks/fawry")
@limiter.limit(LIMIT_WEBHOOK)
async def webhook_fawry(request: Request, db: Session = Depends(get_db)):
    """Handle Fawry payment webhooks (MD5 signature verification)."""
    body = await request.body()
    signature = request.headers.get("fawry-signature", "") or request.headers.get("Fawry-Signature", "")
    
    if not fw.verify_webhook(body, signature):
        raise HTTPException(403, "Invalid Fawry webhook signature")
    
    import json
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "Invalid JSON body") from e
    
    reference_number = data.get("referenceNumber", "")
    merchant_ref = data.get("merchantRefNum", "")
    status_code = data.get("statusCode", "")
    
    fp = f"fawry:{reference_number}"
    if db.query(PaymentEvent).filter(PaymentEvent.provider_event_fingerprint == fp).first():
        return {"received": True, "duplicate": True}
    
    # Find payment by reference number or merchant ref
    pay = db.query(Payment).filter(
        (Payment.external_payment_id == reference_number) | 
        (Payment.external_payment_id == merchant_ref),
        Payment.provider == "fawry"
    ).first()
    
    if not pay:
        logger.warning("Fawry webhook: no payment for ref %s", reference_number)
        # Still record the event for reconciliation
        ev = PaymentEvent(
            payment_id=None,
            event_type="fawry_webhook_orphan",
            provider_event_fingerprint=fp,
            payload=data,
            processed_ok=False,
        )
        db.add(ev)
        db.commit()
        raise HTTPException(404, "Payment not found")
    
    ev = PaymentEvent(
        payment_id=pay.id,
        event_type="fawry_callback",
        provider_event_fingerprint=fp,
        payload=data,
        processed_ok=False,
    )
    db.add(ev)
    db.flush()
    
    # Map Fawry status to payment status
    if status_code == "PAID" or status_code == "SUCCESS":
        orch.mark_payment_succeeded(db, pay, {"fawry_ref": reference_number})
    elif status_code == "FAILED" or status_code == "DECLINED":
        orch.mark_payment_failed(db, pay, f"fawry_{status_code.lower()}")
    elif status_code == "EXPIRED":
        orch.mark_payment_failed(db, pay, "fawry_expired")
    elif status_code == "CANCELED":
        orch.mark_payment_failed(db, pay, "fawry_canceled")
    # For COD: status remains pending_cod until delivery confirmation
    
    db.query(PaymentEvent).filter(PaymentEvent.id == ev.id).update({"processed_ok": True})
    db.commit()
    return {"received": True}


@router.post("/api/payments/unified/webhooks/valu")
@limiter.limit(LIMIT_WEBHOOK)
async def webhook_valu(request: Request, db: Session = Depends(get_db)):
    """Handle Valu BNPL webhooks (routed through Paymob HMAC)."""
    from services.payment_platform.providers import valu_provider as vu
    
    body = await request.body()
    signature = request.headers.get("hmac", "") or request.headers.get("HMAC", "")
    
    try:
        signature_ok = vu.verify_webhook(body, signature)
    except Exception as exc:
        logger.warning("Valu webhook signature verification failed: %s", exc)
        raise HTTPException(403, "Invalid Valu webhook signature") from exc
    if not signature_ok:
        raise HTTPException(403, "Invalid Valu webhook signature")
    
    import json
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "Invalid JSON body") from e
    
    # Valu webhooks come through Paymob, so structure is similar
    transaction_id = str(data.get("id", ""))
    fp = f"valu:{transaction_id}"
    
    if db.query(PaymentEvent).filter(PaymentEvent.provider_event_fingerprint == fp).first():
        return {"received": True, "duplicate": True}
    
    order_nested = data.get("order") or {}
    paymob_oid = str(order_nested.get("id", ""))
    pay = db.query(Payment).filter(
        Payment.external_payment_id == paymob_oid,
        Payment.provider == "valu"
    ).first()
    
    if not pay:
        logger.warning("Valu webhook: no payment for order %s", paymob_oid)
        ev = PaymentEvent(
            payment_id=None,
            event_type="valu_webhook_orphan",
            provider_event_fingerprint=fp,
            payload=data,
            processed_ok=False,
        )
        db.add(ev)
        db.commit()
        raise HTTPException(404, "Payment not found")
    
    ev = PaymentEvent(
        payment_id=pay.id,
        event_type="valu_callback",
        provider_event_fingerprint=fp,
        payload=data,
        processed_ok=False,
    )
    db.add(ev)
    db.flush()
    
    success = str(data.get("success", "")).lower() == "true"
    if success:
        orch.mark_payment_succeeded(db, pay, {"valu_transaction": transaction_id})
    else:
        orch.mark_payment_failed(db, pay, "valu_declined")
    
    db.query(PaymentEvent).filter(PaymentEvent.id == ev.id).update({"processed_ok": True})
    db.commit()
    return {"received": True}


class PayPalCaptureBody(BaseModel):
    paypal_order_id: str = Field(..., min_length=1)


class ValuEligibilityBody(BaseModel):
    phone: str = Field(..., min_length=10, description="Customer phone number")
    amount_piastres: int = Field(..., ge=1000, description="Amount in piastres (EGP * 100)")
    tenor: Optional[int] = Field(6, description="Installment period in months (6, 9, 12, 18, 24)")


class ValuEligibilityResponse(BaseModel):
    eligible: bool
    max_amount_egp: float
    available_tenors: List[int]
    requested_tenor: int
    reason: Optional[str] = None


@router.post("/api/payments/valu/eligibility", response_model=ValuEligibilityResponse)
@limiter.limit(LIMIT_PAYMENT)
async def check_valu_eligibility(
    request: Request,
    body: ValuEligibilityBody,
):
    """
    Check Valu BNPL eligibility for a customer.

    Returns eligibility status, maximum amount, and available installment tenors.
    """
    from services.payment_platform.providers import valu_check_eligibility

    try:
        result = await valu_check_eligibility(
            customer_phone=body.phone,
            amount_piastres=body.amount_piastres,
            tenor=body.tenor,
        )
        return ValuEligibilityResponse(**result)
    except Exception as e:
        logger.exception("Valu eligibility check failed")
        raise HTTPException(502, f"Valu eligibility check failed: {e}") from e


@router.get("/api/payments/fawry/status/{reference_number}")
@limiter.limit(LIMIT_PAYMENT)
async def get_fawry_status(
    request: Request,
    reference_number: str,
):
    """
    Get the status of a Fawry payment by reference number.

    Returns payment status, amount, and other details.
    """
    from services.payment_platform.providers import fawry_get_charge_status

    if not getattr(fw, "_provider", None) or not fw._provider.merchant_code or not fw._provider.security_key:
        return {
            "status": "unavailable",
            "amount": None,
            "payment_method": None,
            "reference_number": reference_number,
            "merchant_ref": None,
            "provider": "fawry",
            "message": "Fawry is not configured in this environment",
        }

    try:
        result = await fawry_get_charge_status(charge_id=reference_number)
        return {
            "status": result.get("status"),
            "amount": result.get("amount"),
            "payment_method": result.get("payment_method"),
            "reference_number": result.get("charge_id"),
            "merchant_ref": result.get("merchant_ref"),
            "provider": "fawry",
        }
    except Exception as e:
        logger.exception("Fawry status check failed")
        raise HTTPException(502, f"Fawry status check failed: {e}") from e


@router.post("/api/payments/unified/paypal/capture")
@limiter.limit(LIMIT_PAYMENT)
async def paypal_capture_after_return(
    request: Request,
    body: PayPalCaptureBody,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    if not user:
        raise HTTPException(401, "Authentication required")
    pay = db.query(Payment).filter(Payment.external_payment_id == body.paypal_order_id, Payment.provider == "paypal").first()
    if not pay:
        raise HTTPException(404, "Payment session not found")
    order = db.query(OrderModel).filter(OrderModel.id == pay.order_id).first()
    if order and str(order.user_id) != str(user.id):
        raise HTTPException(403, "Order ownership mismatch")
    try:
        cap = await pp.capture_order(body.paypal_order_id)
    except Exception as e:
        logger.exception("PayPal capture failed")
        raise HTTPException(502, str(e)) from e
    status = cap.get("status")
    if status == "COMPLETED":
        orch.mark_payment_succeeded(db, pay, {"capture": cap})
        return {"success": True, "status": status}
    return {"success": False, "status": status}


@router.get("/api/invoices/{invoice_id}")
async def get_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.user_id:
        if not user:
            raise HTTPException(401, "Authentication required")
        if str(inv.user_id) != str(user.id):
            raise HTTPException(403, "Not allowed to access this invoice")
    path = inv.pdf_storage_path
    if not path:
        raise HTTPException(404, "PDF missing")
    import os

    if not os.path.isfile(path):
        raise HTTPException(404, "PDF file missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=f"{inv.invoice_number}.pdf")


# ============================================================================
# Egypt-Specific Payment Methods (Meeza, InstaPay, Valu)
# ============================================================================

class MeezaPaymentBody(BaseModel):
    order_id: str = Field(..., min_length=1)
    billing: Optional[Dict[str, str]] = None


class MeezaPaymentResponse(BaseModel):
    payment_record_id: str
    provider: str = "paymob"
    payment_method: str = "meeza"
    iframe_token: str
    paymob_order_id: int
    iframe_url: Optional[str] = None
    integration_type: str = "meeza"


@router.post("/api/payments/paymob/meeza", response_model=MeezaPaymentResponse)
@limiter.limit(LIMIT_PAYMENT)
async def create_meeza_payment_session(
    request: Request,
    body: MeezaPaymentBody,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Create a Meeza card payment session.
    Meeza is Egypt's domestic card scheme - lower fees for local cards.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    order = db.query(OrderModel).filter(OrderModel.id == body.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if str(order.user_id) != str(user.id):
        raise HTTPException(403, "Order ownership mismatch")

    # Check Meeza integration is configured
    meeza_integration = pm.get_integration_id("meeza")
    if not meeza_integration:
        raise HTTPException(503, "Meeza payment method not configured")

    idem = request.headers.get("x-idempotency-key") or request.headers.get("X-Idempotency-Key")
    cents = int(round(float(order.total) * 100))

    # Check for existing payment
    if idem:
        existing = db.query(Payment).filter(Payment.idempotency_key == idem).first()
        if existing and existing.client_payload:
            return MeezaPaymentResponse(**existing.client_payload)

    pay = Payment(
        order_id=order.id,
        user_id=str(user.id),
        provider="paymob",
        status=PaymentStatus.processing.value,
        amount_cents=cents,
        currency="egp",
        idempotency_key=idem or f"idem_meeza_{uuid.uuid4().hex}",
    )
    db.add(pay)
    db.flush()

    billing = {**(body.billing or {}), "currency": "EGP"}

    try:
        tok = await pm.auth_token()
        reg = await pm.register_order(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            merchant_order_id=order.id,
        )
        paymob_oid = int(reg.get("id"))
        payment_key = await pm.create_payment_key(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            paymob_order_id=paymob_oid,
            billing=billing,
            payment_method="meeza",
        )
    except Exception as e:
        db.rollback()
        logger.exception("Meeza payment session failed")
        raise HTTPException(502, f"Meeza payment session failed: {e}") from e

    pay.external_payment_id = str(paymob_oid)
    pay.status = PaymentStatus.processing.value

    iframe_base = os.getenv("PAYMOB_IFRAME_URL", "https://accept.paymob.com/api/acceptance/iframes")
    iframe_id = os.getenv("PAYMOB_IFRAME_ID_MEEZA", os.getenv("PAYMOB_IFRAME_ID", "")).strip()
    iframe_url = f"{iframe_base}/{iframe_id}?payment_token={payment_key}" if iframe_id else None

    out = MeezaPaymentResponse(
        payment_record_id=pay.id,
        provider="paymob",
        payment_method="meeza",
        iframe_token=payment_key,
        paymob_order_id=paymob_oid,
        iframe_url=iframe_url,
        integration_type="meeza",
    )
    pay.client_payload = out.model_dump()
    db.add(
        PaymentEvent(
            payment_id=pay.id,
            event_type="meeza_session_created",
            provider_event_fingerprint=f"meeza:{paymob_oid}",
            payload={"order_id": paymob_oid},
        )
    )
    db.commit()
    return out


class InstaPayPaymentBody(BaseModel):
    order_id: str = Field(..., min_length=1)
    billing: Optional[Dict[str, str]] = None
    bank_code: Optional[str] = None  # Optional: specific bank preference


class InstaPayPaymentResponse(BaseModel):
    payment_record_id: str
    provider: str = "paymob"
    payment_method: str = "instapay"
    iframe_token: str
    paymob_order_id: int
    iframe_url: Optional[str] = None
    integration_type: str = "instapay"
    supported_banks: List[str] = Field(default_factory=lambda: [
        "CIB", "QNB", "AlexBank", "Banque Misr",
        "National Bank of Egypt", "Commercial International Bank"
    ])


@router.post("/api/payments/paymob/instapay", response_model=InstaPayPaymentResponse)
@limiter.limit(LIMIT_PAYMENT)
async def create_instapay_payment_session(
    request: Request,
    body: InstaPayPaymentBody,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Create an InstaPay bank transfer payment session.
    InstaPay provides instant bank transfers from all major Egyptian banks.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    order = db.query(OrderModel).filter(OrderModel.id == body.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if str(order.user_id) != str(user.id):
        raise HTTPException(403, "Order ownership mismatch")

    # Check InstaPay integration is configured
    instapay_integration = pm.get_integration_id("instapay")
    if not instapay_integration:
        raise HTTPException(503, "InstaPay payment method not configured")

    idem = request.headers.get("x-idempotency-key") or request.headers.get("X-Idempotency-Key")
    cents = int(round(float(order.total) * 100))

    # Check for existing payment
    if idem:
        existing = db.query(Payment).filter(Payment.idempotency_key == idem).first()
        if existing and existing.client_payload:
            return InstaPayPaymentResponse(**existing.client_payload)

    pay = Payment(
        order_id=order.id,
        user_id=str(user.id),
        provider="paymob",
        status=PaymentStatus.processing.value,
        amount_cents=cents,
        currency="egp",
        idempotency_key=idem or f"idem_instapay_{uuid.uuid4().hex}",
    )
    db.add(pay)
    db.flush()

    billing = {**(body.billing or {}), "currency": "EGP"}

    try:
        tok = await pm.auth_token()
        reg = await pm.register_order(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            merchant_order_id=order.id,
        )
        paymob_oid = int(reg.get("id"))
        payment_key = await pm.create_payment_key(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            paymob_order_id=paymob_oid,
            billing=billing,
            payment_method="instapay",
        )
    except Exception as e:
        db.rollback()
        logger.exception("InstaPay payment session failed")
        raise HTTPException(502, f"InstaPay payment session failed: {e}") from e

    pay.external_payment_id = str(paymob_oid)
    pay.status = PaymentStatus.processing.value

    iframe_base = os.getenv("PAYMOB_IFRAME_URL", "https://accept.paymob.com/api/acceptance/iframes")
    iframe_id = os.getenv("PAYMOB_IFRAME_ID_INSTAPAY", os.getenv("PAYMOB_IFRAME_ID", "")).strip()
    iframe_url = f"{iframe_base}/{iframe_id}?payment_token={payment_key}" if iframe_id else None

    out = InstaPayPaymentResponse(
        payment_record_id=pay.id,
        provider="paymob",
        payment_method="instapay",
        iframe_token=payment_key,
        paymob_order_id=paymob_oid,
        iframe_url=iframe_url,
        integration_type="instapay",
    )
    pay.client_payload = out.model_dump()
    db.add(
        PaymentEvent(
            payment_id=pay.id,
            event_type="instapay_session_created",
            provider_event_fingerprint=f"instapay:{paymob_oid}",
            payload={"order_id": paymob_oid},
        )
    )
    db.commit()
    return out


class ValuPaymentBody(BaseModel):
    order_id: str = Field(..., min_length=1)
    billing: Optional[Dict[str, str]] = None
    tenor: int = Field(6, ge=6, le=36, description="Installment period in months")


class ValuPaymentResponse(BaseModel):
    payment_record_id: str
    provider: str = "paymob"
    payment_method: str = "valu"
    iframe_token: str
    paymob_order_id: int
    iframe_url: Optional[str] = None
    tenor_months: int
    monthly_installment_piastres: int
    integration_type: str = "valu"


@router.post("/api/payments/paymob/valu", response_model=ValuPaymentResponse)
@limiter.limit(LIMIT_PAYMENT)
async def create_valu_payment_session(
    request: Request,
    body: ValuPaymentBody,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Create a Valu BNPL (Buy Now, Pay Later) payment session.
    Valu allows customers to split payments over 6-36 months.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    order = db.query(OrderModel).filter(OrderModel.id == body.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if str(order.user_id) != str(user.id):
        raise HTTPException(403, "Order ownership mismatch")

    # Check Valu integration is configured
    valu_integration = pm.get_integration_id("valu")
    if not valu_integration:
        raise HTTPException(503, "Valu BNPL not configured")

    idem = request.headers.get("x-idempotency-key") or request.headers.get("X-Idempotency-Key")
    cents = int(round(float(order.total) * 100))

    # Validate tenor
    valid_tenors = [6, 9, 12, 18, 24, 36]
    if body.tenor not in valid_tenors:
        raise HTTPException(400, f"Invalid tenor. Must be one of: {valid_tenors}")

    # Check for existing payment
    if idem:
        existing = db.query(Payment).filter(Payment.idempotency_key == idem).first()
        if existing and existing.client_payload:
            return ValuPaymentResponse(**existing.client_payload)

    pay = Payment(
        order_id=order.id,
        user_id=str(user.id),
        provider="paymob",
        status=PaymentStatus.processing.value,
        amount_cents=cents,
        currency="egp",
        idempotency_key=idem or f"idem_valu_{uuid.uuid4().hex}",
    )
    db.add(pay)
    db.flush()

    billing = {**(body.billing or {}), "currency": "EGP"}

    try:
        tok = await pm.auth_token()
        reg = await pm.register_order(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            merchant_order_id=order.id,
        )
        paymob_oid = int(reg.get("id"))
        payment_key = await pm.create_payment_key(
            auth_tok=tok,
            amount_cents=cents,
            currency="EGP",
            paymob_order_id=paymob_oid,
            billing=billing,
            payment_method="valu",
        )
    except Exception as e:
        db.rollback()
        logger.exception("Valu payment session failed")
        raise HTTPException(502, f"Valu payment session failed: {e}") from e

    pay.external_payment_id = str(paymob_oid)
    pay.status = PaymentStatus.processing.value

    # Calculate monthly installment (simple division, provider may add fees)
    monthly = cents // body.tenor

    iframe_base = os.getenv("PAYMOB_IFRAME_URL", "https://accept.paymob.com/api/acceptance/iframes")
    iframe_id = os.getenv("PAYMOB_IFRAME_ID_VALU", os.getenv("PAYMOB_IFRAME_ID", "")).strip()
    iframe_url = f"{iframe_base}/{iframe_id}?payment_token={payment_key}" if iframe_id else None

    out = ValuPaymentResponse(
        payment_record_id=pay.id,
        provider="paymob",
        payment_method="valu",
        iframe_token=payment_key,
        paymob_order_id=paymob_oid,
        iframe_url=iframe_url,
        tenor_months=body.tenor,
        monthly_installment_piastres=monthly,
        integration_type="valu",
    )
    pay.client_payload = out.model_dump()
    db.add(
        PaymentEvent(
            payment_id=pay.id,
            event_type="valu_session_created",
            provider_event_fingerprint=f"valu:{paymob_oid}",
            payload={"order_id": paymob_oid, "tenor": body.tenor},
        )
    )
    db.commit()
    return out
