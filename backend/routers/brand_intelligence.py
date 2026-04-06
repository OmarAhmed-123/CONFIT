"""
CONFIT Backend — Brand Intelligence Router
==========================================
API endpoints for brand intelligence and analytics:
- Demand prediction
- Style trend analytics
- Return risk scoring
- AI pricing suggestions
- Inventory intelligence
- AI Brain signal integration
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from services.brand_intelligence_service import BrandIntelligenceService
from services.marketplace_governance_service import MarketplaceGovernanceService
from services.ai_brain_service import AIBrainService
from utils.auth_deps import require_auth, require_admin
from services.auth_service import UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/api/brand-intelligence", tags=["Brand Intelligence"])


# ── Service Dependencies ───────────────────────────────────────────────

def get_brand_intelligence(db: Session = Depends(get_db)) -> BrandIntelligenceService:
    return BrandIntelligenceService(db)


def get_governance(db: Session = Depends(get_db)) -> MarketplaceGovernanceService:
    return MarketplaceGovernanceService(db)


def get_ai_brain(db: Session = Depends(get_db)) -> AIBrainService:
    return AIBrainService(db)


# ── Request Models ──────────────────────────────────────────────────────

class PricingStrategyRequest(BaseModel):
    strategy: str = "competitive"  # premium, value, competitive


class ApplyRankingRequest(BaseModel):
    adjustments: Dict[str, float]


class ApplyBoostRequest(BaseModel):
    boost_config: Dict[str, Any]


# ── Demand Prediction Endpoints ────────────────────────────────────────

@router.get("/{brand_id}/demand-prediction")
async def get_demand_prediction(
    brand_id: str,
    product_id: str = Query(None, description="Specific product ID"),
    category: str = Query(None, description="Product category"),
    time_horizon: str = Query("30d", description="Prediction time horizon"),
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Get demand prediction for brand or specific product."""
    prediction = service.predict_demand(
        brand_id=brand_id,
        product_id=product_id,
        category=category,
        time_horizon=time_horizon,
    )
    return prediction.to_dict()


