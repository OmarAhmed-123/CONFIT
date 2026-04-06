"""
CONFIT Backend - Virtual Try-On Celery Tasks
============================================
Async tasks for virtual try-on processing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app, DatabaseTask


logger = get_task_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TRY-ON PROCESSING TASK
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tryon_tasks.process_tryon",
    max_retries=3,
    default_retry_delay=30,
)
def process_tryon(self, session_id: str):
    """
    Process virtual try-on session.
    
    Args:
        session_id: Try-on session UUID
    """
    logger.info(f"Processing try-on session: {session_id}")
    
    # Run async processing
    return asyncio.run(_process_tryon_async(session_id))


async def _process_tryon_async(session_id: str):
    """Async try-on processing."""
    from infrastructure.database import async_session_factory
    from application.services.tryon_service import VirtualTryOnService
    
    async with async_session_factory() as session:
        try:
            service = VirtualTryOnService(session)
            await service.process_try_on(UUID(session_id))
            await session.commit()
            
            logger.info(f"Try-on completed: {session_id}")
            return {"status": "completed", "session_id": session_id}
            
        except Exception as e:
            logger.error(f"Try-on failed: {session_id} - {e}")
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────────────────
# BATCH PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="workers.tryon_tasks.batch_process_tryons",
)
def batch_process_tryons(self, session_ids: list):
    """
    Process multiple try-on sessions in batch.
    
    Args:
        session_ids: List of try-on session UUIDs
    """
    logger.info(f"Batch processing {len(session_ids)} try-on sessions")
    
    # Create subtasks for each session
    tasks = [
        process_tryon.s(session_id)
        for session_id in session_ids
    ]
    
    # Execute in parallel
    from celery import group
    job = group(tasks)
    result = job.apply_async()
    
    return {"batch_id": result.id, "count": len(session_ids)}


# ─────────────────────────────────────────────────────────────────────────────
# CLEANUP TASKS
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="workers.tryon_tasks.cleanup_expired_sessions",
)
def cleanup_expired_sessions():
    """Clean up expired try-on sessions."""
    return asyncio.run(_cleanup_expired_sessions_async())


async def _cleanup_expired_sessions_async():
    """Async cleanup of expired sessions."""
    from infrastructure.database import async_session_factory
    from sqlalchemy import update
    from datetime import timedelta
    from database.models import TryOnSession
    from domain.base import TryOnStatus
    
    async with async_session_factory() as session:
        # Mark sessions as expired if older than 24 hours and still pending
        expiry_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        
        stmt = (
            update(TryOnSession)
            .where(
                TryOnSession.status == TryOnStatus.PENDING.value,
                TryOnSession.created_at < expiry_threshold,
            )
            .values(status=TryOnStatus.EXPIRED.value)
        )
        
        result = await session.execute(stmt)
        await session.commit()
        
        expired_count = result.rowcount
        logger.info(f"Expired {expired_count} try-on sessions")
        
        return {"expired_count": expired_count}


# ─────────────────────────────────────────────────────────────────────────────
# QUALITY CHECK TASK
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="workers.tryon_tasks.validate_quality",
)
def validate_quality(self, session_id: str):
    """Validate quality of completed try-on."""
    return asyncio.run(_validate_quality_async(session_id))


async def _validate_quality_async(session_id: str):
    """Async quality validation."""
    from infrastructure.database import async_session_factory
    from application.services.tryon_service import VirtualTryOnService
    
    async with async_session_factory() as session:
        service = VirtualTryOnService(session)
        result = await service.validate_result(UUID(session_id))
        return result
