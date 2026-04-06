"""
CONFIT Backend - Recommendation API Routes
==========================================
AI-powered product recommendations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_recommendation_service, get_current_user, get_current_user_optional
from application.services.recommendation_service import (
    RecommendationEngine,
    RecommendationDTO,
    PersonalizedRecommendationsDTO,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "",
    response_model=PersonalizedRecommendationsDTO,
    summary="Get personalized recommendations",
)
async def get_personalized_recommendations(
    limit: int = Query(20, ge=1, le=50),
    recommendation_service: RecommendationEngine = Depends(get_recommendation_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get personalized recommendations for user."""
    from uuid import UUID
    return await recommendation_service.get_personalized_recommendations(
        user_id=UUID(current_user.user_id),
        limit=limit,
    )


@router.get(
    "/products/{product_id}/similar",
    response_model=List[RecommendationDTO],
    summary="Get similar products",
)
async def get_similar_products(
    product_id: str,
    limit: int = Query(10, ge=1, le=50),
    recommendation_service: RecommendationEngine = Depends(get_recommendation_service),
):
    """Get similar products."""
    from uuid import UUID
    return await recommendation_service.get_similar_products(
        product_id=UUID(product_id),
        limit=limit,
    )


@router.get(
    "/style-based",
    response_model=List[RecommendationDTO],
    summary="Get style-based recommendations",
)
async def get_style_based_recommendations(
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    recommendation_service: RecommendationEngine = Depends(get_recommendation_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get recommendations based on user's style profile."""
    from uuid import UUID
    return await recommendation_service.get_style_based_recommendations(
        user_id=UUID(current_user.user_id),
        occasion=occasion,
        season=season,
        limit=limit,
    )


@router.get(
    "/complete-outfit/{product_id}",
    response_model=List[RecommendationDTO],
    summary="Get complete outfit recommendations",
)
async def get_complete_outfit_recommendations(
    product_id: str,
    limit: int = Query(5, ge=1, le=20),
    recommendation_service: RecommendationEngine = Depends(get_recommendation_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get items that complete an outfit with the given product."""
    from uuid import UUID
    return await recommendation_service.get_complete_outfit_recommendations(
        product_id=UUID(product_id),
        user_id=UUID(current_user.user_id),
        limit=limit,
    )
