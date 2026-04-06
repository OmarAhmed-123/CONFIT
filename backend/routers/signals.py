"""
CONFIT Backend — Behavior Signal Router
======================================
Behavioral intelligence endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.behavior_signal_service import BehaviorSignalService, get_behavior_signal_service
from models.profile_models import (
    BehaviorSignalCreate,
    BehaviorSignalResponse,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/signals", tags=["Behavior Signals"])


@router.post("/track", response_model=BehaviorSignalResponse)
async def track_signal(
    data: BehaviorSignalCreate,
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    return signal_service.track(
        user_id=user.id,
        signal_type=data.signal_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        context=data.context,
        duration_ms=data.duration_ms,
    )


@router.post("/track/batch", response_model=List[BehaviorSignalResponse])
async def track_signals_batch(
    signals: List[BehaviorSignalCreate],
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    return signal_service.track_batch(user.id, signals)


@router.get("/", response_model=List[BehaviorSignalResponse])
async def get_user_signals(
    signal_types: str = None,
    entity_type: str = None,
    limit: int = 100,
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    types_list = signal_types.split(",") if signal_types else None
    return signal_service.get_user_signals(
        user_id=user.id,
        signal_types=types_list,
        entity_type=entity_type,
        limit=limit,
    )


@router.get("/aggregate/{entity_type}")
async def aggregate_signals(
    entity_type: str,
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    return signal_service.aggregate_by_entity(user.id, entity_type)


@router.get("/summary")
async def get_preference_summary(
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    return signal_service.get_preference_summary(user.id)


@router.get("/counts")
async def get_signal_counts(
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    return signal_service.get_signal_counts_by_type(user.id)


@router.delete("/clear")
async def clear_user_signals(
    user: UserProfile = Depends(require_auth),
    signal_service: BehaviorSignalService = Depends(get_behavior_signal_service),
):
    count = signal_service.clear_user_signals(user.id)
    return {"deleted": count}
