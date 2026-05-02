"""
CONFIT Backend — Sentry Integration
====================================
Wires sentry-sdk for FastAPI with performance monitoring.
PII scrubbing via before_send strips emails and phone numbers.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Patterns for PII scrubbing
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?[0-9]{1,3}[\s\-]?\(?[0-9]{1,4}\)?[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,4}")


def _scrub_pii_from_string(value: str) -> str:
    value = _EMAIL_RE.sub("[EMAIL_REDACTED]", value)
    value = _PHONE_RE.sub("[PHONE_REDACTED]", value)
    return value


def _scrub_pii(data: Any) -> Any:
    """Recursively scrub emails and phone numbers from dicts/lists/strings."""
    if isinstance(data, str):
        return _scrub_pii_from_string(data)
    if isinstance(data, dict):
        return {k: _scrub_pii(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_scrub_pii(i) for i in data]
    return data


def before_send(event: Dict[str, Any], hint: Any) -> Optional[Dict[str, Any]]:
    """Sentry before_send hook: strip PII from exception events."""
    try:
        # Scrub exception values
        if "exception" in event:
            for exc in event["exception"].get("values", []):
                if "value" in exc:
                    exc["value"] = _scrub_pii_from_string(str(exc["value"]))

        # Scrub request data
        if "request" in event:
            for key in ("data", "query_string", "cookies", "headers"):
                if key in event["request"]:
                    event["request"][key] = _scrub_pii(event["request"][key])

        # Scrub breadcrumbs
        if "breadcrumbs" in event:
            for crumb in event["breadcrumbs"].get("values", []):
                if "message" in crumb:
                    crumb["message"] = _scrub_pii_from_string(str(crumb["message"]))
                if "data" in crumb:
                    crumb["data"] = _scrub_pii(crumb["data"])
    except Exception:
        pass
    return event


def before_send_transaction(event: Dict[str, Any], hint: Any) -> Optional[Dict[str, Any]]:
    """Sentry before_send_transaction hook: strip PII from transaction events."""
    try:
        if "request" in event:
            for key in ("data", "query_string", "cookies", "headers"):
                if key in event["request"]:
                    event["request"][key] = _scrub_pii(event["request"][key])
    except Exception:
        pass
    return event


def init_sentry() -> None:
    """Initialize Sentry SDK for FastAPI if SENTRY_DSN is set."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry DSN not configured — skipping Sentry initialization")
        return

    env = os.getenv("ENVIRONMENT", "development").lower()
    sample_rate = 1.0 if env in ("development", "dev") else 0.1

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                sentry_logging,
            ],
            traces_sample_rate=sample_rate,
            profiles_sample_rate=sample_rate if env in ("production", "prod") else 0.0,
            before_send=before_send,
            before_send_transaction=before_send_transaction,
            attach_stacktrace=True,
            include_source_context=True,
            include_local_variables=False,
            max_breadcrumbs=50,
            send_default_pii=False,
        )
        logger.info("Sentry initialized (env=%s, traces_sample_rate=%s)", env, sample_rate)
    except Exception as exc:
        logger.warning("Failed to initialize Sentry: %s", exc)
