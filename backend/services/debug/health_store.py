"""
Health Check History Store
==========================
Persists health check results to SQLite for historical analysis.
Enables correlation between payment failures and infrastructure events.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "health_history.db")


@dataclass
class HealthHistoryEntry:
    """A single health check history entry."""
    id: str
    provider: str
    check_name: str
    status: str
    latency_ms: float
    message: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertEntry:
    """An alert entry for in-app notifications."""
    id: str
    provider: str
    check_name: str
    status: str  # "fail", "warn"
    message: str
    timestamp: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HealthHistoryStore:
    """
    SQLite-backed store for health check history.
    Thread-safe for single-process usage.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.abspath(DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Health history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_history (
                        id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        check_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        latency_ms REAL NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        details TEXT DEFAULT '{}',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Index for efficient queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_history_provider 
                    ON health_history(provider)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_history_timestamp 
                    ON health_history(timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_history_status 
                    ON health_history(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_history_check_name 
                    ON health_history(check_name)
                """)
                
                # Alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        check_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        acknowledged INTEGER DEFAULT 0,
                        acknowledged_at TEXT,
                        acknowledged_by TEXT,
                        details TEXT DEFAULT '{}'
                    )
                """)
                
                # Index for alerts
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged 
                    ON alerts(acknowledged)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                    ON alerts(timestamp)
                """)
                
                # Alert state tracking (for edge-triggered alerts)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_state (
                        provider TEXT NOT NULL,
                        check_name TEXT NOT NULL,
                        last_status TEXT NOT NULL,
                        last_alerted_at TEXT,
                        PRIMARY KEY (provider, check_name)
                    )
                """)
                
                conn.commit()
                logger.info(f"Health history database initialized at {self.db_path}")
            finally:
                conn.close()
    
    def add_health_entry(self, entry: HealthHistoryEntry) -> None:
        """Add a health check entry to history."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO health_history 
                    (id, provider, check_name, status, latency_ms, message, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.provider,
                    entry.check_name,
                    entry.status,
                    entry.latency_ms,
                    entry.message,
                    entry.timestamp,
                    json.dumps(entry.details),
                ))
                conn.commit()
            finally:
                conn.close()
    
    def add_health_entries(self, entries: List[HealthHistoryEntry]) -> None:
        """Add multiple health check entries to history."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                for entry in entries:
                    cursor.execute("""
                        INSERT INTO health_history 
                        (id, provider, check_name, status, latency_ms, message, timestamp, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.id,
                        entry.provider,
                        entry.check_name,
                        entry.status,
                        entry.latency_ms,
                        entry.message,
                        entry.timestamp,
                        json.dumps(entry.details),
                    ))
                conn.commit()
            finally:
                conn.close()
    
    def get_health_history(
        self,
        limit: int = 100,
        offset: int = 0,
        provider: Optional[str] = None,
        check_name: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[HealthHistoryEntry]:
        """Get health history with optional filters."""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM health_history WHERE 1=1"
            params: List[Any] = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            if check_name:
                query += " AND check_name = ?"
                params.append(check_name)
            if status:
                query += " AND status = ?"
                params.append(status)
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                HealthHistoryEntry(
                    id=row["id"],
                    provider=row["provider"],
                    check_name=row["check_name"],
                    status=row["status"],
                    latency_ms=row["latency_ms"],
                    message=row["message"],
                    timestamp=row["timestamp"],
                    details=json.loads(row["details"] or "{}"),
                )
                for row in rows
            ]
        finally:
            conn.close()
    
    def get_health_history_count(
        self,
        provider: Optional[str] = None,
        check_name: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> int:
        """Get count of health history entries matching filters."""
        conn = self._get_connection()
        try:
            query = "SELECT COUNT(*) FROM health_history WHERE 1=1"
            params: List[Any] = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            if check_name:
                query += " AND check_name = ?"
                params.append(check_name)
            if status:
                query += " AND status = ?"
                params.append(status)
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        with self._lock:
            conn = self._get_connection()
            try:
                cutoff = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM health_history WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ALERTS
    # ─────────────────────────────────────────────────────────────────────────
    
    def add_alert(self, alert: AlertEntry) -> None:
        """Add an alert entry."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alerts 
                    (id, provider, check_name, status, message, timestamp, 
                     acknowledged, acknowledged_at, acknowledged_by, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.id,
                    alert.provider,
                    alert.check_name,
                    alert.status,
                    alert.message,
                    alert.timestamp,
                    1 if alert.acknowledged else 0,
                    alert.acknowledged_at,
                    alert.acknowledged_by,
                    json.dumps(alert.details),
                ))
                conn.commit()
            finally:
                conn.close()
    
    def get_alerts(
        self,
        limit: int = 50,
        unacknowledged_first: bool = True,
    ) -> List[AlertEntry]:
        """Get alerts, optionally sorted with unacknowledged first."""
        conn = self._get_connection()
        try:
            if unacknowledged_first:
                query = """
                    SELECT * FROM alerts 
                    ORDER BY acknowledged ASC, timestamp DESC 
                    LIMIT ?
                """
            else:
                query = """
                    SELECT * FROM alerts 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
            
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            return [
                AlertEntry(
                    id=row["id"],
                    provider=row["provider"],
                    check_name=row["check_name"],
                    status=row["status"],
                    message=row["message"],
                    timestamp=row["timestamp"],
                    acknowledged=bool(row["acknowledged"]),
                    acknowledged_at=row["acknowledged_at"],
                    acknowledged_by=row["acknowledged_by"],
                    details=json.loads(row["details"] or "{}"),
                )
                for row in rows
            ]
        finally:
            conn.close()
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: Optional[str] = None,
    ) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alerts 
                    SET acknowledged = 1, 
                        acknowledged_at = ?, 
                        acknowledged_by = ?
                    WHERE id = ? AND acknowledged = 0
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    acknowledged_by,
                    alert_id,
                ))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()
    
    def get_unacknowledged_count(self) -> int:
        """Get count of unacknowledged alerts."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ALERT STATE (Edge-Triggered Logic)
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_last_check_status(self, provider: str, check_name: str) -> Optional[str]:
        """Get the last known status for a check."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_status FROM alert_state 
                WHERE provider = ? AND check_name = ?
            """, (provider, check_name))
            row = cursor.fetchone()
            return row["last_status"] if row else None
        finally:
            conn.close()
    
    def update_check_status(
        self,
        provider: str,
        check_name: str,
        status: str,
    ) -> Optional[str]:
        """
        Update check status and return previous status if changed.
        Returns None if status unchanged or first time.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Get current state
                cursor.execute("""
                    SELECT last_status FROM alert_state 
                    WHERE provider = ? AND check_name = ?
                """, (provider, check_name))
                row = cursor.fetchone()
                
                previous_status = row["last_status"] if row else None
                
                # Update or insert
                cursor.execute("""
                    INSERT INTO alert_state (provider, check_name, last_status, last_alerted_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(provider, check_name) 
                    DO UPDATE SET last_status = ?
                """, (
                    provider,
                    check_name,
                    status,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                ))
                conn.commit()
                
                # Return previous if changed
                if previous_status and previous_status != status:
                    return previous_status
                return None
            finally:
                conn.close()
    
    def should_alert(
        self,
        provider: str,
        check_name: str,
        current_status: str,
    ) -> bool:
        """
        Determine if an alert should be sent (edge-triggered logic).
        Only alert on state change to fail/warn, not on recurring failures.
        """
        # Only alert on fail or warn
        if current_status not in ("fail", "warn"):
            return False
        
        previous_status = self.get_last_check_status(provider, check_name)
        
        # First time seeing this check - alert
        if previous_status is None:
            return True
        
        # Status changed from pass/skip to fail/warn - alert
        if previous_status in ("pass", "skip") and current_status in ("fail", "warn"):
            return True
        
        # Status changed from fail to warn or vice versa - alert
        if previous_status != current_status:
            return True
        
        # Same status as before - don't re-alert
        return False
    
    def mark_alerted(self, provider: str, check_name: str) -> None:
        """Mark that an alert was sent for this check."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alert_state 
                    SET last_alerted_at = ?
                    WHERE provider = ? AND check_name = ?
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    provider,
                    check_name,
                ))
                conn.commit()
            finally:
                conn.close()


# Global store instance
_health_store: Optional[HealthHistoryStore] = None


def get_health_store() -> HealthHistoryStore:
    """Get or create the global health history store."""
    global _health_store
    if _health_store is None:
        _health_store = HealthHistoryStore()
    return _health_store
