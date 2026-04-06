"""
CONFIT Backend — Style DNA API Routes
=====================================
API endpoints for Style DNA feature.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_current_user_optional, get_db
from core.security.rbac import AuthContext
from services.style_dna_service import StyleDNAService, get_style_dna_service
from models.style_dna_models import (
    StyleDNAResponseDTO,
    StyleDNACreateDTO,
    StyleDNADashboardDTO,
    StyleAnalysisResultDTO,
    StyleSimilarityDTO,
    StyleQuizSubmissionDTO,
    StyleQuizResultDTO,
    StyleEvolutionDTO,
    StyleClusterDTO,
    StyleSignalCreateDTO,
    StyleCategory,
    BudgetLevel,
    FitPreference,
)


router = APIRouter(prefix="/style-dna", tags=["Style DNA"])


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY INJECTION
# ─────────────────────────────────────────────────────────────────────────────

async def get_style_dna(
    db: AsyncSession = Depends(get_db),
) -> StyleDNAService:
    """Get Style DNA service instance."""
    return get_style_dna_service(db)


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=StyleDNAResponseDTO,
    summary="Get user's Style DNA profile",
)
async def get_style_profile(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get the current user's Style DNA profile.
    Creates a new profile if one doesn't exist.
    """
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    return style_dna._profile_to_dto(profile)


@router.patch(
    "/profile",
    response_model=StyleDNAResponseDTO,
    summary="Update Style DNA profile",
)
async def update_style_profile(
    update_data: StyleDNACreateDTO,
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Update the user's Style DNA profile.
    Records changes in evolution history.
    """
    profile = await style_dna.update_profile(
        user_id=UUID(current_user.user_id),
        update_data=update_data,
    )
    return style_dna._profile_to_dto(profile)


@router.get(
    "/dashboard",
    response_model=StyleDNADashboardDTO,
    summary="Get Style DNA dashboard data",
)
async def get_style_dashboard(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get complete dashboard data for Style DNA visualization.
    Includes style map, color wheel, brand universe, and insights.
    """
    return await style_dna.get_dashboard_data(UUID(current_user.user_id))


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=StyleAnalysisResultDTO,
    summary="Analyze user's style",
)
async def analyze_style(
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh analysis"),
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Perform comprehensive style analysis.
    
    Analyzes:
    - Wardrobe items
    - Purchase history
    - Style quiz answers
    - Browsing behavior
    
    Generates style embedding and assigns to cluster.
    """
    return await style_dna.analyze_user_style(
        user_id=UUID(current_user.user_id),
        force_refresh=force_refresh,
    )


@router.get(
    "/completeness",
    summary="Get profile completeness",
)
async def get_profile_completeness(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get profile completeness percentage and breakdown."""
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    return {
        "completeness": float(profile.profile_completeness),
        "breakdown": style_dna._get_completeness_breakdown(profile),
        "version": profile.profile_version,
    }


# ─────────────────────────────────────────────────────────────────────────────
    # SIMILARITY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/similar-users",
    response_model=List[StyleSimilarityDTO],
    summary="Find users with similar style",
)
async def find_similar_users(
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0),
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Find users with similar Style DNA.
    Uses vector similarity on style embeddings.
    """
    return await style_dna.find_similar_users(
        user_id=UUID(current_user.user_id),
        limit=limit,
        min_similarity=min_similarity,
    )


@router.get(
    "/cluster",
    response_model=Optional[dict],
    summary="Get user's style cluster",
)
async def get_style_cluster(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get the user's assigned style cluster.
    Returns cluster details and assignment confidence.
    """
    assignment = await style_dna._get_cluster_assignment(UUID(current_user.user_id))
    return assignment.model_dump() if assignment else None


