"""
CONFIT Backend - Metrics Collection
====================================
Prometheus metrics for payment and auth operations.
"""

from __future__ import annotations

import os
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY, generate_latest

# ─────────────────────────────────────────────────────────────────────────────
# METRIC DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

# Payment metrics
PAYMENT_REQUESTS = Counter(
    "confit_payment_requests_total",
    "Total payment requests",
    ["provider", "status"],
)

PAYMENT_AMOUNT = Histogram(
    "confit_payment_amount_dollars",
    "Payment amount in dollars",
    ["provider", "currency"],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

PAYMENT_LATENCY = Histogram(
    "confit_payment_latency_seconds",
    "Payment processing latency",
    ["provider", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PAYMENT_ERRORS = Counter(
    "confit_payment_errors_total",
    "Total payment errors",
    ["provider", "error_type"],
)

# Invoice metrics
INVOICE_GENERATED = Counter(
    "confit_invoice_generated_total",
    "Total invoices generated",
    ["status"],
)

INVOICE_LATENCY = Histogram(
    "confit_invoice_generation_seconds",
    "Invoice generation latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0],
)

# Auth metrics
AUTH_REQUESTS = Counter(
    "confit_auth_requests_total",
    "Total authentication requests",
    ["type", "status"],
)

AUTH_LATENCY = Histogram(
    "confit_auth_latency_seconds",
    "Authentication latency",
    ["type"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

OAUTH_LOGINS = Counter(
    "confit_oauth_logins_total",
    "Total OAuth logins",
    ["provider", "status"],
)

# Order metrics
ORDERS_CREATED = Counter(
    "confit_orders_created_total",
    "Total orders created",
    ["delivery_method"],
)

ORDER_VALUE = Histogram(
    "confit_order_value_dollars",
    "Order value in dollars",
    ["delivery_method"],
    buckets=[25, 50, 100, 200, 500, 1000],
)

# Webhook metrics
WEBHOOK_RECEIVED = Counter(
    "confit_webhook_received_total",
    "Total webhooks received",
    ["provider", "event_type"],
)

WEBHOOK_PROCESSING = Histogram(
    "confit_webhook_processing_seconds",
    "Webhook processing latency",
    ["provider"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0],
)

# Celery task metrics
CELERY_TASKS = Counter(
    "confit_celery_tasks_total",
    "Total Celery tasks",
    ["task", "status"],
)

CELERY_QUEUE_DEPTH = Gauge(
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
