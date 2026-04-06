"""
Structured JSON Logging for Payment Infrastructure
=================================================
Provides structured JSON logging for all payment middleware and endpoint activity.
Emits to both stdout (for external log aggregation) and the SQLite store.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Check if structlog is available
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
        }
        
        # Add extra fields from record
        extra_fields = getattr(record, "extra", {})
        log_data.update(extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger that emits JSON logs.
    Falls back to standard logging with JSON formatter if structlog unavailable.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(name)
        
        if HAS_STRUCTLOG:
            # Configure structlog
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            self._structlog = structlog.get_logger(name)
        else:
            self._structlog = None
    
    def _get_environment(self) -> str:
        return os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))
    
    def log(
        self,
        level: str,
        message: str,
        trace_id: Optional[str] = None,
        provider: Optional[str] = None,
        method: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        latency_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
        error: Optional[str] = None,
        logging_overhead_ms: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Log a structured message with payment-specific fields."""
        
        extra: Dict[str, Any] = {
            "environment": self._get_environment(),
        }
        
        if trace_id:
            extra["trace_id"] = trace_id
        if provider:
            extra["provider"] = provider
        if method:
            extra["method"] = method
        if url:
            extra["url"] = url
        if status_code is not None:
            extra["status_code"] = status_code
        if latency_ms is not None:
            extra["latency_ms"] = latency_ms
        if correlation_id:
            extra["correlation_id"] = correlation_id
        if error:
            extra["error"] = error
        if logging_overhead_ms is not None:
            extra["logging_overhead_ms"] = logging_overhead_ms
        
        extra.update(kwargs)
        
        if HAS_STRUCTLOG and self._structlog:
            # Use structlog
            log_method = getattr(self._structlog, level, self._structlog.info)
            log_method(message, **extra)
        else:
            # Use standard logging with extra
            record = self._logger.makeRecord(
                self.name,
                getattr(logging, level.upper(), logging.INFO),
                "",
                0,
                message,
                (),
                None,
            )
            record.extra = extra
            self._logger.handle(record)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self.log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self.log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.log("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self.log("debug", message, **kwargs)


def configure_structured_logging() -> None:
    """Configure root logger for structured JSON output."""
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
    
    # Set level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))


# Create a module-level structured logger for payment operations
payment_logger = StructuredLogger("confit.payment")


def get_payment_logger() -> StructuredLogger:
    """Get the payment structured logger."""
    return payment_logger
