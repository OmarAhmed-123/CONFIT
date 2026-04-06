"""
CONFIT Backend — Onboarding Router
=================================
Adaptive onboarding flow endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.onboarding_service import OnboardingService, get_onboarding_service
from models.profile_models import (
    OnboardingStatusResponse,
    StyleQuizSubmission,
    StyleArchetypeResult,
    OnboardingPhaseData,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    return onboarding_service.get_status(user.id)


@router.post("/start", response_model=OnboardingStatusResponse)
async def start_onboarding(
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    return onboarding_service.start(user.id)


@router.post("/phase/{phase}", response_model=OnboardingStatusResponse)
async def complete_phase(
    phase: int,
    data: OnboardingPhaseData,
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    if phase < 1 or phase > 5:
        raise HTTPException(status_code=400, detail="Invalid phase number")
    return onboarding_service.complete_phase(user.id, phase, data.data)


@router.post("/skip/{phase}", response_model=OnboardingStatusResponse)
async def skip_phase(
    phase: int,
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    if phase < 1 or phase > 5:
        raise HTTPException(status_code=400, detail="Invalid phase number")
    return onboarding_service.skip_phase(user.id, phase)


@router.get("/quiz/questions")
async def get_quiz_questions(
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    return onboarding_service.get_quiz_questions()


@router.post("/quiz", response_model=StyleArchetypeResult)
async def submit_style_quiz(
    submission: StyleQuizSubmission,
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    return onboarding_service.submit_quiz(user.id, submission)


@router.post("/complete", response_model=OnboardingStatusResponse)
async def complete_onboarding(
    user: UserProfile = Depends(require_auth),
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
):
    return onboarding_service.complete(user.id)
