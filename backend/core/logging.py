"""
CONFIT Backend — Structured Logging (structlog)
================================================
JSON output in production, pretty console in development.
Includes request_id, user_id, path, duration_ms, status via contextvars.

Usage:
    from core.logging import get_logger, configure_logging
    logger = get_logger("my_module")
    logger.info("user_action", user_id="123", item_id="456")
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Optional

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ── Context Variables ──────────────────────────────────────────────────

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
path_var: ContextVar[Optional[str]] = ContextVar("path", default=None)


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    if request_id is not None:
        request_id_var.set(request_id)
    if user_id is not None:
        user_id_var.set(user_id)
    if path is not None:
        path_var.set(path)


def clear_request_context() -> None:
    request_id_var.set(None)
    user_id_var.set(None)
    path_var.set(None)


# ── Shared Processors ──────────────────────────────────────────────────


def add_context_vars(logger, method_name, event_dict):
    """Inject request_id / user_id / path from contextvars into every log line."""
    rid = request_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    uid = user_id_var.get()
    if uid:
        event_dict["user_id"] = uid
    pth = path_var.get()
    if pth:
        event_dict["path"] = pth
    return event_dict


def add_service_info(logger, method_name, event_dict):
    event_dict["service"] = "confit-api"
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    return event_dict


# ── Configuration ──────────────────────────────────────────────────────


def configure_logging() -> None:
    """
    Configure structlog and stdlib logging once at app startup.
    JSON in production, colored console in development.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    json_output = env in ("production", "prod", "staging", "stage")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_context_vars,
        add_service_info,
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # Production: compact JSON
        structlog.configure(
            processors=shared_processors + [structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level, logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: pretty colored console
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(
                    colors=True, sort_keys=False
                )
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level, logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Also wrap stdlib logging so third-party libs emit structured logs
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True, sort_keys=False)
        if not json_output
        else structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound with service context."""
    return structlog.get_logger(name)


# ── Middleware ───────────────────────────────────────────────────────────


class StructlogContextMiddleware(BaseHTTPMiddleware):
    """
    Injects request_id (from header or generated), user_id (from JWT if present),
    and path into structlog contextvars so every log line inside the request
    is automatically enriched.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate or reuse request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Attempt to extract user_id from JWT if present
        user_id: Optional[str] = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header.replace("Bearer ", "")
                # Unverified decode for user_id only (no signature check needed for logging)
                payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
                user_id = str(payload.get("sub", payload.get("user_id", "")))
                if not user_id:
                    user_id = None
            except Exception:
                pass

        # Set context
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            path=request.url.path,
        )

        start = time.time()
        response = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.time() - start) * 1000
            status_code = response.status_code if response is not None else 500
            # Emit a single structured access log line
            logger = get_logger("confit.access")
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            clear_request_context()

        # Propagate request ID back to caller
        response.headers["X-Request-ID"] = request_id
        return response
