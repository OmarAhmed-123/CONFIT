"""
Payment API Log Store — SQLite Persistent Storage
=================================================
Async SQLite-backed store for payment request/response logs.
Provides persistence, filtering, pagination, and automatic cleanup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, AsyncIterator

import aiosqlite

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "payment_logs.db")

# Configuration
MAX_ROWS = 10_000
CLEANUP_DAYS = 7
CLEANUP_INTERVAL_HOURS = 24


@dataclass
class PaymentLogEntry:
    """A single payment API request/response log entry."""
    id: str
    trace_id: str
    correlation_id: str
    provider: str  # "paymob" or "paypal"
    timestamp: str
    request_method: str
    request_url: str
    request_headers: Dict[str, Any]
    request_payload: Optional[Dict[str, Any]]
    request_params: Optional[Dict[str, Any]]
    response_status_code: Optional[int]
    response_headers: Dict[str, Any]
    response_body: Optional[Any]
    latency_ms: float
    success: bool
    error: Optional[str]
    logging_overhead_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaymentLogStore:
    """
    Async SQLite-backed store for payment logs.
    Thread-safe for single-process usage with async operations.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.abspath(DEFAULT_DB_PATH)
        self._db: Optional[aiosqlite.Connection] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database and start cleanup task."""
        if self._initialized:
            return
        
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        
        await self._init_tables()
        await self._run_migrations()
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self._initialized = True
        logger.info(f"Payment log store initialized at {self.db_path}")
    
    async def close(self) -> None:
        """Close database connection and stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        if self._db:
            await self._db.close()
            self._db = None
        
        self._initialized = False
        logger.info("Payment log store closed")
    
    async def _init_tables(self) -> None:
        """Initialize database tables."""
        assert self._db is not None
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS payment_logs (
                id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                request_method TEXT NOT NULL,
                request_url TEXT NOT NULL,
                request_headers TEXT DEFAULT '{}',
                request_payload TEXT,
                request_params TEXT,
                response_status_code INTEGER,
                response_headers TEXT DEFAULT '{}',
                response_body TEXT,
                latency_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                error TEXT,
                logging_overhead_ms REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for efficient queries
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_logs_trace_id 
            ON payment_logs(trace_id)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_logs_correlation_id 
            ON payment_logs(correlation_id)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_logs_provider 
            ON payment_logs(provider)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_logs_timestamp 
            ON payment_logs(timestamp)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payment_logs_success 
            ON payment_logs(success)
        """)
        
        await self._db.commit()
    
    async def _run_migrations(self) -> None:
        """Run database migrations."""
        assert self._db is not None
        
        # Migration 1: Add logging_overhead_ms column if not exists
        cursor = await self._db.execute("PRAGMA table_info(payment_logs)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if "logging_overhead_ms" not in columns:
            await self._db.execute(
                "ALTER TABLE payment_logs ADD COLUMN logging_overhead_ms REAL"
            )
            await self._db.commit()
            logger.info("Migration: Added logging_overhead_ms column")
    
    async def add_entry(self, entry: PaymentLogEntry) -> None:
        """Add a log entry to the store."""
        assert self._db is not None
        
        await self._db.execute("""
            INSERT INTO payment_logs 
            (id, trace_id, correlation_id, provider, timestamp, 
             request_method, request_url, request_headers, request_payload, request_params,
             response_status_code, response_headers, response_body, 
             latency_ms, success, error, logging_overhead_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.trace_id,
            entry.correlation_id,
            entry.provider,
            entry.timestamp,
            entry.request_method,
            entry.request_url,
            json.dumps(entry.request_headers),
            json.dumps(entry.request_payload) if entry.request_payload else None,
            json.dumps(entry.request_params) if entry.request_params else None,
            entry.response_status_code,
            json.dumps(entry.response_headers),
            json.dumps(entry.response_body) if entry.response_body else None,
            entry.latency_ms,
            1 if entry.success else 0,
            entry.error,
            entry.logging_overhead_ms,
        ))
        await self._db.commit()
    
    async def get_entries(
        self,
        page: int = 1,
        page_size: int = 50,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> tuple[List[PaymentLogEntry], int]:
        """
        Get paginated log entries with optional filters.
        Returns (entries, total_count).
        """
        assert self._db is not None
        
        # Build query
        conditions: List[str] = []
        params: List[Any] = []
        
        if provider:
            conditions.append("provider = ?")
            params.append(provider.lower())
        
        if status:
            if status.lower() == "success":
                conditions.append("success = 1")
            elif status.lower() == "failure":
                conditions.append("success = 0")
        
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        
        if correlation_id:
            conditions.append("correlation_id = ?")
            params.append(correlation_id)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM payment_logs WHERE {where_clause}"
        cursor = await self._db.execute(count_query, params)
        total_count = (await cursor.fetchone())[0]
        
        # Get paginated entries
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT * FROM payment_logs 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """
        cursor = await self._db.execute(data_query, params + [page_size, offset])
        rows = await cursor.fetchall()
        
        entries = [self._row_to_entry(row) for row in rows]
        return entries, total_count
    
    async def get_by_trace_id(self, trace_id: str) -> Optional[PaymentLogEntry]:
        """Get a specific log entry by trace ID."""
        assert self._db is not None
        
        cursor = await self._db.execute(
            "SELECT * FROM payment_logs WHERE trace_id = ?",
            (trace_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_entry(row) if row else None
    
    async def get_by_correlation_id(self, correlation_id: str) -> List[PaymentLogEntry]:
        """Get all log entries for a correlation ID (request + response pair)."""
        assert self._db is not None
        
        cursor = await self._db.execute(
            "SELECT * FROM payment_logs WHERE correlation_id = ? ORDER BY timestamp",
            (correlation_id,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]
    
    async def get_failed_entries(self, limit: int = 50) -> List[PaymentLogEntry]:
        """Get failed requests for replay functionality."""
        assert self._db is not None
        
        cursor = await self._db.execute(
            "SELECT * FROM payment_logs WHERE success = 0 ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]
    
    async def get_recent_entries(self, limit: int = 100) -> List[PaymentLogEntry]:
        """Get most recent entries."""
        assert self._db is not None
        
        cursor = await self._db.execute(
            "SELECT * FROM payment_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]
    
    async def count_entries(self) -> int:
        """Get total entry count."""
        assert self._db is not None
        
        cursor = await self._db.execute("SELECT COUNT(*) FROM payment_logs")
        return (await cursor.fetchone())[0]
    
    async def cleanup_old_entries(self, days: int = CLEANUP_DAYS) -> int:
        """Remove entries older than specified days."""
        assert self._db is not None
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cursor = await self._db.execute(
            "DELETE FROM payment_logs WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        deleted = cursor.rowcount
        await self._db.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old payment log entries (older than {days} days)")
        
        return deleted
    
    async def enforce_max_rows(self, max_rows: int = MAX_ROWS) -> int:
        """Delete oldest entries if total exceeds max_rows."""
        assert self._db is not None
        
        count = await self.count_entries()
        if count <= max_rows:
            return 0
        
        excess = count - max_rows
        cursor = await self._db.execute("""
            DELETE FROM payment_logs 
            WHERE id IN (
                SELECT id FROM payment_logs 
                ORDER BY timestamp ASC 
                LIMIT ?
            )
        """, (excess,))
        deleted = cursor.rowcount
        await self._db.commit()
        
        if deleted > 0:
            logger.info(f"Enforced max rows: deleted {deleted} oldest entries (limit: {max_rows})")
        
        return deleted
    
    async def clear_all(self) -> None:
        """Clear all log entries."""
        assert self._db is not None
        
        await self._db.execute("DELETE FROM payment_logs")
        await self._db.commit()
        logger.info("Cleared all payment log entries")
    
    def _row_to_entry(self, row: aiosqlite.Row) -> PaymentLogEntry:
        """Convert a database row to a PaymentLogEntry."""
        return PaymentLogEntry(
            id=row["id"],
            trace_id=row["trace_id"],
            correlation_id=row["correlation_id"],
            provider=row["provider"],
            timestamp=row["timestamp"],
            request_method=row["request_method"],
            request_url=row["request_url"],
            request_headers=json.loads(row["request_headers"] or "{}"),
            request_payload=json.loads(row["request_payload"]) if row["request_payload"] else None,
            request_params=json.loads(row["request_params"]) if row["request_params"] else None,
            response_status_code=row["response_status_code"],
            response_headers=json.loads(row["response_headers"] or "{}"),
            response_body=json.loads(row["response_body"]) if row["response_body"] else None,
            latency_ms=row["latency_ms"],
            success=bool(row["success"]),
            error=row["error"],
            logging_overhead_ms=row["logging_overhead_ms"],
        )
    
    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)
                
                # Cleanup old entries
                await self.cleanup_old_entries(CLEANUP_DAYS)
                
                # Enforce max rows
                await self.enforce_max_rows(MAX_ROWS)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Payment log cleanup error: {e}")
    
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for transactional operations."""
        assert self._db is not None
        try:
            yield self._db
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise


# Global store instance
_payment_log_store: Optional[PaymentLogStore] = None


def get_payment_log_store() -> PaymentLogStore:
    """Get or create the global payment log store (sync factory)."""
    global _payment_log_store
    if _payment_log_store is None:
        _payment_log_store = PaymentLogStore()
    return _payment_log_store


async def init_payment_log_store() -> PaymentLogStore:
    """Initialize and return the global payment log store (async init)."""
    store = get_payment_log_store()
    if not store._initialized:
        await store.initialize()
    return store


async def close_payment_log_store() -> None:
    """Close the global payment log store."""
    global _payment_log_store
    if _payment_log_store:
        await _payment_log_store.close()
