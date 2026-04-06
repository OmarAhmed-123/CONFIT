"""
CONFIT Backend - AI Cost Tracker Service
========================================
Tracks costs across all AI services with daily aggregation and kill-switch.

Features:
- Per-service cost tracking
- Daily budget enforcement
- Redis real-time counters
- PostgreSQL persistence
- Admin dashboard endpoints
- Kill-switch for budget overrun
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
AI_DAILY_BUDGET_USD = float(os.getenv("AI_DAILY_BUDGET_USD", "100.0"))
AI_BUDGET_WARNING_THRESHOLD = float(os.getenv("AI_BUDGET_WARNING_THRESHOLD", "0.8"))  # 80%
AI_BUDGET_KILL_THRESHOLD = float(os.getenv("AI_BUDGET_KILL_THRESHOLD", "1.0"))  # 100%


class AIService(str, Enum):
    """Supported AI services."""
    MUSE = "muse"
    MIRROR = "mirror"
    VISUAL_SEARCH = "visual_search"
    WARDROBE = "wardrobe"


@dataclass
class CostEntry:
    """A single cost tracking entry."""
    id: Optional[str] = None
    service: str = ""
    model: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DailyCostSummary:
    """Daily cost summary for a service."""
    date: date
    service: str
    total_cost_usd: float
    total_calls: int
    total_tokens_in: int
    total_tokens_out: int
    avg_latency_ms: float
    success_rate: float
    unique_users: int


@dataclass
class BudgetStatus:
    """Current budget status."""
    daily_budget_usd: float
    spent_usd: float
    remaining_usd: float
    percent_used: float
    is_warning: bool
    is_exceeded: bool
    kill_switch_active: bool


class AICostTracker:
    """
    AI Cost Tracker Service.
    
    Tracks costs across all AI services with budget enforcement.
    
    Usage:
        tracker = AICostTracker(db, redis)
        
        # Track a call
        await tracker.track(
            service="muse",
            model="gpt-4o",
            user_id="user-123",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.0125,
            latency_ms=1500,
        )
        
        # Check budget
        status = await tracker.get_budget_status()
        if status.is_exceeded:
            raise Exception("Daily budget exceeded")
    """
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._kill_switch_active = False
    
    # ==========================================
    # Main Tracking Method
    # ==========================================
    
    async def track(
        self,
        service: str,
        model: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Track an AI service call.
        
        Updates Redis counters in real-time and queues DB write.
        
        Args:
            service: Service name (muse, mirror, etc.)
            model: Model identifier
            user_id: User UUID
            session_id: Session ID
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_usd: Cost in USD
            latency_ms: Latency in milliseconds
            success: Whether call succeeded
            error_message: Error if failed
            metadata: Additional metadata
            
        Returns:
            True if tracked successfully
        """
        import uuid
        
        entry = CostEntry(
            id=str(uuid.uuid4()),
            service=service,
            model=model,
            user_id=user_id,
            session_id=session_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
        
        # 1. Update Redis real-time counters
        self._update_redis_counters(entry)
        
        # 2. Check budget and potentially activate kill-switch
        budget_status = await self.get_budget_status()
        if budget_status.is_exceeded:
            self._kill_switch_active = True
            logger.warning(f"AI budget exceeded: ${budget_status.spent_usd:.2f} / ${budget_status.daily_budget_usd:.2f}")
        
        # 3. Queue async write to database
        await self._persist_entry(entry)
        
        return True
    
    def _update_redis_counters(self, entry: CostEntry) -> None:
        """Update Redis counters for real-time monitoring."""
        if not self.redis:
            return
        
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Global daily cost
            self.redis.incrbyfloat(
                f"ai:cost:daily:{today}:total",
                entry.cost_usd
            )
            
            # Per-service daily cost
            self.redis.incrbyfloat(
                f"ai:cost:daily:{today}:service:{entry.service}",
                entry.cost_usd
            )
            
            # Per-service call count
            self.redis.incr(
                f"ai:calls:daily:{today}:service:{entry.service}"
            )
            
            # Per-user daily cost
            if entry.user_id:
                self.redis.incrbyfloat(
                    f"ai:cost:daily:{today}:user:{entry.user_id}",
                    entry.cost_usd
                )
            
            # Set TTL (36 hours)
            ttl = 129600
            for key in [
                f"ai:cost:daily:{today}:total",
                f"ai:cost:daily:{today}:service:{entry.service}",
                f"ai:calls:daily:{today}:service:{entry.service}",
            ]:
                self.redis.expire(key, ttl, nx=True)
            
        except Exception as e:
            logger.warning(f"Failed to update Redis counters: {e}")
    
    async def _persist_entry(self, entry: CostEntry) -> None:
        """Persist cost entry to database."""
        try:
            sql = text("""
                INSERT INTO ai_cost_logs (
                    id, service, model, user_id, session_id,
                    tokens_in, tokens_out, cost_usd, latency_ms,
                    success, error_message, metadata, created_at
                ) VALUES (
                    :id, :service, :model, :user_id, :session_id,
                    :tokens_in, :tokens_out, :cost_usd, :latency_ms,
                    :success, :error_message, :metadata, :created_at
                )
            """)
            
            self.db.execute(sql, {
                "id": entry.id,
                "service": entry.service,
                "model": entry.model,
                "user_id": entry.user_id,
                "session_id": entry.session_id,
                "tokens_in": entry.tokens_in,
                "tokens_out": entry.tokens_out,
                "cost_usd": entry.cost_usd,
                "latency_ms": entry.latency_ms,
                "success": entry.success,
                "error_message": entry.error_message,
                "metadata": json.dumps(entry.metadata),
                "created_at": entry.created_at,
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist cost entry: {e}")
            self.db.rollback()
    
    # ==========================================
    # Budget Management
    # ==========================================
    
    async def get_budget_status(self) -> BudgetStatus:
        """Get current budget status."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        spent_usd = 0.0
        
        # Try Redis first for real-time data
        if self.redis:
            try:
                value = self.redis.get(f"ai:cost:daily:{today}:total")
                if value:
                    spent_usd = float(value)
            except Exception:
                pass
        
        # Fallback to database if Redis not available
        if spent_usd == 0.0:
            spent_usd = await self._get_daily_spend_from_db()
        
        percent_used = (spent_usd / AI_DAILY_BUDGET_USD) * 100 if AI_DAILY_BUDGET_USD > 0 else 0
        
        return BudgetStatus(
            daily_budget_usd=AI_DAILY_BUDGET_USD,
            spent_usd=spent_usd,
            remaining_usd=max(0, AI_DAILY_BUDGET_USD - spent_usd),
            percent_used=percent_used,
            is_warning=percent_used >= AI_BUDGET_WARNING_THRESHOLD * 100,
            is_exceeded=spent_usd >= AI_DAILY_BUDGET_USD,
            kill_switch_active=self._kill_switch_active,
        )
    
    async def _get_daily_spend_from_db(self) -> float:
        """Get today's total spend from database."""
        try:
            today = datetime.now(timezone.utc).date()
            sql = text("""
                SELECT COALESCE(SUM(cost_usd), 0) as total
                FROM ai_cost_logs
                WHERE DATE(created_at) = :today
            """)
            
            result = self.db.execute(sql, {"today": today})
            row = result.fetchone()
            
            return float(row.total) if row else 0.0
            
        except Exception as e:
            logger.error(f"Failed to get daily spend from DB: {e}")
            return 0.0
    
    def is_kill_switch_active(self) -> bool:
        """Check if kill-switch is active."""
        return self._kill_switch_active
    
    def activate_kill_switch(self) -> None:
        """Manually activate kill-switch."""
        self._kill_switch_active = True
        logger.warning("AI kill-switch manually activated")
    
    def deactivate_kill_switch(self) -> None:
        """Manually deactivate kill-switch."""
        self._kill_switch_active = False
        logger.info("AI kill-switch deactivated")
    
    # ==========================================
    # Reporting & Aggregation
    # ==========================================
    
    async def get_daily_summary(
        self,
        target_date: Optional[date] = None,
        service: Optional[str] = None
    ) -> List[DailyCostSummary]:
        """
        Get daily cost summary.
        
        Args:
            target_date: Date to summarize (default: today)
            service: Filter by service (optional)
            
        Returns:
            List of DailyCostSummary objects
        """
        target_date = target_date or datetime.now(timezone.utc).date()
        
        try:
            if service:
                sql = text("""
                    SELECT
                        DATE(created_at) as date,
                        service,
                        SUM(cost_usd) as total_cost,
                        COUNT(*) as total_calls,
                        SUM(tokens_in) as total_tokens_in,
                        SUM(tokens_out) as total_tokens_out,
                        AVG(latency_ms) as avg_latency,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM ai_cost_logs
                    WHERE DATE(created_at) = :date AND service = :service
                    GROUP BY DATE(created_at), service
                """)
                result = self.db.execute(sql, {"date": target_date, "service": service})
            else:
                sql = text("""
                    SELECT
                        DATE(created_at) as date,
                        service,
                        SUM(cost_usd) as total_cost,
                        COUNT(*) as total_calls,
                        SUM(tokens_in) as total_tokens_in,
                        SUM(tokens_out) as total_tokens_out,
                        AVG(latency_ms) as avg_latency,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM ai_cost_logs
                    WHERE DATE(created_at) = :date
                    GROUP BY DATE(created_at), service
                    ORDER BY total_cost DESC
                """)
                result = self.db.execute(sql, {"date": target_date})
            
            summaries = []
            for row in result.fetchall():
                summaries.append(DailyCostSummary(
                    date=row.date,
                    service=row.service,
                    total_cost_usd=float(row.total_cost),
                    total_calls=row.total_calls,
                    total_tokens_in=row.total_tokens_in or 0,
                    total_tokens_out=row.total_tokens_out or 0,
                    avg_latency_ms=float(row.avg_latency) if row.avg_latency else 0,
                    success_rate=float(row.success_rate) if row.success_rate else 0,
                    unique_users=row.unique_users or 0,
                ))
            
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}")
            return []
    
    async def get_cost_report(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "service"  # service, user, model
    ) -> Dict[str, Any]:
        """
        Generate cost report for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            group_by: Grouping dimension
            
        Returns:
            Dict with report data
        """
        try:
            if group_by == "service":
                group_clause = "service"
            elif group_by == "user":
                group_clause = "user_id"
            elif group_by == "model":
                group_clause = "model"
            else:
                group_clause = "service"
            
            sql = text(f"""
                SELECT
                    {group_clause} as group_key,
                    SUM(cost_usd) as total_cost,
                    COUNT(*) as total_calls,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    AVG(latency_ms) as avg_latency,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
                FROM ai_cost_logs
                WHERE DATE(created_at) >= :start_date AND DATE(created_at) <= :end_date
                GROUP BY {group_clause}
                ORDER BY total_cost DESC
            """)
            
            result = self.db.execute(sql, {
                "start_date": start_date,
                "end_date": end_date,
            })
            
            rows = result.fetchall()
            
            # Calculate totals
            total_cost = sum(float(row.total_cost) for row in rows)
            total_calls = sum(row.total_calls for row in rows)
            
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "group_by": group_by,
                "total_cost_usd": total_cost,
                "total_calls": total_calls,
                "budget_usd": AI_DAILY_BUDGET_USD * (end_date - start_date).days,
                "groups": [
                    {
                        "key": row.group_key or "unknown",
                        "total_cost_usd": float(row.total_cost),
                        "total_calls": row.total_calls,
                        "total_tokens_in": row.total_tokens_in or 0,
                        "total_tokens_out": row.total_tokens_out or 0,
                        "avg_latency_ms": float(row.avg_latency) if row.avg_latency else 0,
                        "success_rate": float(row.success_rate) if row.success_rate else 0,
                    }
                    for row in rows
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cost report: {e}")
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "group_by": group_by,
                "error": str(e),
            }
    
    async def get_user_cost_history(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[CostEntry]:
        """Get cost history for a specific user."""
        try:
            sql = text("""
                SELECT * FROM ai_cost_logs
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, {"user_id": user_id, "limit": limit})
            rows = result.fetchall()
            
            entries = []
            for row in rows:
                entries.append(CostEntry(
                    id=row.id,
                    service=row.service,
                    model=row.model,
                    user_id=row.user_id,
                    session_id=row.session_id,
                    tokens_in=row.tokens_in,
                    tokens_out=row.tokens_out,
                    cost_usd=float(row.cost_usd),
                    latency_ms=float(row.latency_ms),
                    success=row.success,
                    error_message=row.error_message,
                    metadata=json.loads(row.metadata) if row.metadata else {},
                    created_at=row.created_at,
                ))
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get user cost history: {e}")
            return []
    
    # ==========================================
    # Aggregation Tasks
    # ==========================================
    
    async def aggregate_daily_costs(self, target_date: Optional[date] = None) -> bool:
        """
        Aggregate daily costs into summary table.
        
        Called by scheduled task.
        """
        target_date = target_date or datetime.now(timezone.utc).date()
        
        try:
            # Check if summary already exists
            check_sql = text("""
                SELECT 1 FROM ai_cost_daily_summary
                WHERE summary_date = :date
            """)
            result = self.db.execute(check_sql, {"date": target_date})
            
            if result.fetchone():
                # Update existing
                sql = text("""
                    INSERT INTO ai_cost_daily_summary (
                        summary_date, service, total_cost_usd, total_calls,
                        total_tokens_in, total_tokens_out, avg_latency_ms, success_rate, unique_users
                    )
                    SELECT
                        DATE(created_at),
                        service,
                        SUM(cost_usd),
                        COUNT(*),
                        SUM(tokens_in),
                        SUM(tokens_out),
                        AVG(latency_ms),
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*),
                        COUNT(DISTINCT user_id)
                    FROM ai_cost_logs
                    WHERE DATE(created_at) = :date
                    GROUP BY DATE(created_at), service
                    ON CONFLICT (summary_date, service) DO UPDATE SET
                        total_cost_usd = EXCLUDED.total_cost_usd,
                        total_calls = EXCLUDED.total_calls,
                        total_tokens_in = EXCLUDED.total_tokens_in,
                        total_tokens_out = EXCLUDED.total_tokens_out,
                        avg_latency_ms = EXCLUDED.avg_latency_ms,
                        success_rate = EXCLUDED.success_rate,
                        unique_users = EXCLUDED.unique_users
                """)
            else:
                # Insert new
                sql = text("""
                    INSERT INTO ai_cost_daily_summary (
                        summary_date, service, total_cost_usd, total_calls,
                        total_tokens_in, total_tokens_out, avg_latency_ms, success_rate, unique_users
                    )
                    SELECT
                        DATE(created_at),
                        service,
                        SUM(cost_usd),
                        COUNT(*),
                        SUM(tokens_in),
                        SUM(tokens_out),
                        AVG(latency_ms),
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*),
                        COUNT(DISTINCT user_id)
                    FROM ai_cost_logs
                    WHERE DATE(created_at) = :date
                    GROUP BY DATE(created_at), service
                """)
            
            self.db.execute(sql, {"date": target_date})
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to aggregate daily costs: {e}")
            self.db.rollback()
            return False


# Singleton instance for convenience
_cost_tracker_instance: Optional[AICostTracker] = None


def get_cost_tracker(db: Session = None, redis=None) -> AICostTracker:
    """Get or create cost tracker instance."""
    global _cost_tracker_instance
    
    if _cost_tracker_instance is None:
        if db is None:
            from database.database import get_db
            db = next(get_db())
        if redis is None:
            try:
                from core.redis_client import get_redis_client
                redis = get_redis_client()
            except Exception:
                pass
        
        _cost_tracker_instance = AICostTracker(db, redis)
    
    return _cost_tracker_instance
