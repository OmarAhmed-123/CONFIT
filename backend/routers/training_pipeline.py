from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi import Depends
from pydantic import BaseModel, Field

from services.training_job_scheduler import TrainingJobScheduler
from services.training_pipeline_service import TrainingPipelineService, TrainingParams
from utils.auth_deps import require_admin
from services.auth_service import UserProfile


router = APIRouter(prefix="/api/training", tags=["Training"])

_scheduler = TrainingJobScheduler()
_pipeline = TrainingPipelineService()


class TrainingJobStartRequest(BaseModel):
    lookback_days: int = Field(30, ge=1, le=365)
    max_pairs: int = Field(2000, ge=10, le=50000)
    apply_overrides: bool = Field(True, description="Apply computed signal weights to runtime")
    candidate_signal_types: Optional[List[str]] = Field(
        None,
        description="If omitted, uses all current SIGNAL_CONFIG keys.",
    )
    pairs_seed: int = Field(42, ge=0, le=999999)


@router.post("/jobs", response_model=Dict[str, Any])
async def start_training_job(
    req: TrainingJobStartRequest,
    admin: UserProfile = Depends(require_admin),
) -> Dict[str, Any]:
    job = _scheduler.create_job(meta={"kind": "preference_dataset_and_reward_calibration"})

    params = TrainingParams(
        lookback_days=req.lookback_days,
        max_pairs=req.max_pairs,
        apply_overrides=req.apply_overrides,
        candidate_signal_types=req.candidate_signal_types,
        pairs_seed=req.pairs_seed,
    )

    def runner_sync() -> Dict[str, Any]:
        return _pipeline.run_job_sync(job_id=job.id, params=params)

    _scheduler.run_background(job.id, runner_sync)
    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
    }


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_training_job(
    job_id: str,
    admin: UserProfile = Depends(require_admin),
) -> Dict[str, Any]:
    job = _scheduler.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found.")

    return {
        "success": True,
        "job": {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "message": job.message,
            "error_code": job.error_code,
            "artifacts": job.artifacts,
            "result": job.result,
        },
    }


@router.post("/jobs/{job_id}/cancel", response_model=Dict[str, Any])
async def cancel_training_job(
    job_id: str,
    admin: UserProfile = Depends(require_admin),
) -> Dict[str, Any]:
    ok = _scheduler.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Training job not found or cannot cancel.")
    return {"success": True, "cancelled": True, "job_id": job_id}

