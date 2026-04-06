"""
Post-success side effects: event bus, invoice PDF, pickup finalization.
Used synchronously from the API or from Celery worker (same code path = no drift).
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from services.payment_platform.event_bus import DomainEvent, bus
from services.payment_platform.event_bus import run_async_task

logger = logging.getLogger(__name__)


def _emit_payment_success_event(order_id: str, payment_id: str, provider: str) -> None:
    payload = {"order_id": order_id, "payment_id": payment_id, "provider": provider}

    async def _pub() -> None:
        await bus.publish(DomainEvent("payment_success", payload))

    run_async_task(_pub())


def _emit_pickup(order_id: str) -> None:
    from services.payment_platform.pickup_finalize import finalize_pickup_after_online_payment

    async def _run() -> None:
        await finalize_pickup_after_online_payment(order_id)

    run_async_task(_run())


def run_post_payment_success_sync(db: Session, *, order_id: str, payment_id: str, provider: str) -> None:
    """Idempotent invoice; pickup finalize is idempotent; bus may run multiple times."""
    _emit_payment_success_event(order_id, payment_id, provider)

    from services.payment_platform.invoice_service import generate_invoice_for_order

    generate_invoice_for_order(db, order_id=order_id, payment_id=payment_id)

    _emit_pickup(order_id)

    # Placeholder for transactional email (SES/SendGrid/etc.)
    logger.info("payment_receipt_email_deferred order_id=%s payment_id=%s", order_id, payment_id)


def schedule_post_payment_success(order_id: str, payment_id: str, provider: str) -> None:
    """
    Enqueue Celery when PAYMENT_USE_CELERY=1 and broker is reachable; else run inline.
    """
    use_celery = os.getenv("PAYMENT_USE_CELERY", "").lower() in ("1", "true", "yes")
    if use_celery:
        try:
            from workers.payment_tasks import process_payment_success

            process_payment_success.delay(order_id, payment_id, provider)
            logger.info("payment_success_enqueued_celery order_id=%s payment_id=%s", order_id, payment_id)
            return
        except Exception:
            logger.exception("Celery enqueue failed; falling back to synchronous post-payment workflow")

    from database.session import SessionLocal

    db2 = SessionLocal()
    try:
        run_post_payment_success_sync(db2, order_id=order_id, payment_id=payment_id, provider=provider)
    finally:
        db2.close()
