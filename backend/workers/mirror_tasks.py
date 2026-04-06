"""
CONFIT Backend - MIRROR Celery Tasks
====================================
Celery worker tasks for virtual try-on processing.
"""

import logging
from celery import shared_task
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@shared_task(
    name="workers.mirror_tasks.process_tryon",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_tryon(self, session_id: str) -> dict:
    """
    Process a virtual try-on session.
    
    This task is queued by MirrorService.start_tryon() and
    handles the async call to Replicate IDM-VTON.
    
    Args:
        session_id: The try-on session ID
        
    Returns:
        Dict with status and result info
    """
    import asyncio
    from database.database import get_db
    from services.ai.mirror_service import MirrorService
    from core.redis_client import get_redis_client
    
    logger.info(f"Processing try-on session: {session_id}")
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        # Get Redis client
        redis = get_redis_client()
        
        # Create service
        service = MirrorService(db, redis)
        
        # Process synchronously (we're already in a worker)
        asyncio.run(service.process_tryon_task(session_id))
        
        # Get final result
        result = asyncio.run(service.get_result(session_id))
        
        return {
            "session_id": session_id,
            "status": result.status.value,
            "success": result.status.value == "completed",
            "error": result.error_message,
        }
        
    except Exception as e:
        logger.error(f"Try-on processing failed for {session_id}: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Mark as failed after max retries
        try:
            from database.database import get_db
            from sqlalchemy import text
            
            db = next(get_db())
            db.execute(text("""
                UPDATE try_on_sessions SET status = 'failed', error_message = :error
                WHERE id = :id
            """), {"id": session_id, "error": str(e)})
            db.commit()
        except Exception:
            pass
        
        return {
            "session_id": session_id,
            "status": "failed",
            "success": False,
            "error": str(e),
        }


@shared_task(name="workers.mirror_tasks.cleanup_expired")
def cleanup_expired_sessions() -> dict:
    """
    Clean up expired try-on sessions and photos.
    
    This should be scheduled to run daily.
    
    Returns:
        Dict with count of cleaned sessions
    """
    import asyncio
    from database.database import get_db
    from services.ai.mirror_service import MirrorService
    from core.redis_client import get_redis_client
    
    logger.info("Running try-on session cleanup")
    
    try:
        db = next(get_db())
        redis = get_redis_client()
        service = MirrorService(db, redis)
        
        count = asyncio.run(service.cleanup_expired_sessions())
        
        logger.info(f"Cleaned up {count} expired sessions")
        
        return {"cleaned_count": count, "success": True}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"cleaned_count": 0, "success": False, "error": str(e)}


@shared_task(name="workers.mirror_tasks.delete_user_data")
def delete_user_data(user_id: str) -> dict:
    """
    Delete all try-on data for a user (GDPR compliance).
    
    Args:
        user_id: User UUID
        
    Returns:
        Dict with success status
    """
    import asyncio
    from database.database import get_db
    from services.ai.mirror_service import MirrorService
    from core.redis_client import get_redis_client
    
    logger.info(f"Deleting try-on data for user: {user_id}")
    
    try:
        db = next(get_db())
        redis = get_redis_client()
        service = MirrorService(db, redis)
        
        success = asyncio.run(service.delete_user_data(user_id))
        
        return {"user_id": user_id, "success": success}
        
    except Exception as e:
        logger.error(f"User data deletion failed: {e}")
        return {"user_id": user_id, "success": False, "error": str(e)}
