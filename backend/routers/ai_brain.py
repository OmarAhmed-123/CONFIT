"""
CONFIT Backend — AI Brain Router
=================================
API endpoints for the centralized personalization engine.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.ai_brain_service import AIBrainService, get_ai_brain_service
from utils.auth_deps import require_auth
from services.auth_service import UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/api/brain", tags=["AI Central Brain"])


# ── Request/Response Models ───────────────────────────────────────────

class TrackInteractionRequest(BaseModel):
    interaction_type: str
    entity_type: str
    entity_id: str
    context: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None


class TrackOutfitFeedbackRequest(BaseModel):
    outfit_id: str
    accepted: bool
    feedback_type: str = "explicit"
    reason: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class TrackOccasionRequest(BaseModel):
    occasion: str
    outfit_id: str
    context: Optional[Dict[str, Any]] = None


class TrackBudgetRequest(BaseModel):
    action: str
    amount: float
    context: Optional[Dict[str, Any]] = None


class OutfitRecommendationRequest(BaseModel):
    occasion: Optional[str] = None
    budget: Optional[float] = None
    item_constraints: Optional[Dict[str, str]] = None
    use_wardrobe: bool = True
    limit: int = 5


class ColorValidationRequest(BaseModel):
    colors: List[str]


class PatternValidationRequest(BaseModel):
    patterns: List[str]


class SilhouetteValidationRequest(BaseModel):
    silhouettes: List[str]


class OccasionCheckRequest(BaseModel):
    outfit_data: Dict[str, Any]
    occasion: str


# ── Signal Collection Endpoints (INPUT) ───────────────────────────────

@router.post("/track/interaction")
async def track_interaction(
    data: TrackInteractionRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track user interaction for implicit preference learning."""
    brain.track_interaction(
        user_id=user.id,
        interaction_type=data.interaction_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        context=data.context,
        duration_ms=data.duration_ms,
    )
    return {"status": "tracked", "signal_type": data.interaction_type}


