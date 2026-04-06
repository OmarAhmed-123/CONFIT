"""
Celery tasks for payment post-processing.

Registered by importing this module after `celery_app` is constructed (see workers/celery_app.py).

Tasks:
- process_payment_success: Invoice, pickup finalize, email trigger
- process_payment_failed: Log, notify user, update metrics
- send_payment_receipt_email: Transactional email via provider
- dead_letter_handler: Retry from DLQ with manual intervention
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery import Task
from celery.exceptions import Reject

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Idempotency cache key prefix for task dedup
IDEMPOTENCY_PREFIX = "payment_task_idem"


class PaymentSideEffectTask(Task):
    """Base task with retry, DLQ routing, and idempotency."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 5, "countdown": 15}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "payment_task_permanent_failure task_id=%s args=%s exc=%s",
            task_id,
            args,
            exc,
            exc_info=einfo,
        )
        # DLQ: push to dead_letter queue for manual inspection
        self._push_to_dlq(task_id, args, kwargs, exc, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "payment_task_retry task_id=%s attempt=%s/%s exc=%s",
            task_id,
            self.request.retries,
            self.max_retries,
            exc,
        )

    def _push_to_dlq(
        self,
        task_id: str,
        args: tuple,
        kwargs: dict,
        exc: Exception,
        einfo,
    ) -> None:
        """Push failed task to dead_letter queue for manual intervention."""
        try:
            import redis
            r = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
            dlq_key = "dead_letter:payments"
            entry = {
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "traceback": str(einfo) if einfo else None,
            }
            r.rpush(dlq_key, json.dumps(entry, default=str))
            logger.info("dlq_pushed task_id=%s queue=%s", task_id, dlq_key)
        except Exception:
            logger.exception("dlq_push_failed task_id=%s", task_id)


class IdempotentPaymentTask(PaymentSideEffectTask):
    """Task that checks idempotency before execution."""

    def __call__(self, *args, **kwargs):
        idem_key = kwargs.get("idempotency_key") or self._derive_idempotency_key(args)
        if idem_key and self._is_duplicate(idem_key):
            logger.info("task_duplicate_skipped idempotency_key=%s", idem_key)
            return {"ok": True, "duplicate": True, "idempotency_key": idem_key}
        result = super().__call__(*args, **kwargs)
        if idem_key:
            self._mark_completed(idem_key)
        return result

    def _derive_idempotency_key(self, args: tuple) -> Optional[str]:
        """Derive idempotency key from task arguments."""
        if len(args) >= 2:
            return f"{IDEMPOTENCY_PREFIX}:{args[0]}:{args[1]}"
        return None

    def _is_duplicate(self, key: str) -> bool:
        try:
            import redis
            r = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
            return r.exists(f"{key}:completed")
        except Exception:
            return False

    def _mark_completed(self, key: str) -> None:
        try:
            import redis
            r = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
            r.setex(f"{key}:completed", 86400 * 7, "1")  # 7 day TTL
        except Exception:
            pass


