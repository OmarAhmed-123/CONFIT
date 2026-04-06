"""
Store-scoped repository helpers for sales analytics.
Enforces tenant scoping and sets PostgreSQL RLS context.
"""

from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from database.sales_analytics_models import SalesTransaction


class SalesAnalyticsRepository:
    def __init__(self, db: Session, store_id: UUID, slow_query_ms: int = 500) -> None:
        self._db = db
        self._store_id = store_id
        self._slow_query_ms = slow_query_ms

    @property
    def store_id(self) -> UUID:
        return self._store_id

    def apply_store_scope(self) -> None:
        """
        Applies PostgreSQL RLS context for current transaction.
        Safe no-op on SQLite or non-PostgreSQL engines.
        """
        bind = self._db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return
        self._db.execute(
            text("SELECT set_config('app.current_store_id', :store_id, true)"),
            {"store_id": str(self._store_id)},
        )

    def base_sales_query(self):
        return select(SalesTransaction).where(
            SalesTransaction.store_id == self._store_id,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active.is_(True),
        )

    def time_query(self, callback):
        started = time.perf_counter()
        result = callback()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        # lightweight hook for telemetry logs in service layer
        return result, elapsed_ms, elapsed_ms > self._slow_query_ms
