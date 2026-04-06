from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class TrainingJob:
    id: str
    status: str
    created_at: float
    updated_at: float
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)


class TrainingJobScheduler:
    """
    Simple in-memory training job scheduler (scaffold).

    This is intentionally lightweight: jobs are best-effort and will reset
    if the backend restarts. Production deployments should move this to a
    persistent queue/workers (e.g. Celery/RQ/Cloud Tasks).
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, TrainingJob] = {}
        self._ttl_sec = max(int(__import__("os").getenv("TRAINING_JOB_TTL_SEC", "3600")), 60)

    def create_job(self, meta: Optional[Dict[str, Any]] = None) -> TrainingJob:
        now = time.time()
        job = TrainingJob(
            id=str(uuid.uuid4()),
            status="queued",
            created_at=now,
            updated_at=now,
            progress=0,
            artifacts={"meta": meta or {}},
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[TrainingJob]:
        self.cleanup_expired()
        return self._jobs.get(job_id)

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in ("completed", "failed", "cancelled") and (now - job.updated_at) > self._ttl_sec
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)
        return len(expired)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in ("completed", "failed", "cancelled"):
            return False
        job.status = "cancelled"
        job.updated_at = time.time()
        job.progress = 0
        job.message = "Job cancelled by user."
        return True

    def run_background(self, job_id: str, runner_sync: Callable[[], Dict[str, Any]]) -> None:
        asyncio.create_task(self._run(job_id, runner_sync))

    async def _run(self, job_id: str, runner_sync: Callable[[], Dict[str, Any]]) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        if job.status == "cancelled":
            return

        job.status = "running"
        job.updated_at = time.time()
        job.progress = 10
        try:
            result = await asyncio.to_thread(runner_sync)
            if job.status == "cancelled":
                return

            job.status = "completed" if result.get("success", True) else "failed"
            job.progress = 100
            job.result = result
            job.artifacts.update(result.get("artifacts") or {})
            job.message = result.get("message") or ("Training completed." if job.status == "completed" else "Training failed.")
        except asyncio.TimeoutError:
            job.status = "failed"
            job.progress = 100
            job.error_code = "TRAINING_TIMEOUT"
            job.message = "Training timed out."
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.error_code = "TRAINING_EXCEPTION"
            job.message = str(exc)
        finally:
            job.updated_at = time.time()

