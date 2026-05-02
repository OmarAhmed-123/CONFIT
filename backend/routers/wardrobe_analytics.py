"""
CONFIT Backend — Wardrobe Analytics Router
===========================================
GROUP 4: Personal Wardrobe & Smart Reuse
API endpoints for wardrobe analytics and personalization.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from services.wardrobe_analytics_service import WardrobeAnalyticsService, get_wardrobe_analytics_service
from services.ai_brain_service import AIBrainService, get_ai_brain_service
from utils.auth_deps import require_auth
from services.auth_service import UserProfile
from models.wardrobe_analytics_models import (
    WearLogEntry,
    OutfitHistoryCreate,
    OutfitHistoryResponse,
    WardrobeAnalyticsResponse,
    SustainabilityInsightsResponse,
    CapsuleWardrobeResponse,
    DeclutterSuggestionResponse,
    WardrobeConfidenceResponse,
    PurchaseAvoidanceResponse,
    SeasonalRotationResponse,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/wardrobe/analytics", tags=["Wardrobe Analytics"])


# ── Dependencies ───────────────────────────────────────────────────────

def get_analytics(
    db: Session = Depends(get_db),
):
    """Get WardrobeAnalyticsService (without AI brain)."""
    return get_wardrobe_analytics_service(db)


def get_analytics_with_ai(
    db: Session = Depends(get_db),
    ai_brain: AIBrainService = Depends(get_ai_brain_service),
):
    """Get WardrobeAnalyticsService (with AI brain)."""
    return get_wardrobe_analytics_service(db, ai_brain)


# ── Request Models ─────────────────────────────────────────────────────

class SetSeasonRequest(BaseModel):
    item_id: str
    primary_season: str
    secondary_seasons: Optional[List[str]] = None
    temp_range: Optional[dict] = None


class PurchaseCheckRequest(BaseModel):
    product_name: str
    product_category: str
    product_color: str
    product_price: Optional[float] = None


class OutfitRatingRequest(BaseModel):
    outfit_id: str
    rating: int
    notes: Optional[str] = None


# ── Wear Frequency Tracking ────────────────────────────────────────────

@router.post("/wear/log")
async def log_wear(
    data: WearLogEntry,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
    analytics: WardrobeAnalyticsService = Depends(get_analytics_with_ai),
):
    """Log a wear event for a wardrobe item."""
    result = analytics.log_wear(
        user_id=user.id,
        item_id=data.item_id,
        occasion=data.occasion,
        outfit_id=data.outfit_id,
        worn_at=data.worn_at,
    )
    return {"status": "logged", "data": result}


@router.get("/wear/stats")
async def get_wear_stats(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get wear frequency statistics for user's wardrobe."""
    return analytics.get_wear_frequency_stats(user.id)


# ── Seasonal Rotation ──────────────────────────────────────────────────

