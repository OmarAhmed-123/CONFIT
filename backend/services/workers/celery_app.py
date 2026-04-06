"""
CONFIT Backend — Celery Application Configuration
=================================================
Production-ready Celery setup for async GPU processing.

Features:
- GPU memory management
- Task routing (GPU vs CPU queues)
- Retry logic with exponential backoff
- Health monitoring
"""

import os
import logging
from celery import Celery
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    worker_ready,
    worker_shutdown,
)
from kombu import Queue

logger = logging.getLogger(__name__)

# ===========================================
# Celery App Configuration
# ===========================================

app = Celery('confit_tryon')

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

app.conf.update(
    # Broker settings
    broker_url=REDIS_URL,
    result_backend=f"{REDIS_URL.rsplit('/', 1)[0]}/1",  # Use DB 1 for results
    
    # Serialization
    task_serializer='json',
    accept_content=['json', 'pickle'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
    },
    
    # Task settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
    task_track_started=True,
    
    # Time limits (prevent stuck tasks)
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task per worker at a time
    worker_concurrency=2,  # Limit concurrent GPU tasks
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (memory leak prevention)
    
    # Task routing
    task_queues=[
        Queue('gpu', routing_key='gpu'),
        Queue('cpu', routing_key='cpu'),
        Queue('default', routing_key='default'),
    ],
    
    task_routes={
        'services.workers.tryon_worker.process_tryon': {'queue': 'gpu'},
        'services.workers.tryon_worker.process_rotation': {'queue': 'gpu'},
        'services.workers.preprocessing_worker.*': {'queue': 'cpu'},
        'services.workers.maintenance_worker.*': {'queue': 'cpu'},
    },
    
    # Task default settings
    task_default_queue='default',
    task_default_exchange='tasks',
    task_default_routing_key='task.default',
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        'health-check-every-minute': {
            'task': 'services.workers.tryon_worker.health_check',
            'schedule': 60.0,  # Every minute
        },
        'cleanup-gpu-memory-every-5-minutes': {
            'task': 'services.workers.maintenance_worker.cleanup_gpu_memory',
            'schedule': 300.0,  # Every 5 minutes
        },
    },
)


# ===========================================
# Signal Handlers
# ===========================================

@task_prerun.connect
def init_gpu_context(task_id, task, *args, **kwargs):
    """
    Initialize GPU context before task execution.
    Ensures GPU is ready and memory is clear.
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            # Clear cache before task
            torch.cuda.empty_cache()
            
            # Log GPU status
            device = torch.cuda.current_device()
            allocated = torch.cuda.memory_allocated(device) / 1024**3
            reserved = torch.cuda.memory_reserved(device) / 1024**3
            
            logger.info(
                f"GPU context initialized for task {task_id}: "
                f"Allocated={allocated:.2f}GB, Reserved={reserved:.2f}GB"
            )
    except ImportError:
        logger.debug("PyTorch not available, skipping GPU init")
    except Exception as e:
        logger.warning(f"GPU init failed: {e}")


@task_postrun.connect
def cleanup_gpu_context(task_id, task, retval, *args, **kwargs):
    """
    Cleanup GPU context after task completion.
    Frees memory and synchronizes.
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            # Synchronize before cleanup
            torch.cuda.synchronize()
            
            # Clear cache
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            
            # Log GPU status
            device = torch.cuda.current_device()
            allocated = torch.cuda.memory_allocated(device) / 1024**3
            
            logger.info(
                f"GPU context cleaned for task {task_id}: "
                f"Final allocated={allocated:.2f}GB"
            )
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"GPU cleanup failed: {e}")


@task_failure.connect
def handle_task_failure(task_id, exception, *args, **kwargs):
    """
    Handle task failures with logging and cleanup.
    """
    logger.error(
        f"Task {task_id} failed with exception: {exception}",
        exc_info=True
    )
    
    # Force GPU cleanup on failure
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


@worker_ready.connect
def on_worker_ready(**kwargs):
    """
    Called when worker is ready to accept tasks.
    """
    logger.info("=" * 50)
    logger.info("CONFIT Celery Worker Ready")
    logger.info("=" * 50)
    
    # Log GPU status
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA Available: {torch.cuda.is_available()}")
            logger.info(f"CUDA Version: {torch.version.cuda}")
            logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            logger.warning("CUDA not available - running in CPU mode")
    except ImportError:
        logger.warning("PyTorch not installed")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    """
    Called when worker is shutting down.
    """
    logger.info("Celery worker shutting down...")
    
    # Final GPU cleanup
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.info("GPU memory cleared on shutdown")
    except Exception:
        pass


# ===========================================
# Utility Functions
# ===========================================

def get_queue_length(queue_name: str = 'gpu') -> int:
    """
    Get the number of tasks waiting in a queue.
    Useful for load balancing.
    """
    from kombu import Connection
    
    with Connection(REDIS_URL) as conn:
        queue = conn.SimpleQueue(queue_name)
        return queue.qsize()


def get_active_tasks() -> list:
    """
    Get list of currently active tasks.
    """
    inspect = app.control.inspect()
    active = inspect.active()
    
    if active:
        return [
            {
                'task_id': task['id'],
                'name': task['name'],
                'worker': worker,
            }
            for worker, tasks in active.items()
            for task in tasks
        ]
    return []


def revoke_task(task_id: str, terminate: bool = False):
    """
    Revoke a task by ID.
    
    Args:
        task_id: Task ID to revoke
        terminate: Whether to terminate running task
    """
    app.control.revoke(task_id, terminate=terminate)
    logger.info(f"Task {task_id} revoked (terminate={terminate})")


# ===========================================
# Health Check
# ===========================================

def check_broker_connection() -> bool:
    """Check if broker is connected."""
    try:
        from kombu import Connection
        with Connection(REDIS_URL) as conn:
            conn.connect()
            return True
    except Exception as e:
        logger.error(f"Broker connection failed: {e}")
        return False


def get_worker_stats() -> dict:
    """Get worker statistics."""
    inspect = app.control.inspect()
    
    return {
        'active': inspect.active(),
        'reserved': inspect.reserved(),
        'stats': inspect.stats(),
        'registered': inspect.registered(),
    }
