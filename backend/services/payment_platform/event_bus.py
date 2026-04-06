"""
Event bus for payment domain events.

Production mode (ASYNC_EVENT_BUS=1): Uses Redis streams for durability
Development mode (default): In-process dispatcher with BackgroundTasks

Both modes use the same event names and handler signatures for seamless upgrade.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class DomainEvent:
    name: str
    payload: Dict[str, Any]
    id: Optional[str] = None
    correlation_id: Optional[str] = None

    @classmethod
    def create(cls, name: str, payload: Dict[str, Any], correlation_id: Optional[str] = None) -> "DomainEvent":
        import uuid
        return cls(
            id=f"evt_{uuid.uuid4().hex[:16]}",
            name=name,
            payload=payload,
            correlation_id=correlation_id,
        )


class PaymentEventBus:
    """
    Event bus that supports both in-process and async Redis modes.

    Set ASYNC_EVENT_BUS=1 to enable Redis-backed async event bus.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._async_mode = os.getenv("ASYNC_EVENT_BUS", "").lower() in ("1", "true", "yes")
        self._async_bus = None

    def subscribe(self, name: str, handler: EventHandler) -> None:
        self._handlers.setdefault(name, []).append(handler)
        if self._async_mode:
            self._register_async_handler(name, handler)

    def _register_async_handler(self, name: str, handler: EventHandler) -> None:
        """Register handler with async bus when available."""
        # Lazy import to avoid circular dependencies
        try:
            from services.payment_platform.async_event_bus import async_bus
            async def _wrapper(event):
                # Convert async_bus DomainEvent to legacy format
                await handler(event.payload)
            async_bus.subscribe(name, _wrapper)
        except ImportError:
            logger.debug("async_event_bus not available, using in-process mode")

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to handlers."""
        logger.info(
            "event_bus publish name=%s keys=%s async_mode=%s",
            event.name,
            list(event.payload.keys()),
            self._async_mode,
        )

        if self._async_mode:
            await self._publish_async(event)
        else:
            await self._publish_in_process(event)

    async def _publish_async(self, event: DomainEvent) -> None:
        """Publish to Redis stream (production mode)."""
        try:
            from services.payment_platform.async_event_bus import async_bus, DomainEvent as AsyncDomainEvent
            async_event = AsyncDomainEvent.create(
                name=event.name,
                payload=event.payload,
                correlation_id=event.correlation_id,
            )
            await async_bus.publish(async_event)
        except Exception:
            logger.exception("async_publish_failed falling back to in-process")
            await self._publish_in_process(event)

    async def _publish_in_process(self, event: DomainEvent) -> None:
        """Publish to in-process handlers (development mode)."""
        for h in self._handlers.get(event.name, []):
            try:
                await h(event.payload)
            except Exception:
                logger.exception("event handler failed for %s", event.name)

    def publish_sync(self, event: DomainEvent) -> None:
        """Publish from sync context (e.g., after DB commit)."""
        run_async_task(self.publish(event))


# Global event bus instance
bus = PaymentEventBus()


def run_async_task(coro: Awaitable[None]) -> None:
    """Schedule coroutine from sync code (e.g. after DB commit)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            asyncio.run(coro)
    except RuntimeError:
        asyncio.run(coro)