# ─────────────────────────────────────────────────────────────────────────────
# STYLE QUIZ ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/quiz",
    response_model=StyleQuizResultDTO,
    summary="Submit style quiz",
)
async def submit_style_quiz(
    submission: StyleQuizSubmissionDTO,
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Submit style quiz responses.
    Updates user's Style DNA profile based on answers.
    """
    return await style_dna.submit_style_quiz(
        user_id=UUID(current_user.user_id),
        submission=submission,
    )


@router.get(
    "/quiz/questions",
    summary="Get style quiz questions",
)
async def get_quiz_questions(
    quiz_type: str = Query("initial", description="Quiz type"),
):
    """
    Get style quiz questions.
    Returns questions for the specified quiz type.
    """
    # Define quiz questions
    questions = [
        {
            "id": "style_1",
            "type": "image_select",
            "question": "Which outfit resonates most with your style?",
            "options": [
                {"id": "classic", "label": "Classic Elegance", "image": "/quiz/classic.jpg"},
                {"id": "trendy", "label": "Trendy Modern", "image": "/quiz/trendy.jpg"},
                {"id": "bohemian", "label": "Bohemian Free", "image": "/quiz/bohemian.jpg"},
                {"id": "minimalist", "label": "Minimalist Clean", "image": "/quiz/minimalist.jpg"},
            ],
        },
        {
            "id": "style_2",
            "type": "multi_select",
            "question": "Select colors you love wearing",
            "options": [
                {"id": "black", "label": "Black", "color": "#000000"},
                {"id": "white", "label": "White", "color": "#FFFFFF"},
                {"id": "navy", "label": "Navy", "color": "#1B2838"},
                {"id": "beige", "label": "Beige", "color": "#F5F5DC"},
                {"id": "red", "label": "Red", "color": "#FF0000"},
                {"id": "blue", "label": "Blue", "color": "#0000FF"},
                {"id": "green", "label": "Green", "color": "#008000"},
                {"id": "pink", "label": "Pink", "color": "#FFC0CB"},
            ],
        },
        {
            "id": "style_3",
            "type": "single_select",
            "question": "How do you prefer your clothes to fit?",
            "options": [
                {"id": "tight", "label": "Fitted/Tight"},
                {"id": "slim", "label": "Slim"},
                {"id": "regular", "label": "Regular"},
                {"id": "relaxed", "label": "Relaxed"},
                {"id": "oversized", "label": "Oversized"},
            ],
        },
        {
            "id": "style_4",
            "type": "multi_select",
            "question": "What occasions do you dress for most?",
            "options": [
                {"id": "everyday", "label": "Everyday/Casual"},
                {"id": "work", "label": "Work/Office"},
                {"id": "formal", "label": "Formal Events"},
                {"id": "date_night", "label": "Date Night"},
                {"id": "weekend", "label": "Weekend Activities"},
                {"id": "athletic", "label": "Athletic/Active"},
            ],
        },
        {
            "id": "style_5",
            "type": "single_select",
            "question": "What's your typical budget for a clothing item?",
            "options": [
                {"id": "budget_conscious", "label": "Under $50"},
                {"id": "moderate", "label": "$50 - $150"},
                {"id": "premium", "label": "$150 - $500"},
                {"id": "luxury", "label": "$500 - $1500"},
                {"id": "ultra_luxury", "label": "Over $1500"},
            ],
        },
        {
            "id": "style_6",
            "type": "multi_select",
            "question": "Which patterns do you prefer?",
            "options": [
                {"id": "solid", "label": "Solid Colors"},
                {"id": "stripes", "label": "Stripes"},
                {"id": "plaid", "label": "Plaid/Checkered"},
                {"id": "floral", "label": "Floral"},
                {"id": "geometric", "label": "Geometric"},
                {"id": "animal_print", "label": "Animal Print"},
            ],
        },
        {
            "id": "style_7",
            "type": "multi_select",
            "question": "Select styles that describe you",
            "options": [
                {"id": "classic", "label": "Classic"},
                {"id": "trendy", "label": "Trendy"},
                {"id": "minimalist", "label": "Minimalist"},
                {"id": "edgy", "label": "Edgy"},
                {"id": "romantic", "label": "Romantic"},
                {"id": "sporty", "label": "Sporty"},
                {"id": "streetwear", "label": "Streetwear"},
                {"id": "vintage", "label": "Vintage"},
            ],
        },
        {
            "id": "style_8",
            "type": "single_select",
            "question": "What's your skin undertone?",
            "options": [
                {"id": "warm", "label": "Warm (golden/peachy)"},
                {"id": "cool", "label": "Cool (pinkish/bluish)"},
                {"id": "neutral", "label": "Neutral"},
                {"id": "unsure", "label": "Not sure"},
            ],
        },
    ]
    
    return {
        "quiz_type": quiz_type,
        "questions": questions,
        "total_questions": len(questions),
    }


# ─────────────────────────────────────────────────────────────────────────────
# EVOLUTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/evolution",
    response_model=List[StyleEvolutionDTO],
    summary="Get style evolution history",
)
async def get_evolution_history(
    limit: int = Query(20, ge=1, le=100),
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get the user's style evolution history.
    Shows how style preferences have changed over time.
    """
    return await style_dna._get_evolution_history(
        user_id=UUID(current_user.user_id),
        limit=limit,
    )


@router.get(
    "/evolution/timeline",
    summary="Get style evolution timeline",
)
async def get_evolution_timeline(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get style evolution timeline for visualization.
    Aggregates evolution events by time period.
    """
    events = await style_dna._get_evolution_history(
        user_id=UUID(current_user.user_id),
        limit=50,
    )
    
    # Group by month
    timeline = {}
    for event in events:
        month_key = event.created_at.strftime("%Y-%m")
        if month_key not in timeline:
            timeline[month_key] = {
                "month": month_key,
                "events": [],
                "change_count": 0,
            }
        timeline[month_key]["events"].append(event.model_dump())
        timeline[month_key]["change_count"] += 1
    
    return {
        "timeline": list(timeline.values()),
        "total_events": len(events),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/signals",
    summary="Record style signal",
)
async def record_style_signal(
    signal: StyleSignalCreateDTO,
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Record a behavioral style signal.
    Used for tracking browsing, views, and other implicit preferences.
    """
    result = await style_dna.record_signal(
        user_id=UUID(current_user.user_id),
        signal_type=signal.signal_type,
        signal_category=signal.signal_category,
        entity_type=signal.entity_type,
        entity_id=signal.entity_id,
        signal_data=signal.signal_data,
        base_weight=signal.base_weight,
        context=signal.context,
    )
    
    return {
        "id": str(result.id),
        "recorded": True,
        "created_at": result.created_at.isoformat(),
    }


@router.post(
    "/signals/batch",
    summary="Record multiple style signals",
)
async def record_batch_signals(
    signals: List[StyleSignalCreateDTO],
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Record multiple style signals at once.
    Useful for batch processing of behavioral data.
    """
    recorded = []
    
    for signal in signals:
        result = await style_dna.record_signal(
            user_id=UUID(current_user.user_id),
            signal_type=signal.signal_type,
            signal_category=signal.signal_category,
            entity_type=signal.entity_type,
            entity_id=signal.entity_id,
            signal_data=signal.signal_data,
            base_weight=signal.base_weight,
            context=signal.context,
        )
        recorded.append(str(result.id))
    
    return {
        "recorded_count": len(recorded),
        "signal_ids": recorded,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/preferences/colors",
    summary="Get color preferences",
)
async def get_color_preferences(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get detailed color preferences with recommendations."""
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    colors = profile.color_preferences or {}
    
    return {
        "primary": colors.get("primary", []),
        "secondary": colors.get("secondary", []),
        "avoided": colors.get("avoided", []),
        "undertone": colors.get("undertone"),
        "palette_type": colors.get("palette_type"),
        "recommended": style_dna._get_recommended_colors(colors.get("undertone")),
        "color_harmony": {
            "best_combinations": _get_color_combinations(colors.get("primary", [])),
        },
    }


@router.get(
    "/preferences/occasions",
    summary="Get occasion preferences",
)
async def get_occasion_preferences(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get occasion preferences with weights."""
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    occasions = profile.occasion_preferences or {}
    
    # Sort by weight
    sorted_occasions = sorted(
        occasions.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return {
        "occasions": dict(sorted_occasions),
        "top_occasions": [o[0] for o in sorted_occasions[:3]],
        "occasion_suggestions": _get_occasion_suggestions(sorted_occasions),
    }


@router.get(
    "/preferences/brands",
    summary="Get brand affinity",
)
async def get_brand_affinity(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get brand affinity scores."""
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    brands = profile.brand_affinity or []
    
    return {
        "brands": brands,
        "top_brands": sorted(brands, key=lambda x: x.get("affinity_score", 0), reverse=True)[:5],
        "brand_count": len(brands),
    }


@router.get(
    "/preferences/budget",
    summary="Get budget preferences",
)
async def get_budget_preferences(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get budget level and range preferences."""
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    return {
        "budget_level": profile.budget_level.value if profile.budget_level else "moderate",
        "budget_range": profile.budget_range or {},
        "suggestions": _get_budget_suggestions(profile.budget_level),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHTS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/insights",
    summary="Get style insights",
)
async def get_style_insights(
    style_dna: StyleDNAService = Depends(get_style_dna),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Get personalized style insights.
    Includes recommendations for profile improvement.
    """
    profile = await style_dna.get_or_create_profile(UUID(current_user.user_id))
    
    insights = await style_dna._generate_insights(profile)
    recommendations = await style_dna._generate_style_recommendations(profile)
    
    return {
        "insights": insights,
        "recommendations": recommendations,
        "confidence": float(profile.style_confidence),
        "completeness": float(profile.profile_completeness),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _get_color_combinations(colors: List[str]) -> List[dict]:
    """Get recommended color combinations."""
    if not colors:
        return []
    
    combinations = []
    neutrals = {"black", "white", "gray", "navy", "beige", "brown"}
    
    for color in colors[:3]:
        if color.lower() in neutrals:
            # Neutrals go with everything
            combinations.append({
                "base": color,
                "matches": ["any accent color", "other neutrals"],
                "type": "versatile",
            })
        else:
            # Color-specific combinations
            combinations.append({
                "base": color,
                "matches": list(neutrals)[:3],
                "type": "accent",
            })
    
    return combinations


def _get_occasion_suggestions(occasions: List[tuple]) -> List[dict]:
    """Get suggestions based on occasion preferences."""
    suggestions = []
    
    low_occasions = [o for o, w in occasions if w < 0.3]
    
    if "formal" in low_occasions:
        suggestions.append({
            "occasion": "formal",
            "message": "Consider adding formal pieces to your wardrobe",
            "priority": "medium",
        })
    
    if "work" in low_occasions:
        suggestions.append({
            "occasion": "work",
            "message": "Build a capsule work wardrobe",
            "priority": "low",
        })
    
    return suggestions


def _get_budget_suggestions(budget_level) -> List[dict]:
    """Get suggestions based on budget level."""
    if not budget_level:
        return []
    
    suggestions = []
    
    if budget_level.value == "budget_conscious":
        suggestions.append({
            "tip": "Look for sales and outlet stores",
            "brands": ["H&M", "Uniqlo", "Zara"],
        })
    elif budget_level.value == "luxury":
        suggestions.append({
            "tip": "Invest in timeless pieces",
            "brands": ["Ralph Lauren", "Burberry", "Theory"],
        })
    
    return suggestions
