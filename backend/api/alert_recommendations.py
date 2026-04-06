"""
CONFIT Backend — Alert Recommendations API
==========================================
FastAPI routes for the Predictive Alert Recommendations Engine.
Provides endpoints for generating, retrieving, and managing recommendations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import Store
from database.sales_alert_models import SalesAlertPreferences
from database.alert_recommendation_models import (
    AlertRecommendation,
    StorePatternAnalysis,
    RecommendationType,
    RecommendationStatus,
    ConfidenceLevel,
    ImpactEstimate,
)
from services.predictive_recommendation_engine import PredictiveRecommendationEngine
from services.recommendation_backtester import RecommendationBacktester
from services.ab_testing_service import ABTestingService
from schemas.alert_recommendation_schemas import (
    AlertRecommendation as AlertRecommendationSchema,
    GenerateRecommendationsRequest,
    GenerateRecommendationsResponse,
    ApplyRecommendationRequest,
    ApplyRecommendationResponse,
    DismissRecommendationRequest,
    RecommendationFeedbackRequest,
    RecommendationListRequest,
    RecommendationListResponse,
    StorePatternAnalysis as StorePatternAnalysisSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alert-recommendations", tags=["Alert Recommendations"])


# ─── Helper Functions ───────────────────────────────────────────────────────────

def _get_store_id(db: Session, store_id: str) -> str:
    """Validate store exists and return ID."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return str(store.id)


def _recommendation_to_schema(rec: AlertRecommendation) -> Dict[str, Any]:
    """Convert ORM model to schema dict."""
    return {
        "id": str(rec.id),
        "store_id": str(rec.store_id),
        "type": rec.type.value if rec.type else None,
        "status": rec.status.value if rec.status else None,
        "title": rec.title,
        "description": rec.description,
        "thresholds": rec.thresholds or [],
        "confidence": rec.confidence.value if rec.confidence else "medium",
        "confidence_score": rec.confidence_score,
        "impact_estimate": rec.impact_estimate.value if rec.impact_estimate else "medium",
        "explanation": rec.explanation or {},
        "backtest_summary": rec.backtest_summary,
        "backtest_events": rec.backtest_events or [],
        "data_window_days": rec.data_window_days,
        "generated_at": rec.generated_at.isoformat() if rec.generated_at else None,
        "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
        "shown_at": rec.shown_at.isoformat() if rec.shown_at else None,
        "accepted_at": rec.accepted_at.isoformat() if rec.accepted_at else None,
        "dismissed_at": rec.dismissed_at.isoformat() if rec.dismissed_at else None,
        "applied_at": rec.applied_at.isoformat() if rec.applied_at else None,
        "user_feedback": rec.user_feedback,
        "rank_score": rec.rank_score,
    }


