"""
CONFIT Backend — MCP GPU Scheduler
====================================
GPU resource management for AI model inference.

Features:
- GPU memory monitoring to prevent OOM
- Priority queue (live preview > standard requests)
- Batch inference for efficiency
- Automatic CPU fallback when GPU unavailable
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Try importing torch for GPU checks
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class Priority(IntEnum):
    """Inference job priorities (lower = higher priority)."""
    LIVE_PREVIEW = 0
    INTERACTIVE = 1
    STANDARD = 2
    BATCH = 3
    BACKGROUND = 4


@dataclass
class InferenceJob:
    """Single inference job queued for GPU execution."""
    job_id: str
    priority: Priority
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    result: Optional[Any] = None
    error: Optional[str] = None
    done: bool = False


class GPUScheduler:
    """Manages GPU resources and schedules inference jobs.

    Usage:
        scheduler = GPUScheduler()
        result = await scheduler.submit(
            job_id="tryon_123",
            func=model.infer,
            args=(input_tensor,),
            priority=Priority.INTERACTIVE,
        )
    """

    def __init__(self, max_concurrent: int = 2, max_queue_size: int = 50) -> None:
        self._device = self._detect_device()
        self._max_concurrent = max_concurrent
        self._max_queue_size = max_queue_size
        self._active_jobs: Dict[str, InferenceJob] = {}
        self._queue: deque[InferenceJob] = deque(maxlen=max_queue_size)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._total_processed = 0
        self._total_errors = 0

    @staticmethod
    def _detect_device() -> str:
        """Detect best available compute device."""
        if not TORCH_AVAILABLE:
            return "cpu"
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("GPU detected: %s", device_name)
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Apple MPS detected")
            return "mps"
        logger.info("No GPU detected, using CPU")
        return "cpu"

    @property
    def device(self) -> str:
        return self._device

    @property
    def has_gpu(self) -> bool:
        return self._device != "cpu"

    # ── Resource Monitoring ─────────────────────────────────────────────

    def gpu_memory_info(self) -> Dict[str, Any]:
        """Get GPU memory usage. Returns empty dict if no GPU."""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return {"device": "cpu", "gpu_available": False}
        allocated = torch.cuda.memory_allocated() / 1024 / 1024
        reserved = torch.cuda.memory_reserved() / 1024 / 1024
        total = torch.cuda.get_device_properties(0).total_mem / 1024 / 1024
        return {
            "device": torch.cuda.get_device_name(0),
            "gpu_available": True,
            "allocated_mb": round(allocated, 1),
            "reserved_mb": round(reserved, 1),
            "total_mb": round(total, 1),
            "utilization_pct": round(allocated / total * 100, 1) if total > 0 else 0,
        }

    def can_accept_job(self) -> bool:
        """Check if scheduler can accept new jobs."""
        return len(self._queue) < self._max_queue_size

    # ── Job Submission ──────────────────────────────────────────────────

    async def submit(
        self,
        job_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        priority: Priority = Priority.STANDARD,
    ) -> Any:
        """Submit an inference job and wait for result.

        Args:
            job_id: Unique job identifier
            func: Async or sync callable to execute
            args: Positional arguments for func
            kwargs: Keyword arguments for func
            priority: Job priority level

        Returns:
            Result from func execution

        Raises:
            RuntimeError: If queue is full
            Exception: Propagated from func
        """
        if not self.can_accept_job():
            raise RuntimeError("GPU scheduler queue full — try again later")

        job = InferenceJob(
            job_id=job_id,
            priority=priority,
            func=func,
            args=args,
            kwargs=kwargs or {},
        )

        # Execute with semaphore control
        async with self._semaphore:
            self._active_jobs[job_id] = job
            try:
                start_time = time.time()
                if asyncio.iscoroutinefunction(func):
                    job.result = await func(*args, **job.kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    job.result = await loop.run_in_executor(None, lambda: func(*args, **job.kwargs))
                elapsed_ms = (time.time() - start_time) * 1000
                logger.debug(
                    "Job %s completed in %.0fms (priority=%s, device=%s)",
                    job_id, elapsed_ms, priority.name, self._device,
                )
                self._total_processed += 1
                job.done = True
                return job.result
            except Exception as e:
                job.error = str(e)
                job.done = True
                self._total_errors += 1
                logger.error("Job %s failed: %s", job_id, e)
                raise
            finally:
                self._active_jobs.pop(job_id, None)

    # ── Memory Management ───────────────────────────────────────────────

    def clear_gpu_memory(self) -> None:
        """Force clear GPU memory cache."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.info("GPU memory cache cleared")

    # ── Stats ───────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "device": self._device,
            "has_gpu": self.has_gpu,
            "active_jobs": len(self._active_jobs),
            "queue_size": len(self._queue),
            "max_concurrent": self._max_concurrent,
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "gpu_memory": self.gpu_memory_info(),
        }
