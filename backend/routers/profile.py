"""
CONFIT Backend — Profile Router
===============================
User profile management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.session import get_db
from services.profile_service import ProfileService, get_profile_service
from services.confidence_service import ConfidenceService, get_confidence_service
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


@router.get("", response_model=dict)
async def get_profile(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get unified user profile summary."""
    style = profile_service.get_style_profile(user.id)
    body = profile_service.get_body_profile(user.id)
    budget = profile_service.get_budget_profile(user.id)
    completeness = profile_service.get_completeness(user.id)
    return {
        "user_id": user.id,
        "style_profile": style,
        "body_profile": body,
        "budget_profile": budget,
        "completeness": completeness,
    }


@router.patch("", response_model=dict)
async def update_profile(
    data: dict,
    request: Request,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Update user profile fields."""
    client = get_client_info(request)
    updated = {}
    if "style_profile" in data:
        updated["style_profile"] = profile_service.update_style_profile(
            user_id=user.id,
            data=StyleProfileCreate(**data["style_profile"]),
            source="explicit",
            ip_address=client["ip_address"],
            user_agent=client["user_agent"],
        )
    if "body_profile" in data:
        updated["body_profile"] = profile_service.update_body_profile(
            user_id=user.id,
            data=BodyProfileCreate(**data["body_profile"]),
            source="explicit",
            ip_address=client["ip_address"],
            user_agent=client["user_agent"],
        )
    if "budget_profile" in data:
        updated["budget_profile"] = profile_service.update_budget_profile(
            user_id=user.id,
            data=BudgetProfileCreate(**data["budget_profile"]),
            source="explicit",
            ip_address=client["ip_address"],
            user_agent=client["user_agent"],
        )
    return {"user_id": user.id, "updated": updated}


@router.get("/style", response_model=StyleProfileResponse)
async def get_style_profile(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    profile_service = ProfileService(db)
    profile = profile_service.get_style_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return profile


@router.patch("/style", response_model=StyleProfileResponse)
async def update_style_profile(
    data: StyleProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    client = get_client_info(request)
    return profile_service.update_style_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.post("/style/archetype", response_model=StyleArchetypeResult)
async def calculate_archetype(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    result = profile_service.calculate_archetype(user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/body", response_model=BodyProfileResponse)
async def get_body_profile(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    profile = profile_service.get_body_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Body profile not found")
    return profile


@router.patch("/body", response_model=BodyProfileResponse)
async def update_body_profile(
    data: BodyProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    client = get_client_info(request)
    return profile_service.update_body_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/budget", response_model=BudgetProfileResponse)
async def get_budget_profile(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    profile = profile_service.get_budget_profile(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Budget profile not found")
    return profile


@router.patch("/budget", response_model=BudgetProfileResponse)
async def update_budget_profile(
    data: BudgetProfileCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    client = get_client_info(request)
    return profile_service.update_budget_profile(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/brands", response_model=List[BrandAffinityResponse])
async def get_brand_affinities(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return profile_service.get_brand_affinities(user.id)


@router.post("/brands", response_model=BrandAffinityResponse)
async def add_brand_affinity(
    data: BrandAffinityCreate,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return profile_service.add_brand_affinity(user.id, data, source="explicit")


@router.delete("/brands/{brand_id}")
async def remove_brand_affinity(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    success = profile_service.remove_brand_affinity(user.id, brand_id)
    if not success:
        raise HTTPException(status_code=404, detail="Brand affinity not found")
    return {"success": True}


@router.get("/context", response_model=ContextualPreferenceResponse)
async def get_contextual_preferences(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    pref = profile_service.get_contextual_preferences(user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Contextual preferences not found")
    return pref


@router.patch("/context", response_model=ContextualPreferenceResponse)
async def update_contextual_preferences(
    data: ContextualPreferenceCreate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    client = get_client_info(request)
    return profile_service.update_contextual_preferences(
        user_id=user.id,
        data=data,
        source="explicit",
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/confidence", response_model=ConfidenceProfileResponse)
async def get_confidence_profile(
    user: UserProfile = Depends(require_auth),
    confidence_service: ConfidenceService = Depends(get_confidence_service),
):
    return confidence_service.get_profile(user.id)


@router.post("/confidence/recalculate", response_model=ConfidenceProfileResponse)
async def recalculate_confidence(
    user: UserProfile = Depends(require_auth),
    confidence_service: ConfidenceService = Depends(get_confidence_service),
):
    return confidence_service.recalculate(user.id, trigger_event="manual_request")


@router.get("/confidence/history")
async def get_confidence_history(
    limit: int = 30,
    user: UserProfile = Depends(require_auth),
    confidence_service: ConfidenceService = Depends(get_confidence_service),
):
    return confidence_service.get_history(user.id, limit=limit)


@router.get("/completeness", response_model=ProfileCompletenessResponse)
async def get_profile_completeness(
    user: UserProfile = Depends(require_auth),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return profile_service.get_completeness(user.id)