@celery_app.task(
    bind=True,
    base=IdempotentPaymentTask,
    name="workers.payment_tasks.process_payment_success",
    queue="payments",
    ignore_result=False,
)
def process_payment_success(
    self,
    order_id: str,
    payment_id: str,
    provider: str,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Process successful payment: invoice, pickup, email notification."""
    from database.session import SessionLocal
    from services.payment_platform.post_payment_workflow import run_post_payment_success_sync

    logger.info(
        "celery_payment_success_start task_id=%s order_id=%s payment_id=%s provider=%s",
        self.request.id,
        order_id,
        payment_id,
        provider,
    )
    db = SessionLocal()
    try:
        run_post_payment_success_sync(db, order_id=order_id, payment_id=payment_id, provider=provider)
        # Trigger email task
        send_payment_receipt_email.delay(order_id, payment_id)
        return {"ok": True, "order_id": order_id, "payment_id": payment_id}
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=PaymentSideEffectTask,
    name="workers.payment_tasks.process_payment_failed",
    queue="payments",
    ignore_result=False,
)
def process_payment_failed(
    self,
    order_id: str,
    payment_id: str,
    provider: str,
    reason: str,
) -> dict:
    """Handle failed payment: log, update metrics, notify user."""
    from database.session import SessionLocal
    from database.models import Order as OrderModel
    from database.payment_platform_models import Payment

    logger.warning(
        "celery_payment_failed task_id=%s order_id=%s payment_id=%s provider=%s reason=%s",
        self.request.id,
        order_id,
        payment_id,
        provider,
        reason,
    )
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = "failed"
            db.commit()
        # Emit event for observability
        from services.payment_platform.event_bus import DomainEvent, bus
        import asyncio
        async def _emit():
            await bus.publish(DomainEvent("payment_failed", {
                "order_id": order_id,
                "payment_id": payment_id,
                "provider": provider,
                "reason": reason,
            }))
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_emit())
            else:
                asyncio.run(_emit())
        except RuntimeError:
            asyncio.run(_emit())
        return {"ok": True, "order_id": order_id, "payment_id": payment_id, "reason": reason}
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=PaymentSideEffectTask,
    name="workers.payment_tasks.send_payment_receipt_email",
    queue="emails",
    ignore_result=False,
)
def send_payment_receipt_email(self, order_id: str, payment_id: str) -> dict:
    """Send payment receipt email via configured provider (SES, SendGrid, etc.)."""
    import os
    from database.session import SessionLocal
    from database.models import Order as OrderModel, User as UserModel
    from database.payment_platform_models import Invoice

    logger.info(
        "celery_send_receipt_email task_id=%s order_id=%s payment_id=%s",
        self.request.id,
        order_id,
        payment_id,
    )
    db = SessionLocal()
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order:
            logger.warning("send_receipt_email: order not found order_id=%s", order_id)
            return {"ok": False, "error": "order_not_found"}
        user = db.query(UserModel).filter(UserModel.id == order.user_id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
        if not user or not user.email:
            logger.warning("send_receipt_email: no user email order_id=%s", order_id)
            return {"ok": False, "error": "no_email"}
        # Email provider selection
        provider = os.getenv("EMAIL_PROVIDER", "ses").lower()
        try:
            if provider == "ses":
                _send_via_ses(user.email, order, invoice)
            elif provider == "sendgrid":
                _send_via_sendgrid(user.email, order, invoice)
            elif provider == "mock":
                logger.info("mock_email_sent to=%s order_id=%s", user.email, order_id)
            else:
                logger.warning("send_receipt_email: unknown provider=%s", provider)
            return {"ok": True, "email": user.email, "order_id": order_id}
        except Exception as e:
            logger.exception("send_receipt_email_failed order_id=%s", order_id)
            raise
    finally:
        db.close()


def _send_via_ses(email: str, order, invoice) -> None:
    """Send via AWS SES."""
    import os
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    ses = boto3.client("ses", region_name=os.getenv("AWS_SES_REGION", "us-east-1"))
    sender = os.getenv("SES_SENDER_EMAIL", "noreply@confit.app")
    subject = f"Your CONFIT Order #{order.order_number or order.id} - Receipt"
    html = _build_receipt_html(order, invoice)
    ses.send_email(
        Source=sender,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": html}},
        },
    )
    logger.info("ses_email_sent to=%s order_id=%s", email, order.id)


def _send_via_sendgrid(email: str, order, invoice) -> None:
    """Send via SendGrid."""
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    sender = os.getenv("SENDGRID_SENDER_EMAIL", "noreply@confit.app")
    subject = f"Your CONFIT Order #{order.order_number or order.id} - Receipt"
    html = _build_receipt_html(order, invoice)
    msg = Mail(from_email=sender, to_emails=email, subject=subject, html_content=html)
    sg.send(msg)
    logger.info("sendgrid_email_sent to=%s order_id=%s", email, order.id)


def _build_receipt_html(order, invoice) -> str:
    """Build receipt email HTML body."""
    inv_num = invoice.invoice_number if invoice else f"ORD-{order.id[:8]}"
    total = order.total if hasattr(order, "total") else "N/A"
    return f"""
    <html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
    <h1 style="color: #1a1a1a;">Thank you for your order!</h1>
    <p>Your order <strong>#{order.order_number or order.id}</strong> has been confirmed.</p>
    <p>Invoice: <strong>{inv_num}</strong></p>
    <p>Total: <strong>${total}</strong></p>
    <p>We'll notify you when your items are on the way.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="color: #666; font-size: 12px;">CONFIT — AI-Powered Fashion</p>
    </body></html>
    """


@celery_app.task(
    bind=True,
    name="workers.payment_tasks.replay_dlq_task",
    queue="payments",
)
def replay_dlq_task(self, limit: int = 10) -> dict:
    """Replay tasks from dead letter queue. Use with caution."""
    import os
    import json
    import redis

    r = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    dlq_key = "dead_letter:payments"
    replayed = []
    for _ in range(limit):
        raw = r.lpop(dlq_key)
        if not raw:
            break
        entry = json.loads(raw)
        task_name = entry.get("task_name")
        args = entry.get("args", [])
        kwargs = entry.get("kwargs", {})
        try:
            if task_name == "workers.payment_tasks.process_payment_success":
                process_payment_success.delay(*args, **kwargs)
                replayed.append({"task_id": entry.get("task_id"), "status": "replayed"})
            elif task_name == "workers.payment_tasks.process_payment_failed":
                process_payment_failed.delay(*args, **kwargs)
                replayed.append({"task_id": entry.get("task_id"), "status": "replayed"})
            else:
                logger.warning("replay_dlq: unknown task_name=%s", task_name)
                replayed.append({"task_id": entry.get("task_id"), "status": "unknown_task"})
        except Exception as e:
            logger.exception("replay_dlq_failed task_id=%s", entry.get("task_id"))
            replayed.append({"task_id": entry.get("task_id"), "status": "failed", "error": str(e)})
    return {"replayed": replayed, "count": len(replayed)}
