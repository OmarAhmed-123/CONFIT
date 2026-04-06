"""
CONFIT Backend — Brand Ecosystem Router
======================================
API endpoints for cross-group brand ecosystem integration:
- GROUP 1: User identity integration
- GROUP 2: Styling recommendation integration
- GROUP 3: Try-on fit integration
- GROUP 4: Wardrobe sustainability integration
- GROUP 5: Checkout confidence integration
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from services.brand_ecosystem_integration import BrandEcosystemIntegration
from services.brand_intelligence_service import BrandIntelligenceService
from services.marketplace_governance_service import MarketplaceGovernanceService
from utils.auth_deps import require_auth, require_admin
from services.auth_service import UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/api/brand-ecosystem", tags=["Brand Ecosystem Integration"])


# ── Service Dependencies ───────────────────────────────────────────────

def get_ecosystem(db: Session = Depends(get_db)) -> BrandEcosystemIntegration:
    return BrandEcosystemIntegration(db)


# ── Request Models ──────────────────────────────────────────────────────

class BrandAffinityRequest(BaseModel):
    affinity_score: float
    context: Dict[str, Any] = None


class BrandInteractionRequest(BaseModel):
    interaction_type: str
    context: Dict[str, Any] = None


class BrandEventRequest(BaseModel):
    event_type: str
    data: Dict[str, Any]


# ── GROUP 6 → GROUP 1: Brand to User Identity ───────────────────────────

@router.post("/{brand_id}/propagate-affinity/{user_id}")
async def propagate_brand_affinity(
    brand_id: str,
    user_id: str,
    data: BrandAffinityRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Propagate brand affinity to user profile (GROUP 1 integration)."""
    result = await ecosystem.propagate_brand_affinity_to_user(
        user_id=user_id,
        brand_id=brand_id,
        affinity_score=data.affinity_score,
        context=data.context,
    )
    return result