# ─── Recommendation Generation ─────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateRecommendationsResponse)
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate personalized alert recommendations for a store.
    Analyzes 60-90 days of historical data to suggest optimal thresholds.
    """
    store_id = _get_store_id(db, request.store_id)
    
    # Check for cached recommendations (unless force refresh)
    if not request.force_refresh:
        cached = db.query(AlertRecommendation).filter(
            AlertRecommendation.store_id == store_id,
            AlertRecommendation.status == RecommendationStatus.PENDING,
            AlertRecommendation.generated_at >= datetime.now(timezone.utc) - timedelta(hours=24),
        ).all()
        
        if cached:
            logger.info(f"Returning cached recommendations for store {store_id}")
            return GenerateRecommendationsResponse(
                store_id=store_id,
                recommendations=[_recommendation_to_schema(r) for r in cached],
                pattern_analysis={},
                generated_at=cached[0].generated_at.isoformat(),
                cache_hit=True,
            )
    
    # Get current preferences
    preferences = db.query(SalesAlertPreferences).filter(
        SalesAlertPreferences.store_id == store_id
    ).first()
    
    current_thresholds = {}
    if preferences:
        current_thresholds = preferences.thresholds or {}
    
    # Generate recommendations
    engine = PredictiveRecommendationEngine(db)
    recommendations = engine.generate_recommendations(
        store_id=store_id,
        current_preferences=current_thresholds,
        data_window_days=request.data_window_days,
    )
    
    # Run backtesting for each recommendation
    backtester = RecommendationBacktester(db)
    
    for rec in recommendations:
        backtest_summary = backtester.backtest_recommendation(
            rec, store_id, request.data_window_days
        )
        rec["backtest_summary"] = backtest_summary.model_dump()
        
        # Generate display-friendly backtest results
        display = backtester.generate_backtest_display(
            backtest_summary,
            [],  # Events are stored separately
        )
        rec["backtest_display"] = display
    
    # Persist recommendations
    persisted = []
    for rec_data in recommendations:
        rec = AlertRecommendation(
            store_id=store_id,
            type=RecommendationType(rec_data["type"]),
            status=RecommendationStatus.PENDING,
            title=rec_data["title"],
            description=rec_data.get("description"),
            thresholds=rec_data.get("thresholds", []),
            confidence=ConfidenceLevel(rec_data.get("confidence", "medium")),
            confidence_score=rec_data.get("confidence_score", 0.5),
            impact_estimate=ImpactEstimate(rec_data.get("impact_estimate", "medium")),
            explanation=rec_data.get("explanation", {}),
            backtest_summary=rec_data.get("backtest_summary"),
            backtest_events=rec_data.get("backtest_events", []),
            data_window_days=request.data_window_days,
            rank_score=rec_data.get("rank_score", 0),
        )
        db.add(rec)
        persisted.append(rec)
    
    # Store pattern analysis
    patterns = engine.analyze_store_patterns(store_id, request.data_window_days)
    
    pattern_analysis = db.query(StorePatternAnalysis).filter(
        StorePatternAnalysis.store_id == store_id
    ).first()
    
    if pattern_analysis:
        pattern_analysis.return_patterns = patterns.get("return_patterns")
        pattern_analysis.aov_patterns = patterns.get("aov_patterns")
        pattern_analysis.conversion_patterns = patterns.get("conversion_patterns")
        pattern_analysis.inventory_patterns = patterns.get("inventory_patterns")
        pattern_analysis.seasonal_patterns = patterns.get("seasonal_patterns")
        pattern_analysis.customer_segment_patterns = patterns.get("customer_segment_patterns")
        pattern_analysis.data_quality_score = patterns.get("data_quality_score", 0)
        pattern_analysis.has_sufficient_data = patterns.get("has_sufficient_data", False)
        pattern_analysis.analysis_date = datetime.now(timezone.utc)
    else:
        pattern_analysis = StorePatternAnalysis(
            store_id=store_id,
            return_patterns=patterns.get("return_patterns"),
            aov_patterns=patterns.get("aov_patterns"),
            conversion_patterns=patterns.get("conversion_patterns"),
            inventory_patterns=patterns.get("inventory_patterns"),
            seasonal_patterns=patterns.get("seasonal_patterns"),
            customer_segment_patterns=patterns.get("customer_segment_patterns"),
            data_quality_score=patterns.get("data_quality_score", 0),
            has_sufficient_data=patterns.get("has_sufficient_data", False),
            data_window_days=request.data_window_days,
        )
        db.add(pattern_analysis)
    
    db.commit()
    
    # Refresh to get IDs
    for rec in persisted:
        db.refresh(rec)
    
    logger.info(f"Generated {len(persisted)} recommendations for store {store_id}")
    
    return GenerateRecommendationsResponse(
        store_id=store_id,
        recommendations=[_recommendation_to_schema(r) for r in persisted],
        pattern_analysis=patterns,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cache_hit=False,
    )


# ─── Recommendation Retrieval ──────────────────────────────────────────────────

@router.get("/{store_id}", response_model=RecommendationListResponse)
async def get_recommendations(
    store_id: str,
    status: Optional[List[str]] = Query(None),
    types: Optional[List[str]] = Query(None),
    min_confidence: Optional[str] = Query(None),
    include_dismissed: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Retrieve recommendations for a store.
    Supports filtering by status, type, and confidence.
    """
    store_id = _get_store_id(db, store_id)
    
    query = db.query(AlertRecommendation).filter(
        AlertRecommendation.store_id == store_id,
    )
    
    # Apply filters
    if status:
        status_enums = [RecommendationStatus(s) for s in status if s in [e.value for e in RecommendationStatus]]
        query = query.filter(AlertRecommendation.status.in_(status_enums))
    
    if types:
        type_enums = [RecommendationType(t) for t in types if t in [e.value for e in RecommendationType]]
        query = query.filter(AlertRecommendation.type.in_(type_enums))
    
    if min_confidence:
        confidence_order = {"low": 0, "medium": 1, "high": 2}
        min_level = confidence_order.get(min_confidence, 0)
        valid_levels = [c for c, v in confidence_order.items() if v >= min_level]
        query = query.filter(AlertRecommendation.confidence.in_([ConfidenceLevel(c) for c in valid_levels]))
    
    if not include_dismissed:
        query = query.filter(AlertRecommendation.status != RecommendationStatus.DISMISSED)
    
    # Count total
    total_count = query.count()
    
    # Paginate
    offset = (page - 1) * limit
    recommendations = query.order_by(
        AlertRecommendation.rank_score.desc(),
        AlertRecommendation.generated_at.desc()
    ).offset(offset).limit(limit).all()
    
    return RecommendationListResponse(
        recommendations=[_recommendation_to_schema(r) for r in recommendations],
        total_count=total_count,
        page=page,
        limit=limit,
        has_more=(offset + limit) < total_count,
    )


