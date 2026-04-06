"""
Payment API Request/Response Logger
===================================
Intercepts and logs all outbound API calls to Paymob and PayPal.
Uses an in-memory ring buffer with configurable max size.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)

# Sensitive headers/fields to redact
SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "api_key", "apikey",
    "x-auth-token", "auth_token", "token", "access_token",
    "client_secret", "secret", "password", "paymob_api_key",
    "paypal_client_secret", "stripe_secret_key"
}

SENSITIVE_PAYLOAD_FIELDS = {
    "api_key", "apiToken", "auth_token", "authToken",
    "client_secret", "secret", "password", "card_number",
    "cvv", "cvc", "card_number", "cardNumber"
}


def _redact_dict(d: Dict[str, Any], sensitive_keys: set) -> Dict[str, Any]:
    """Recursively redact sensitive keys in a dictionary."""
    if not isinstance(d, dict):
        return d
    
    result = {}
    for key, value in d.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower in sensitive_keys or key in sensitive_keys:
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = _redact_dict(value, sensitive_keys)
        elif isinstance(value, list):
            result[key] = [
                _redact_dict(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


@dataclass
class PaymentLogEntry:
    """A single payment API request/response log entry."""
    trace_id: str
    provider: str  # "paymob" or "paypal"
    timestamp: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    latency_ms: float
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaymentLogStore:
    """
    In-memory ring buffer for payment logs.
    Thread-safe for single-process usage.
    """
    
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._by_trace_id: Dict[str, PaymentLogEntry] = {}
    
    def add(self, entry: PaymentLogEntry) -> None:
        """Add a log entry, evicting oldest if at capacity."""
        if len(self._buffer) == self.max_size:
            # Evict oldest
            oldest = self._buffer[0]
            self._by_trace_id.pop(oldest.trace_id, None)
        
        self._buffer.append(entry)
        self._by_trace_id[entry.trace_id] = entry
    
    def get_all(self, limit: int = 100, provider: Optional[str] = None) -> List[PaymentLogEntry]:
        """Get recent logs, optionally filtered by provider."""
        entries = list(self._buffer)
        if provider:
            entries = [e for e in entries if e.provider == provider]
        return entries[-limit:][::-1]  # Most recent first
    
    def get_by_trace_id(self, trace_id: str) -> Optional[PaymentLogEntry]:
        """Get a specific log entry by trace ID."""
        return self._by_trace_id.get(trace_id)
    
    def get_failed(self, limit: int = 50) -> List[PaymentLogEntry]:
        """Get failed requests for replay."""
        return [e for e in self._buffer if not e.success][-limit:][::-1]
    
    def clear(self) -> None:
        """Clear all logs."""
        self._buffer.clear()
        self._by_trace_id.clear()
    
    @property
    def count(self) -> int:
        return len(self._buffer)


# Global store instance
_payment_log_store: Optional[PaymentLogStore] = None


def get_payment_log_store() -> PaymentLogStore:
    """Get or create the global payment log store."""
    global _payment_log_store
    if _payment_log_store is None:
        max_size = int(os.getenv("DEBUG_LOG_MAX_SIZE", "500"))
        _payment_log_store = PaymentLogStore(max_size=max_size)
    return _payment_log_store


class PaymentLoggingClient:
    """
    HTTP client wrapper that logs all payment-related requests.
    Use this instead of raw httpx.AsyncClient for payment API calls.
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
        self._store = store or get_payment_log_store()
        self._client = httpx.AsyncClient(timeout=timeout)
    
    def _generate_trace_id(self) -> str:
        return f"{self.provider}-{uuid.uuid4().hex[:12]}"
    
    def _redact_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Redact sensitive headers."""
        result = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                result[key] = "***REDACTED***"
            else:
                result[key] = value
        return result
    
    def _redact_payload(self, payload: Any) -> Any:
        """Redact sensitive fields in payload."""
        if isinstance(payload, dict):
            return _redact_dict(payload, SENSITIVE_PAYLOAD_FIELDS)
        return payload
    
    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make a request and log it."""
        trace_id = self._generate_trace_id()
        url = f"{self.base_url}{path}"
        
        # Prepare request log
        request_headers = headers or {}
        request_payload = json_data or data
        
        logged_request = {
            "method": method,
            "url": url,
            "headers": self._redact_headers(request_headers),
            "payload": self._redact_payload(request_payload) if request_payload else None,
            "params": params,
        }
        
        start_time = time.perf_counter()
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
            )
            success = response.status_code < 400
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"[{trace_id}] {self.provider} request failed: {e}")
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Prepare response log
            logged_response = {
                "status_code": response.status_code if response else None,
                "headers": dict(response.headers) if response else {},
                "body": None,
            }
            
            if response is not None:
                try:
                    # Try to parse as JSON
                    logged_response["body"] = response.json()
                except Exception:
                    # Fallback to text (truncated)
                    text = response.text
                    logged_response["body"] = text[:1000] if text else None
            
            # Create log entry
            entry = PaymentLogEntry(
                trace_id=trace_id,
                provider=self.provider,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request=logged_request,
                response=logged_response,
                latency_ms=round(latency_ms, 2),
                success=success,
                error=error_msg,
            )
            
            self._store.add(entry)
            logger.info(
                f"[{trace_id}] {self.provider} {method} {path} "
                f"-> {response.status_code if response else 'ERROR'} ({latency_ms:.1f}ms)"
            )
        
        return response
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
    
    async def close(self) -> None:
        await self._client.aclose()
    
    async def __aenter__(self) -> "PaymentLoggingClient":
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.close()


# Provider-specific client factories
def create_paymob_logging_client() -> PaymentLoggingClient:
    """Create a logging client for Paymob API."""
    base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
    return PaymentLoggingClient(provider="paymob", base_url=base_url, timeout=30.0)


def create_paypal_logging_client() -> PaymentLoggingClient:
    """Create a logging client for PayPal API."""
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower().strip()
    if mode == "live":
        base_url = "https://api-m.paypal.com"
    else:
        base_url = "https://api-m.sandbox.paypal.com"
    return PaymentLoggingClient(provider="paypal", base_url=base_url, timeout=45.0)
