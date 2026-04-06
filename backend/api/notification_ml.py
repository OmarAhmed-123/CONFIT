"""
CONFIT — Notification ML API Endpoints
=====================================
FastAPI endpoints for the notification ML optimization system.
Provides APIs for predictions, persona management, and accuracy tracking.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from services.notification_ml import (
    NotificationMLPipeline,
    PipelineConfig,
)
from services.notification_ml.feature_engineering import compute_features_from_events, RecipientFeatures
from services.notification_ml.delivery_predictor import compute_optimal_hour_from_events
from api.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["notification-ml"])

# Global pipeline instance (initialized on startup)
_pipeline: Optional[NotificationMLPipeline] = None


def get_pipeline() -> NotificationMLPipeline:
    """Get or create the ML pipeline instance."""
    global _pipeline
    if _pipeline is None:
        # Would be initialized with actual DB connection
        _pipeline = NotificationMLPipeline(config=PipelineConfig())
    return _pipeline


async def _fetch_events_for_recipient(
    db: AsyncSession,
    recipient_id: str,
    recipient_type: str,
    window_days: int,
) -> List[Dict[str, Any]]:
    """Fetch recent notification events for one recipient."""
    start_date = datetime.utcnow() - timedelta(days=window_days)
    result = await db.execute(
        text(
            """
            SELECT id, notification_id, channel, event_type, event_timestamp,
                   payload, time_spent_ms, scroll_depth, action_taken
            FROM notification_events
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
              AND event_timestamp >= :start_date
            ORDER BY event_timestamp ASC
            """
        ),
        {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type,
            "start_date": start_date,
        },
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def _fetch_training_features_and_labels(
    db: AsyncSession,
    recipient_type: Optional[str],
    window_days: int,
    min_events: int,
) -> tuple[List[RecipientFeatures], List[Dict[str, Any]]]:
    """Build training features + optimal-hour labels from event logs."""
    start_date = datetime.utcnow() - timedelta(days=window_days)
    recipients_result = await db.execute(
        text(
            """
            SELECT recipient_id, recipient_type, COUNT(*) AS event_count
            FROM notification_events
            WHERE event_timestamp >= :start_date
              AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
            GROUP BY recipient_id, recipient_type
            HAVING COUNT(*) >= :min_events
            """
        ),
        {
            "start_date": start_date,
            "recipient_type": recipient_type,
            "min_events": min_events,
        },
    )
    recipients = [dict(row._mapping) for row in recipients_result.fetchall()]

    features_list: List[RecipientFeatures] = []
    engagement_records: List[Dict[str, Any]] = []
    for rec in recipients:
        rid = rec["recipient_id"]
        rtype = rec["recipient_type"]
        events = await _fetch_events_for_recipient(db, rid, rtype, window_days)
        if not events:
            continue
        features = compute_features_from_events(events=events, recipient_id=rid, recipient_type=rtype)
        optimal_hour = compute_optimal_hour_from_events(events=events, recipient_id=rid)
        if optimal_hour is None:
            continue
        features_list.append(features)
        engagement_records.append(
            {
                "recipient_id": rid,
                "optimal_hour": optimal_hour,
                "event_timestamp": events[-1].get("event_timestamp"),
            }
        )
    return features_list, engagement_records


# ─── Request/Response Models ─────────────────────────────────────────────

class PredictionRequest(BaseModel):
    """Request for delivery time prediction."""
    recipient_id: str
    recipient_type: str = Field(..., pattern="^(customer|owner)$")
    notification_type: Optional[str] = None
    channel: Optional[str] = Field(None, pattern="^(in_app|email|push|toast)$")


class PredictionResponse(BaseModel):
    """Response with delivery time prediction."""
    recipient_id: str
    recipient_type: str
    persona_id: Optional[str]
    recommended_hour: int
    confidence_score: float
    recommended_hours: List[Dict[str, Any]]
    explanation: Dict[str, Any]
    model_version: str
    expires_at: str


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""
    recipient_ids: List[str]
    recipient_type: str = Field(..., pattern="^(customer|owner)$")


class BatchPredictionResponse(BaseModel):
    """Response with batch predictions."""
    predictions: List[PredictionResponse]
    total: int
    model_version: str


class PersonaResponse(BaseModel):
    """Response with persona details."""
    id: str
    name: str
    description: str
    recipient_type: str
    characteristics: Dict[str, Any]
    recipient_count: int
    avg_open_rate: float
    avg_click_rate: float
    avg_conversion_rate: Optional[float]
    avg_response_time_min: Optional[float]


class TrainRequest(BaseModel):
    """Request to train the model."""
    recipient_type: Optional[str] = Field(None, pattern="^(customer|owner)$")
    n_personas: Optional[int] = Field(None, ge=3, le=10)
    model_type: Optional[str] = Field(None, pattern="^(gradient_boosting|random_forest|decision_tree)$")


class TrainResponse(BaseModel):
    """Response from training."""
    model_version: str
    personas: List[PersonaResponse]
    metrics: Dict[str, Any]
    completed_at: str


class AccuracyReportResponse(BaseModel):
    """Response with accuracy report."""
    overall: Dict[str, Any]
    daily: List[Dict[str, Any]]
    trends: Dict[str, Any]
    personas: Dict[str, Dict[str, Any]]


class DriftCheckResponse(BaseModel):
    """Response from drift check."""
    has_drift: bool
    alerts: List[Dict[str, Any]]
    recommendation: Optional[str]


class RecipientFeaturesResponse(BaseModel):
    """Response with recipient features."""
    recipient_id: str
    recipient_type: str
    hourly_open_rates: List[float]
    daily_open_rates: List[float]
    overall_open_rate: float
    peak_hour: Optional[int]
    peak_day: Optional[int]
    consistency_score: float


# ─── Prediction Endpoints ────────────────────────────────────────────────

@router.post("/predict", response_model=PredictionResponse)
async def predict_delivery_time(
    request: PredictionRequest,
    pipeline: NotificationMLPipeline = Depends(get_pipeline),
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    """
    Predict optimal delivery time for a single recipient.
    
    Returns the recommended hour for notification delivery along with
    confidence score and explanation.
    """
    if not pipeline.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Model not trained. Please train the model first."
        )
    
    try:
        recipient_events = await _fetch_events_for_recipient(
            db=db,
            recipient_id=request.recipient_id,
            recipient_type=request.recipient_type,
            window_days=pipeline.config.feature_window_days,
        )
        features = compute_features_from_events(
            events=recipient_events,
            recipient_id=request.recipient_id,
            recipient_type=request.recipient_type,
        )

        prediction, explanation = pipeline.predict(
            recipient_id=request.recipient_id,
            recipient_type=request.recipient_type,
            notification_type=request.notification_type,
            channel=request.channel,
            features=features,
        )
        
        return PredictionResponse(
            recipient_id=prediction.recipient_id,
            recipient_type=prediction.recipient_type,
            persona_id=prediction.persona_id,
            recommended_hour=prediction.recommended_hour,
            confidence_score=prediction.confidence_score,
            recommended_hours=prediction.recommended_hours,
            explanation=explanation.to_dict(),
            model_version=prediction.model_version,
            expires_at=prediction.expires_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_delivery_times_batch(
    request: BatchPredictionRequest,
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> BatchPredictionResponse:
    """
    Predict optimal delivery times for multiple recipients.
    
    Efficiently processes multiple recipients in a single request.
    """
    if not pipeline.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Model not trained. Please train the model first."
        )
    
    try:
        results = pipeline.predict_batch(
            recipient_ids=request.recipient_ids,
            recipient_type=request.recipient_type
        )
        
        predictions = [
            PredictionResponse(
                recipient_id=pred.recipient_id,
                recipient_type=pred.recipient_type,
                persona_id=pred.persona_id,
                recommended_hour=pred.recommended_hour,
                confidence_score=pred.confidence_score,
                recommended_hours=pred.recommended_hours,
                explanation=expl.to_dict(),
                model_version=pred.model_version,
                expires_at=pred.expires_at.isoformat()
            )
            for pred, expl in results
        ]
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            model_version=pipeline.model_version or "unknown"
        )
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Training Endpoints ───────────────────────────────────────────────────

@router.post("/train", response_model=TrainResponse)
async def train_model(
    request: TrainRequest,
    pipeline: NotificationMLPipeline = Depends(get_pipeline),
    db: AsyncSession = Depends(get_db),
) -> TrainResponse:
    """
    Train the ML model.
    
    This endpoint triggers model training. For large datasets, training
    may run in the background.
    """
    try:
        # Update config if provided
        if request.n_personas:
            pipeline.config.n_personas = request.n_personas
        if request.model_type:
            pipeline.config.model_type = request.model_type
        
        features_list, engagement_records = await _fetch_training_features_and_labels(
            db=db,
            recipient_type=request.recipient_type,
            window_days=pipeline.config.feature_window_days,
            min_events=pipeline.config.min_events_per_recipient,
        )
        result = pipeline.train(
            recipient_type=request.recipient_type,
            engagement_records=engagement_records,
            features_list=features_list,
        )
        
        return TrainResponse(
            model_version=result.model_version,
            personas=[
                PersonaResponse(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    recipient_type=p.recipient_type,
                    characteristics=p.characteristics,
                    recipient_count=p.recipient_count,
                    avg_open_rate=p.avg_open_rate,
                    avg_click_rate=p.avg_click_rate,
                    avg_conversion_rate=p.avg_conversion_rate,
                    avg_response_time_min=p.avg_response_time_min
                )
                for p in result.personas
            ],
            metrics=result.metrics,
            completed_at=result.completed_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_model_status(
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> Dict[str, Any]:
    """
    Get current model status.
    
    Returns information about the loaded model and its version.
    """
    return {
        "is_trained": pipeline.is_trained,
        "model_version": pipeline.model_version,
        "n_personas": len(pipeline.personas) if pipeline.is_trained else 0,
        "config": pipeline.config.to_dict() if pipeline.config else None,
    }


# ─── Persona Endpoints ────────────────────────────────────────────────────

@router.get("/personas", response_model=List[PersonaResponse])
async def list_personas(
    recipient_type: Optional[str] = Query(None, pattern="^(customer|owner)$"),
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> List[PersonaResponse]:
    """
    List all personas.
    
    Optionally filter by recipient type.
    """
    if not pipeline.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Model not trained."
        )
    
    personas = pipeline.personas
    
    if recipient_type:
        personas = [p for p in personas if p.recipient_type == recipient_type]
    
    return [
        PersonaResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            recipient_type=p.recipient_type,
            characteristics=p.characteristics,
            recipient_count=p.recipient_count,
            avg_open_rate=p.avg_open_rate,
            avg_click_rate=p.avg_click_rate,
            avg_conversion_rate=p.avg_conversion_rate,
            avg_response_time_min=p.avg_response_time_min
        )
        for p in personas
    ]


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> PersonaResponse:
    """
    Get details of a specific persona.
    """
    if not pipeline.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Model not trained."
        )
    
    persona = pipeline.persona_clusterer.get_persona_by_id(persona_id)
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return PersonaResponse(
        id=persona.id,
        name=persona.name,
        description=persona.description,
        recipient_type=persona.recipient_type,
        characteristics=persona.characteristics,
        recipient_count=persona.recipient_count,
        avg_open_rate=persona.avg_open_rate,
        avg_click_rate=persona.avg_click_rate,
        avg_conversion_rate=persona.avg_conversion_rate,
        avg_response_time_min=persona.avg_response_time_min
    )


# ─── Accuracy & Monitoring Endpoints ──────────────────────────────────────

@router.get("/accuracy", response_model=AccuracyReportResponse)
async def get_accuracy_report(
    days: int = Query(30, ge=1, le=90),
    persona_id: Optional[str] = None,
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> AccuracyReportResponse:
    """
    Get accuracy report for the model.
    
    Returns metrics comparing ML-optimized delivery vs baseline timing.
    """
    report = pipeline.get_accuracy_report(days=days, persona_id=persona_id)
    
    return AccuracyReportResponse(
        overall=report["overall"],
        daily=report["daily"],
        trends=report["trends"],
        personas=report["personas"]
    )


@router.post("/drift/check", response_model=DriftCheckResponse)
async def check_model_drift(
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> DriftCheckResponse:
    """
    Check for model drift.
    
    Analyzes recent performance to detect degradation.
    """
    if not pipeline.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Model not trained."
        )
    
    result = pipeline.check_drift()
    
    return DriftCheckResponse(
        has_drift=result.has_drift,
        alerts=[a.to_dict() for a in result.alerts],
        recommendation=result.recommendation
    )


# ─── Feature Endpoints ────────────────────────────────────────────────────

@router.get("/features/{recipient_id}", response_model=RecipientFeaturesResponse)
async def get_recipient_features(
    recipient_id: str,
    recipient_type: str = Query(..., pattern="^(customer|owner)$"),
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> RecipientFeaturesResponse:
    """
    Get computed features for a recipient.
    
    Returns the engagement profile used for predictions.
    """
    try:
        features = pipeline.feature_engineer.compute_features(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            window_days=pipeline.config.feature_window_days
        )
        
        return RecipientFeaturesResponse(
            recipient_id=features.recipient_id,
            recipient_type=features.recipient_type,
            hourly_open_rates=features.hourly_open_rates,
            daily_open_rates=features.daily_open_rates,
            overall_open_rate=features.overall_open_rate,
            peak_hour=features.peak_hour,
            peak_day=features.peak_day,
            consistency_score=features.consistency_score
        )
    except Exception as e:
        logger.error(f"Feature computation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Model Management Endpoints ───────────────────────────────────────────

@router.post("/models/{model_version}/load")
async def load_model_version(
    model_version: str,
    pipeline: NotificationMLPipeline = Depends(get_pipeline)
) -> Dict[str, Any]:
    """
    Load a specific model version.
    
    Used to switch between trained model versions.
    """
    try:
        pipeline.load_models(model_version)
        return {
            "status": "loaded",
            "model_version": model_version,
            "n_personas": len(pipeline.personas)
        }
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_model_versions() -> Dict[str, Any]:
    """
    List available model versions.
    
    Returns all saved model versions that can be loaded.
    """
    import os
    
    model_dir = "models/notification_ml"
    
    if not os.path.exists(model_dir):
        return {"versions": []}
    
    versions = []
    for name in os.listdir(model_dir):
        path = os.path.join(model_dir, name)
        if os.path.isdir(path):
            config_path = os.path.join(path, "config.json")
            if os.path.exists(config_path):
                versions.append({
                    "version": name,
                    "path": path
                })
    
    return {"versions": versions}


# ─── Health Check ─────────────────────────────────────────────────────────

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "notification-ml"}
