"""
Health Check Scheduler Service
==============================
Integrates APScheduler to run background health check jobs.
Configurable interval (default: 5 minutes).
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.debug.health_check import (
    run_all_health_checks,
    HealthCheckResult,
    compute_overall_status,
    ProviderHealthSnapshot,
)
from services.debug.health_store import (
    get_health_store,
    HealthHistoryEntry,
    HealthHistoryStore,
)
from services.debug.alert_system import process_health_check_results

logger = logging.getLogger(__name__)

# Global health snapshot (updated by scheduler)
_health_snapshot: Dict[str, Any] = {}
_scheduler = None


def get_health_snapshot() -> Dict[str, Any]:
    """Get the current health snapshot (non-blocking)."""
    return _health_snapshot.copy()


def _is_scheduler_enabled() -> bool:
    """Check if scheduler should be enabled based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    # Only enable in development, staging, or test
    return env in ("development", "dev", "staging", "test")


def _get_check_interval_minutes() -> int:
    """Get the health check interval in minutes."""
    return int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", "5"))


async def run_health_check_job() -> None:
    """
    Main health check job executed by the scheduler.
    Runs all checks, stores results, and dispatches alerts.
    """
    global _health_snapshot
    
    start_time = datetime.now(timezone.utc)
    logger.info("Starting scheduled health check run")
    
    try:
        store = get_health_store()
        
        # Run all health checks
        all_results = await run_all_health_checks()
        
        # Process alerts for each provider
        for provider, results in all_results.items():
            await process_health_check_results(results, store)
        
        # Store results in history
        all_entries: List[HealthHistoryEntry] = []
        for provider, results in all_results.items():
            for result in results:
                entry = HealthHistoryEntry(
                    id=f"hc-{uuid.uuid4().hex[:12]}",
                    provider=result.provider,
                    check_name=result.check_name,
                    status=result.status,
                    latency_ms=result.latency_ms,
                    message=result.message,
                    timestamp=result.timestamp,
                    details=result.details,
                )
                all_entries.append(entry)
        
        store.add_health_entries(all_entries)
        
        # Build snapshot
        snapshot: Dict[str, Any] = {
            "last_run": start_time.isoformat(),
            "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            "providers": {},
        }
        
        for provider, results in all_results.items():
            checks = {r.check_name: r.status for r in results if r.status != "skip"}
            avg_latency = sum(r.latency_ms for r in results if r.latency_ms > 0) / len([r for r in results if r.latency_ms > 0]) if any(r.latency_ms > 0 for r in results) else 0
            
            snapshot["providers"][provider] = ProviderHealthSnapshot(
                overall=compute_overall_status(checks),
                checks=checks,
                last_checked=start_time.isoformat(),
                latency_ms=round(avg_latency, 2),
                details={
                    "full_results": [r.to_dict() for r in results],
                },
            ).to_dict()
        
        _health_snapshot = snapshot
        
        logger.info(
            f"Health check run completed in {snapshot['duration_ms']:.0f}ms - "
            f"Paymob: {snapshot['providers'].get('paymob', {}).get('overall', 'unknown')}, "
            f"PayPal: {snapshot['providers'].get('paypal', {}).get('overall', 'unknown')}"
        )
        
    except Exception as e:
        logger.exception(f"Health check job failed: {e}")
        _health_snapshot = {
            "last_run": start_time.isoformat(),
            "error": str(e),
            "providers": {},
        }


def start_scheduler() -> Optional[Any]:
    """
    Start the APScheduler background scheduler.
    Returns the scheduler instance or None if not enabled.
    """
    global _scheduler
    
    if not _is_scheduler_enabled():
        logger.info("Health check scheduler disabled (not in dev/staging/test environment)")
        return None
    
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        interval_minutes = _get_check_interval_minutes()
        
        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            run_health_check_job,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="health_check_job",
            name="Payment Provider Health Check",
            max_instances=1,  # Prevent overlapping runs
            coalesce=True,  # Combine missed runs
        )
        
        _scheduler.start()
        logger.info(f"Health check scheduler started (interval: {interval_minutes} min)")
        
        # Run initial check immediately
        asyncio.create_task(run_health_check_job())
        
        return _scheduler
    except ImportError:
        logger.warning("APScheduler not installed - health check scheduler disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to start health check scheduler: {e}")
        return None


def stop_scheduler() -> None:
    """Stop the scheduler if running."""
    global _scheduler
    
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Health check scheduler stopped")
        except Exception as e:
            logger.warning(f"Error stopping scheduler: {e}")
        finally:
            _scheduler = None


def is_scheduler_running() -> bool:
    """Check if the scheduler is running."""
    return _scheduler is not None and _scheduler.running


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

async def trigger_health_check() -> Dict[str, Any]:
    """
    Manually trigger a health check run.
    Returns the results immediately.
    """
    await run_health_check_job()
    return get_health_snapshot()


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI LIFESPAN INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

class HealthSchedulerManager:
    """Context manager for FastAPI lifespan integration."""
    
    def __init__(self):
        self.scheduler = None
    
    async def __aenter__(self) -> "HealthSchedulerManager":
        self.scheduler = start_scheduler()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        stop_scheduler()


def get_scheduler_manager() -> HealthSchedulerManager:
    """Get a scheduler manager for lifespan integration."""
    return HealthSchedulerManager()