@router.get("/seasonal")
async def get_seasonal_rotation(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get seasonal rotation status and recommendations."""
    return analytics.get_seasonal_rotation(user.id)


@router.post("/seasonal/set")
async def set_item_season(
    data: SetSeasonRequest,
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Set seasonal classification for an item."""
    rotation = analytics.set_item_season(
        user_id=user.id,
        item_id=data.item_id,
        primary_season=data.primary_season,
        secondary_seasons=data.secondary_seasons,
        temp_range=data.temp_range,
    )
    return {
        "status": "updated",
        "item_id": data.item_id,
        "season": data.primary_season,
    }


# ── Outfit History ──────────────────────────────────────────────────────

@router.post("/outfits/log")
async def log_outfit(
    data: OutfitHistoryCreate,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
    analytics: WardrobeAnalyticsService = Depends(get_analytics_with_ai),
):
    """Log an outfit worn by the user."""
    outfit = analytics.log_outfit(
        user_id=user.id,
        item_ids=data.item_ids,
        outfit_name=data.outfit_name,
        occasion=data.occasion,
        weather=data.weather,
        temperature_c=data.temperature_c,
        is_favorite=data.is_favorite,
        ai_generated=data.ai_generated,
    )
    return {
        "status": "logged",
        "outfit_id": outfit.id,
        "item_count": len(data.item_ids),
    }


@router.get("/outfits/history")
async def get_outfit_history(
    limit: int = Query(20, ge=1, le=100),
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get outfit history for user."""
    return analytics.get_outfit_history(
        user_id=user.id,
        limit=limit,
        occasion=occasion,
        season=season,
    )


@router.post("/outfits/rate")
async def rate_outfit(
    data: OutfitRatingRequest,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Rate an outfit from history."""
    from models.wardrobe_analytics_models import OutfitHistory
    
    outfit = db.query(OutfitHistory).filter(
        OutfitHistory.id == data.outfit_id,
        OutfitHistory.user_id == user.id,
    ).first()
    
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    outfit.user_rating = data.rating
    outfit.feedback_notes = data.notes
    db.commit()
    
    return {"status": "rated", "rating": data.rating}


@router.post("/outfits/{outfit_id}/favorite")
async def toggle_favorite(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Toggle favorite status for an outfit."""
    from models.wardrobe_analytics_models import OutfitHistory
    
    outfit = db.query(OutfitHistory).filter(
        OutfitHistory.id == outfit_id,
        OutfitHistory.user_id == user.id,
    ).first()
    
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    outfit.is_favorite = not outfit.is_favorite
    db.commit()
    
    return {"status": "updated", "is_favorite": outfit.is_favorite}


# ── Unused Item Alerts ─────────────────────────────────────────────────

@router.get("/unused")
async def get_unused_items(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get items that haven't been worn recently."""
    return analytics.get_unused_items(user.id)


# ── Sustainability Insights ────────────────────────────────────────────

@router.get("/sustainability")
async def get_sustainability_insights(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get sustainability insights for wardrobe."""
    return analytics.get_sustainability_insights(user.id)


@router.post("/sustainability/recalculate")
async def recalculate_sustainability(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Recalculate sustainability metrics."""
    metrics = analytics.calculate_sustainability_metrics(user.id)
    return {
        "status": "recalculated",
        "sustainability_score": float(metrics.sustainability_score),
        "utilization_score": float(metrics.wardrobe_utilization_score),
    }


# ── Color & Style Analysis ─────────────────────────────────────────────

@router.get("/colors")
async def analyze_colors(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Analyze color distribution in wardrobe."""
    return analytics.analyze_color_dominance(user.id)


@router.get("/categories")
async def analyze_categories(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Analyze category/style distribution in wardrobe."""
    return analytics.analyze_style_dominance(user.id)


# ── Wardrobe Confidence Score ──────────────────────────────────────────

@router.get("/confidence")
async def get_wardrobe_confidence(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get wardrobe confidence score."""
    confidence = analytics.calculate_wardrobe_confidence(user.id)
    return {
        "overall_confidence": float(confidence.overall_confidence),
        "dimensions": {
            "variety": float(confidence.variety_score),
            "versatility": float(confidence.versatility_score),
            "utilization": float(confidence.utilization_score),
            "cohesion": float(confidence.cohesion_score),
            "seasonality": float(confidence.seasonality_score),
            "quality": float(confidence.quality_score),
        },
        "outfit_readiness": float(confidence.outfit_readiness),
        "occasion_coverage": confidence.occasion_coverage,
        "top_improvements": confidence.top_improvements,
        "quick_wins": confidence.quick_wins,
    }


# ── Capsule Wardrobe Detection ────────────────────────────────────────

@router.get("/capsules")
async def get_capsule_wardrobes(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Detect and get capsule wardrobes."""
    capsules = analytics.detect_capsule_wardrobes(user.id)
    return [{
        "id": str(c.id),
        "name": c.capsule_name,
        "type": c.capsule_type,
        "item_count": c.item_count,
        "cohesion_score": float(c.cohesion_score),
        "versatility_score": float(c.versatility_score),
        "outfit_combinations": c.outfit_combinations,
        "dominant_colors": c.dominant_colors,
        "is_ai_suggested": c.is_ai_suggested,
    } for c in capsules]


# ── Smart Declutter ────────────────────────────────────────────────────

@router.get("/declutter")
async def get_declutter_suggestions(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get smart declutter suggestions."""
    suggestions = analytics.generate_declutter_suggestions(user.id)
    return [{
        "id": str(s.id),
        "item_id": s.item_id,
        "suggestion_type": s.suggestion_type,
        "confidence": float(s.confidence),
        "reason": s.reason,
        "estimated_resale_value": float(s.estimated_resale_value) if s.estimated_resale_value else None,
        "status": s.status,
    } for s in suggestions]


@router.post("/declutter/{suggestion_id}/dismiss")
async def dismiss_declutter_suggestion(
    suggestion_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Dismiss a declutter suggestion."""
    from models.wardrobe_analytics_models import DeclutterSuggestion
    from datetime import datetime, timezone
    
    suggestion = db.query(DeclutterSuggestion).filter(
        DeclutterSuggestion.id == suggestion_id,
        DeclutterSuggestion.user_id == user.id,
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion.status = "dismissed"
    suggestion.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"status": "dismissed"}


@router.post("/declutter/{suggestion_id}/act")
async def act_on_declutter_suggestion(
    suggestion_id: str,
    action: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark action taken on declutter suggestion."""
    from models.wardrobe_analytics_models import DeclutterSuggestion
    from datetime import datetime, timezone
    
    suggestion = db.query(DeclutterSuggestion).filter(
        DeclutterSuggestion.id == suggestion_id,
        DeclutterSuggestion.user_id == user.id,
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion.status = "acted"
    suggestion.action_taken = action
    suggestion.acted_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"status": "acted", "action": action}


# ── Purchase Avoidance ─────────────────────────────────────────────────

@router.post("/purchase-check")
async def check_purchase_avoidance(
    data: PurchaseCheckRequest,
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics_with_ai),
):
    """Check if user already has similar items to prevent unnecessary purchase."""
    result = analytics.check_purchase_avoidance(
        user_id=user.id,
        product_name=data.product_name,
        product_category=data.product_category,
        product_color=data.product_color,
        product_price=data.product_price,
    )
    return result.model_dump()


# ── Full Analytics Dashboard ───────────────────────────────────────────

@router.get("/dashboard")
async def get_full_analytics(
    user: UserProfile = Depends(require_auth),
    analytics: WardrobeAnalyticsService = Depends(get_analytics_with_ai),
):
    """Get comprehensive wardrobe analytics dashboard."""
    return analytics.get_full_analytics(user.id)


# ── AI Brain Signal Endpoints ──────────────────────────────────────────

@router.get("/ownership-signals")
async def get_ownership_signals(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get ownership signals for AI Brain (items owned, categories, brands)."""
    from database.models import WardrobeItem
    from collections import Counter
    
    items = db.query(WardrobeItem).filter(
        WardrobeItem.owner_user_id == user.id,
    ).all()
    
    categories = Counter(i.category for i in items)
    brands = Counter(i.brand for i in items if i.brand)
    colors = Counter(i.color for i in items if i.color)
    
    return {
        "total_items": len(items),
        "categories": dict(categories),
        "top_brands": dict(brands.most_common(5)),
        "color_distribution": dict(colors),
        "ownership_strength": min(len(items) / 30, 1.0),  # Normalized to 30 items
    }


@router.get("/reuse-patterns")
async def get_reuse_patterns(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get reuse pattern signals for AI Brain."""
    from models.wardrobe_analytics_models import WardrobeItemUsage
    
    usage = db.query(WardrobeItemUsage).filter(
        WardrobeItemUsage.user_id == user.id,
    ).all()
    
    total_wears = sum(u.wear_count for u in usage)
    avg_wears = total_wears / len(usage) if usage else 0
    
    most_worn = sorted(usage, key=lambda u: u.wear_count, reverse=True)[:5]
    
    return {
        "total_wears": total_wears,
        "average_wears_per_item": round(avg_wears, 2),
        "most_worn_items": [{
            "item_id": u.item_id,
            "wear_count": u.wear_count,
            "occasions": u.occasions_worn,
        } for u in most_worn],
        "reuse_rate": min(avg_wears / 10, 1.0),  # Normalized
    }


@router.get("/style-signals")
async def get_style_signals(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
    analytics: WardrobeAnalyticsService = Depends(get_analytics),
):
    """Get style dominance signals for AI Brain."""
    color_analysis = analytics.analyze_color_dominance(user.id)
    style_analysis = analytics.analyze_style_dominance(user.id)
    
    dominant_colors = [c for c in color_analysis if c["is_dominant"]]
    gaps = [s for s in style_analysis if s["is_gap"]]
    
    return {
        "dominant_colors": dominant_colors,
        "color_harmony_groups": list(set(c["harmony_group"] for c in color_analysis)),
        "category_distribution": style_analysis,
        "wardrobe_gaps": gaps,
        "style_balance_score": 100 - len(gaps) * 15,  # Penalty for each gap
    }
