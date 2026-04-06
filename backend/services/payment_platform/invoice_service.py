"""Create invoice rows + PDF after successful payment."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from database.models import Order as OrderModel, User as UserModel, OrderItem as OrderItemModel
from database.payment_platform_models import Invoice
from services.payment_platform.invoice_pdf import build_invoice_pdf
from services.payment_platform.event_bus import DomainEvent, bus

logger = logging.getLogger(__name__)


def _storage_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    base = os.getenv("INVOICE_STORAGE_DIR", str(root / "storage" / "invoices"))
    return Path(base)


def generate_invoice_for_order(db: Session, *, order_id: str, payment_id: str | None) -> Invoice | None:
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        return None
    existing = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if existing:
        return existing

    user = db.query(UserModel).filter(UserModel.id == order.user_id).first()
    items = db.query(OrderItemModel).filter(OrderItemModel.order_id == order_id).all()
    lines = []
    for it in items:
        qty = int(getattr(it, "quantity", 1) or 1)
        price = float(getattr(it, "price", 0) or 0)
        lines.append(
            {
                "name": getattr(it, "name", None) or "Item",
                "quantity": qty,
                "unit_price": price,
                "line_total": price * qty,
            }
        )
    if not lines:
        lines = [{"name": "Order total", "quantity": 1, "unit_price": float(order.total), "line_total": float(order.total)}]

    inv_num = f"CONF-{uuid.uuid4().hex[:6].upper()}"
    subtotal = str(order.subtotal)
    tax = str(order.tax)
    total = str(order.total)
    currency = "USD"

    pdf_name = f"{inv_num.replace(' ', '_')}.pdf"
    pdf_path = _storage_dir() / pdf_name
    build_invoice_pdf(
        path=pdf_path,
        invoice_number=inv_num,
        customer_name=user.name if user else "",
        customer_email=user.email if user else "",
        order_id=order_id,
        lines=lines,
        subtotal=subtotal,
        tax=tax,
        total=total,
        currency=currency,
    )

    inv = Invoice(
        invoice_number=inv_num,
        order_id=order_id,
        user_id=order.user_id,
        payment_id=payment_id,
        subtotal=subtotal,
        tax=tax,
        total=total,
        currency=currency,
        pdf_storage_path=str(pdf_path.resolve()),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    logger.info("invoice_created id=%s number=%s", inv.id, inv_num)

    import asyncio

    async def _emit():
        await bus.publish(DomainEvent("invoice_created", {"invoice_id": inv.id, "order_id": order_id}))

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_emit())
        else:
            asyncio.run(_emit())
    except RuntimeError:
        asyncio.run(_emit())

    return inv