@router.get("/{brand_id}/confidence-impact/{user_id}")
async def get_brand_confidence_impact(
    brand_id: str,
    user_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand impact on user confidence dimensions (GROUP 1)."""
    result = await ecosystem.get_user_brand_confidence_impact(user_id, brand_id)
    return result


# ── GROUP 6 → GROUP 2: Brand to Styling ────────────────────────────────

@router.get("/{brand_id}/recommendation-weight")
async def get_brand_recommendation_weight(
    brand_id: str,
    user_id: str = Query(None, description="Optional user ID for personalization"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand weight for recommendation engine (GROUP 2 integration)."""
    result = await ecosystem.get_brand_recommendation_weight(brand_id, user_id)
    return result


@router.get("/{brand_id}/style-vector")
async def get_brand_style_vector(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand style vector for AI Brain (GROUP 2 integration)."""
    result = await ecosystem.get_brand_style_vector(brand_id)
    return result


# ── GROUP 6 → GROUP 3: Brand to Try-On ──────────────────────────────────

@router.get("/{brand_id}/fit-consistency")
async def get_brand_fit_consistency(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand fit consistency for size prediction (GROUP 3 integration)."""
    result = await ecosystem.get_brand_fit_consistency(brand_id)
    return result


@router.get("/{brand_id}/quality-factor")
async def get_brand_quality_factor(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand quality factor for visual realism (GROUP 3 integration)."""
    result = await ecosystem.get_brand_quality_factor(brand_id)
    return result


# ── GROUP 6 → GROUP 4: Brand to Wardrobe ────────────────────────────────

@router.get("/{brand_id}/sustainability-rating")
async def get_brand_sustainability_rating(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand sustainability rating for wardrobe insights (GROUP 4 integration)."""
    result = await ecosystem.get_brand_sustainability_rating(brand_id)
    return result


@router.get("/{brand_id}/ownership-insights")
async def get_brand_ownership_insights(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand ownership patterns for wardrobe analytics (GROUP 4)."""
    result = await ecosystem.get_brand_ownership_insights(brand_id)
    return result


# ── GROUP 6 → GROUP 5: Brand to Checkout ────────────────────────────────

@router.get("/{brand_id}/purchase-confidence-factor")
async def get_brand_purchase_confidence_factor(
    brand_id: str,
    user_id: str = Query(None, description="Optional user ID"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand factor for purchase confidence calculation (GROUP 5 integration)."""
    result = await ecosystem.get_brand_purchase_confidence_factor(brand_id, user_id)
    return result


@router.get("/{brand_id}/bnpl-eligibility-factor")
async def get_brand_bnpl_eligibility_factor(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get brand factor for BNPL eligibility (GROUP 5 integration)."""
    result = await ecosystem.get_brand_bnpl_eligibility_factor(brand_id)
    return result


# ── Reverse Integration: User Signals → Brand ───────────────────────────

@router.post("/{brand_id}/interaction/{user_id}")
async def process_user_brand_interaction(
    brand_id: str,
    user_id: str,
    data: BrandInteractionRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Process user interaction with brand and update brand intelligence."""
    result = await ecosystem.process_user_brand_interaction(
        user_id=user_id,
        brand_id=brand_id,
        interaction_type=data.interaction_type,
        context=data.context,
    )
    return result


@router.get("/{brand_id}/aggregate-signals")
async def aggregate_user_signals_to_brand(
    brand_id: str,
    time_window_days: int = Query(30, description="Time window in days"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Aggregate all user signals for a brand over time window."""
    result = await ecosystem.aggregate_user_signals_to_brand(brand_id, time_window_days)
    return result


# ── Cross-Group Event Propagation ───────────────────────────────────────

@router.post("/{brand_id}/propagate-event")
async def propagate_brand_event(
    brand_id: str,
    data: BrandEventRequest,
    user: UserProfile = Depends(require_admin),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Propagate brand event to all affected groups (admin only)."""
    result = await ecosystem.propagate_brand_event(
        event_type=data.event_type,
        brand_id=brand_id,
        data=data.data,
    )
    return result


# ── Unified Ecosystem Context ───────────────────────────────────────────

@router.get("/{brand_id}/ecosystem-context")
async def get_brand_ecosystem_context(
    brand_id: str,
    user_id: str = Query(None, description="Optional user ID for personalization"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """
    Get complete brand context across all ecosystem groups.
    
    Single source of truth for brand intelligence across:
    - GROUP 1: User identity impact
    - GROUP 2: Recommendation weight
    - GROUP 3: Fit consistency
    - GROUP 4: Sustainability rating
    - GROUP 5: Purchase confidence factor
    """
    result = await ecosystem.get_brand_ecosystem_context(brand_id, user_id)
    return result


# ── Batch Operations ────────────────────────────────────────────────────

@router.post("/batch/recommendation-weights")
async def get_batch_recommendation_weights(
    brand_ids: List[str],
    user_id: str = Query(None, description="Optional user ID"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get recommendation weights for multiple brands."""
    results = []
    for brand_id in brand_ids:
        result = await ecosystem.get_brand_recommendation_weight(brand_id, user_id)
        results.append(result)
    
    return {
        "brands": results,
        "count": len(results),
    }


@router.post("/batch/ecosystem-contexts")
async def get_batch_ecosystem_contexts(
    brand_ids: List[str],
    user_id: str = Query(None, description="Optional user ID"),
    user: UserProfile = Depends(require_auth),
    ecosystem: BrandEcosystemIntegration = Depends(get_ecosystem),
):
    """Get ecosystem contexts for multiple brands."""
    results = []
    for brand_id in brand_ids[:10]:  # Limit to 10 for performance
        result = await ecosystem.get_brand_ecosystem_context(brand_id, user_id)
        results.append(result)
    
    return {
        "brands": results,
        "count": len(results),
    }


# ── Health Check ────────────────────────────────────────────────────────

@router.get("/health")
async def ecosystem_health_check():
    """Check ecosystem integration health status."""
    return {
        "status": "healthy",
        "integration_groups": [1, 2, 3, 4, 5],
        "signal_types": {
            "brand_to_user": len([
                "brand_affinity_update",
                "brand_trust_change",
            ]),
            "brand_to_styling": len([
                "brand_trend_alignment",
                "brand_style_vector",
            ]),
            "brand_to_tryon": len([
                "brand_fit_consistency",
                "brand_quality_score",
            ]),
            "brand_to_wardrobe": len([
                "brand_sustainability_rating",
                "brand_longevity_score",
            ]),
            "brand_to_checkout": len([
                "brand_trust_index",
                "brand_return_risk",
            ]),
        },
    }
