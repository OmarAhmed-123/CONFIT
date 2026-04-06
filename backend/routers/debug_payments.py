"""
Debug Endpoints for Payment Integration
=======================================
Provides visibility into payment flows via /debug/* endpoints.
Only accessible in development or staging environments.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import settings
from services.debug.payment_logger import (
    get_payment_log_store,
    PaymentLogEntry,
    PaymentLoggingClient,
    create_paymob_logging_client,
    create_paypal_logging_client,
)
from services.debug.health_check import (
    run_all_health_checks,
    HealthCheckResult,
    compute_overall_status,
    ProviderHealthSnapshot,
)
from services.debug.health_store import (
    get_health_store,
    HealthHistoryEntry,
    AlertEntry,
)
from services.debug.health_scheduler import (
    get_health_snapshot,
    trigger_health_check,
    start_scheduler,
    stop_scheduler,
    is_scheduler_running,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug — Payments"])


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT GUARD
# ─────────────────────────────────────────────────────────────────────────────

def _check_debug_access() -> None:
    """Raise 403 if not in development or staging."""
    env = settings.ENVIRONMENT.lower()
    if env not in ("development", "dev", "staging", "test"):
        raise HTTPException(
            status_code=403,
            detail=f"Debug endpoints disabled in '{env}' environment"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ClientErrorReport(BaseModel):
    """Client-side error report from React Error Boundary."""
    error_type: str = Field(..., description="Error type (render, iframe, sdk, dom)")
    message: str
    stack: Optional[str] = None
    component_stack: Optional[str] = None
    url: str
    line: Optional[int] = None
    column: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[Dict[str, Any]] = None


class EnvCheckResult(BaseModel):
    """Result of environment variable validation."""
    variable: str
    present: bool
    valid_format: bool
    value_preview: Optional[str] = None  # First/last 4 chars only
    error: Optional[str] = None


class APIKeyValidation(BaseModel):
    """API key validation result."""
    provider: str
    key_type: str
    status: str  # "valid", "invalid", "missing", "error"
    message: Optional[str] = None
    last_checked: str


class ReplayRequest(BaseModel):
    """Request to replay a failed payment call."""
    trace_id: str
    modifications: Optional[Dict[str, Any]] = None  # Headers/payload overrides


class TestScenarioResult(BaseModel):
    """Result of a test scenario step."""
    step: str
    status: str  # "pass", "fail", "skip"
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY STORES
# ─────────────────────────────────────────────────────────────────────────────

# Client error store (ring buffer)
_client_errors: List[Dict[str, Any]] = []
_MAX_CLIENT_ERRORS = 200

# Performance metrics store
_perf_metrics: Dict[str, List[Dict[str, Any]]] = {
    "iframe_load": [],
    "sdk_init": [],
    "tti": [],  # Time to interactive
}
_MAX_PERF_METRICS = 100

# CORS/SSL issues store
_cors_ssl_issues: List[Dict[str, Any]] = []
_MAX_CORS_SSL_ISSUES = 50


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: LOGS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_payment_logs(
    limit: int = 50,
    provider: Optional[str] = None,
    failures_only: bool = False,
):
    """Get recent payment API logs."""
    _check_debug_access()
    store = get_payment_log_store()
    
    if failures_only:
        entries = store.get_failed(limit=limit)
    else:
        entries = store.get_all(limit=limit, provider=provider)
    
    return {
        "count": len(entries),
        "total_stored": store.count,
        "logs": [e.to_dict() for e in entries],
    }


@router.get("/logs/{trace_id}")
async def get_payment_log_by_trace(trace_id: str):
    """Get a specific log entry by trace ID."""
    _check_debug_access()
    store = get_payment_log_store()
    entry = store.get_by_trace_id(trace_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return entry.to_dict()


@router.delete("/logs")
async def clear_payment_logs():
    """Clear all stored payment logs."""
    _check_debug_access()
    store = get_payment_log_store()
    store.clear()
    return {"success": True, "message": "Logs cleared"}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: CLIENT ERRORS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/client-errors")
async def report_client_error(report: ClientErrorReport):
    """Receive client-side error reports from React Error Boundary."""
    _check_debug_access()
    
    error_record = {
        "id": f"err-{uuid.uuid4().hex[:8]}",
        **report.model_dump(),
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    global _client_errors
    _client_errors.append(error_record)
    if len(_client_errors) > _MAX_CLIENT_ERRORS:
        _client_errors = _client_errors[-_MAX_CLIENT_ERRORS:]
    
    logger.warning(
        f"[CLIENT ERROR] {report.error_type}: {report.message[:100]} "
        f"at {report.url}"
    )
    
    return {"received": True, "id": error_record["id"]}


@router.get("/client-errors")
async def get_client_errors(limit: int = 50, error_type: Optional[str] = None):
    """Get recent client-side errors."""
    _check_debug_access()
    
    errors = _client_errors
    if error_type:
        errors = [e for e in errors if e.get("error_type") == error_type]
    
    return {
        "count": len(errors),
        "errors": errors[-limit:][::-1],
    }


@router.delete("/client-errors")
async def clear_client_errors():
    """Clear all client error records."""
    _check_debug_access()
    global _client_errors
    _client_errors = []
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: ENVIRONMENT CHECK
# ─────────────────────────────────────────────────────────────────────────────

def _validate_env_var(name: str, pattern: Optional[str] = None) -> EnvCheckResult:
    """Validate a single environment variable."""
    value = os.getenv(name, "").strip()
    present = bool(value)
    
    # Value preview (show first 4 and last 4 chars for long values)
    value_preview = None
    if present and len(value) > 12:
        value_preview = f"{value[:4]}...{value[-4:]}"
    elif present:
        value_preview = value if len(value) <= 4 else f"{value[:2]}...{value[-2:]}"
    
    valid_format = True
    error = None
    
    if present and pattern:
        try:
            if not re.match(pattern, value):
                valid_format = False
                error = f"Value doesn't match expected pattern: {pattern}"
        except re.error as e:
            error = f"Invalid regex pattern: {e}"
    
    return EnvCheckResult(
        variable=name,
        present=present,
        valid_format=valid_format,
        value_preview=value_preview,
        error=error,
    )


@router.get("/env-check")
async def check_environment_variables():
    """Validate all payment-related environment variables."""
    _check_debug_access()
    
    results = {
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "providers": {},
        "frontend_vars": {},
        "issues": [],
    }
    
    # Paymob variables
    paymob_results = []
    paymob_vars = [
        ("PAYMOB_API_KEY", r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
        ("PAYMOB_INTEGRATION_ID", r"^\d+$"),
        ("PAYMOB_IFRAME_ID", r"^\d+$"),
        ("PAYMOB_HMAC_SECRET", None),
        ("PAYMOB_SECRET_KEY", r"^(egy_sk_|egy_pk_)?[a-fA-F0-9]+$"),
        ("PAYMOB_PUBLIC_KEY", r"^egy_pk_"),
        ("PAYMOB_BASE_URL", r"^https?://"),
    ]
    
    for var, pattern in paymob_vars:
        result = _validate_env_var(var, pattern)
        paymob_results.append(result.model_dump())
        if not result.present:
            results["issues"].append(f"Missing: {var}")
        elif not result.valid_format:
            results["issues"].append(f"Invalid format: {var}")
    
    results["providers"]["paymob"] = {
        "variables": paymob_results,
        "configured": all(
            os.getenv(v, "").strip() for v in ["PAYMOB_API_KEY", "PAYMOB_INTEGRATION_ID"]
        ),
    }
    
    # PayPal variables
    paypal_results = []
    paypal_vars = [
        ("PAYPAL_CLIENT_ID", r"^[A-Za-z0-9_-]{20,}$"),
        ("PAYPAL_CLIENT_SECRET", r"^[A-Za-z0-9_-]{40,}$"),
        ("PAYPAL_MODE", r"^(sandbox|live)$"),
        ("PAYPAL_WEBHOOK_ID", r"^[A-Z0-9]+$"),
    ]
    
    for var, pattern in paypal_vars:
        result = _validate_env_var(var, pattern)
        paypal_results.append(result.model_dump())
        if not result.present:
            results["issues"].append(f"Missing: {var}")
        elif not result.valid_format:
            results["issues"].append(f"Invalid format: {var}")
    
    results["providers"]["paypal"] = {
        "variables": paypal_results,
        "configured": all(
            os.getenv(v, "").strip() for v in ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"]
        ),
        "mode": os.getenv("PAYPAL_MODE", "sandbox"),
    }
    
    # Stripe variables (for completeness)
    stripe_results = []
    stripe_vars = [
        ("STRIPE_SECRET_KEY", r"^sk_(test_|live_)?[a-zA-Z0-9]+$"),
        ("STRIPE_PUBLISHABLE_KEY", r"^pk_(test_|live_)?[a-zA-Z0-9]+$"),
        ("STRIPE_WEBHOOK_SECRET", r"^whsec_"),
    ]
    
    for var, pattern in stripe_vars:
        result = _validate_env_var(var, pattern)
        stripe_results.append(result.model_dump())
    
    results["providers"]["stripe"] = {
        "variables": stripe_results,
        "configured": all(
            os.getenv(v, "").strip() for v in ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY"]
        ),
    }
    
    # Frontend variables (VITE_ prefix) - these should be accessible at build time
    frontend_vars = [
        "VITE_PAYMOB_PUBLIC_KEY",
        "VITE_PAYPAL_CLIENT_ID",
        "VITE_STRIPE_PUBLISHABLE_KEY",
        "VITE_API_URL",
    ]
    
    for var in frontend_vars:
        result = _validate_env_var(var)
        results["frontend_vars"][var] = result.model_dump()
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: API KEY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

async def _validate_paymob_api_key() -> APIKeyValidation:
    """Validate Paymob API key by requesting auth token."""
    api_key = os.getenv("PAYMOB_API_KEY", "").strip()
    
    if not api_key:
        return APIKeyValidation(
            provider="paymob",
            key_type="api_key",
            status="missing",
            message="PAYMOB_API_KEY not set",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{base_url}/auth/tokens",
                json={"api_key": api_key},
            )
            
            if r.status_code == 200:
                data = r.json()
                if data.get("token"):
                    return APIKeyValidation(
                        provider="paymob",
                        key_type="api_key",
                        status="valid",
                        message="Authentication successful",
                        last_checked=datetime.now(timezone.utc).isoformat(),
                    )
            
            return APIKeyValidation(
                provider="paymob",
                key_type="api_key",
                status="invalid",
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                last_checked=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        return APIKeyValidation(
            provider="paymob",
            key_type="api_key",
            status="error",
            message=str(e)[:200],
            last_checked=datetime.now(timezone.utc).isoformat(),
        )


async def _validate_paypal_credentials() -> APIKeyValidation:
    """Validate PayPal credentials by requesting access token."""
    client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    
    if not client_id or not client_secret:
        return APIKeyValidation(
            provider="paypal",
            key_type="client_credentials",
            status="missing",
            message="PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET not set",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    
    try:
        mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
        base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        
        raw = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{base_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {raw}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            
            if r.status_code == 200:
                data = r.json()
                if data.get("access_token"):
                    return APIKeyValidation(
                        provider="paypal",
                        key_type="client_credentials",
                        status="valid",
                        message=f"OAuth successful ({mode} mode)",
                        last_checked=datetime.now(timezone.utc).isoformat(),
                    )
            
            return APIKeyValidation(
                provider="paypal",
                key_type="client_credentials",
                status="invalid",
                message=f"HTTP {r.status_code}: {r.text[:200]}",
                last_checked=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        return APIKeyValidation(
            provider="paypal",
            key_type="client_credentials",
            status="error",
            message=str(e)[:200],
            last_checked=datetime.now(timezone.utc).isoformat(),
        )


@router.get("/api-keys/validate")
async def validate_api_keys():
    """Live validation of payment provider API keys."""
    _check_debug_access()
    
    results = await asyncio.gather(
        _validate_paymob_api_key(),
        _validate_paypal_credentials(),
    )
    
    return {
        "validations": [r.model_dump() for r in results],
        "all_valid": all(r.status == "valid" for r in results),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/perf-metrics")
async def report_performance_metric(
    metric_type: str,
    value_ms: float,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Report a performance metric from the frontend."""
    _check_debug_access()
    
    if metric_type not in _perf_metrics:
        raise HTTPException(status_code=400, detail=f"Unknown metric type: {metric_type}")
    
    record = {
        "id": f"perf-{uuid.uuid4().hex[:6]}",
        "value_ms": value_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    
    _perf_metrics[metric_type].append(record)
    if len(_perf_metrics[metric_type]) > _MAX_PERF_METRICS:
        _perf_metrics[metric_type] = _perf_metrics[metric_type][-_MAX_PERF_METRICS:]
    
    return {"received": True, "id": record["id"]}


@router.get("/perf-metrics")
async def get_performance_metrics():
    """Get all performance metrics."""
    _check_debug_access()
    
    result = {}
    for metric_type, records in _perf_metrics.items():
        if records:
            values = [r["value_ms"] for r in records]
            result[metric_type] = {
                "count": len(records),
                "avg_ms": sum(values) / len(values),
                "min_ms": min(values),
                "max_ms": max(values),
                "recent": records[-10:][::-1],
            }
        else:
            result[metric_type] = {"count": 0, "recent": []}
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: CORS/SSL ISSUES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/cors-ssl-issues")
async def report_cors_ssl_issue(
    issue_type: str,  # "cors" or "ssl"
    url: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
):
    """Report a CORS or SSL issue from the frontend."""
    _check_debug_access()
    
    record = {
        "id": f"issue-{uuid.uuid4().hex[:6]}",
        "issue_type": issue_type,
        "url": url,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    _cors_ssl_issues.append(record)
    if len(_cors_ssl_issues) > _MAX_CORS_SSL_ISSUES:
        _cors_ssl_issues = _cors_ssl_issues[-_MAX_CORS_SSL_ISSUES:]
    
    logger.warning(f"[{issue_type.upper()} ISSUE] {url}: {message}")
    
    return {"received": True, "id": record["id"]}


@router.get("/cors-ssl-issues")
async def get_cors_ssl_issues():
    """Get all CORS/SSL issues."""
    _check_debug_access()
    return {
        "count": len(_cors_ssl_issues),
        "issues": _cors_ssl_issues[::-1],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: REQUEST REPLAY
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/replay")
async def replay_payment_request(request: ReplayRequest):
    """Replay a failed payment request with optional modifications."""
    _check_debug_access()
    
    store = get_payment_log_store()
    original = store.get_by_trace_id(request.trace_id)
    
    if not original:
        raise HTTPException(status_code=404, detail="Original request not found")
    
    if original.success:
        raise HTTPException(status_code=400, detail="Cannot replay successful request")
    
    # Determine which client to use
    if original.provider == "paymob":
        client = create_paymob_logging_client()
    elif original.provider == "paypal":
        client = create_paypal_logging_client()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {original.provider}")
    
    # Apply modifications
    mods = request.modifications or {}
    
    headers = original.request.get("headers", {})
    if "headers" in mods:
        headers.update(mods["headers"])
    
    payload = original.request.get("payload")
    if "payload" in mods:
        if payload:
            payload.update(mods["payload"])
        else:
            payload = mods["payload"]
    
    method = original.request.get("method", "POST")
    url = original.request.get("url", "")
    
    # Extract path from full URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path or "/"
    except Exception:
        path = "/"
    
    try:
        async with client:
            if method.upper() == "GET":
                response = await client.get(path, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(path, headers=headers, json_data=payload)
            elif method.upper() == "PUT":
                response = await client.put(path, headers=headers, json_data=payload)
            elif method.upper() == "DELETE":
                response = await client.delete(path, headers=headers)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
            
            # Get the new log entry
            new_entry = store.get_all(limit=1)[0]
            
            return {
                "original_trace_id": request.trace_id,
                "new_trace_id": new_entry.trace_id,
                "original_status": original.response.get("status_code"),
                "new_status": response.status_code,
                "original_success": False,
                "new_success": new_entry.success,
                "comparison": {
                    "original": original.to_dict(),
                    "replay": new_entry.to_dict(),
                },
            }
    except Exception as e:
        logger.exception(f"Replay failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/replay/candidates")
async def get_replay_candidates():
    """Get failed requests that can be replayed."""
    _check_debug_access()
    
    store = get_payment_log_store()
    failed = store.get_failed(limit=50)
    
    return {
        "count": len(failed),
        "candidates": [
            {
                "trace_id": e.trace_id,
                "provider": e.provider,
                "timestamp": e.timestamp,
                "error": e.error,
                "status_code": e.response.get("status_code"),
                "url": e.request.get("url"),
            }
            for e in failed
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: TEST SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/test-scenarios/paymob")
async def run_paymob_test_scenario():
    """Run complete Paymob flow test: auth → order → payment_key."""
    _check_debug_access()
    
    results: List[TestScenarioResult] = []
    
    # Step 1: Auth token
    step = TestScenarioResult(step="auth_token", status="pending")
    start = time.perf_counter()
    try:
        api_key = os.getenv("PAYMOB_API_KEY", "").strip()
        if not api_key:
            step.status = "fail"
            step.message = "PAYMOB_API_KEY not set"
        else:
            base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{base_url}/auth/tokens",
                    json={"api_key": api_key},
                )
                step.latency_ms = (time.perf_counter() - start) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    token = data.get("token")
                    if token:
                        step.status = "pass"
                        step.message = "Authentication successful"
                        step.details = {"token_preview": f"{token[:10]}..."}
                    else:
                        step.status = "fail"
                        step.message = "No token in response"
                else:
                    step.status = "fail"
                    step.message = f"HTTP {r.status_code}"
                    step.details = {"response": r.text[:500]}
    except Exception as e:
        step.status = "fail"
        step.message = str(e)[:200]
        step.latency_ms = (time.perf_counter() - start) * 1000
    
    results.append(step)
    
    # If auth failed, skip remaining steps
    if step.status != "pass":
        results.append(TestScenarioResult(step="register_order", status="skip", message="Auth failed"))
        results.append(TestScenarioResult(step="payment_key", status="skip", message="Auth failed"))
        return {"scenario": "paymob", "results": [r.model_dump() for r in results], "passed": False}
    
    auth_token = step.details.get("token_preview", "")  # We need actual token
    
    # Step 2: Register order
    step = TestScenarioResult(step="register_order", status="pending")
    start = time.perf_counter()
    try:
        # Re-auth to get actual token
        base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
        async with httpx.AsyncClient(timeout=15.0) as client:
            auth_r = await client.post(
                f"{base_url}/auth/tokens",
                json={"api_key": os.getenv("PAYMOB_API_KEY", "").strip()},
            )
            token = auth_r.json()["token"]
            
            # Register order
            order_payload = {
                "auth_token": token,
                "delivery_needed": "false",
                "amount_cents": 100,  # Minimal test amount
                "currency": "EGP",
                "merchant_order_id": f"debug-test-{uuid.uuid4().hex[:8]}",
                "items": [],
            }
            
            r = await client.post(f"{base_url}/ecommerce/orders", json=order_payload)
            step.latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code in (200, 201):
                data = r.json()
                order_id = data.get("id")
                if order_id:
                    step.status = "pass"
                    step.message = f"Order registered: {order_id}"
                    step.details = {"order_id": order_id}
                else:
                    step.status = "fail"
                    step.message = "No order ID in response"
            else:
                step.status = "fail"
                step.message = f"HTTP {r.status_code}"
                step.details = {"response": r.text[:500]}
    except Exception as e:
        step.status = "fail"
        step.message = str(e)[:200]
        step.latency_ms = (time.perf_counter() - start) * 1000
    
    results.append(step)
    
    # Step 3: Payment key (if order succeeded)
    if step.status != "pass":
        results.append(TestScenarioResult(step="payment_key", status="skip", message="Order registration failed"))
        return {"scenario": "paymob", "results": [r.model_dump() for r in results], "passed": False}
    
    order_id = step.details.get("order_id")
    step = TestScenarioResult(step="payment_key", status="pending")
    start = time.perf_counter()
    
    try:
        integration_id = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
        if not integration_id:
            step.status = "fail"
            step.message = "PAYMOB_INTEGRATION_ID not set"
        else:
            base_url = os.getenv("PAYMOB_BASE_URL", "https://accept.paymob.com/api")
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Re-auth
                auth_r = await client.post(
                    f"{base_url}/auth/tokens",
                    json={"api_key": os.getenv("PAYMOB_API_KEY", "").strip()},
                )
                token = auth_r.json()["token"]
                
                # Payment key
                pk_payload = {
                    "auth_token": token,
                    "amount_cents": 100,
                    "expiration": 3600,
                    "order_id": order_id,
                    "billing_data": {
                        "apartment": "NA",
                        "email": "test@confit.local",
                        "floor": "NA",
                        "first_name": "Test",
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
                step.latency_ms = (time.perf_counter() - start) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    pk_token = data.get("token")
                    if pk_token:
                        step.status = "pass"
                        step.message = "Payment key generated"
                        step.details = {"key_preview": f"{pk_token[:20]}..."}
                    else:
                        step.status = "fail"
                        step.message = "No token in payment_key response"
                else:
                    step.status = "fail"
                    step.message = f"HTTP {r.status_code}"
                    step.details = {"response": r.text[:500]}
    except Exception as e:
        step.status = "fail"
        step.message = str(e)[:200]
        step.latency_ms = (time.perf_counter() - start) * 1000
    
    results.append(step)
    
    passed = all(r.status == "pass" for r in results)
    return {"scenario": "paymob", "results": [r.model_dump() for r in results], "passed": passed}


@router.post("/test-scenarios/paypal")
async def run_paypal_test_scenario():
    """Run PayPal flow test: OAuth → create order."""
    _check_debug_access()
    
    results: List[TestScenarioResult] = []
    
    # Step 1: OAuth token
    step = TestScenarioResult(step="oauth_token", status="pending")
    start = time.perf_counter()
    
    try:
        client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        
        if not client_id or not client_secret:
            step.status = "fail"
            step.message = "PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET not set"
        else:
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
                step.latency_ms = (time.perf_counter() - start) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    token = data.get("access_token")
                    if token:
                        step.status = "pass"
                        step.message = f"OAuth successful ({mode})"
                        step.details = {"token_preview": f"{token[:20]}..."}
                    else:
                        step.status = "fail"
                        step.message = "No access_token in response"
                else:
                    step.status = "fail"
                    step.message = f"HTTP {r.status_code}"
                    step.details = {"response": r.text[:500]}
    except Exception as e:
        step.status = "fail"
        step.message = str(e)[:200]
        step.latency_ms = (time.perf_counter() - start) * 1000
    
    results.append(step)
    
    if step.status != "pass":
        results.append(TestScenarioResult(step="create_order", status="skip", message="OAuth failed"))
        return {"scenario": "paypal", "results": [r.model_dump() for r in results], "passed": False}
    
    # Step 2: Create order
    step = TestScenarioResult(step="create_order", status="pending")
    start = time.perf_counter()
    
    try:
        mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
        base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        
        client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        raw = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Get fresh token
            auth_r = await client.post(
                f"{base_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {raw}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            token = auth_r.json()["access_token"]
            
            # Create order
            order_payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": f"debug-test-{uuid.uuid4().hex[:8]}",
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
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=order_payload,
            )
            step.latency_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 201:
                data = r.json()
                order_id = data.get("id")
                approve_link = None
                for link in data.get("links", []):
                    if link.get("rel") == "approve":
                        approve_link = link.get("href")
                
                step.status = "pass"
                step.message = f"Order created: {order_id}"
                step.details = {"order_id": order_id, "approve_link": approve_link}
            else:
                step.status = "fail"
                step.message = f"HTTP {r.status_code}"
                step.details = {"response": r.text[:500]}
    except Exception as e:
        step.status = "fail"
        step.message = str(e)[:200]
        step.latency_ms = (time.perf_counter() - start) * 1000
    
    results.append(step)
    
    passed = all(r.status == "pass" for r in results)
    return {"scenario": "paypal", "results": [r.model_dump() for r in results], "passed": passed}


@router.get("/test-scenarios/status")
async def get_test_scenarios_status():
    """Get summary of test scenario runs from logs."""
    _check_debug_access()
    
    store = get_payment_log_store()
    recent = store.get_all(limit=100)
    
    paymob_success = sum(1 for e in recent if e.provider == "paymob" and e.success)
    paymob_fail = sum(1 for e in recent if e.provider == "paymob" and not e.success)
    paypal_success = sum(1 for e in recent if e.provider == "paypal" and e.success)
    paypal_fail = sum(1 for e in recent if e.provider == "paypal" and not e.success)
    
    return {
        "paymob": {"success": paymob_success, "fail": paymob_fail},
        "paypal": {"success": paypal_success, "fail": paypal_fail},
        "last_24h": {
            "total_requests": len(recent),
            "success_rate": (
                sum(1 for e in recent if e.success) / len(recent) * 100 if recent else 0
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def get_payment_health_snapshot():
    """
    Get the current health snapshot for both providers.
    Returns results from the most recent completed health check run.
    Never blocks on live execution.
    """
    _check_debug_access()
    
    snapshot = get_health_snapshot()
    
    if not snapshot:
        # No snapshot yet - return pending state
        return {
            "paymob": {
                "overall": "unknown",
                "checks": {},
                "last_checked": None,
                "latency_ms": 0,
                "message": "Health check not yet run",
            },
            "paypal": {
                "overall": "unknown",
                "checks": {},
                "last_checked": None,
                "latency_ms": 0,
                "message": "Health check not yet run",
            },
            "scheduler_running": is_scheduler_running(),
        }
    
    # Format for the expected response structure
    result = {
        "paymob": snapshot.get("providers", {}).get("paymob", {
            "overall": "unknown",
            "checks": {},
            "last_checked": snapshot.get("last_run"),
            "latency_ms": 0,
        }),
        "paypal": snapshot.get("providers", {}).get("paypal", {
            "overall": "unknown",
            "checks": {},
            "last_checked": snapshot.get("last_run"),
            "latency_ms": 0,
        }),
        "scheduler_running": is_scheduler_running(),
        "last_run": snapshot.get("last_run"),
        "duration_ms": snapshot.get("duration_ms"),
    }
    
    # Remove full_results from details to keep response light
    for provider in ["paymob", "paypal"]:
        if "details" in result[provider]:
            result[provider]["details"] = {
                k: v for k, v in result[provider]["details"].items()
                if k != "full_results"
            }
    
    return result


@router.post("/health/trigger")
async def trigger_manual_health_check():
    """
    Manually trigger a health check run.
    Returns the results immediately (blocking).
    """
    _check_debug_access()
    
    snapshot = await trigger_health_check()
    return snapshot


@router.get("/health/history")
async def get_health_history(
    limit: int = 100,
    offset: int = 0,
    provider: Optional[str] = None,
    check_name: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
):
    """
    Get paginated historical health check results.
    Filterable by provider, check name, status, and time range.
    """
    _check_debug_access()
    
    store = get_health_store()
    
    entries = store.get_health_history(
        limit=limit,
        offset=offset,
        provider=provider,
        check_name=check_name,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    
    total = store.get_health_history_count(
        provider=provider,
        check_name=check_name,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    
    return {
        "count": len(entries),
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": [e.to_dict() for e in entries],
    }


@router.get("/health/history/timeline")
async def get_health_timeline(
    hours: int = 24,
    provider: Optional[str] = None,
):
    """
    Get health check results as a timeline for the last N hours.
    Useful for correlating infrastructure events with payment failures.
    """
    _check_debug_access()
    
    store = get_health_store()
    
    from datetime import timedelta
    start = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    entries = store.get_health_history(
        limit=1000,
        provider=provider,
        start_time=start,
    )
    
    # Group by hour
    timeline: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        hour = entry.timestamp[:13]  # "2024-01-15T10"
        if hour not in timeline:
            timeline[hour] = {
                "hour": hour,
                "pass": 0,
                "fail": 0,
                "warn": 0,
                "skip": 0,
                "entries": [],
            }
        timeline[hour][entry.status] = timeline[hour].get(entry.status, 0) + 1
        timeline[hour]["entries"].append(entry.to_dict())
    
    # Convert to sorted list
    result = sorted(timeline.values(), key=lambda x: x["hour"], reverse=True)
    
    return {
        "hours": hours,
        "provider": provider,
        "timeline": result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: ALERTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """
    Get recent alerts, with unacknowledged first.
    Used by the dashboard to show persistent notification banners.
    """
    _check_debug_access()
    
    store = get_health_store()
    alerts = store.get_alerts(limit=limit, unacknowledged_first=True)
    
    return {
        "count": len(alerts),
        "unacknowledged": store.get_unacknowledged_count(),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """
    Acknowledge an alert, marking it as seen.
    """
    _check_debug_access()
    
    store = get_health_store()
    success = store.acknowledge_alert(alert_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or already acknowledged"
        )
    
    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/alerts/acknowledge-all")
async def acknowledge_all_alerts():
    """
    Acknowledge all unacknowledged alerts.
    """
    _check_debug_access()
    
    store = get_health_store()
    alerts = store.get_alerts(limit=100, unacknowledged_first=True)
    
    acknowledged = 0
    for alert in alerts:
        if not alert.acknowledged:
            store.acknowledge_alert(alert.id)
            acknowledged += 1
    
    return {
        "success": True,
        "acknowledged_count": acknowledged,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: SCHEDULER CONTROL
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Get the status of the health check scheduler.
    """
    _check_debug_access()
    
    return {
        "running": is_scheduler_running(),
        "interval_minutes": int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", "5")),
        "environment": settings.ENVIRONMENT,
        "enabled": settings.ENVIRONMENT.lower() in ("development", "dev", "staging", "test"),
    }


@router.post("/scheduler/start")
async def start_health_scheduler():
    """
    Start the health check scheduler manually.
    Only works in development/staging environments.
    """
    _check_debug_access()
    
    if is_scheduler_running():
        return {"success": True, "message": "Scheduler already running"}
    
    scheduler = start_scheduler()
    
    if scheduler:
        return {"success": True, "message": "Scheduler started"}
    else:
        return {"success": False, "message": "Failed to start scheduler (check APScheduler installation)"}


@router.post("/scheduler/stop")
async def stop_health_scheduler():
    """
    Stop the health check scheduler manually.
    """
    _check_debug_access()
    
    stop_scheduler()
    return {"success": True, "message": "Scheduler stopped"}
