"""
Paymob Accept API -- real HTTP integration.

Required env:
  PAYMOB_API_KEY -- JWT from Paymob dashboard (Authentication --> API Key).
  PAYMOB_INTEGRATION_ID -- numeric integration id (e.g. card / iframe integration).

Egypt-specific integrations:
  PAYMOB_INTEGRATION_ID_3DS -- integration ID for 3D Secure cards
  PAYMOB_INTEGRATION_ID_MEEZA -- integration ID for Meeza cards
  PAYMOB_INTEGRATION_ID_INSTAPAY -- integration ID for Instapay
  PAYMOB_INTEGRATION_ID_VALU -- integration ID for Valu BNPL

Webhook HMAC (choose one; first non-empty wins):
  PAYMOB_HMAC_SECRET -- HMAC secret shown in dashboard (often a hex string), OR
  PAYMOB_SECRET_KEY -- Egypt Accept "Secret key" (egy_sk_...) if your account uses it for HMAC.

Optional:
  PAYMOB_BASE_URL -- default https://accept.paymob.com/api
  PAYMOB_PUBLIC_KEY -- returned to clients only; not used server-side for payment_keys.
  DEBUG_PAYMENT_LOGGING -- set to "true" to enable request/response logging to debug store.
  APP_ENV / ENVIRONMENT -- controls interceptor activation (dev/staging only).

Currency:
  All amounts in PIASTRES (EGP * 100). Egypt VAT 14% applied before payment intent.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any, Dict, Optional, Literal

import httpx

from services.payment_platform.base import (
    BaseIntegration,
    PaymentProviderError,
    egp_to_piastres,
    piastres_to_egp,
)

logger = logging.getLogger(__name__)


class PaymobProvider(BaseIntegration):
    def __init__(self):
        super().__init__()
        self.integration_id = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
        self.integration_id_3ds = os.getenv("PAYMOB_INTEGRATION_ID_3DS", "").strip()
        self.integration_id_meeza = os.getenv("PAYMOB_INTEGRATION_ID_MEEZA", "").strip()
        self.integration_id_instapay = os.getenv("PAYMOB_INTEGRATION_ID_INSTAPAY", "").strip()
        self.integration_id_valu = os.getenv("PAYMOB_INTEGRATION_ID_VALU", "").strip()

    def _get_interceptor_client(self):
        """Get the Paymob interceptor client (lazy import to avoid circular deps)."""
        from middleware.payment_interceptor import get_paymob_interceptor_client
        return get_paymob_interceptor_client()

    def _is_interceptor_enabled(self) -> bool:
        """Check if payment interceptor is enabled (dev/staging or explicit override)."""
        app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
        if app_env in ("development", "dev", "staging", "stage", "test"):
            return True
        return os.getenv("DEBUG_PAYMENT_LOGGING", "false").lower() == "true"

    def _get_integration_id(self, payment_method: str = "card") -> Optional[int]:
        """
        Get integration ID based on payment method.
        
        Supported methods:
          - card: Default card integration
          - card_3ds: 3D Secure cards
          - meeza: Meeza cards (Egypt local card scheme)
          - instapay: Instapay bank transfers
          - valu: Valu BNPL
        """
        # Map payment methods to env vars
        method_to_env = {
            "card": "PAYMOB_INTEGRATION_ID",
            "card_3ds": "PAYMOB_INTEGRATION_ID_3DS",
            "meeza": "PAYMOB_INTEGRATION_ID_MEEZA",
            "instapay": "PAYMOB_INTEGRATION_ID_INSTAPAY",
            "valu": "PAYMOB_INTEGRATION_ID_VALU",
        }
        
        env_key = method_to_env.get(payment_method, "PAYMOB_INTEGRATION_ID")
        val = os.getenv(env_key, "").strip()
        
        if not val:
            # Fall back to default integration ID
            val = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
        
        if val:
            try:
                return int(val)
            except ValueError:
                logger.warning("Invalid %s value: %s", env_key, val)
        return None

    async def _logged_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        """Make a request with full interception and logging (environment-gated)."""
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        if self._is_interceptor_enabled():
            # Use the new interceptor client with SQLite persistence
            client = self._get_interceptor_client()
            return await client.request(method, path, json_data=json_data, headers=headers if headers else None)
        else:
            # Production: direct pass-through with zero overhead
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self._base()}{path}"
                return await client.request(method, url, json=json_data, headers=headers if headers else None)

    async def auth_token(self) -> str:
        key = os.getenv("PAYMOB_API_KEY", "").strip()
        if not key:
            raise RuntimeError("PAYMOB_API_KEY is not set")
        r = await self._logged_request("POST", "/auth/tokens", json_data={"api_key": key})
        r.raise_for_status()
        data = r.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("Paymob auth: missing token in response")
        return str(token)

    async def register_order(
        self,
        *,
        auth_tok: str,
        amount_cents: int,
        currency: str,
        merchant_order_id: str,
    ) -> Dict[str, Any]:
        payload = {
            "auth_token": auth_tok,
            "delivery_needed": "false",
            "amount_cents": amount_cents,
            "currency": currency.upper(),
            "special_reference": merchant_order_id,
            "merchant_order_id": merchant_order_id,
            "items": [],
        }
        r = await self._logged_request("POST", "/ecommerce/orders", json_data=payload)
        r.raise_for_status()
        return r.json()

    async def create_payment_key(
        self,
        *,
        auth_tok: str,
        amount_cents: int,
        currency: str,
        paymob_order_id: int,
        billing: Dict[str, str],
        payment_method: str = "card",
    ) -> str:
        integration_id = self._get_integration_id(payment_method)
        if not integration_id:
            raise RuntimeError("PAYMOB_INTEGRATION_ID is not set")
        
        payload = {
            "auth_token": auth_tok,
            "amount_cents": amount_cents,
            "expiration": 3600,
            "order_id": paymob_order_id,
            "billing_data": {
                "apartment": billing.get("apartment", "NA"),
                "email": billing.get("email", "na@confit.local"),
                "floor": billing.get("floor", "NA"),
                "first_name": billing.get("first_name", "Customer"),
                "street": billing.get("street", "NA"),
                "building": billing.get("building", "NA"),
                "phone_number": billing.get("phone", "+10000000000"),
                "shipping_method": "PKG",
                "postal_code": billing.get("postal_code", "00000"),
                "city": billing.get("city", "Cairo"),
                "country": billing.get("country", "EG"),
                "last_name": billing.get("last_name", "CONFIT"),
                "state": billing.get("state", "NA"),
            },
            "currency": currency.upper(),
            "integration_id": integration_id,
            "lock_order_when_paid": "false",
        }
        r = await self._logged_request("POST", "/acceptance/payment_keys", json_data=payload)
        r.raise_for_status()
        data = r.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("Paymob payment_keys: missing token")
        return str(token)

    def verify_callback_hmac(self, obj: Dict[str, Any], received_hmac: str) -> bool:
        """
        Verify Paymob transaction-response HMAC (SHA512).
        https://docs.paymob.com/docs/hmac-calculation
        """
        secret = self._hmac_secret_bytes()
        if not secret:
            logger.error("PAYMOB_HMAC_SECRET or PAYMOB_SECRET_KEY not set -- rejecting webhook")
            return False
        # Concatenation order per Paymob Accept docs (transaction object fields)
        ac = str(obj.get("amount_cents", ""))
        created_at = str(obj.get("created_at", ""))
        cur = str(obj.get("currency", ""))
        err_occ = str(obj.get("error_occured", "")).lower()
        has_parent = str(obj.get("has_parent_transaction", "")).lower()
        tid = str(obj.get("id", ""))
        integration_id = str(obj.get("integration_id", ""))
        is_3ds = str(obj.get("is_3d_secure", "")).lower()
        is_auth = str(obj.get("is_auth", "")).lower()
        is_capture = str(obj.get("is_capture", "")).lower()
        is_refunded = str(obj.get("is_refunded", "")).lower()
        is_standalone = str(obj.get("is_standalone_payment", "")).lower()
        is_voided = str(obj.get("is_voided", "")).lower()
        order_obj = obj.get("order") or {}
        order_id = str(order_obj.get("id", ""))
        owner = str(obj.get("owner", ""))
        pending = str(obj.get("pending", "")).lower()
        sd = obj.get("source_data") or {}
        pan = str(sd.get("pan", ""))
        sub_t = str(sd.get("sub_type", ""))
        typ = str(sd.get("type", ""))
        success = str(obj.get("success", "")).lower()
        concat = (
            ac
            + created_at
            + cur
            + err_occ
            + has_parent
            + tid
            + integration_id
            + is_3ds
            + is_auth
            + is_capture
            + is_refunded
            + is_standalone
            + is_voided
            + order_id
            + owner
            + pending
            + pan
            + sub_t
            + typ
            + success
        )
        digest = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
        return hmac.compare_digest(digest, (received_hmac or "").lower())

    def _hmac_secret_bytes(self) -> bytes:
        """Prefer explicit HMAC field; fall back to Egypt secret key if teams use one value."""
        s = os.getenv("PAYMOB_HMAC_SECRET", "").strip()
        if not s:
            s = os.getenv("PAYMOB_SECRET_KEY", "").strip()
        return s.encode("utf-8")

    def _base(self) -> str:
        return os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api").rstrip("/")
    
    # BaseIntegration abstract method implementations
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str = "card",
        idempotency_key: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a Paymob payment charge.
        
        Args:
            amount_piastres: Amount in piastres (EGP * 100)
            customer: Customer details (email, phone, first_name, last_name, etc.)
            order_ref: Unique order reference
            payment_method: One of 'card', 'card_3ds', 'meeza', 'instapay', 'valu'
            idempotency_key: Optional idempotency key for the charge
            
        Returns:
            Dict with charge_id, status, iframe_url, payment_key
        """
        # Currency is always EGP for Egypt payments
        currency = kwargs.get("currency", "EGP")
        
        try:
            tok = await self.auth_token()
            reg = await self.register_order(
                auth_tok=tok,
                amount_cents=amount_piastres,
                currency=currency,
                merchant_order_id=order_ref,
            )
            paymob_oid = int(reg.get("id"))
            payment_key = await self.create_payment_key(
                auth_tok=tok,
                amount_cents=amount_piastres,
                currency=currency,
                paymob_order_id=paymob_oid,
                billing=customer,
                payment_method=payment_method,
            )
        except Exception as e:
            raise PaymentProviderError(
                f"Paymob charge failed: {e}",
                provider="paymob",
                details={"order_ref": order_ref},
            ) from e
        
        iframe_base = os.getenv("PAYMOB_IFRAME_URL", "https://accept.paymob.com/api/acceptance/iframes")
        iframe_id = os.getenv("PAYMOB_IFRAME_ID", "").strip()
        iframe_url = f"{iframe_base}/{iframe_id}?payment_token={payment_key}" if iframe_id else None
        
        return {
            "charge_id": str(paymob_oid),
            "status": "pending",
            "payment_key": payment_key,
            "iframe_url": iframe_url,
            "paymob_order_id": paymob_oid,
            "provider": "paymob",
        }
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Verify Paymob webhook signature.
        
        IMPORTANT: This verifies HMAC on the parsed JSON object, not raw bytes.
        Paymob sends the HMAC in a header (usually 'hmac' or in the callback URL).
        """
        import json
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            logger.error("Paymob webhook: invalid JSON payload")
            return False
        return self.verify_callback_hmac(obj, signature)
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a Paymob transaction.
        
        Note: Paymob refunds require the transaction_id, not order_id.
        """
        tok = await self.auth_token()
        
        payload = {
            "auth_token": tok,
            "transaction_id": int(reference_number),
            "amount_cents": amount_piastres,
        }
        
        r = await self._logged_request(
            "POST",
            "/acceptance/void_refund/refund",
            json_data=payload,
        )
        
        if r.status_code not in (200, 201):
            raise PaymentProviderError(
                f"Paymob refund failed: HTTP {r.status_code}",
                provider="paymob",
                details={"response": r.text},
            )
        
        return r.json()
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """
        Get the status of a Paymob order/charge.
        """
        tok = await self.auth_token()
        
        r = await self._logged_request(
            "GET",
            f"/ecommerce/orders/{charge_id}",
            json_data={"auth_token": tok},
        )
        
        if r.status_code != 200:
            raise PaymentProviderError(
                f"Paymob get_charge_status failed: HTTP {r.status_code}",
                provider="paymob",
                details={"charge_id": charge_id},
            )
        
        return r.json()


