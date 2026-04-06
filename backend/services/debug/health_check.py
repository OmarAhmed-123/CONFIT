"""
Health Check Service for Payment Providers
==========================================
Scheduled health checks for Paymob and PayPal with predictive alerting.
Runs synthetic test scenarios and produces structured results.
"""

from __future__ import annotations

import base64
import logging
import os
import socket
import ssl
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK RESULT MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    provider: str
    check_name: str
    status: str  # "pass", "fail", "warn"
    latency_ms: float
    message: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderHealthSnapshot:
    """Aggregated health snapshot for a provider."""
    overall: str  # "healthy", "degraded", "down"
    checks: Dict[str, str]  # check_name -> status
    last_checked: str
    latency_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# PAYMOB HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────

async def check_paymob_api_key() -> HealthCheckResult:
    """Validate Paymob API key by requesting auth token."""
    start = time.perf_counter()
    api_key = os.getenv("PAYMOB_API_KEY", "").strip()
    
    if not api_key:
        return HealthCheckResult(
            provider="paymob",
            check_name="api_key",
            status="fail",
            latency_ms=0,
            message="PAYMOB_API_KEY not set",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{base_url}/auth/tokens",
                json={"api_key": api_key},
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                data = r.json()
                token = data.get("token")
                if token:
                    return HealthCheckResult(
                        provider="paymob",
                        check_name="api_key",
                        status="pass",
                        latency_ms=round(latency_ms, 2),
                        message="Authentication successful",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details={"token_preview": f"{token[:10]}..."},
                    )
            
            return HealthCheckResult(
                provider="paymob",
                check_name="api_key",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paymob",
            check_name="api_key",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paymob_order_registration(auth_token: str) -> HealthCheckResult:
    """Submit a synthetic order and validate response schema."""
    start = time.perf_counter()
    base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            order_payload = {
                "auth_token": auth_token,
                "delivery_needed": "false",
                "amount_cents": 100,  # Minimal test amount
                "currency": "EGP",
                "merchant_order_id": f"health-check-{uuid.uuid4().hex[:8]}",
                "items": [],
            }
            
            r = await client.post(f"{base_url}/ecommerce/orders", json=order_payload)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code in (200, 201):
                data = r.json()
                order_id = data.get("id")
                if order_id:
                    return HealthCheckResult(
                        provider="paymob",
                        check_name="order_registration",
                        status="pass",
                        latency_ms=round(latency_ms, 2),
                        message=f"Order registered: {order_id}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details={"order_id": order_id},
                    )
                return HealthCheckResult(
                    provider="paymob",
                    check_name="order_registration",
                    status="fail",
                    latency_ms=round(latency_ms, 2),
                    message="No order ID in response",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            return HealthCheckResult(
                provider="paymob",
                check_name="order_registration",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paymob",
            check_name="order_registration",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paymob_payment_key(auth_token: str, order_id: int) -> HealthCheckResult:
    """Generate payment key and validate iframe URL can be constructed."""
    start = time.perf_counter()
    integration_id = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
    iframe_id = os.getenv("PAYMOB_IFRAME_ID", "").strip()
    base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
    
    if not integration_id:
        return HealthCheckResult(
            provider="paymob",
            check_name="payment_key",
            status="fail",
            latency_ms=0,
            message="PAYMOB_INTEGRATION_ID not set",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            pk_payload = {
                "auth_token": auth_token,
                "amount_cents": 100,
                "expiration": 3600,
                "order_id": order_id,
                "billing_data": {
                    "apartment": "NA",
                    "email": "health-check@confit.local",
                    "floor": "NA",
                    "first_name": "HealthCheck",
                    "street": "NA",
                    "building": "NA",
                    "phone_number": "+10000000000",
                    "shipping_method": "PKG",
                    "postal_code": "00000",
                    "city": "Cairo",
                    "country": "EG",
                    "last_name": "CONFIT",
                    "state": "NA",
                },
                "currency": "EGP",
                "integration_id": int(integration_id),
                "lock_order_when_paid": "false",
            }
            
            r = await client.post(f"{base_url}/acceptance/payment_keys", json=pk_payload)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                data = r.json()
                pk_token = data.get("token")
                if pk_token:
                    iframe_url = f"https://accept.paymob.com/api/acceptance/iframes/{iframe_id}?payment_token={pk_token}" if iframe_id else None
                    return HealthCheckResult(
                        provider="paymob",
                        check_name="payment_key",
                        status="pass",
                        latency_ms=round(latency_ms, 2),
                        message="Payment key generated",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details={
                            "key_preview": f"{pk_token[:20]}...",
                            "iframe_url": iframe_url,
                        },
                    )
                return HealthCheckResult(
                    provider="paymob",
                    check_name="payment_key",
                    status="fail",
                    latency_ms=round(latency_ms, 2),
                    message="No token in payment_key response",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            return HealthCheckResult(
                provider="paymob",
                check_name="payment_key",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paymob",
            check_name="payment_key",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paymob_iframe_rendering(iframe_url: Optional[str]) -> HealthCheckResult:
    """Perform HTTP GET on iframe URL and assert 200 with expected HTML."""
    start = time.perf_counter()
    
    if not iframe_url:
        return HealthCheckResult(
            provider="paymob",
            check_name="iframe",
            status="warn",
            latency_ms=0,
            message="PAYMOB_IFRAME_ID not configured - skipping iframe check",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(iframe_url)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                # Check if response contains expected HTML content
                content = r.text
                if "<!DOCTYPE html" in content or "<html" in content.lower():
                    return HealthCheckResult(
                        provider="paymob",
                        check_name="iframe",
                        status="pass",
                        latency_ms=round(latency_ms, 2),
                        message="Iframe renders correctly",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details={"content_length": len(content)},
                    )
                return HealthCheckResult(
                    provider="paymob",
                    check_name="iframe",
                    status="warn",
                    latency_ms=round(latency_ms, 2),
                    message="Iframe returned 200 but content may not be valid HTML",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            
            return HealthCheckResult(
                provider="paymob",
                check_name="iframe",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paymob",
            check_name="iframe",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paymob_cors_preflight() -> HealthCheckResult:
    """Send OPTIONS request to Paymob endpoints and validate CORS headers."""
    start = time.perf_counter()
    base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test CORS preflight on auth endpoint
            r = await client.options(
                f"{base_url}/auth/tokens",
                headers={
                    "Origin": os.getenv("FRONTEND_URL", "http://localhost:5173"),
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            # Check for CORS headers in response
            allow_origin = r.headers.get("Access-Control-Allow-Origin", "")
            allow_methods = r.headers.get("Access-Control-Allow-Methods", "")
            
            if allow_origin:
                return HealthCheckResult(
                    provider="paymob",
                    check_name="cors",
                    status="pass",
                    latency_ms=round(latency_ms, 2),
                    message=f"CORS configured: Allow-Origin={allow_origin}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    details={
                        "allow_origin": allow_origin,
                        "allow_methods": allow_methods,
                    },
                )
            
            # No CORS headers - this is expected for external APIs (they handle CORS on their end)
            return HealthCheckResult(
                provider="paymob",
                check_name="cors",
                status="warn",
                latency_ms=round(latency_ms, 2),
                message="No CORS headers returned - external API handles CORS client-side",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paymob",
            check_name="cors",
            status="warn",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def run_paymob_health_checks() -> List[HealthCheckResult]:
    """Run all Paymob health checks in sequence (some depend on previous results)."""
    results: List[HealthCheckResult] = []
    
    # 1. API Key validation
    api_key_result = await check_paymob_api_key()
    results.append(api_key_result)
    
    # If API key failed, skip remaining checks
    if api_key_result.status != "pass":
        results.append(HealthCheckResult(
            provider="paymob",
            check_name="order_registration",
            status="skip",
            latency_ms=0,
            message="Skipped: API key check failed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        results.append(HealthCheckResult(
            provider="paymob",
            check_name="payment_key",
            status="skip",
            latency_ms=0,
            message="Skipped: API key check failed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        results.append(HealthCheckResult(
            provider="paymob",
            check_name="iframe",
            status="skip",
            latency_ms=0,
            message="Skipped: API key check failed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        results.append(await check_paymob_cors_preflight())
        return results
    
    # Get auth token for subsequent checks
    auth_token = api_key_result.details.get("token_preview", "")
    
    # Re-auth to get actual token
    try:
        base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{base_url}/auth/tokens",
                json={"api_key": os.getenv("PAYMOB_API_KEY", "").strip()},
            )
            auth_token = r.json().get("token", "")
    except Exception:
        pass
    
    # 2. Order registration
    order_result = await check_paymob_order_registration(auth_token)
    results.append(order_result)
    
    # 3. Payment key generation
    iframe_url = None
    if order_result.status == "pass" and auth_token:
        order_id = order_result.details.get("order_id")
        if order_id:
            pk_result = await check_paymob_payment_key(auth_token, order_id)
            results.append(pk_result)
            iframe_url = pk_result.details.get("iframe_url")
        else:
            results.append(HealthCheckResult(
                provider="paymob",
                check_name="payment_key",
                status="skip",
                latency_ms=0,
                message="Skipped: No order ID from registration",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
    else:
        results.append(HealthCheckResult(
            provider="paymob",
            check_name="payment_key",
            status="skip",
            latency_ms=0,
            message="Skipped: Order registration failed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
    
    # 4. Iframe rendering
    iframe_result = await check_paymob_iframe_rendering(iframe_url)
    results.append(iframe_result)
    
    # 5. CORS preflight
    cors_result = await check_paymob_cors_preflight()
    results.append(cors_result)
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# PAYPAL HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────

async def check_paypal_oauth() -> HealthCheckResult:
    """Validate PayPal credentials by requesting access token."""
    start = time.perf_counter()
    client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    
    if not client_id or not client_secret:
        return HealthCheckResult(
            provider="paypal",
            check_name="oauth",
            status="fail",
            latency_ms=0,
            message="PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET not set",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
        base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        
        raw = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{base_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {raw}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            # Check for rate limit headers
            rate_limit_remaining = r.headers.get("X-RateLimit-Remaining")
            rate_limit_reset = r.headers.get("X-RateLimit-Reset")
            
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                if token:
                    details = {"token_preview": f"{token[:20]}...", "mode": mode}
                    if rate_limit_remaining:
                        details["rate_limit_remaining"] = rate_limit_remaining
                    if rate_limit_reset:
                        details["rate_limit_reset"] = rate_limit_reset
                    
                    return HealthCheckResult(
                        provider="paypal",
                        check_name="oauth",
                        status="pass",
                        latency_ms=round(latency_ms, 2),
                        message=f"OAuth successful ({mode} mode)",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details=details,
                    )
            
            return HealthCheckResult(
                provider="paypal",
                check_name="oauth",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paypal",
            check_name="oauth",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paypal_order_creation(access_token: str) -> HealthCheckResult:
    """Create a test order via PayPal API and validate response."""
    start = time.perf_counter()
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
    base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            order_payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": f"health-check-{uuid.uuid4().hex[:8]}",
                        "amount": {"currency_code": "USD", "value": "1.00"},
                    }
                ],
                "application_context": {
                    "return_url": "http://localhost:5173/debug/payments",
                    "cancel_url": "http://localhost:5173/debug/payments",
                    "user_action": "PAY_NOW",
                },
            }
            
            r = await client.post(
                f"{base_url}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=order_payload,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 201:
                data = r.json()
                order_id = data.get("id")
                approve_link = None
                for link in data.get("links", []):
                    if link.get("rel") == "approve":
                        approve_link = link.get("href")
                
                return HealthCheckResult(
                    provider="paypal",
                    check_name="order_creation",
                    status="pass",
                    latency_ms=round(latency_ms, 2),
                    message=f"Order created: {order_id}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    details={"order_id": order_id, "approve_link": approve_link},
                )
            
            return HealthCheckResult(
                provider="paypal",
                check_name="order_creation",
                status="fail",
                latency_ms=round(latency_ms, 2),
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paypal",
            check_name="order_creation",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_paypal_ssl_certificate() -> HealthCheckResult:
    """Verify TLS certificate for PayPal API is valid and not near expiration."""
    start = time.perf_counter()
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
    hostname = "api.paypal.com" if mode == "live" else "api.sandbox.paypal.com"
    
    try:
        context = ssl.create_default_context()
        
        # Set timeout for SSL check
        sock = socket.create_connection((hostname, 443), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=hostname)
        
        cert = ssock.getpeercert()
        ssock.close()
        
        # Parse expiration date
        expiry_str = cert.get("notAfter", "")
        if expiry_str:
            # Parse the date format: "May 25 23:59:59 2025 GMT"
            from datetime import datetime
            expiry_date = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            
            days_remaining = (expiry_date - datetime.now(timezone.utc)).days
            latency_ms = (time.perf_counter() - start) * 1000
            
            if days_remaining <= 7:
                return HealthCheckResult(
                    provider="paypal",
                    check_name="ssl_cert",
                    status="fail",
                    latency_ms=round(latency_ms, 2),
                    message=f"SSL certificate expires in {days_remaining} days (CRITICAL)",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    details={
                        "expiry_date": expiry_str,
                        "days_remaining": days_remaining,
                    },
                )
            elif days_remaining <= 30:
                return HealthCheckResult(
                    provider="paypal",
                    check_name="ssl_cert",
                    status="warn",
                    latency_ms=round(latency_ms, 2),
                    message=f"SSL certificate expires in {days_remaining} days",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    details={
                        "expiry_date": expiry_str,
                        "days_remaining": days_remaining,
                    },
                )
            
            return HealthCheckResult(
                provider="paypal",
                check_name="ssl_cert",
                status="pass",
                latency_ms=round(latency_ms, 2),
                message=f"SSL certificate valid for {days_remaining} more days",
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={
                    "expiry_date": expiry_str,
                    "days_remaining": days_remaining,
                },
            )
        
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paypal",
            check_name="ssl_cert",
            status="warn",
            latency_ms=round(latency_ms, 2),
            message="Could not determine certificate expiry",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            provider="paypal",
            check_name="ssl_cert",
            status="fail",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def run_paypal_health_checks() -> List[HealthCheckResult]:
    """Run all PayPal health checks in sequence."""
    results: List[HealthCheckResult] = []
    
    # 1. OAuth validation
    oauth_result = await check_paypal_oauth()
    results.append(oauth_result)
    
    # 2. Order creation (if OAuth passed)
    access_token = None
    if oauth_result.status == "pass":
        # Re-auth to get actual token
        try:
            mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
            base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
            client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
            client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
            raw = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{base_url}/v1/oauth2/token",
                    headers={
                        "Authorization": f"Basic {raw}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                )
                access_token = r.json().get("access_token")
        except Exception:
            pass
        
        if access_token:
            order_result = await check_paypal_order_creation(access_token)
            results.append(order_result)
        else:
            results.append(HealthCheckResult(
                provider="paypal",
                check_name="order_creation",
                status="skip",
                latency_ms=0,
                message="Skipped: Could not get access token",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
    else:
        results.append(HealthCheckResult(
            provider="paypal",
            check_name="order_creation",
            status="skip",
            latency_ms=0,
            message="Skipped: OAuth check failed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
    
    # 3. SSL certificate check (independent)
    ssl_result = await check_paypal_ssl_certificate()
    results.append(ssl_result)
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTIVE ALERTS
# ─────────────────────────────────────────────────────────────────────────────

async def check_api_key_expiry() -> List[HealthCheckResult]:
    """Check if API keys have known expiry dates and warn accordingly."""
    results: List[HealthCheckResult] = []
    now = datetime.now(timezone.utc)
    
    # Paymob key expiry
    paymob_expiry = os.getenv("PAYMOB_KEY_EXPIRES_AT", "").strip()
    if paymob_expiry:
        try:
            expiry_date = datetime.fromisoformat(paymob_expiry.replace("Z", "+00:00"))
            days_remaining = (expiry_date - now).days
            
            if days_remaining <= 3:
                results.append(HealthCheckResult(
                    provider="paymob",
                    check_name="api_key_expiry",
                    status="fail",
                    latency_ms=0,
                    message=f"Paymob API key expires in {days_remaining} days (CRITICAL)",
                    timestamp=now.isoformat(),
                    details={"expiry_date": paymob_expiry, "days_remaining": days_remaining},
                ))
            elif days_remaining <= 14:
                results.append(HealthCheckResult(
                    provider="paymob",
                    check_name="api_key_expiry",
                    status="warn",
                    latency_ms=0,
                    message=f"Paymob API key expires in {days_remaining} days",
                    timestamp=now.isoformat(),
                    details={"expiry_date": paymob_expiry, "days_remaining": days_remaining},
                ))
        except Exception as e:
            logger.warning(f"Could not parse PAYMOB_KEY_EXPIRES_AT: {e}")
    
    # PayPal key expiry
    paypal_expiry = os.getenv("PAYPAL_KEY_EXPIRES_AT", "").strip()
    if paypal_expiry:
        try:
            expiry_date = datetime.fromisoformat(paypal_expiry.replace("Z", "+00:00"))
            days_remaining = (expiry_date - now).days
            
            if days_remaining <= 3:
                results.append(HealthCheckResult(
                    provider="paypal",
                    check_name="api_key_expiry",
                    status="fail",
                    latency_ms=0,
                    message=f"PayPal credentials expire in {days_remaining} days (CRITICAL)",
                    timestamp=now.isoformat(),
                    details={"expiry_date": paypal_expiry, "days_remaining": days_remaining},
                ))
            elif days_remaining <= 14:
                results.append(HealthCheckResult(
                    provider="paypal",
                    check_name="api_key_expiry",
                    status="warn",
                    latency_ms=0,
                    message=f"PayPal credentials expire in {days_remaining} days",
                    timestamp=now.isoformat(),
                    details={"expiry_date": paypal_expiry, "days_remaining": days_remaining},
                ))
        except Exception as e:
            logger.warning(f"Could not parse PAYPAL_KEY_EXPIRES_AT: {e}")
    
    return results


def check_rate_limit_approach(result: HealthCheckResult) -> Optional[HealthCheckResult]:
    """Check if a health check result indicates rate limit approach."""
    if result.check_name == "oauth" and result.details:
        rate_limit_remaining = result.details.get("rate_limit_remaining")
        rate_limit_reset = result.details.get("rate_limit_reset")
        
        if rate_limit_remaining is not None:
            try:
                remaining = int(rate_limit_remaining)
                # Assume typical limit is around 500 requests/hour
                if remaining < 100:  # Less than 20% remaining
                    return HealthCheckResult(
                        provider=result.provider,
                        check_name="rate_limit",
                        status="warn",
                        latency_ms=0,
                        message=f"Rate limit approaching: {remaining} requests remaining",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        details={
                            "remaining": remaining,
                            "reset": rate_limit_reset,
                        },
                    )
            except (ValueError, TypeError):
                pass
    
    return None


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_overall_status(checks: Dict[str, str]) -> str:
    """Compute overall status from individual check statuses."""
    if not checks:
        return "down"
    
    if any(s == "fail" for s in checks.values()):
        return "down"
    if any(s == "warn" for s in checks.values()):
        return "degraded"
    return "healthy"


async def run_all_health_checks() -> Dict[str, List[HealthCheckResult]]:
    """Run all health checks for both providers and return results."""
    paymob_results = await run_paymob_health_checks()
    paypal_results = await run_paypal_health_checks()
    expiry_results = await check_api_key_expiry()
    
    # Check for rate limit warnings
    rate_limit_warnings = []
    for result in paypal_results:
        rate_limit_warn = check_rate_limit_approach(result)
        if rate_limit_warn:
            rate_limit_warnings.append(rate_limit_warn)
    
    return {
        "paymob": paymob_results,
        "paypal": paypal_results + expiry_results + rate_limit_warnings,
    }
