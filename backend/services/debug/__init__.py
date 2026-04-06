"""Debug services for payment integration."""

# Legacy in-memory logger (kept for backwards compatibility)
from .payment_logger import (
    PaymentLogStore as InMemoryPaymentLogStore,
    PaymentLogEntry as LegacyPaymentLogEntry,
    PaymentLoggingClient,
    get_payment_log_store as get_in_memory_log_store,
    create_paymob_logging_client,
    create_paypal_logging_client,
)

# New SQLite-backed persistent store
from .payment_log_store import (
    PaymentLogStore,
    PaymentLogEntry,
    get_payment_log_store,
    init_payment_log_store,
    close_payment_log_store,
)

# Structured logging
from .structured_logging import (
    StructuredLogger,
    configure_structured_logging,
    get_payment_logger,
)

__all__ = [
    # Legacy (in-memory)
    "InMemoryPaymentLogStore",
    "LegacyPaymentLogEntry",
    "PaymentLoggingClient",
    "get_in_memory_log_store",
    "create_paymob_logging_client",
    "create_paypal_logging_client",
    # New (SQLite-backed)
    "PaymentLogStore",
    "PaymentLogEntry",
    "get_payment_log_store",
    "init_payment_log_store",
    "close_payment_log_store",
    # Structured logging
    "StructuredLogger",
    "configure_structured_logging",
    "get_payment_logger",
]
