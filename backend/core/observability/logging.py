"""
CONFIT Backend - Structured Logging
===================================
JSON-structured logging with correlation IDs and request context.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter."""

    def __init__(self, service_name: str = "confit-api", environment: str = "development"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base fields
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "env": self.environment,
        }

        # Add context from ContextVar
        request_id = request_id_var.get()
        if request_id:
            log_obj["request_id"] = request_id

        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_obj["correlation_id"] = correlation_id

        user_id = user_id_var.get()
        if user_id:
            log_obj["user_id"] = user_id

        # Add location info
        log_obj["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add extra fields
        if hasattr(record, "data") and record.data:
            log_obj["data"] = record.data

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_obj, default=str)


class StructuredLogger(logging.Logger):
    """Logger with structured logging support."""

    def _log_with_data(
        self,
        level: int,
        msg: str,
        data: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs,
    ) -> None:
        """Log with additional structured data."""
        extra = kwargs.get("extra", {})
        extra["data"] = data or {}
        kwargs["extra"] = extra
        self._log(level, msg, args, **kwargs)

    def info_data(self, msg: str, data: Optional[Dict[str, Any]] = None, *args, **kwargs) -> None:
        self._log_with_data(logging.INFO, msg, data, *args, **kwargs)

    def warning_data(self, msg: str, data: Optional[Dict[str, Any]] = None, *args, **kwargs) -> None:
        self._log_with_data(logging.WARNING, msg, data, *args, **kwargs)

    def error_data(self, msg: str, data: Optional[Dict[str, Any]] = None, *args, **kwargs) -> None:
        self._log_with_data(logging.ERROR, msg, data, *args, **kwargs)

    def debug_data(self, msg: str, data: Optional[Dict[str, Any]] = None, *args, **kwargs) -> None:
        self._log_with_data(logging.DEBUG, msg, data, *args, **kwargs)


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "confit-api",
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_output: Use JSON format (True) or human-readable (False)
        service_name: Service name for log records
    """
    # Set custom logger class
    logging.setLoggerClass(StructuredLogger)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        # JSON formatter for production
        formatter = StructuredFormatter(
            service_name=service_name,
            environment=os.getenv("ENVIRONMENT", "development"),
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return logging.getLogger(name)  # type: ignore


# Convenience function for setting request context
def set_request_context(
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Set context variables for the current request."""
    if request_id:
        request_id_var.set(request_id)
    if correlation_id:
        correlation_id_var.set(correlation_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """Clear context variables after request."""
    request_id_var.set(None)
    correlation_id_var.set(None)
    user_id_var.set(None)
