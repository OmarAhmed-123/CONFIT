"""
CONFIT Backend — Domain Events (in-process)
==========================================
Single-source-of-truth domain events for the backend.

This is intentionally in-process (no external broker) but keeps a clean
publish/subscribe boundary so we can later swap to Redis/Kafka without
duplicating business logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, DefaultDict
from collections import defaultdict

logger = logging.getLogger(__name__)


EVENT_ORDER_PICKUP_SELECTED = "order.pickup_selected"
EVENT_ORDER_PLACED = "order.placed"
EVENT_PAYMENT_SUCCESS = "payment.success"
EVENT_ORDER_SHIPPED = "order.shipped"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    occurred_at: datetime
    payload: dict[str, Any]


Handler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        handlers = list(self._handlers.get(event.name, []))
        if not handlers:
            return
        for h in handlers:
            try:
                h(event)
            except Exception:
                logger.exception("Domain event handler failed (%s)", event.name)


event_bus = EventBus()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)

