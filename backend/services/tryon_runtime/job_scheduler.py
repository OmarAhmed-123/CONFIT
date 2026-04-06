from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RenderJob:
    id: str
    status: str
    created_at: float
    updated_at: float
    progress: int = 0
    result_image: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    backend_name: Optional[str] = None
    render_kind: str = "final"
    quality_score: Optional[float] = None
    failure_kind: Optional[str] = None
    alignment_diagnostics_json: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class TryOnJobScheduler:
    """In-memory async job scheduler for final render jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, RenderJob] = {}
        self._ttl_sec = max(60, int(__import__("os").getenv("TRYON_JOB_TTL_SEC", "1800")))

    def create_job(self, meta: Optional[Dict[str, Any]] = None) -> RenderJob:
        now = time.time()
        job = RenderJob(
            id=str(uuid.uuid4()),
            status="queued",
            created_at=now,
            updated_at=now,
            progress=0,
            meta=meta or {},
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[RenderJob]:
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

    def run_background(self, job_id: str, coro) -> None:
        asyncio.create_task(self._run(job_id, coro))

    async def _run(self, job_id: str, coro) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        if job.status == "cancelled":
            return
        job.status = "running"
        job.progress = 10
        job.updated_at = time.time()
        timeout_sec = max(60, int(__import__("os").getenv("TRYON_RENDER_TIMEOUT_SEC", "300")))
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_sec)
            if job.status == "cancelled":
                return
            if result.get("success"):
                job.status = "completed"
                job.progress = 100
                job.result_image = result.get("image_url") or result.get("result_image")
                job.backend_name = result.get("backend_name")
                job.quality_score = result.get("quality_score")
                job.alignment_diagnostics_json = result.get("alignment_diagnostics_json")
                job.message = "Final render completed."
            else:
                job.status = "failed"
                job.progress = 100
                job.error_code = result.get("error_code") or "FINAL_RENDER_FAILED"
                job.message = result.get("message") or "Final render failed."
                job.failure_kind = result.get("failure_kind") or job.error_code
            job.updated_at = time.time()
        except asyncio.TimeoutError:
            job.status = "failed"
            job.progress = 100
            job.error_code = "RENDER_TIMEOUT"
            job.message = f"Render timed out after {timeout_sec}s."
            job.failure_kind = "RENDER_TIMEOUT"
            job.updated_at = time.time()
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.error_code = "FINAL_RENDER_EXCEPTION"
            job.message = str(exc)
            job.updated_at = time.time()

