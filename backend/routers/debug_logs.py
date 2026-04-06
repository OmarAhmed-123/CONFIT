"""
Debug Logs Router
=================
Environment-gated endpoint for viewing payment transaction logs.
Provides paginated, filterable access to the SQLite log store.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.debug.payment_log_store import (
    PaymentLogEntry,
    PaymentLogStore,
    get_payment_log_store,
    init_payment_log_store,
)
from services.debug.structured_logging import get_payment_logger

logger = logging.getLogger(__name__)
structured_logger = get_payment_logger()

router = APIRouter(prefix="/api/debug", tags=["Debug"])


def _is_debug_endpoint_enabled() -> bool:
    """Check if debug endpoints should be active."""
    app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    
    # Only active in development and staging
    if app_env in ("development", "dev", "staging", "stage", "test"):
        return True
    
    # Check explicit override
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return True
    
    return False


class PaginatedLogsResponse:
    """Response model for paginated logs."""
    
    @staticmethod
    def build(
        entries: List[PaymentLogEntry],
        total_count: int,
        page: int,
        page_size: int,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the response dictionary."""
        return {
            "success": True,
            "data": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0,
                "filters": {
                    "provider": provider,
                    "status": status,
                    "trace_id": trace_id,
                },
                "entries": [entry.to_dict() for entry in entries],
            },
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            },
        }


@router.get("/logs")
async def get_payment_logs(
    provider: Optional[str] = Query(
        None,
        description="Filter by provider: 'paymob' or 'paypal'",
        pattern="^(paymob|paypal|stripe)$",
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by status: 'success' (2xx) or 'failure' (non-2xx)",
        pattern="^(success|failure)$",
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        50,
        ge=1,
        le=200,
        description="Number of entries per page (max 200)",
    ),
    trace_id: Optional[str] = Query(
        None,
        description="Look up a specific transaction by trace ID",
    ),
    correlation_id: Optional[str] = Query(
        None,
        description="Look up all entries for a correlation ID",
    ),
    start_time: Optional[str] = Query(
        None,
        description="Filter entries after this ISO 8601 timestamp",
    ),
    end_time: Optional[str] = Query(
        None,
        description="Filter entries before this ISO 8601 timestamp",
    ),
) -> Dict[str, Any]:
    """
    Get paginated, filterable payment transaction logs.
    
    **Environment-gated**: Only available in development/staging.
    
    Returns:
    - `total_count`: Total number of matching entries
    - `page`: Current page number
    - `page_size`: Number of entries per page
    - `total_pages`: Total number of pages
    - `entries`: Array of log entries with all captured fields
    - Each entry includes `correlation_id` linking request/response pairs
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production. Set ENABLE_DEBUG_ENDPOINTS=true to override.",
        )
    
    # Initialize store if needed
    store = await init_payment_log_store()
    
    # Handle trace_id lookup (single entry)
    if trace_id:
        entry = await store.get_by_trace_id(trace_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Trace ID not found: {trace_id}")
        
        structured_logger.info(
            "Debug log lookup by trace_id",
            trace_id=trace_id,
            provider=entry.provider,
        )
        
        return {
            "success": True,
            "data": {
                "entry": entry.to_dict(),
            },
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            },
        }
    
    # Handle correlation_id lookup (multiple entries)
    if correlation_id:
        entries = await store.get_by_correlation_id(correlation_id)
        if not entries:
            raise HTTPException(status_code=404, detail=f"Correlation ID not found: {correlation_id}")
        
        structured_logger.info(
            "Debug log lookup by correlation_id",
            correlation_id=correlation_id,
            count=len(entries),
        )
        
        return {
            "success": True,
            "data": {
                "entries": [entry.to_dict() for entry in entries],
                "count": len(entries),
            },
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            },
        }
    
    # Normal paginated query
    entries, total_count = await store.get_entries(
        page=page,
        page_size=page_size,
        provider=provider.lower() if provider else None,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    
    structured_logger.info(
        "Debug logs query",
        provider=provider,
        status=status,
        page=page,
        page_size=page_size,
        total_count=total_count,
    )
    
    return PaginatedLogsResponse.build(
        entries=entries,
        total_count=total_count,
        page=page,
        page_size=page_size,
        provider=provider,
        status=status,
        trace_id=trace_id,
    )


@router.get("/logs/failed")
async def get_failed_payment_logs(
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of failed entries to return",
    ),
) -> Dict[str, Any]:
    """
    Get failed payment requests for replay functionality.
    
    Returns the most recent failed requests, useful for debugging
    and implementing a request replay tool.
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production.",
        )
    
    store = await init_payment_log_store()
    entries = await store.get_failed_entries(limit=limit)
    
    structured_logger.info(
        "Debug failed logs query",
        count=len(entries),
        limit=limit,
    )
    
    return {
        "success": True,
        "data": {
            "entries": [entry.to_dict() for entry in entries],
            "count": len(entries),
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
        },
    }


