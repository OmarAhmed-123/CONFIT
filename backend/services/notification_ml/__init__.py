"""
CONFIT — Notification ML Optimization Services
==============================================
ML pipeline for predictive notification delivery optimization.

Modules:
- feature_engineering: Extract engagement patterns from notification events
- persona_clustering: Segment recipients into behavioral personas
- delivery_predictor: Predict optimal delivery times
- explainability: Generate human-readable explanations
- accuracy_tracker: Monitor prediction accuracy
- drift_detector: Detect model drift and trigger retraining
"""

from .feature_engineering import FeatureEngineer, RecipientFeatures
from .persona_clustering import PersonaClusterer, PersonaDefinition
from .delivery_predictor import DeliveryPredictor, DeliveryPrediction, TrainingResult
from .explainability import Explainer, PredictionExplanation
from .accuracy_tracker import AccuracyTracker, AccuracyMetrics
from .drift_detector import DriftDetector, DriftCheckResult
from .pipeline import NotificationMLPipeline, PipelineConfig, PipelineResult

__all__ = [
    "FeatureEngineer",
    "RecipientFeatures",
    "PersonaClusterer",
    "PersonaDefinition",
    "DeliveryPredictor",
    "DeliveryPrediction",
    "TrainingResult",
    "Explainer",
    "PredictionExplanation",
    "AccuracyTracker",
    "AccuracyMetrics",
    "DriftDetector",
    "DriftCheckResult",
    "NotificationMLPipeline",
    "PipelineConfig",
    "PipelineResult",
]
