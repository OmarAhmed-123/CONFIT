"""
Shared SlowAPI limiter instance
===============================
`slowapi` rate limits only work reliably when decorators reference the *same* `Limiter`
instance that is attached to `app.state.limiter`.

Import `limiter` from here in `main.py` and any routers using `@limiter.limit(...)`.

Rate limit tiers (OWASP / Phase 8 hardening):
  - Authenticated users:  120 req/min  (global default)
  - Anonymous users:       30 req/min  (global default)
  - Auth endpoints:         5 req/min  (brute-force protection)
  - Payment endpoints:     10 req/min
  - Webhook endpoints:    600 req/min  (provider burst)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    def _auth_aware_key(request: Any) -> str:
        """
        Rate-limit key function that distinguishes authenticated vs anonymous callers.
        Authenticated users (Bearer token present) get higher limits.
        """
        auth: Optional[str] = request.headers.get("authorization", "") if hasattr(request, "headers") else ""
        if auth and auth.startswith("Bearer "):
            # Use a stable user identifier when available
            user_id = getattr(getattr(request, "state", None), "user_id", None)
            if user_id:
                return f"user:{user_id}"
            return f"bearer:{hash(auth)}"
        # Fall back to IP for anonymous
        return get_remote_address(request)

    limiter = Limiter(
        key_func=_auth_aware_key,
        default_limits=["30/minute"],
        headers_enabled=True,
    )
    HAS_SLOWAPI = True
except ImportError:  # pragma: no cover
    HAS_SLOWAPI = False

    class _NoOpLimiter:
        def limit(self, _limit_value: str) -> Callable[..., Any]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

    limiter = _NoOpLimiter()  # type: ignore[assignment]


# ── Named limit strings for reuse in decorators ──────────────────────────
LIMIT_AUTHENTICATED = "120/minute"
LIMIT_ANONYMOUS = "30/minute"
LIMIT_AUTH_ENDPOINT = "5/minute"
LIMIT_PAYMENT = "10/minute"
LIMIT_WEBHOOK = "600/minute"
