"""
CONFIT Backend — AI Cost Admin v1 Router
========================================
GET  /api/v1/ai-admin/budget        — Current budget status
GET  /api/v1/ai-admin/daily-report  — 24h aggregate cost report
GET  /api/v1/ai-admin/cost-report   — Custom range cost report
POST /api/v1/ai-admin/kill-switch   — Activate/deactivate kill-switch
GET  /api/v1/ai-admin/user-costs    — Per-user cost history
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database.session import get_db
from services.ai.cost_tracker import get_cost_tracker, AICostTracker
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-admin", tags=["AI Admin — Cost Dashboard"])


# ── Schemas ──────────────────────────────────────────────────────────

class BudgetStatusResponse(BaseModel):
    daily_budget_usd: float
    spent_usd: float
    remaining_usd: float
    percent_used: float
    is_warning: bool
    is_exceeded: bool
    kill_switch_active: bool


class ServiceCostSummary(BaseModel):
    service: str
    total_cost_usd: float
    total_calls: int
    total_tokens_in: int
    total_tokens_out: int
    avg_latency_ms: float
    success_rate: float
    unique_users: int


class DailyReportResponse(BaseModel):
    date: str
    total_cost_usd: float
    total_calls: int
    services: list[ServiceCostSummary] = []


class CostReportResponse(BaseModel):
    start_date: str
    end_date: str
    group_by: str
    total_cost_usd: float
    total_calls: int
    budget_usd: float
    groups: list[dict] = []


class KillSwitchRequest(BaseModel):
    activate: bool


# ── Auth gate (admin only) ───────────────────────────────────────────

def _require_admin(user: UserProfile = Depends(require_auth)) -> UserProfile:
    role = getattr(user, "role", "user") or "user"
    if role not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin access required")
    return user


def _get_tracker(db=Depends(get_db)) -> AICostTracker:
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    return get_cost_tracker(db, redis)


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    user: UserProfile = Depends(_require_admin),
    tracker: AICostTracker = Depends(_get_tracker),
):
    """Current AI budget status with kill-switch state."""
    status = await tracker.get_budget_status()
    return BudgetStatusResponse(
        daily_budget_usd=status.daily_budget_usd,
        spent_usd=status.spent_usd,
        remaining_usd=status.remaining_usd,
        percent_used=status.percent_used,
        is_warning=status.is_warning,
        is_exceeded=status.is_exceeded,
        kill_switch_active=status.kill_switch_active,
    )


@router.get("/daily-report", response_model=DailyReportResponse)
async def get_daily_report(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD (default: today)"),
    user: UserProfile = Depends(_require_admin),
    tracker: AICostTracker = Depends(_get_tracker),
):
    """24-hour aggregate cost report by service."""
    if target_date:
        d = date.fromisoformat(target_date)
    else:
        d = datetime.now(timezone.utc).date()

    summaries = await tracker.get_daily_summary(target_date=d)

    total_cost = sum(s.total_cost_usd for s in summaries)
    total_calls = sum(s.total_calls for s in summaries)

    return DailyReportResponse(
        date=d.isoformat(),
        total_cost_usd=total_cost,
        total_calls=total_calls,
        services=[
            ServiceCostSummary(
                service=s.service,
                total_cost_usd=s.total_cost_usd,
                total_calls=s.total_calls,
                total_tokens_in=s.total_tokens_in,
                total_tokens_out=s.total_tokens_out,
                avg_latency_ms=s.avg_latency_ms,
                success_rate=s.success_rate,
                unique_users=s.unique_users,
            )
            for s in summaries
        ],
    )


@router.get("/cost-report", response_model=CostReportResponse)
async def get_cost_report(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    group_by: str = Query("service", description="service | user | model"),
    user: UserProfile = Depends(_require_admin),
    tracker: AICostTracker = Depends(_get_tracker),
):
    """Custom date-range cost report."""
    report = await tracker.get_cost_report(
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        group_by=group_by,
    )
    return CostReportResponse(**report)


@router.post("/kill-switch")
async def toggle_kill_switch(
    payload: KillSwitchRequest,
    user: UserProfile = Depends(_require_admin),
    tracker: AICostTracker = Depends(_get_tracker),
):
    """Manually activate or deactivate the AI kill-switch."""
    if payload.activate:
        tracker.activate_kill_switch()
        return {"kill_switch": "activated", "message": "Non-critical AI services disabled."}
    else:
        tracker.deactivate_kill_switch()
        return {"kill_switch": "deactivated", "message": "AI services re-enabled."}


@router.get("/user-costs")
async def get_user_costs(
    user_id: str = Query(...),
    limit: int = Query(100, ge=1, le=500),
    user: UserProfile = Depends(_require_admin),
    tracker: AICostTracker = Depends(_get_tracker),
):
    """Per-user cost history (admin view)."""
    entries = await tracker.get_user_cost_history(user_id, limit)
    return [
        {
            "id": e.id,
            "service": e.service,
            "model": e.model,
            "tokens_in": e.tokens_in,
            "tokens_out": e.tokens_out,
            "cost_usd": e.cost_usd,
            "latency_ms": e.latency_ms,
            "success": e.success,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
