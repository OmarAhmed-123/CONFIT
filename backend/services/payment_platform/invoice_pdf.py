"""PDF invoice generation (ReportLab — no system GTK deps)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def _money(s: str | float | Decimal) -> str:
    try:
        return f"{Decimal(str(s)):.2f}"
    except Exception:
        return str(s)


def build_invoice_pdf(
    *,
    path: Path,
    invoice_number: str,
    customer_name: str,
    customer_email: str,
    order_id: str,
    lines: List[dict[str, Any]],
    subtotal: str,
    tax: str,
    total: str,
    currency: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, "CONFIT — Invoice")
    y -= 28
    c.setFont("Helvetica", 10)
    c.drawString(72, y, f"Invoice #: {invoice_number}")
    y -= 14
    c.drawString(72, y, f"Date (UTC): {datetime.now(timezone.utc).isoformat()}")
    y -= 14
    c.drawString(72, y, f"Order: {order_id}")
    y -= 24
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "Bill to")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(72, y, customer_name or "—")
    y -= 14
    c.drawString(72, y, customer_email or "—")
    y -= 28
    c.setFont("Helvetica-Bold", 10)
    c.drawString(72, y, "Item")
    c.drawString(320, y, "Qty")
    c.drawString(380, y, "Price")
    c.drawString(460, y, "Line total")
    y -= 14
    c.setFont("Helvetica", 9)
    for row in lines:
        if y < 100:
            c.showPage()
            y = height - 72
        name = str(row.get("name", "Item"))[:48]
        qty = str(row.get("quantity", 1))
        price = _money(row.get("unit_price", 0))
        lt = _money(row.get("line_total", 0))
        c.drawString(72, y, name)
        c.drawString(320, y, qty)
        c.drawString(380, y, price)
        c.drawString(460, y, lt)
        y -= 14
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(360, y, f"Subtotal ({currency})")
    c.drawString(460, y, _money(subtotal))
    y -= 14
    c.drawString(360, y, f"Tax ({currency})")
    c.drawString(460, y, _money(tax))
    y -= 16
    c.drawString(360, y, f"Total ({currency})")
    c.drawString(460, y, _money(total))
    c.showPage()
    c.save()
    logger.info("invoice pdf written %s", path)
