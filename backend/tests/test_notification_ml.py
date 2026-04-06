"""
CONFIT — Notification ML Pipeline Tests
======================================
Unit tests for the notification ML optimization system.
Tests feature engineering, persona clustering, prediction, and integration.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

# Import modules to test
from services.notification_ml.feature_engineering import (
    FeatureEngineer,
    RecipientFeatures,
    compute_features_from_events,
)
from services.notification_ml.persona_clustering import (
    PersonaClusterer,
    PersonaDefinition,
    ClusteringResult,
    PERSONA_NAME_TEMPLATES,
)
from services.notification_ml.delivery_predictor import (
    DeliveryPredictor,
    DeliveryPrediction,
    TrainingResult,
    compute_optimal_hour_from_events,
)
from services.notification_ml.explainability import (
    Explainer,
    PredictionExplanation,
    generate_explanation,
)
from services.notification_ml.accuracy_tracker import (
    AccuracyTracker,
    AccuracyMetrics,
    PredictionOutcome,
)
from services.notification_ml.drift_detector import (
    DriftDetector,
    DriftAlert,
    DriftCheckResult,
)
from services.notification_ml.pipeline import (
    NotificationMLPipeline,
    PipelineConfig,
    PipelineResult,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_events():
    """Sample notification events for testing."""
    now = datetime.utcnow()
    events = []
    
    # Generate events for 30 days
    for day in range(30):
        for hour in [9, 10, 11, 14, 15, 18, 19]:  # Typical engagement hours
            ts = now - timedelta(days=30 - day, hours=24 - hour)
            
            # Sent event
            events.append({
                "id": f"event_{day}_{hour}_sent",
                "notification_id": f"notif_{day}_{hour}",
                "event_type": "sent",
                "event_timestamp": ts,
                "channel": "in_app",
                "recipient_id": "user_123",
                "recipient_type": "customer",
            })
            
            # Read event (with some probability)
            if hour in [9, 10, 18]:  # Higher open rates at these hours
                events.append({
                    "id": f"event_{day}_{hour}_read",
                    "notification_id": f"notif_{day}_{hour}",
                    "event_type": "read",
                    "event_timestamp": ts + timedelta(minutes=5),
                    "channel": "in_app",
                    "recipient_id": "user_123",
                    "recipient_type": "customer",
                })
                
                # Click event (lower probability)
                if hour == 9:
                    events.append({
                        "id": f"event_{day}_{hour}_clicked",
                        "notification_id": f"notif_{day}_{hour}",
                        "event_type": "clicked",
                        "event_timestamp": ts + timedelta(minutes=10),
                        "channel": "in_app",
                        "recipient_id": "user_123",
                        "recipient_type": "customer",
                    })
    
    return events


@pytest.fixture
def sample_features():
    """Sample RecipientFeatures for testing."""
    return RecipientFeatures(
        recipient_id="user_123",
        recipient_type="customer",
        hourly_open_rates=[0.1, 0.05, 0.02, 0.01, 0.01, 0.02, 0.05, 0.15, 
                          0.45, 0.42, 0.35, 0.20, 0.15, 0.12, 0.18, 0.22,
                          0.20, 0.25, 0.38, 0.32, 0.15, 0.08, 0.05, 0.03],
        hourly_click_rates=[0.02, 0.01, 0.00, 0.00, 0.00, 0.01, 0.02, 0.08,
                           0.25, 0.22, 0.15, 0.08, 0.05, 0.04, 0.08, 0.10,
                           0.08, 0.12, 0.18, 0.15, 0.05, 0.02, 0.01, 0.01],
        hourly_event_counts=[10, 5, 2, 1, 1, 2, 5, 15, 45, 42, 35, 20, 
                            15, 12, 18, 22, 20, 25, 38, 32, 15, 8, 5, 3],
        daily_open_rates=[0.25, 0.28, 0.26, 0.24, 0.22, 0.15, 0.10],
        daily_click_rates=[0.12, 0.14, 0.11, 0.10, 0.09, 0.05, 0.03],
        total_notifications_sent=350,
        total_notifications_opened=100,
        total_notifications_clicked=40,
        overall_open_rate=0.286,
        overall_click_rate=0.114,
        consistency_score=0.75,
        recency_weighted_engagement=0.32,
        preferred_channel="in_app",
        peak_hour=8,
        peak_day=1,
        engagement_trend_30d=0.02,
        engagement_trend_60d=0.01,
        engagement_trend_90d=0.005,
        conversion_rate_30d=0.08,
        repeat_purchase_rate=0.25,
        account_tenure_days=180,
    )


@pytest.fixture
def sample_features_list(sample_features):
    """List of sample features for multiple recipients."""
    features_list = []
    
    # Create variations of the sample features
    for i in range(100):
        f = RecipientFeatures(
            recipient_id=f"user_{i}",
            recipient_type="customer" if i < 70 else "owner",
            hourly_open_rates=list(np.random.dirichlet(np.ones(24)) * 0.5),
            hourly_click_rates=list(np.random.dirichlet(np.ones(24)) * 0.2),
            hourly_event_counts=[int(np.random.exponential(20)) for _ in range(24)],
            daily_open_rates=list(np.random.dirichlet(np.ones(7)) * 0.4),
            daily_click_rates=list(np.random.dirichlet(np.ones(7)) * 0.15),
            total_notifications_sent=int(np.random.exponential(100)),
            overall_open_rate=np.random.beta(2, 5),
            overall_click_rate=np.random.beta(1, 8),
            consistency_score=np.random.beta(3, 2),
            peak_hour=np.random.randint(0, 24),
            peak_day=np.random.randint(0, 7),
            preferred_channel="in_app",
            engagement_trend_30d=np.random.normal(0, 0.01),
            conversion_rate_30d=np.random.beta(1, 10),
            repeat_purchase_rate=np.random.beta(1, 4),
            account_tenure_days=np.random.randint(30, 365),
        )
        f.total_notifications_opened = int(f.total_notifications_sent * f.overall_open_rate)
        f.total_notifications_clicked = int(f.total_notifications_sent * f.overall_click_rate)
        features_list.append(f)
    
    return features_list


@pytest.fixture
def sample_persona():
    """Sample persona definition."""
    return PersonaDefinition(
        id="persona_0",
        name="Early Morning Engagers",
        description="Recipients who engage most actively with notifications in the early morning hours",
        recipient_type="customer",
        characteristics={
            "peak_hour": 8,
            "peak_hours": [8, 9, 10],
            "avg_open_rate": 0.45,
            "consistency_score": 0.78,
            "engagement_pattern": "early_morning",
        },
        recipient_count=150,
        avg_open_rate=0.45,
        avg_click_rate=0.18,
        avg_conversion_rate=0.12,
        model_version="v20260406_test",
        cluster_id=0,
    )


# ─── Feature Engineering Tests ─────────────────────────────────────────────

class TestFeatureEngineering:
    """Tests for feature engineering module."""
    
    def test_compute_features_from_events(self, sample_events):
        """Test computing features from events."""
        features = compute_features_from_events(
            events=sample_events,
            recipient_id="user_123",
            recipient_type="customer"
        )
        
        assert features.recipient_id == "user_123"
        assert features.recipient_type == "customer"
        assert features.total_notifications_sent > 0
        assert len(features.hourly_open_rates) == 24
        assert len(features.daily_open_rates) == 7
        assert features.peak_hour is not None
    
    def test_hourly_profile_computation(self, sample_events):
        """Test that hourly profiles are computed correctly."""
        features = compute_features_from_events(
            events=sample_events,
            recipient_id="user_123",
            recipient_type="customer"
        )
        
        # Peak hours should be 9, 10, or 18 (where we added more read events)
        assert features.peak_hour in [8, 9, 10, 17, 18]
        
        # Hourly rates should be between 0 and 1
        for rate in features.hourly_open_rates:
            assert 0 <= rate <= 1
    
    def test_daily_profile_computation(self, sample_events):
        """Test that daily profiles are computed correctly."""
        features = compute_features_from_events(
            events=sample_events,
            recipient_id="user_123",
            recipient_type="customer"
        )
        
        assert len(features.daily_open_rates) == 7
        assert len(features.daily_click_rates) == 7
        assert 0 <= features.peak_day <= 6
    
    def test_aggregate_metrics(self, sample_events):
        """Test aggregate metric computation."""
        features = compute_features_from_events(
            events=sample_events,
            recipient_id="user_123",
            recipient_type="customer"
        )
        
        assert features.total_notifications_sent > 0
        assert features.total_notifications_opened >= 0
        assert features.total_notifications_clicked >= 0
        assert 0 <= features.overall_open_rate <= 1
        assert 0 <= features.overall_click_rate <= 1
    
    def test_behavioral_signals(self, sample_events):
        """Test behavioral signal computation."""
        features = compute_features_from_events(
            events=sample_events,
            recipient_id="user_123",
            recipient_type="customer"
        )
        
        assert 0 <= features.consistency_score <= 1
        assert 0 <= features.recency_weighted_engagement <= 1
        assert features.preferred_channel is not None
    
    def test_to_feature_vector(self, sample_features):
        """Test conversion to feature vector."""
        vector = sample_features.to_feature_vector()
        
        assert isinstance(vector, np.ndarray)
        assert vector.dtype == np.float32
        assert len(vector) > 0
        
        # All values should be finite
        assert np.all(np.isfinite(vector))
    
    def test_to_dict(self, sample_features):
        """Test conversion to dictionary."""
        d = sample_features.to_dict()
        
        assert d["recipient_id"] == "user_123"
        assert d["recipient_type"] == "customer"
        assert "hourly_open_rates" in d
        assert "peak_hour" in d


# ─── Persona Clustering Tests ──────────────────────────────────────────────

class TestPersonaClustering:
    """Tests for persona clustering module."""
    
    def test_clustering_fit_predict(self, sample_features_list):
        """Test clustering fit and predict."""
        clusterer = PersonaClusterer(n_personas=5, auto_select_k=False)
        
        result = clusterer.fit_predict(sample_features_list, auto_select_k=False)
        
        assert len(result.personas) > 0
        assert len(result.recipient_assignments) == len(sample_features_list)
        assert "silhouette_score" in result.metrics
        assert result.model_version is not None
    
    def test_persona_creation(self, sample_features_list):
        """Test that personas are created with proper attributes."""
        clusterer = PersonaClusterer(n_personas=5, auto_select_k=False)
        result = clusterer.fit_predict(sample_features_list, auto_select_k=False)
        
        for persona in result.personas:
            assert persona.id is not None
            assert persona.name is not None
            assert persona.description is not None
            assert persona.recipient_type in ["customer", "owner"]
            assert persona.recipient_count > 0
            assert 0 <= persona.avg_open_rate <= 1
    
    def test_recipient_assignments(self, sample_features_list):
        """Test that recipients are assigned to personas."""
        clusterer = PersonaClusterer(n_personas=5, auto_select_k=False)
        result = clusterer.fit_predict(sample_features_list, auto_select_k=False)
        
        for recipient_id, (persona_id, confidence) in result.recipient_assignments.items():
            assert persona_id in [p.id for p in result.personas]
            assert 0 <= confidence <= 1
    
    def test_auto_select_k(self, sample_features_list):
        """Test automatic selection of number of clusters."""
        clusterer = PersonaClusterer(min_personas=3, max_personas=8)
        result = clusterer.fit_predict(sample_features_list, auto_select_k=True)
        
        assert clusterer.n_personas >= clusterer.min_personas
        assert clusterer.n_personas <= clusterer.max_personas
    
    def test_predict_persona(self, sample_features_list, sample_features):
        """Test predicting persona for a single recipient."""
        clusterer = PersonaClusterer(n_personas=5, auto_select_k=False)
        clusterer.fit_predict(sample_features_list, auto_select_k=False)
        
        persona_id, confidence = clusterer.predict_persona(sample_features)
        
        assert persona_id is not None
        assert 0 <= confidence <= 1
    
    def test_save_load_model(self, sample_features_list):
        """Test saving and loading the model."""
        clusterer = PersonaClusterer(n_personas=5, auto_select_k=False)
        result = clusterer.fit_predict(sample_features_list, auto_select_k=False)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "persona_model.pkl")
            clusterer.save_model(path)
            
            # Load into new clusterer
            new_clusterer = PersonaClusterer()
            new_clusterer.load_model(path)
            
            assert new_clusterer.n_personas == clusterer.n_personas
            assert len(new_clusterer.personas) == len(clusterer.personas)


# ─── Delivery Predictor Tests ──────────────────────────────────────────────

class TestDeliveryPredictor:
    """Tests for delivery predictor module."""
    
    def test_model_training(self, sample_features_list):
        """Test model training."""
        predictor = DeliveryPredictor(model_type="decision_tree")
        
        # Create engagement records
        engagement_records = [
            {
                "recipient_id": f.recipient_id,
                "optimal_hour": f.peak_hour if f.peak_hour else 10,
                "event_timestamp": datetime.utcnow() - timedelta(days=np.random.randint(1, 60))
            }
            for f in sample_features_list
        ]
        
        result = predictor.train(sample_features_list, engagement_records)
        
        assert result.model_version is not None
        assert result.training_samples > 0
        assert result.validation_samples > 0
        assert "accuracy_top1" in result.metrics
    
    def test_prediction(self, sample_features_list, sample_features):
        """Test making a prediction."""
        predictor = DeliveryPredictor(model_type="decision_tree")
        
        engagement_records = [
            {
                "recipient_id": f.recipient_id,
                "optimal_hour": f.peak_hour if f.peak_hour else 10,
            }
            for f in sample_features_list
        ]
        
        predictor.train(sample_features_list, engagement_records)
        
        prediction = predictor.predict(sample_features, persona_id="persona_0")
        
        assert 0 <= prediction.recommended_hour <= 23
        assert 0 <= prediction.confidence_score <= 1
        assert len(prediction.recommended_hours) == 3
        assert prediction.model_version is not None
    
    def test_batch_prediction(self, sample_features_list):
        """Test batch predictions."""
        predictor = DeliveryPredictor(model_type="decision_tree")
        
        engagement_records = [
            {
                "recipient_id": f.recipient_id,
                "optimal_hour": f.peak_hour if f.peak_hour else 10,
            }
            for f in sample_features_list
        ]
        
        predictor.train(sample_features_list, engagement_records)
        
        predictions = predictor.predict_batch(sample_features_list[:10])
        
        assert len(predictions) == 10
        for pred in predictions:
            assert 0 <= pred.recommended_hour <= 23
    
    def test_compute_optimal_hour(self, sample_events):
        """Test computing optimal hour from events."""
        optimal = compute_optimal_hour_from_events(sample_events, "user_123")
        
        assert optimal is not None
        assert 0 <= optimal <= 23


# ─── Explainability Tests ──────────────────────────────────────────────────

class TestExplainability:
    """Tests for explainability module."""
    
    def test_explanation_generation(self, sample_features, sample_persona):
        """Test generating an explanation."""
        prediction = DeliveryPrediction(
            recipient_id="user_123",
            recipient_type="customer",
            persona_id="persona_0",
            recommended_hour=9,
            confidence_score=0.75,
            recommended_hours=[
                {"hour": 9, "score": 0.75},
                {"hour": 10, "score": 0.68},
                {"hour": 18, "score": 0.55}
            ],
            model_version="v20260406_test",
        )
        
        explainer = Explainer()
        explanation = explainer.explain_prediction(
            prediction=prediction,
            features=sample_features,
            persona=sample_persona
        )
        
        assert explanation.recipient_id == "user_123"
        assert explanation.recommended_hour == 9
        assert explanation.reason is not None
        assert len(explanation.reason) > 0
        assert explanation.confidence_score == 0.75
    
    def test_fallback_reasoning(self, sample_features):
        """Test fallback reasoning for low confidence."""
        prediction = DeliveryPrediction(
            recipient_id="user_123",
            recipient_type="customer",
            persona_id=None,
            recommended_hour=9,
            confidence_score=0.35,  # Low confidence
            recommended_hours=[{"hour": 9, "score": 0.35}],
            model_version="v20260406_test",
        )
        
        explainer = Explainer()
        explanation = explainer.explain_prediction(
            prediction=prediction,
            features=sample_features
        )
        
        assert explanation.fallback_reason is not None
        assert "low" in explanation.fallback_reason.lower() or "limited" in explanation.fallback_reason.lower()
    
    def test_time_period_classification(self):
        """Test time period classification."""
        explainer = Explainer()
        
        assert explainer._get_time_period(3) == "late night"
        assert explainer._get_time_period(8) == "early morning"
        assert explainer._get_time_period(10) == "morning"
        assert explainer._get_time_period(13) == "midday"
        assert explainer._get_time_period(15) == "afternoon"
        assert explainer._get_time_period(19) == "evening"
        assert explainer._get_time_period(22) == "night"
    
    def test_hour_formatting(self):
        """Test hour formatting."""
        explainer = Explainer()
        
        assert explainer._format_hour(0) == "12 AM"
        assert explainer._format_hour(9) == "9 AM"
        assert explainer._format_hour(12) == "12 PM"
        assert explainer._format_hour(15) == "3 PM"


# ─── Accuracy Tracker Tests ────────────────────────────────────────────────

class TestAccuracyTracker:
    """Tests for accuracy tracking module."""
    
    def test_record_outcome(self):
        """Test recording an outcome."""
        tracker = AccuracyTracker()
        
        outcome = tracker.record_outcome(
            prediction_id="pred_123",
            recipient_id="user_123",
            recipient_type="customer",
            persona_id="persona_0",
            predicted_hour=9,
            confidence_score=0.75,
            model_version="v20260406_test",
            sent_at=datetime.utcnow(),
            actual_hour=9,
            was_ml_timed=True,
            was_opened=True,
            was_clicked=False,
            was_converted=False
        )
        
        assert outcome.prediction_id == "pred_123"
        assert outcome.was_opened == True
        assert outcome.was_ml_timed == True
    
    def test_compute_metrics(self):
        """Test computing accuracy metrics."""
        tracker = AccuracyTracker()
        
        # Record multiple outcomes
        for i in range(20):
            tracker.record_outcome(
                prediction_id=f"pred_{i}",
                recipient_id=f"user_{i}",
                recipient_type="customer",
                persona_id="persona_0",
                predicted_hour=9,
                confidence_score=0.7,
                model_version="v20260406_test",
                sent_at=datetime.utcnow() - timedelta(hours=i),
                actual_hour=9,
                was_ml_timed=i % 2 == 0,  # Half ML, half baseline
                was_opened=np.random.random() < 0.6 if i % 2 == 0 else np.random.random() < 0.4,
                was_clicked=np.random.random() < 0.3 if i % 2 == 0 else np.random.random() < 0.2,
                was_converted=False
            )
        
        metrics = tracker.compute_metrics(
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        assert metrics.total_predictions == 20
        assert 0 <= metrics.ml_open_rate <= 1
        assert 0 <= metrics.baseline_open_rate <= 1
    
    def test_daily_metrics(self):
        """Test computing daily metrics."""
        tracker = AccuracyTracker()
        
        for i in range(50):
            tracker.record_outcome(
                prediction_id=f"pred_{i}",
                recipient_id=f"user_{i}",
                recipient_type="customer",
                persona_id="persona_0",
                predicted_hour=9,
                confidence_score=0.7,
                model_version="v20260406_test",
                sent_at=datetime.utcnow() - timedelta(days=i % 5),
                actual_hour=9,
                was_ml_timed=True,
                was_opened=np.random.random() < 0.5,
                was_clicked=False,
                was_converted=False
            )
        
        daily = tracker.compute_daily_metrics(days=5)
        
        assert len(daily) == 5


# ─── Drift Detector Tests ──────────────────────────────────────────────────

class TestDriftDetector:
    """Tests for drift detection module."""
    
    def test_performance_drift_detection(self):
        """Test detecting performance drift."""
        detector = DriftDetector()
        
        result = detector.check_performance_drift(
            model_version="v20260406_test",
            baseline_metrics={
                "accuracy_top1": 0.65,
                "accuracy_top3": 0.85,
                "mae_hours": 2.0,
            },
            current_metrics={
                "accuracy_top1": 0.50,  # 23% drop
                "accuracy_top3": 0.70,  # 18% drop
                "mae_hours": 2.5,
            }
        )
        
        assert result.has_drift == True
        assert len(result.alerts) > 0
        assert result.recommendation is not None
    
    def test_no_drift_detection(self):
        """Test when no drift is present."""
        detector = DriftDetector()
        
        result = detector.check_performance_drift(
            model_version="v20260406_test",
            baseline_metrics={
                "accuracy_top1": 0.65,
                "accuracy_top3": 0.85,
            },
            current_metrics={
                "accuracy_top1": 0.63,  # Small change
                "accuracy_top3": 0.84,
            }
        )
        
        assert result.has_drift == False
    
    def test_data_drift_detection(self):
        """Test detecting data drift."""
        detector = DriftDetector()
        
        # Create baseline and current feature distributions
        np.random.seed(42)
        baseline = np.random.normal(0, 1, (1000, 10))
        current = np.random.normal(0.5, 1.2, (1000, 10))  # Shifted distribution
        
        result = detector.check_data_drift(
            model_version="v20260406_test",
            baseline_features=baseline,
            current_features=current,
            feature_names=[f"feature_{i}" for i in range(10)]
        )
        
        assert result.has_drift == True
    
    def test_severity_classification(self):
        """Test drift severity classification."""
        detector = DriftDetector()
        
        assert detector._classify_severity(0.03) == "low"
        assert detector._classify_severity(0.12) == "medium"
        assert detector._classify_severity(0.25) == "high"
        assert detector._classify_severity(0.35) == "critical"
    
    def test_alert_resolution(self):
        """Test resolving alerts."""
        detector = DriftDetector()
        
        # Trigger an alert
        detector.check_performance_drift(
            model_version="v20260406_test",
            baseline_metrics={"accuracy_top1": 0.65},
            current_metrics={"accuracy_top1": 0.40}
        )
        
        alerts = detector.get_active_alerts()
        assert len(alerts) > 0
        
        # Resolve the alert
        resolved = detector.resolve_alert(
            alert_id=alerts[0].id,
            resolution_notes="Retraining completed",
            trigger_retraining=True
        )
        
        assert resolved is not None
        assert resolved.status == "resolved"
        assert resolved.retraining_triggered == True


# ─── Pipeline Integration Tests ────────────────────────────────────────────

class TestPipeline:
    """Tests for the complete ML pipeline."""
    
    def test_pipeline_training(self, sample_features_list):
        """Test training the complete pipeline."""
        config = PipelineConfig(
            n_personas=5,
            model_type="decision_tree",
            feature_window_days=90
        )
        
        pipeline = NotificationMLPipeline(config=config)
        
        # Create engagement records
        engagement_records = [
            {
                "recipient_id": f.recipient_id,
                "optimal_hour": f.peak_hour if f.peak_hour else 10,
                "event_timestamp": datetime.utcnow() - timedelta(days=np.random.randint(1, 60))
            }
            for f in sample_features_list
        ]
        
        result = pipeline.train(
            recipient_type=None,
            engagement_records=engagement_records
        )
        
        assert result.model_version is not None
        assert len(result.personas) > 0
        assert pipeline.is_trained
    
    def test_pipeline_prediction(self, sample_features_list, sample_features):
        """Test making predictions with the pipeline."""
        config = PipelineConfig(
            n_personas=5,
            model_type="decision_tree"
        )
        
        pipeline = NotificationMLPipeline(config=config)
        
        engagement_records = [
            {"recipient_id": f.recipient_id, "optimal_hour": f.peak_hour or 10}
            for f in sample_features_list
        ]
        
        pipeline.train(engagement_records=engagement_records)
        
        prediction, explanation = pipeline.predict(
            recipient_id="user_123",
            recipient_type="customer",
            features=sample_features
        )
        
        assert 0 <= prediction.recommended_hour <= 23
        assert explanation.reason is not None
    
    def test_pipeline_config(self):
        """Test pipeline configuration."""
        config = PipelineConfig(
            feature_window_days=60,
            n_personas=4,
            model_type="random_forest"
        )
        
        assert config.feature_window_days == 60
        assert config.n_personas == 4
        assert config.model_type == "random_forest"
        
        d = config.to_dict()
        assert d["feature_window_days"] == 60
    
    def test_model_persistence(self, sample_features_list):
        """Test saving and loading models."""
        config = PipelineConfig(model_type="decision_tree")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config.model_directory = tmpdir
            
            pipeline = NotificationMLPipeline(config=config)
            
            engagement_records = [
                {"recipient_id": f.recipient_id, "optimal_hour": f.peak_hour or 10}
                for f in sample_features_list
            ]
            
            result = pipeline.train(engagement_records=engagement_records)
            version = result.model_version
            
            # Load into new pipeline
            new_pipeline = NotificationMLPipeline(config=config)
            new_pipeline.load_models(version)
            
            assert new_pipeline.is_trained
            assert len(new_pipeline.personas) == len(pipeline.personas)


# ─── Run Tests ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