@router.get("/logs/stats")
async def get_payment_logs_stats() -> Dict[str, Any]:
    """
    Get statistics about the payment log store.
    
    Returns counts by provider, success/failure ratios, etc.
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production.",
        )
    
    store = await init_payment_log_store()
    
    # Get all entries for stats calculation
    all_entries, total_count = await store.get_entries(page_size=10000)
    
    # Calculate stats
    provider_counts: Dict[str, int] = {}
    success_count = 0
    failure_count = 0
    total_latency_ms = 0.0
    max_latency_ms = 0.0
    
    for entry in all_entries:
        # Provider count
        provider_counts[entry.provider] = provider_counts.get(entry.provider, 0) + 1
        
        # Success/failure count
        if entry.success:
            success_count += 1
        else:
            failure_count += 1
        
        # Latency stats
        if entry.latency_ms:
            total_latency_ms += entry.latency_ms
            max_latency_ms = max(max_latency_ms, entry.latency_ms)
    
    avg_latency_ms = total_latency_ms / total_count if total_count > 0 else 0
    
    return {
        "success": True,
        "data": {
            "total_count": total_count,
            "by_provider": provider_counts,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            "avg_latency_ms": round(avg_latency_ms, 2),
            "max_latency_ms": round(max_latency_ms, 2),
            "store_limits": {
                "max_rows": 10000,
                "cleanup_days": 7,
            },
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
        },
    }


@router.delete("/logs")
async def clear_payment_logs(
    confirm: bool = Query(
        False,
        description="Set to true to confirm deletion of all logs",
    ),
) -> Dict[str, Any]:
    """
    Clear all payment logs from the store.
    
    **Dangerous operation**: Requires confirm=true to execute.
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production.",
        )
    
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion not confirmed. Set confirm=true to proceed.",
        )
    
    store = await init_payment_log_store()
    await store.clear_all()
    
    structured_logger.warning("Debug logs cleared")
    
    return {
        "success": True,
        "message": "All payment logs have been cleared.",
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/env-check")
async def debug_env_check() -> Dict[str, Any]:
    """
    Check environment configuration for payment providers.
    
    Returns which providers are configured and their settings
    (with secrets redacted).
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production.",
        )
    
    # Check Paymob
    paymob_api_key = os.getenv("PAYMOB_API_KEY", "").strip()
    paymob_integration_id = os.getenv("PAYMOB_INTEGRATION_ID", "").strip()
    paymob_iframe_id = os.getenv("PAYMOB_IFRAME_ID", "").strip()
    paymob_hmac = os.getenv("PAYMOB_HMAC_SECRET", os.getenv("PAYMOB_SECRET_KEY", "")).strip()
    
    # Check PayPal
    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox").strip()
    paypal_webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    
    # Check Stripe
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    
    return {
        "success": True,
        "data": {
            "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            "debug_endpoints_enabled": _is_debug_endpoint_enabled(),
            "payment_logging_enabled": os.getenv("DEBUG_PAYMENT_LOGGING", "true").lower() == "true",
            "providers": {
                "paymob": {
                    "configured": bool(paymob_api_key and paymob_integration_id),
                    "api_key_set": bool(paymob_api_key),
                    "api_key_preview": f"{paymob_api_key[:8]}..." if paymob_api_key and len(paymob_api_key) > 8 else None,
                    "integration_id": paymob_integration_id or None,
                    "iframe_id": paymob_iframe_id or None,
                    "hmac_configured": bool(paymob_hmac),
                },
                "paypal": {
                    "configured": bool(paypal_client_id and paypal_client_secret),
                    "client_id_set": bool(paypal_client_id),
                    "client_id_preview": f"{paypal_client_id[:12]}..." if paypal_client_id and len(paypal_client_id) > 12 else None,
                    "mode": paypal_mode,
                    "webhook_configured": bool(paypal_webhook_id),
                },
                "stripe": {
                    "configured": bool(stripe_publishable_key and stripe_secret_key),
                    "publishable_key_set": bool(stripe_publishable_key),
                    "secret_key_set": bool(stripe_secret_key),
                },
            },
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/client-errors")
async def get_client_errors(
    limit: int = Query(50, ge=1, le=200),
    provider: Optional[str] = Query(None, pattern="^(paymob|paypal|stripe)$"),
) -> Dict[str, Any]:
    """
    Get recent client-side errors from payment integrations.
    
    This endpoint is for tracking errors that occur on the client side
    during payment processing (e.g., iframe errors, redirect failures).
    """
    
    # Environment gate
    if not _is_debug_endpoint_enabled():
        raise HTTPException(
            status_code=404,
            detail="Debug endpoints are disabled in production.",
        )
    
    # Get failed entries from the log store
    store = await init_payment_log_store()
    entries = await store.get_failed_entries(limit=limit)
    
    # Filter by provider if specified
    if provider:
        entries = [e for e in entries if e.provider == provider.lower()]
    
    # Group errors by type
    error_summary: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        error_key = entry.error or "unknown_error"
        if error_key not in error_summary:
            error_summary[error_key] = []
        error_summary[error_key].append({
            "trace_id": entry.trace_id,
            "timestamp": entry.timestamp,
            "provider": entry.provider,
            "url": entry.request_url,
            "status_code": entry.response_status_code,
        })
    
    return {
        "success": True,
        "data": {
            "total_errors": len(entries),
            "error_summary": error_summary,
            "recent_errors": [entry.to_dict() for entry in entries[:20]],
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
        },
    }
