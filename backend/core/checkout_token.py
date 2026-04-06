"""
HMAC-signed checkout tokens so guest (or cookieless) clients can complete
unified payment without a JWT, without exposing arbitrary order access.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time


def _secret() -> bytes:
    s = os.getenv("CHECKOUT_HMAC_SECRET", "").strip()
    if not s:
        s = os.getenv("JWT_SECRET", "").strip()
    if not s:
        raise RuntimeError("CHECKOUT_HMAC_SECRET or JWT_SECRET must be set for checkout tokens")
    return s.encode("utf-8")


def mint_checkout_token(order_id: str, ttl_seconds: int = 7200) -> str:
    """Short-lived token bound to order_id (include in X-Checkout-Token)."""
    exp = int(time.time()) + max(300, ttl_seconds)
    body = f"{order_id}:{exp}"
    sig = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    b64 = base64.urlsafe_b64encode(body.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{b64}.{sig}"


def verify_checkout_token(order_id: str, token: str) -> bool:
    if not token or not order_id:
        return False
    try:
        b64_part, sig = token.rsplit(".", 1)
        pad = "=" * (-len(b64_part) % 4)
        body = base64.urlsafe_b64decode(b64_part + pad).decode("utf-8")
        oid, exp_s = body.split(":", 1)
        if oid != order_id:
            return False
        if int(exp_s) < time.time():
            return False
        expect = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expect, sig)
    except Exception:
        return False
