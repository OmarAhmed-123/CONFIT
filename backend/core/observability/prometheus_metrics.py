"""
CONFIT Backend — Custom Prometheus Metrics
===========================================
Registers custom business metrics alongside the default FastAPI instrumentation.
Handles idempotent registration for uvicorn reload compatibility.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY


_metrics_cache = {}


def _get_or_create_counter(name: str, documentation: str, labelnames: list[str] = None):
    """Get existing counter or create new one (idempotent for reloads)."""
    cache_key = f"counter:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]
    labelnames = labelnames or []
    try:
        metric = Counter(name, documentation, labelnames)
        _metrics_cache[cache_key] = metric
        return metric
    except ValueError:
        # Metric already exists in registry, find and return it
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                _metrics_cache[cache_key] = collector
                return collector
        raise


def _get_or_create_histogram(name: str, documentation: str, labelnames: list[str] = None, buckets: list[float] = None):
    """Get existing histogram or create new one (idempotent for reloads)."""
    cache_key = f"histogram:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]
    labelnames = labelnames or []
    try:
        if buckets:
            metric = Histogram(name, documentation, labelnames, buckets=buckets)
        else:
            metric = Histogram(name, documentation, labelnames)
        _metrics_cache[cache_key] = metric
        return metric
    except ValueError:
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                _metrics_cache[cache_key] = collector
                return collector
        raise


def _get_or_create_gauge(name: str, documentation: str, labelnames: list[str] = None):
    """Get existing gauge or create new one (idempotent for reloads)."""
    cache_key = f"gauge:{name}"
    if cache_key in _metrics_cache:
        return _metrics_cache[cache_key]
    labelnames = labelnames or []
    try:
        metric = Gauge(name, documentation, labelnames)
        _metrics_cache[cache_key] = metric
        return metric
    except ValueError:
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                _metrics_cache[cache_key] = collector
                return collector
        raise


# ── Business Metrics ───────────────────────────────────────────────────

confit_orders_total = _get_or_create_counter(
    "confit_orders_total",
    "Total orders processed",
    ["status", "country"],
)

confit_payments_total = _get_or_create_counter(
    "confit_payments_total",
    "Total payment attempts",
    ["provider", "status"],
)

confit_ai_cost_usd_total = _get_or_create_counter(
    "confit_ai_cost_usd_total",
    "Total AI service cost in USD",
    ["service"],
)

confit_donor_coupons_redeemed_total = _get_or_create_counter(
    "confit_donor_coupons_redeemed_total",
    "Total donor coupons redeemed",
    [],
)

# ── System Metrics (supplement instrumentator defaults) ─────────────────

confit_request_duration_seconds = _get_or_create_histogram(
    "confit_request_duration_seconds",
    "Request latency with normalized path",
    ["method", "path", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

confit_active_users_gauge = _get_or_create_gauge(
    "confit_active_users",
    "Currently active users (approximate via active JWT sessions)",
)


def get_metrics_text() -> str:
    """Return all metrics in Prometheus text exposition format."""
    return generate_latest().decode("utf-8")
