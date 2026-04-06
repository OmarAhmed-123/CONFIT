"""
CONFIT Backend - Celery Application
===================================
Celery configuration for async task processing.
"""

import os
from celery import Celery
from celery.schedules import crontab


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")


# ─────────────────────────────────────────────────────────────────────────────
# CELERY APP
# ─────────────────────────────────────────────────────────────────────────────

celery_app = Celery(
    "confit",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "workers.tryon_tasks",
        "workers.visual_search_tasks",
        "workers.recommendation_tasks",
        "workers.notification_tasks",
        "workers.analytics_tasks",
        "workers.mirror_tasks",
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# CELERY CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Task routing
    task_routes={
        "workers.tryon_tasks.*": {"queue": "tryon"},
        "workers.visual_search_tasks.*": {"queue": "search"},
        "workers.recommendation_tasks.*": {"queue": "recommendations"},
        "workers.notification_tasks.*": {"queue": "notifications"},
        "workers.analytics_tasks.*": {"queue": "analytics"},
        "workers.payment_tasks.*": {"queue": "payments"},
        "workers.mirror_tasks.*": {"queue": "mirror"},
    },
    
    # Task time limits
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Clean up expired sessions every hour
        "cleanup-expired-sessions": {
            "task": "workers.analytics_tasks.cleanup_expired_sessions",
            "schedule": crontab(minute=0),  # Every hour
        },
        # Update product recommendations daily
        "update-recommendations": {
            "task": "workers.recommendation_tasks.update_all_recommendations",
            "schedule": crontab(hour=3, minute=0),  # 3 AM daily
        },
        # Generate daily analytics
        "generate-daily-analytics": {
            "task": "workers.analytics_tasks.generate_daily_analytics",
            "schedule": crontab(hour=1, minute=0),  # 1 AM daily
        },
        # Sync product search index
        "sync-search-index": {
            "task": "workers.analytics_tasks.sync_search_index",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        # Mirror: cleanup expired try-on sessions daily
        "mirror-cleanup-expired": {
            "task": "workers.mirror_tasks.cleanup_expired",
            "schedule": crontab(hour=4, minute=0),  # 4 AM UTC daily
        },
        # Nightly aggregation for analytics summaries (2am Cairo = midnight UTC)
        "analytics-daily-aggregation": {
            "task": "workers.analytics_tasks.aggregate_daily_summaries",
            "schedule": crontab(hour=0, minute=0),  # Midnight UTC
        },
        # Weekly archive of old analytics events (Sundays at 3am UTC)
        "analytics-weekly-archive": {
            "task": "workers.analytics_tasks.archive_old_events",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
            "args": (180,),  # Archive events older than 180 days
        },
    },
)

# Payment tasks (import after app exists to avoid circular import in Celery constructor)
try:
    import workers.payment_tasks  # noqa: F401
except Exception:  # pragma: no cover — optional when running API-only
    pass


# ─────────────────────────────────────────────────────────────────────────────
# TASK BASE CLASS
# ─────────────────────────────────────────────────────────────────────────────

from celery import Task
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Task with database session management."""
    
    _db_session = None
    
    @property
    def db_session(self):
        if self._db_session is None:
            from infrastructure.database import async_session_factory
            self._db_session = async_session_factory()
        return self._db_session
    
    async def close_db_session(self):
        """Close database session."""
        if self._db_session is not None:
            await self._db_session.close()
            self._db_session = None


class RetryableTask(Task):
    """Task with automatic retry logic."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 10}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_task_status(task_id: str) -> dict:
    """Get task status by ID."""
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None,
    }


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """Revoke a task."""
    celery_app.control.revoke(task_id, terminate=terminate)
    return True


def get_active_tasks() -> list:
    """Get all active tasks."""
    inspect = celery_app.control.inspect()
    active = inspect.active()
    
    tasks = []
    if active:
        for worker, task_list in active.items():
            for task in task_list:
                tasks.append({
                    "worker": worker,
                    "task_id": task["id"],
                    "name": task["name"],
                    "args": task["args"],
                    "kwargs": task["kwargs"],
                })
    
    return tasks


def get_queue_lengths() -> dict:
    """Get queue lengths."""
    inspect = celery_app.control.inspect()
    
    return {
        "active": len(get_active_tasks()),
        "reserved": sum(len(t) for t in (inspect.reserved() or {}).values()),
        "scheduled": sum(len(t) for t in (inspect.scheduled() or {}).values()),
    }
