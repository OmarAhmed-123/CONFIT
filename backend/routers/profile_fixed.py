"""
CONFIT Backend — Profile Router
===============================
User profile management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.session import get_db
from services.profile_service import ProfileService
from services.confidence_service import ConfidenceService
from models.profile_models import (
    StyleProfileCreate,
    StyleProfileResponse,
    BodyProfileCreate,
    BodyProfileResponse,
    BudgetProfileCreate,
    BudgetProfileResponse,
    BrandAffinityCreate,
    BrandAffinityResponse,
    ContextualPreferenceCreate,
    ContextualPreferenceResponse,
    ConfidenceProfileResponse,
    ProfileCompletenessResponse,
    StyleArchetypeResult,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/profile", tags=["Profile"])


def get_client_info(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.get("/style", response_model=StyleProfileResponse)
async def get_style_profile(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    profile = service.get_style_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return profile


@router.patch("/style", response_model=StyleProfileResponse)
async def update_style_profile(
    data: StyleProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    client = get_client_info(request)
    service = ProfileService(db)
    return service.update_style_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.post("/style/archetype", response_model=StyleArchetypeResult)
async def calculate_archetype(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    result = service.calculate_archetype(user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/body", response_model=BodyProfileResponse)
async def get_body_profile(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    profile = service.get_body_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Body profile not found")
    return profile


@router.patch("/body", response_model=BodyProfileResponse)
async def update_body_profile(
    data: BodyProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    client = get_client_info(request)
    service = ProfileService(db)
    return service.update_body_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/budget", response_model=BudgetProfileResponse)
async def get_budget_profile(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    profile = service.get_budget_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Budget profile not found")
    return profile


@router.patch("/budget", response_model=BudgetProfileResponse)
async def update_budget_profile(
    data: BudgetProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    client = get_client_info(request)
    service = ProfileService(db)
    return service.update_budget_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/brands", response_model=List[BrandAffinityResponse])
async def get_brand_affinities(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.get_brand_affinities(user.id)


@router.post("/brands", response_model=BrandAffinityResponse)
async def add_brand_affinity(
    data: BrandAffinityCreate,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.add_brand_affinity(user.id, data, source="explicit")


@router.delete("/brands/{brand_id}")
async def remove_brand_affinity(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    success = service.remove_brand_affinity(user.id, brand_id)
    if not success:
        raise HTTPException(status_code=404, detail="Brand affinity not found")
    return {"success": True}


@router.get("/context", response_model=ContextualPreferenceResponse)
async def get_contextual_preferences(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    pref = service.get_contextual_preferences(user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Contextual preferences not found")
    return pref


@router.patch("/context", response_model=ContextualPreferenceResponse)
async def update_contextual_preferences(
    data: ContextualPreferenceCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    client = get_client_info(request)
    service = ProfileService(db)
    return service.update_contextual_preferences(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/confidence", response_model=ConfidenceProfileResponse)
async def get_confidence_profile(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ConfidenceService(db)
    return service.get_profile(user.id)


@router.post("/confidence/recalculate", response_model=ConfidenceProfileResponse)
async def recalculate_confidence(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ConfidenceService(db)
    return service.recalculate(user.id, trigger_event="manual_request")


@router.get("/confidence/history")
async def get_confidence_history(
    limit: int = 30,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ConfidenceService(db)
    return service.get_history(user.id, limit=limit)


@router.get("/completeness", response_model=ProfileCompletenessResponse)
async def get_profile_completeness(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.get_completeness(user.id)
