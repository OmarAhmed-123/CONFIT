"""
PayPal REST v2 (Orders) — sandbox or live via PAYPAL_MODE.
Env: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE=sandbox|live
Webhook verify: PAYPAL_WEBHOOK_ID + POST /v1/notifications/verify-webhook-signature

Optional:
  DEBUG_PAYMENT_LOGGING — set to "true" to enable request/response logging to debug store.
  APP_ENV / ENVIRONMENT — controls interceptor activation (dev/staging only).
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _get_interceptor_client():
    """Get the PayPal interceptor client (lazy import to avoid circular deps)."""
    from middleware.payment_interceptor import get_paypal_interceptor_client
    return get_paypal_interceptor_client()


def _api_root() -> str:
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower().strip()
    if mode == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def _is_interceptor_enabled() -> bool:
    """Check if payment interceptor is enabled (dev/staging or explicit override)."""
    app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if app_env in ("development", "dev", "staging", "stage", "test"):
        return True
    return os.getenv("DEBUG_PAYMENT_LOGGING", "false").lower() == "true"


async def _logged_request(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    """Make a request with full interception and logging (environment-gated)."""
    if _is_interceptor_enabled():
        # Use the new interceptor client with SQLite persistence
        client = _get_interceptor_client()
        return await client.request(
            method, path, headers=headers, json_data=json_data, data=data
        )
    else:
        # Production: direct pass-through with zero overhead
        async with httpx.AsyncClient(timeout=45.0) as client:
            url = f"{_api_root()}{path}"
            return await client.request(
                method, url, headers=headers, json=json_data, data=data
            )


async def _access_token() -> str:
    cid = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    sec = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        raise RuntimeError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set")
    raw = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    r = await _logged_request(
        "POST",
        "/v1/oauth2/token",
        headers={"Authorization": f"Basic {raw}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError("PayPal OAuth: no access_token")
    return str(tok)


async def create_order(
    *,
    amount_value: str,
    currency: str,
    merchant_ref: str,
    return_url: str,
    cancel_url: str,
) -> Dict[str, Any]:
    tok = await _access_token()
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": merchant_ref,
                "amount": {"currency_code": currency.upper(), "value": amount_value},
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }
    r = await _logged_request(
        "POST",
        "/v2/checkout/orders",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json_data=body,
    )
    r.raise_for_status()
    return r.json()


def extract_approve_link(order_json: Dict[str, Any]) -> Optional[str]:
    for link in order_json.get("links") or []:
        if link.get("rel") == "approve":
            return str(link.get("href"))
    return None


async def capture_order(paypal_order_id: str) -> Dict[str, Any]:
    tok = await _access_token()
    r = await _logged_request(
        "POST",
        f"/v2/checkout/orders/{paypal_order_id}/capture",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    r.raise_for_status()
    return r.json()


async def verify_webhook_signature(headers: Dict[str, str], body: Dict[str, Any]) -> bool:
    wid = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    if not wid:
        logger.error("PAYPAL_WEBHOOK_ID not set")
        return False
    tok = await _access_token()
    verify_body = {
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "webhook_id": wid,
        "webhook_event": body,
    }
    r = await _logged_request(
        "POST",
        "/v1/notifications/verify-webhook-signature",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json_data=verify_body,
    )
    if r.status_code != 200:
        logger.warning("PayPal verify webhook HTTP %s", r.status_code)
        return False
    data = r.json()
    return data.get("verification_status") == "SUCCESS"
