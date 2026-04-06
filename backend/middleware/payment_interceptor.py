"""
Payment API Interceptor Middleware
==================================
Intercepts all outbound HTTP requests to Paymob and PayPal API endpoints.
Environment-gated: only active in development/staging.
Includes performance guardrails to ensure minimal overhead.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from services.debug.payment_log_store import (
    PaymentLogEntry,
    PaymentLogStore,
    get_payment_log_store,
)
from services.debug.structured_logging import get_payment_logger

logger = logging.getLogger(__name__)

# Performance threshold for logging overhead warning (ms)
LOGGING_OVERHEAD_WARNING_THRESHOLD_MS = 10.0

# Sensitive headers to redact (case-insensitive)
SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "api_key", "apikey",
    "x-auth-token", "auth_token", "token", "access_token",
    "client_secret", "secret", "password", "paymob_api_key",
    "paypal_client_secret", "stripe_secret_key", "x-paypal-security",
    "paypal-auth-algo", "paypal-cert-url", "paypal-transmission-id",
}

# Sensitive payload fields to redact (case-insensitive, partial match)
SENSITIVE_PATTERNS = {"token", "secret", "key", "password", "auth", "credential"}


def _is_sensitive_key(key: str) -> bool:
    """Check if a key matches sensitive patterns."""
    key_lower = key.lower().replace("-", "_")
    
    # Exact match for known sensitive headers
    if key_lower in SENSITIVE_HEADERS:
        return True
    
    # Partial match for patterns
    for pattern in SENSITIVE_PATTERNS:
        if pattern in key_lower:
            return True
    
    return False


def _redact_value(value: Any, key: str = "") -> Any:
    """Redact a value if it's sensitive."""
    if key and _is_sensitive_key(key):
        return "***REDACTED***"
    return value