@router.post("/track/outfit-feedback")
async def track_outfit_feedback(
    data: TrackOutfitFeedbackRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track outfit acceptance/rejection for learning."""
    brain.track_outfit_feedback(
        user_id=user.id,
        outfit_id=data.outfit_id,
        accepted=data.accepted,
        feedback_type=data.feedback_type,
        reason=data.reason,
        context=data.context,
    )
    return {
        "status": "tracked",
        "feedback": "accepted" if data.accepted else "rejected",
    }


@router.post("/track/occasion")
async def track_occasion_pattern(
    data: TrackOccasionRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track occasion-based outfit patterns."""
    brain.track_occasion_pattern(
        user_id=user.id,
        occasion=data.occasion,
        outfit_id=data.outfit_id,
        context=data.context,
    )
    return {"status": "tracked", "occasion": data.occasion}


@router.post("/track/budget")
async def track_budget_behavior(
    data: TrackBudgetRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track budget-related behaviors."""
    brain.track_budget_behavior(
        user_id=user.id,
        action=data.action,
        amount=data.amount,
        context=data.context,
    )
    return {"status": "tracked", "action": data.action}


# ── Preference Aggregation Endpoints ───────────────────────────────────

@router.get("/style-vector")
async def get_style_vector(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get user's aggregated style vector."""
    return brain.get_user_style_vector(user.id)


@router.get("/wardrobe-context")
async def get_wardrobe_context(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get wardrobe-aware context for styling."""
    return brain.get_wardrobe_context(user.id)


@router.get("/contextual-factors")
async def get_contextual_factors(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get contextual factors (location, weather, lifestyle)."""
    return brain.get_contextual_factors(user.id)


# ── Recommendation Endpoints (OUTPUT) ────────────────────────────────

@router.post("/recommendations/outfits")
async def get_outfit_recommendations(
    data: OutfitRecommendationRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Generate personalized outfit recommendations."""
    recommendations = brain.generate_outfit_recommendations(
        user_id=user.id,
        occasion=data.occasion,
        budget=data.budget,
        item_constraints=data.item_constraints,
        use_wardrobe=data.use_wardrobe,
        limit=data.limit,
    )
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
    }


# ── Fashion Rule Engine Endpoints ─────────────────────────────────────

@router.post("/validate/colors")
async def validate_colors(
    data: ColorValidationRequest,
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Validate color combination against fashion rules."""
    return brain.validate_color_combination(data.colors)


@router.post("/validate/patterns")
async def validate_patterns(
    data: PatternValidationRequest,
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Validate pattern combination against fashion rules."""
    return brain.validate_pattern_combination(data.patterns)


@router.post("/validate/silhouette")
async def validate_silhouette(
    data: SilhouetteValidationRequest,
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Validate silhouette balance for proportion."""
    return brain.validate_silhouette_balance(data.silhouettes)


@router.post("/validate/occasion")
async def check_occasion_appropriateness(
    data: OccasionCheckRequest,
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Check if outfit meets occasion dress code requirements."""
    return brain.check_occasion_appropriateness(
        outfit_data=data.outfit_data,
        occasion=data.occasion,
    )


# ── Trend Endpoints ───────────────────────────────────────────────────

@router.get("/trends")
async def get_trending_elements(
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get current trending elements."""
    return brain.get_trending_elements()


@router.get("/trends/adapt")
async def adapt_to_trends(
    trend_sensitivity: float = 0.5,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Adapt recommendations to current trends based on user's sensitivity."""
    style_vector = brain.get_user_style_vector(user.id)
    return brain.adapt_to_trends(style_vector, trend_sensitivity)


# ── Weather/Climate Endpoints ──────────────────────────────────────────

@router.get("/weather-recommendations")
async def get_weather_recommendations(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get weather-appropriate styling recommendations."""
    return brain.get_weather_appropriate_items(user.id)


# ── Confidence Endpoints ──────────────────────────────────────────────

@router.post("/confidence/recalculate")
async def recalculate_confidence(
    trigger_event: str = None,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Recalculate user's confidence scores."""
    result = brain.recalculate_user_confidence(user.id, trigger_event)
    return result


@router.get("/confidence/breakdown")
async def get_confidence_breakdown(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get detailed breakdown of user's confidence dimensions."""
    return brain.get_confidence_breakdown(user.id)


# ── Style Evolution Endpoints ─────────────────────────────────────────

@router.post("/evolution/record")
async def record_style_evolution(
    event_type: str,
    previous_value: Any,
    new_value: Any,
    trigger_source: str = "implicit",
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Record style evolution event."""
    brain.update_style_evolution(
        user_id=user.id,
        event_type=event_type,
        previous_value=previous_value,
        new_value=new_value,
        trigger_source=trigger_source,
    )
    return {"status": "recorded", "event_type": event_type}


# ── Commerce Signal Endpoints (GROUP 5) ───────────────────────────────────

class TrackPurchaseRequest(BaseModel):
    order_id: str
    items: List[Dict[str, Any]]
    total: float
    payment_method: str
    context: Optional[Dict[str, Any]] = None


class TrackCartAbandonRequest(BaseModel):
    cart_value: float
    item_count: int
    abandonment_stage: str
    context: Optional[Dict[str, Any]] = None


class TrackPriceSensitivityRequest(BaseModel):
    action: str
    price_point: float
    context: Optional[Dict[str, Any]] = None


class TrackBrandAffinityRequest(BaseModel):
    brand: str
    interaction_type: str
    context: Optional[Dict[str, Any]] = None


@router.post("/track/purchase")
async def track_purchase_behavior(
    data: TrackPurchaseRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track purchase behavior for commerce intelligence."""
    brain.track_purchase_behavior(
        user_id=user.id,
        order_id=data.order_id,
        items=data.items,
        total=data.total,
        payment_method=data.payment_method,
        context=data.context,
    )
    return {"status": "tracked", "order_id": data.order_id}


@router.post("/track/cart-abandon")
async def track_cart_abandonment(
    data: TrackCartAbandonRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track cart abandonment for rescue strategies."""
    brain.track_cart_abandonment(
        user_id=user.id,
        cart_value=data.cart_value,
        item_count=data.item_count,
        abandonment_stage=data.abandonment_stage,
        context=data.context,
    )
    return {"status": "tracked", "stage": data.abandonment_stage}


@router.post("/track/price-sensitivity")
async def track_price_sensitivity(
    data: TrackPriceSensitivityRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track price sensitivity signals."""
    brain.track_price_sensitivity(
        user_id=user.id,
        action=data.action,
        price_point=data.price_point,
        context=data.context,
    )
    return {"status": "tracked", "action": data.action}


@router.post("/track/brand-affinity")
async def track_brand_affinity_signal(
    data: TrackBrandAffinityRequest,
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Track brand affinity signals."""
    brain.track_brand_affinity(
        user_id=user.id,
        brand=data.brand,
        interaction_type=data.interaction_type,
        context=data.context,
    )
    return {"status": "tracked", "brand": data.brand}


@router.get("/commerce-insights")
async def get_commerce_insights(
    user: UserProfile = Depends(require_auth),
    brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get aggregated commerce insights for the user."""
    return brain.get_commerce_insights(user.id)