# Module-level functions for backwards compatibility
# These delegate to a singleton PaymobProvider instance

_provider = PaymobProvider()


async def auth_token() -> str:
    """Get Paymob auth token (backwards compatible function)."""
    return await _provider.auth_token()


async def register_order(
    *,
    auth_tok: str,
    amount_cents: int,
    currency: str,
    merchant_order_id: str,
) -> Dict[str, Any]:
    """Register order with Paymob (backwards compatible function)."""
    return await _provider.register_order(
        auth_tok=auth_tok,
        amount_cents=amount_cents,
        currency=currency,
        merchant_order_id=merchant_order_id,
    )


async def create_payment_key(
    *,
    auth_tok: str,
    amount_cents: int,
    currency: str,
    paymob_order_id: int,
    billing: Dict[str, str],
    payment_method: str = "card",
) -> str:
    """Create payment key (backwards compatible function)."""
    return await _provider.create_payment_key(
        auth_tok=auth_tok,
        amount_cents=amount_cents,
        currency=currency,
        paymob_order_id=paymob_order_id,
        billing=billing,
        payment_method=payment_method,
    )


def verify_callback_hmac(obj: Dict[str, Any], received_hmac: str) -> bool:
    """Verify HMAC (backwards compatible function)."""
    return _provider.verify_callback_hmac(obj, received_hmac)


def get_integration_id(payment_method: str = "card") -> Optional[int]:
    """Get integration ID for payment method (convenience function)."""
    return _provider._get_integration_id(payment_method)
