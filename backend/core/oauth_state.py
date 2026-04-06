"""
Signed OAuth state (CSRF + provider binding). Use OAUTH_STATE_SECRET in production
(multi-worker safe vs in-memory state).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Optional


def _state_secret() -> bytes:
    s = os.getenv("OAUTH_STATE_SECRET", "").strip() or os.getenv("JWT_SECRET", "").strip()
    if not s:
        return b""
    return s.encode("utf-8")


def oauth_signing_enabled() -> bool:
    return bool(_state_secret())


def sign_oauth_state(payload: dict[str, Any], max_age_seconds: int = 600) -> str:
    """Return opaque state string."""
    data = dict(payload)
    data["exp"] = int(time.time()) + max_age_seconds
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sec = _state_secret()
    if not sec:
        raise RuntimeError("OAUTH_STATE_SECRET or JWT_SECRET required for signed OAuth state")
    sig = hmac.new(sec, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") + "." + base64.urlsafe_b64encode(sig).decode(
        "ascii"
    ).rstrip("=")


def verify_oauth_state(token: str) -> Optional[dict[str, Any]]:
    if not token or "." not in token:
        return None
    sec = _state_secret()
    if not sec:
        return None
    try:
        b64_json, b64_sig = token.split(".", 1)
        pad = lambda s: s + "=" * (-len(s) % 4)
        raw = base64.urlsafe_b64decode(pad(b64_json))
        sig = base64.urlsafe_b64decode(pad(b64_sig))
        expect = hmac.new(sec, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expect, sig):
            return None
        data = json.loads(raw.decode("utf-8"))
        if int(data.get("exp", 0)) < time.time():
            return None
        return data
    except Exception:
        return None