@router.get("/single/{recommendation_id}")
async def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
):
    """Get a single recommendation by ID."""
    rec = db.query(AlertRecommendation).filter(
        AlertRecommendation.id == recommendation_id
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return _recommendation_to_schema(rec)


# ─── Recommendation Actions ────────────────────────────────────────────────────

@router.post("/apply", response_model=ApplyRecommendationResponse)
async def apply_recommendation(
    request: ApplyRecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Apply a recommendation to the store's alert preferences.
    Updates the actual threshold values.
    """
    rec = db.query(AlertRecommendation).filter(
        AlertRecommendation.id == request.recommendation_id,
        AlertRecommendation.store_id == request.store_id,
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if rec.status == RecommendationStatus.DISMISSED:
        raise HTTPException(status_code=400, detail="Cannot apply dismissed recommendation")
    
    # Get current preferences
    preferences = db.query(SalesAlertPreferences).filter(
        SalesAlertPreferences.store_id == request.store_id
    ).first()
    
    if not preferences:
        raise HTTPException(status_code=404, detail="Store preferences not found")
    
    # Apply thresholds
    applied_thresholds = {}
    thresholds_to_apply = request.custom_thresholds or {}
    
    for threshold in rec.thresholds:
        param_name = threshold.get("parameter_name")
        recommended_value = threshold.get("recommended_value")
        
        # Use custom value if provided, otherwise use recommended
        value_to_apply = thresholds_to_apply.get(param_name, recommended_value)
        applied_thresholds[param_name] = value_to_apply
    
    # Update preferences
    current_thresholds = preferences.thresholds or {}
    updated_thresholds = {**current_thresholds, **applied_thresholds}
    preferences.thresholds = updated_thresholds
    preferences.updated_at = datetime.now(timezone.utc)
    
    # Update recommendation status
    rec.status = RecommendationStatus.APPLIED
    rec.applied_at = datetime.now(timezone.utc)
    
    # Track A/B test event
    ab_service = ABTestingService(db)
    experiment = ab_service.get_active_experiment()
    if experiment:
        ab_service.track_recommendation_accepted(
            str(experiment.id),
            request.store_id,
            str(rec.id),
        )
    
    db.commit()
    
    logger.info(f"Applied recommendation {request.recommendation_id} to store {request.store_id}")
    
    return ApplyRecommendationResponse(
        success=True,
        recommendation_id=str(rec.id),
        applied_thresholds=applied_thresholds,
        updated_preferences=updated_thresholds,
    )


@router.post("/dismiss")
async def dismiss_recommendation(
    request: DismissRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Dismiss a recommendation without applying it."""
    rec = db.query(AlertRecommendation).filter(
        AlertRecommendation.id == request.recommendation_id,
        AlertRecommendation.store_id == request.store_id,
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    rec.status = RecommendationStatus.DISMISSED
    rec.dismissed_at = datetime.now(timezone.utc)
    rec.user_feedback = request.reason
    
    # Track A/B test event
    ab_service = ABTestingService(db)
    experiment = ab_service.get_active_experiment()
    if experiment:
        ab_service.track_recommendation_dismissed(
            str(experiment.id),
            request.store_id,
            str(rec.id),
        )
    
    db.commit()
    
    logger.info(f"Dismissed recommendation {request.recommendation_id}")
    
    return {"success": True, "recommendation_id": str(rec.id)}


@router.post("/feedback")
async def submit_feedback(
    request: RecommendationFeedbackRequest,
    db: Session = Depends(get_db),
):
    """Submit user feedback on a recommendation."""
    rec = db.query(AlertRecommendation).filter(
        AlertRecommendation.id == request.recommendation_id,
        AlertRecommendation.store_id == request.store_id,
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    rec.user_rating = request.rating
    rec.user_feedback = request.feedback_text
    rec.was_valuable = request.was_valuable
    
    db.commit()
    
    return {"success": True, "recommendation_id": str(rec.id)}


@router.post("/shown/{recommendation_id}")
async def mark_recommendation_shown(
    recommendation_id: str,
    store_id: str,
    db: Session = Depends(get_db),
):
    """Mark a recommendation as shown to the user."""
    rec = db.query(AlertRecommendation).filter(
        AlertRecommendation.id == recommendation_id,
        AlertRecommendation.store_id == store_id,
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if rec.status == RecommendationStatus.PENDING:
        rec.status = RecommendationStatus.SHOWN
        rec.shown_at = datetime.now(timezone.utc)
        
        # Track A/B test event
        ab_service = ABTestingService(db)
        experiment = ab_service.get_active_experiment()
        if experiment:
            ab_service.track_recommendation_shown(
                str(experiment.id),
                store_id,
                str(rec.id),
            )
        
        db.commit()
    
    return {"success": True}


# ─── Pattern Analysis ──────────────────────────────────────────────────────────

@router.get("/patterns/{store_id}")
async def get_pattern_analysis(
    store_id: str,
    db: Session = Depends(get_db),
):
    """Get the cached pattern analysis for a store."""
    store_id = _get_store_id(db, store_id)
    
    analysis = db.query(StorePatternAnalysis).filter(
        StorePatternAnalysis.store_id == store_id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Pattern analysis not found")
    
    return analysis.to_dict()


# ─── A/B Test Management ───────────────────────────────────────────────────────

@router.get("/ab-test/experiment")
async def get_active_experiment(
    db: Session = Depends(get_db),
):
    """Get the currently active A/B test experiment."""
    ab_service = ABTestingService(db)
    experiment = ab_service.get_active_experiment()
    
    if not experiment:
        return {"active": False, "experiment": None}
    
    return {
        "active": True,
        "experiment": experiment.to_dict(),
    }


@router.get("/ab-test/assignment/{store_id}")
async def get_store_ab_assignment(
    store_id: str,
    db: Session = Depends(get_db),
):
    """Get a store's A/B test group assignment."""
    store_id = _get_store_id(db, store_id)
    
    ab_service = ABTestingService(db)
    assignment = ab_service.get_store_assignment(store_id)
    
    if not assignment:
        # Auto-assign if experiment is active
        experiment = ab_service.get_active_experiment()
        if experiment:
            assignment = ab_service.assign_store_to_group(
                str(experiment.id),
                store_id,
            )
    
    if not assignment:
        return {"assigned": False, "group": "control"}
    
    return {
        "assigned": True,
        "group": assignment.group.value,
        "experiment_id": str(assignment.experiment_id),
    }


@router.get("/ab-test/report/{experiment_id}")
async def get_experiment_report(
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """Get a comprehensive report for an experiment."""
    ab_service = ABTestingService(db)
    report = ab_service.get_experiment_report(experiment_id)
    return report


@router.get("/ab-test/summary")
async def get_experiments_summary(
    db: Session = Depends(get_db),
):
    """Get summary of all A/B test experiments."""
    ab_service = ABTestingService(db)
    summary = ab_service.get_all_experiments_summary()
    return summary


# ─── Admin Endpoints ───────────────────────────────────────────────────────────

@router.post("/admin/create-experiment")
async def create_experiment(
    name: str,
    description: str,
    control_group_size: int = 50,
    treatment_group_size: int = 50,
    min_duration_days: int = 30,
    db: Session = Depends(get_db),
):
    """Create a new A/B test experiment (admin only)."""
    ab_service = ABTestingService(db)
    experiment = ab_service.create_experiment(
        name=name,
        description=description,
        control_group_size=control_group_size,
        treatment_group_size=treatment_group_size,
        min_duration_days=min_duration_days,
    )
    return experiment.to_dict()


@router.post("/admin/end-experiment/{experiment_id}")
async def end_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """End an A/B test experiment (admin only)."""
    ab_service = ABTestingService(db)
    experiment = ab_service.end_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return experiment.to_dict()


@router.delete("/admin/clear-cache/{store_id}")
async def clear_recommendation_cache(
    store_id: str,
    db: Session = Depends(get_db),
):
    """Clear cached recommendations for a store (admin only)."""
    store_id = _get_store_id(db, store_id)
    
    deleted = db.query(AlertRecommendation).filter(
        AlertRecommendation.store_id == store_id,
        AlertRecommendation.status == RecommendationStatus.PENDING,
    ).delete()
    
    db.commit()
    
    return {"success": True, "deleted_count": deleted}