def _redact_dict(d: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """Recursively redact sensitive keys in a dictionary."""
    if depth > 10:  # Prevent infinite recursion
        return d
    
    if not isinstance(d, dict):
        return d
    
    result = {}
    for key, value in d.items():
        key_lower = key.lower().replace("-", "_")
        
        if _is_sensitive_key(key):
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = _redact_dict(value, depth + 1)
        elif isinstance(value, list):
            result[key] = [
                _redact_dict(item, depth + 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive headers."""
    result = {}
    for key, value in headers.items():
        if _is_sensitive_key(key):
            result[key] = "***REDACTED***"
        else:
            result[key] = value
    return result


def _infer_provider(url: str) -> Optional[str]:
    """Infer payment provider from URL."""
    url_lower = url.lower()
    if "paymob" in url_lower or "accept.paymob" in url_lower:
        return "paymob"
    if "paypal" in url_lower:
        return "paypal"
    if "stripe" in url_lower:
        return "stripe"
    return None


def _is_payment_url(url: str) -> bool:
    """Check if URL is a payment provider endpoint."""
    return _infer_provider(url) is not None


def _is_interceptor_enabled() -> bool:
    """Check if the interceptor should be active based on environment."""
    app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    
    # Only active in development and staging
    if app_env in ("development", "dev", "staging", "stage", "test"):
        return True
    
    # Check explicit override
    if os.getenv("DEBUG_PAYMENT_LOGGING", "false").lower() == "true":
        return True
    
    return False


class InterceptedResponse:
    """Wrapper for httpx.Response that logs the request/response cycle."""
    
    def __init__(
        self,
        response: httpx.Response,
        log_entry: PaymentLogEntry,
        store: PaymentLogStore,
    ):
        self._response = response
        self._log_entry = log_entry
        self._store = store
        self._logged = False
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)
    
    def __bool__(self) -> bool:
        return bool(self._response)


class PaymentInterceptorClient:
    """
    HTTP client that intercepts and logs all payment-related requests.
    Use this for all Paymob and PayPal outbound calls.
    
    Features:
    - Environment-gated (no-op in production)
    - Sensitive data redaction
    - Performance guardrails
    - Structured JSON logging
    - SQLite persistence
    """
    
    def __init__(
        self,
        provider: str,
        base_url: str,
        timeout: float = 30.0,
        store: Optional[PaymentLogStore] = None,
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._store = store
        self._client = httpx.AsyncClient(timeout=timeout)
        self._enabled = _is_interceptor_enabled()
        self._structured_logger = get_payment_logger()
    
    @property
    def store(self) -> PaymentLogStore:
        """Get the log store (lazy initialization)."""
        if self._store is None:
            self._store = get_payment_log_store()
        return self._store
    
    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID for this request."""
        return f"{self.provider}-{uuid.uuid4().hex[:12]}"
    
    def _generate_correlation_id(self) -> str:
        """Generate a correlation ID for linking request/response pairs."""
        return uuid.uuid4().hex
    
    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with full interception and logging.
        
        In production, this is a pass-through with zero overhead.
        In development/staging, it logs request/response details.
        """
        # Fast path: production mode - no logging overhead
        if not self._enabled:
            url = f"{self.base_url}{path}"
            return await self._client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                data=data,
                params=params,
                **kwargs,
            )
        
        # Development/staging mode: full interception
        return await self._intercepted_request(
            method, path,
            headers=headers,
            json_data=json_data,
            data=data,
            params=params,
            **kwargs,
        )
    
    async def _intercepted_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with full interception and logging."""
        
        trace_id = self._generate_trace_id()
        correlation_id = self._generate_correlation_id()
        url = f"{self.base_url}{path}"
        
        # Start logging overhead timer
        logging_start = time.perf_counter()
        
        # Prepare request log data
        request_headers = headers or {}
        request_payload = json_data or data
        
        logged_request_headers = _redact_headers(request_headers)
        logged_request_payload = _redact_dict(request_payload) if isinstance(request_payload, dict) else request_payload
        logged_params = _redact_dict(params) if params else None
        
        # Execute request and measure latency
        request_start = time.perf_counter()
        response = None
        error_msg = None
        success = False
        
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                data=data,
                params=params,
                **kwargs,
            )
            success = response.status_code < 400
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[{trace_id}] {self.provider} request failed: {e}")
            raise
        finally:
            # Calculate latencies
            request_latency_ms = (time.perf_counter() - request_start) * 1000
            
            # Prepare response log data
            logged_response_headers = {}
            logged_response_body = None
            
            if response is not None:
                logged_response_headers = dict(response.headers)
                try:
                    logged_response_body = response.json()
                except Exception:
                    text = response.text
                    logged_response_body = text[:2000] if text else None
            
            # Create log entry
            entry = PaymentLogEntry(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                correlation_id=correlation_id,
                provider=self.provider,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_method=method,
                request_url=url,
                request_headers=logged_request_headers,
                request_payload=logged_request_payload,
                request_params=logged_params,
                response_status_code=response.status_code if response else None,
                response_headers=logged_response_headers,
                response_body=logged_response_body,
                latency_ms=round(request_latency_ms, 2),
                success=success,
                error=error_msg,
            )
            
            # Persist to store (async, non-blocking)
            try:
                await self.store.add_entry(entry)
            except Exception as e:
                logger.warning(f"[{trace_id}] Failed to persist log entry: {e}")
            
            # Calculate logging overhead
            logging_overhead_ms = (time.perf_counter() - logging_start) * 1000 - request_latency_ms
            entry.logging_overhead_ms = round(logging_overhead_ms, 2)
            
            # Emit structured log
            self._structured_logger.info(
                f"Payment API request: {method} {path}",
                trace_id=trace_id,
                correlation_id=correlation_id,
                provider=self.provider,
                method=method,
                url=url,
                status_code=response.status_code if response else None,
                latency_ms=round(request_latency_ms, 2),
                logging_overhead_ms=round(logging_overhead_ms, 2),
            )
            
            # Performance guardrail: warn if logging overhead exceeds threshold
            if logging_overhead_ms > LOGGING_OVERHEAD_WARNING_THRESHOLD_MS:
                self._structured_logger.warning(
                    f"Payment logging overhead exceeded threshold: {logging_overhead_ms:.2f}ms > {LOGGING_OVERHEAD_WARNING_THRESHOLD_MS}ms",
                    trace_id=trace_id,
                    provider=self.provider,
                    logging_overhead_ms=round(logging_overhead_ms, 2),
                )
        
        return response
    
    # Convenience methods
    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)
    
    async def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)
    
    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
    
    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self) -> "PaymentInterceptorClient":
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# Factory functions for provider-specific clients
def create_paymob_interceptor_client(
    store: Optional[PaymentLogStore] = None,
) -> PaymentInterceptorClient:
    """Create an interceptor client for Paymob API."""
    base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
    return PaymentInterceptorClient(
        provider="paymob",
        base_url=base_url,
        timeout=30.0,
        store=store,
    )


def create_paypal_interceptor_client(
    store: Optional[PaymentLogStore] = None,
) -> PaymentInterceptorClient:
    """Create an interceptor client for PayPal API."""
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower().strip()
    if mode == "live":
        base_url = "https://api-m.paypal.com"
    else:
        base_url = "https://api-m.sandbox.paypal.com"
    return PaymentInterceptorClient(
        provider="paypal",
        base_url=base_url,
        timeout=45.0,
        store=store,
    )


def create_stripe_interceptor_client(
    store: Optional[PaymentLogStore] = None,
) -> PaymentInterceptorClient:
    """Create an interceptor client for Stripe API."""
    return PaymentInterceptorClient(
        provider="stripe",
        base_url="https://api.stripe.com/v1",
        timeout=30.0,
        store=store,
    )


# Global interceptor clients (lazy-initialized)
_paymob_client: Optional[PaymentInterceptorClient] = None
_paypal_client: Optional[PaymentInterceptorClient] = None


def get_paymob_interceptor_client() -> PaymentInterceptorClient:
    """Get or create the global Paymob interceptor client."""
    global _paymob_client
    if _paymob_client is None:
        _paymob_client = create_paymob_interceptor_client()
    return _paymob_client


def get_paypal_interceptor_client() -> PaymentInterceptorClient:
    """Get or create the global PayPal interceptor client."""
    global _paypal_client
    if _paypal_client is None:
        _paypal_client = create_paypal_interceptor_client()
    return _paypal_client


async def close_interceptor_clients() -> None:
    """Close all global interceptor clients."""
    global _paymob_client, _paypal_client
    
    if _paymob_client:
        await _paymob_client.close()
        _paymob_client = None
    
    if _paypal_client:
        await _paypal_client.close()
        _paypal_client = None