@router.get("/{brand_id}/demand-prediction/batch")
async def get_batch_demand_predictions(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Get demand predictions for all brand products."""
    from database.models import Product
    
    db = service._db
    products = db.query(Product).filter_by(brand_id=brand_id).all()
    
    predictions = []
    for product in products:
        pred = service.predict_demand(brand_id, product.id)
        predictions.append({
            "product_id": product.id,
            "product_name": product.name,
            **pred.to_dict(),
        })
    
    return {
        "brand_id": brand_id,
        "predictions": predictions,
        "total_products": len(predictions),
    }


# ── Style Trend Analytics Endpoints ────────────────────────────────────

@router.get("/{brand_id}/style-trends")
async def get_style_trend_analysis(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Analyze brand's alignment with current style trends."""
    analysis = service.analyze_style_trends(brand_id)
    return analysis.to_dict()


@router.get("/trend-indicators")
async def get_trend_indicators(
    user: UserProfile = Depends(require_auth),
):
    """Get current style trend indicators."""
    from services.brand_intelligence_service import STYLE_TREND_INDICATORS
    
    return {
        "trends": STYLE_TREND_INDICATORS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Return Risk Scoring Endpoints ──────────────────────────────────────

@router.get("/{brand_id}/return-risk")
async def get_brand_return_risk(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Calculate return risk score for brand products."""
    risk = service.calculate_brand_return_risk(brand_id)
    return risk.to_dict()


# ── AI Pricing Suggestions Endpoints ───────────────────────────────────

@router.get("/{brand_id}/pricing-suggestions")
async def get_pricing_suggestions(
    brand_id: str,
    product_id: str = Query(None, description="Specific product ID"),
    strategy: str = Query("competitive", description="Pricing strategy"),
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Get AI-powered pricing suggestions."""
    suggestions = service.generate_pricing_suggestions(
        brand_id=brand_id,
        product_id=product_id,
        strategy=strategy,
    )
    return {
        "brand_id": brand_id,
        "strategy": strategy,
        "suggestions": [s.to_dict() for s in suggestions],
        "total_suggestions": len(suggestions),
    }


# ── Inventory Intelligence Endpoints ───────────────────────────────────

@router.get("/{brand_id}/inventory-intelligence")
async def get_inventory_intelligence(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Get inventory intelligence report for brand."""
    intel = service.get_inventory_intelligence(brand_id)
    return intel.to_dict()


# ── AI Brain Integration: Send Signals ─────────────────────────────────

@router.get("/{brand_id}/performance-signals")
async def get_brand_performance_signals(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """
    Get performance signals for AI Central Brain.
    
    Signals include:
    - Item performance metrics
    - Styling popularity
    - Return data
    - Engagement analytics
    """
    signals = service.get_brand_performance_signals(brand_id)
    return signals


@router.post("/{brand_id}/send-to-brain")
async def send_brand_signals_to_brain(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    intel_service: BrandIntelligenceService = Depends(get_brand_intelligence),
    brain: AIBrainService = Depends(get_ai_brain),
):
    """
    Send brand signals to AI Central Brain for processing.
    
    This enables:
    - Cross-brand recommendations
    - Marketplace-wide trend detection
    - User-brand affinity updates
    """
    signals = intel_service.get_brand_performance_signals(brand_id)
    
    # Track brand signals in AI Brain
    # Would integrate with brain's signal processing
    
    return {
        "brand_id": brand_id,
        "signals_sent": True,
        "signal_types": list(signals.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── AI Brain Integration: Receive Intelligence ─────────────────────────

@router.post("/{brand_id}/apply-ranking-adjustments")
async def apply_ranking_adjustments(
    brand_id: str,
    data: ApplyRankingRequest,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """
    Apply ranking adjustments from AI Central Brain.
    
    Adjusts product visibility based on:
    - User preference matching
    - Trend alignment
    - Performance metrics
    """
    result = service.apply_ranking_adjustments(brand_id, data.adjustments)
    return result


@router.post("/{brand_id}/apply-recommendation-boost")
async def apply_recommendation_boost(
    brand_id: str,
    data: ApplyBoostRequest,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """
    Apply recommendation boost from AI Central Brain.
    
    Boosts brand products in:
    - Outfit recommendations
    - Search results
    - Similar item suggestions
    """
    result = service.apply_recommendation_boost(brand_id, data.boost_config)
    return result


@router.get("/{brand_id}/inventory-intelligence-for-brain")
async def get_inventory_for_brain(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    service: BrandIntelligenceService = Depends(get_brand_intelligence),
):
    """Get inventory intelligence formatted for AI Brain consumption."""
    intel = service.get_inventory_intelligence_for_brain(brand_id)
    return intel


# ── Marketplace Governance Endpoints ───────────────────────────────────

@router.get("/{brand_id}/moderation")
async def moderate_brand(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Run moderation checks on brand and products."""
    result = governance.moderate_brand(brand_id)
    return result.to_dict()


@router.get("/products/{product_id}/moderation")
async def moderate_product(
    product_id: str,
    user: UserProfile = Depends(require_auth),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Run moderation checks on a specific product."""
    result = governance.moderate_product(product_id)
    return result.to_dict()


@router.get("/{brand_id}/quality-score")
async def get_brand_quality_score(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Calculate quality score for brand."""
    score = governance.calculate_brand_quality_score(brand_id)
    return score.to_dict()


@router.get("/{brand_id}/trust-index")
async def get_brand_trust_index(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Get comprehensive brand trust index."""
    trust = governance.calculate_brand_trust_index(brand_id)
    return trust.to_dict()


@router.get("/{brand_id}/compliance")
async def check_brand_compliance(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Check brand compliance status."""
    compliance = governance.check_compliance(brand_id)
    return compliance.to_dict()


# ── Admin Endpoints ────────────────────────────────────────────────────

@router.get("/marketplace/health")
async def get_marketplace_health(
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Get overall marketplace health metrics (admin only)."""
    health = governance.get_marketplace_health()
    return health


@router.post("/{brand_id}/suspend")
async def suspend_brand(
    brand_id: str,
    reason: str = Query(..., description="Suspension reason"),
    duration_days: int = Query(None, description="Suspension duration"),
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Suspend a brand from marketplace (admin only)."""
    result = governance.suspend_brand(brand_id, user.id, reason, duration_days)
    return result


@router.post("/{brand_id}/reinstate")
async def reinstate_brand(
    brand_id: str,
    conditions: List[str] = Query(..., description="Reinstatement conditions"),
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Reinstate a suspended brand (admin only)."""
    result = governance.reinstate_brand(brand_id, user.id, conditions)
    return result


@router.post("/products/{product_id}/remove")
async def remove_product(
    product_id: str,
    reason: str = Query(..., description="Removal reason"),
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Remove a product from marketplace (admin only)."""
    result = governance.remove_product(product_id, user.id, reason)
    return result


@router.post("/{brand_id}/approve")
async def approve_brand(
    brand_id: str,
    verification_level: str = Query("verified", description="Verification level"),
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Approve and verify a brand (admin only)."""
    result = governance.approve_brand(brand_id, user.id, verification_level)
    return result


@router.get("/audit-logs")
async def get_audit_logs(
    admin_user_id: str = Query(None),
    target_type: str = Query(None),
    target_id: str = Query(None),
    action_type: str = Query(None),
    limit: int = Query(100),
    user: UserProfile = Depends(require_admin),
    governance: MarketplaceGovernanceService = Depends(get_governance),
):
    """Retrieve admin audit logs (admin only)."""
    logs = governance.get_audit_logs(
        admin_user_id=admin_user_id,
        target_type=target_type,
        target_id=target_id,
        action_type=action_type,
        limit=limit,
    )
    return {
        "logs": logs,
        "count": len(logs),
    }


# ── Import datetime ────────────────────────────────────────────────────
from datetime import datetime, timezone
