"""
CONFIT Backend - Metrics Collection
====================================
Prometheus metrics for payment and auth operations.
Idempotent registration for uvicorn reload compatibility.
"""

from __future__ import annotations

import os
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY, generate_latest


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


# ─────────────────────────────────────────────────────────────────────────────
# METRIC DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

# Payment metrics
PAYMENT_REQUESTS = _get_or_create_counter(
    "confit_payment_requests_total",
    "Total payment requests",
    ["provider", "status"],
)

PAYMENT_AMOUNT = _get_or_create_histogram(
    "confit_payment_amount_dollars",
    "Payment amount in dollars",
    ["provider", "currency"],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

PAYMENT_LATENCY = _get_or_create_histogram(
    "confit_payment_latency_seconds",
    "Payment processing latency",
    ["provider", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PAYMENT_ERRORS = _get_or_create_counter(
    "confit_payment_errors_total",
    "Total payment errors",
    ["provider", "error_type"],
)

# Invoice metrics
INVOICE_GENERATED = _get_or_create_counter(
    "confit_invoice_generated_total",
    "Total invoices generated",
    ["status"],
)

INVOICE_LATENCY = _get_or_create_histogram(
    "confit_invoice_generation_seconds",
    "Invoice generation latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0],
)

# Auth metrics
AUTH_REQUESTS = _get_or_create_counter(
    "confit_auth_requests_total",
    "Total authentication requests",
    ["type", "status"],
)

AUTH_LATENCY = _get_or_create_histogram(
    "confit_auth_latency_seconds",
    "Authentication latency",
    ["type"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

OAUTH_LOGINS = _get_or_create_counter(
    "confit_oauth_logins_total",
    "Total OAuth logins",
    ["provider", "status"],
)

# Order metrics
ORDERS_CREATED = _get_or_create_counter(
    "confit_new_orders_total",
    "Total orders created",
    ["delivery_method"],
)

ORDER_VALUE = _get_or_create_histogram(
    "confit_order_value_dollars",
    "Order value in dollars",
    ["delivery_method"],
    buckets=[25, 50, 100, 200, 500, 1000],
)

# Webhook metrics
WEBHOOK_RECEIVED = _get_or_create_counter(
    "confit_webhook_received_total",
    "Total webhooks received",
    ["provider", "event_type"],
)

WEBHOOK_PROCESSING = _get_or_create_histogram(
    "confit_webhook_processing_seconds",
    "Webhook processing latency",
    ["provider"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0],
)

# Celery task metrics
CELERY_TASKS = _get_or_create_counter(
    "confit_celery_tasks_total",
    "Total Celery tasks",
    ["task", "status"],
)

CELERY_QUEUE_DEPTH = _get_or_create_gauge(
    "confit_celery_queue_depth",
    "Celery queue depth",
    ["queue"],
)


# ─────────────────────────────────────────────────────────────────────────────
# METRICS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

class Metrics:
    """Helper class for recording metrics."""

    @staticmethod
    def payment_success(provider: str, amount: float, currency: str = "USD") -> None:
        """Record successful payment."""
        PAYMENT_REQUESTS.labels(provider=provider, status="success").inc()
        PAYMENT_AMOUNT.labels(provider=provider, currency=currency).observe(amount)

    @staticmethod
    def payment_failure(provider: str, error_type: str) -> None:
        """Record failed payment."""
        PAYMENT_REQUESTS.labels(provider=provider, status="failed").inc()
        PAYMENT_ERRORS.labels(provider=provider, error_type=error_type).inc()

    @staticmethod
    def payment_latency(provider: str, operation: str, seconds: float) -> None:
        """Record payment latency."""
        PAYMENT_LATENCY.labels(provider=provider, operation=operation).observe(seconds)

    @staticmethod
    def invoice_generated(status: str = "success") -> None:
        """Record invoice generation."""
        INVOICE_GENERATED.labels(status=status).inc()

    @staticmethod
    def auth_request(auth_type: str, status: str) -> None:
        """Record auth request."""
        AUTH_REQUESTS.labels(type=auth_type, status=status).inc()

    @staticmethod
    def oauth_login(provider: str, status: str) -> None:
        """Record OAuth login."""
        OAUTH_LOGINS.labels(provider=provider, status=status).inc()

    @staticmethod
    def order_created(delivery_method: str, value: float) -> None:
        """Record order creation."""
        ORDERS_CREATED.labels(delivery_method=delivery_method).inc()
        ORDER_VALUE.labels(delivery_method=delivery_method).observe(value)

    @staticmethod
    def webhook_received(provider: str, event_type: str) -> None:
        """Record webhook receipt."""
        WEBHOOK_RECEIVED.labels(provider=provider, event_type=event_type).inc()

    @staticmethod
    def celery_task(task: str, status: str) -> None:
        """Record Celery task."""
        CELERY_TASKS.labels(task=task, status=status).inc()


# Global metrics instance
metrics = Metrics()


def setup_metrics(port: int = 9090) -> None:
    """
    Start Prometheus metrics server.

    Args:
        port: Port for metrics endpoint
    """
    from prometheus_client import start_http_server
    start_http_server(port)


def get_metrics_text() -> str:
    """Get metrics in Prometheus text format."""
    return generate_latest(REGISTRY).decode("utf-8")
