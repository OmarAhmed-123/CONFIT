# CONFIT — Notification ML Pipeline Documentation

## Overview

The Notification ML Pipeline is a production-ready machine learning system that optimizes notification delivery times for the CONFIT platform. It transforms engagement analytics into actionable predictions, enabling personalized delivery timing for customers and store/factory owners.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Notification ML Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │   Feature        │    │   Persona        │    │   Delivery       │       │
│  │   Engineering    │───▶│   Clustering     │───▶│   Predictor      │       │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘       │
│          │                       │                      │                    │
│          ▼                       ▼                      ▼                    │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │   Recipient      │    │   Persona        │    │   Delivery       │       │
│  │   Features       │    │   Definitions    │    │   Prediction     │       │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘       │
│                                                          │                    │
│  ┌──────────────────────────────────────────────────────┼──────────────┐   │
│  │                    Monitoring Layer                  │              │   │
│  │  ┌──────────────────┐  ┌──────────────────┐         ▼              │   │
│  │  │   Accuracy       │  │   Drift          │    ┌──────────────────┐ │   │
│  │  │   Tracker        │  │   Detector       │    │   Explainer      │ │   │
│  │  └──────────────────┘  └──────────────────┘    └──────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    A/B Testing Integration                           │   │
│  │  • ML Predictions as treatment variant                               │   │
│  │  • Default timing as control variant                                 │   │
│  │  • Statistical significance testing                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Feature Engineering (`feature_engineering.py`)

Extracts engagement patterns from notification events for ML model training and inference.

**Key Features:**
- Hourly engagement profiles (24 values, 0-23)
- Daily engagement profiles (7 values, Mon-Sun)
- Aggregate metrics (open rate, click rate)
- Behavioral signals (consistency, recency-weighted engagement)
- Time-series trends (30/60/90 day windows)
- Recipient-type specific features (response time for owners, conversion for customers)

**Usage:**
```python
from services.notification_ml import FeatureEngineer

engineer = FeatureEngineer(db_connection=db)
features = engineer.compute_features(
    recipient_id="user_123",
    recipient_type="customer",
    window_days=90
)

# Convert to feature vector for ML
vector = features.to_feature_vector()
```

### 2. Persona Clustering (`persona_clustering.py`)

Segments recipients into behavioral personas using K-means clustering.

**Persona Types:**
| Persona | Description | Characteristics |
|---------|-------------|----------------|
| Early Morning Engagers | Active 6-9 AM | High morning open rates |
| Mid-Morning Responders | Active 9-11 AM | Professional work-break patterns |
| Lunch Time Browsers | Active 11 AM-1 PM | Midday break engagement |
| Afternoon Actives | Active 1-5 PM | Work hours engagement |
| Evening Browsers | Active 5-9 PM | After-work engagement |
| Night Owl Engagers | Active 9 PM-2 AM | Late evening activity |
| Weekend Responders | Active Sat-Sun | Low weekday engagement |
| Always-On Processors | Consistent all day | High consistency score |
| Quick Responders (owners) | Fast response time | <15 min avg response |
| Delayed Responders (owners) | Slower response | >60 min avg response |

**Usage:**
```python
from services.notification_ml import PersonaClusterer

clusterer = PersonaClusterer(n_personas=5)
result = clusterer.fit_predict(features_list)

# Get persona for a recipient
persona_id, confidence = clusterer.predict_persona(features)
```

### 3. Delivery Predictor (`delivery_predictor.py`)

Predicts optimal delivery hour using supervised classification.

**Model Options:**
- `gradient_boosting` (default): Best accuracy, moderate interpretability
- `random_forest`: Good accuracy, better parallelization
- `decision_tree`: Maximum interpretability, lower accuracy

**Usage:**
```python
from services.notification_ml import DeliveryPredictor

predictor = DeliveryPredictor(model_type="gradient_boosting")
result = predictor.train(features_list, engagement_records)

# Make prediction
prediction = predictor.predict(features, persona_id="persona_0")
print(f"Optimal hour: {prediction.recommended_hour}")
print(f"Confidence: {prediction.confidence_score}")
```

### 4. Explainability (`explainability.py`)

Generates human-readable explanations for predictions.

**Explanation Components:**
- **Reason**: Why this hour is optimal (e.g., "45% open rate at 9 AM vs 12% at 3 PM")
- **Feature Importance**: Top contributing features
- **Historical Context**: Past engagement patterns
- **Similar Recipients**: Outcomes for similar personas
- **Confidence Breakdown**: Data quality, pattern clarity, persona match
- **Fallback Reasoning**: Explanation for low-confidence predictions

**Usage:**
```python
from services.notification_ml import Explainer

explainer = Explainer()
explanation = explainer.explain_prediction(
    prediction=prediction,
    features=features,
    persona=persona
)

print(explanation.reason)
print(explanation.feature_importance)
```

### 5. Accuracy Tracker (`accuracy_tracker.py`)

Monitors prediction accuracy and computes lift metrics.

**Metrics Tracked:**
- Open rate lift (ML vs baseline)
- Click rate lift
- Conversion lift
- Response time improvement (for owners)
- Statistical significance (p-values)

**Usage:**
```python
from services.notification_ml import AccuracyTracker

tracker = AccuracyTracker(db_connection=db)

# Record outcome
tracker.record_outcome(
    prediction_id="pred_123",
    recipient_id="user_123",
    was_opened=True,
    was_clicked=False
)

# Get metrics
metrics = tracker.compute_metrics(start_date, end_date)
print(f"Open rate lift: {metrics.open_rate_lift:.2%}")
```

### 6. Drift Detector (`drift_detector.py`)

Detects model performance degradation and data drift.

**Drift Types:**
- **Performance Drift**: Model accuracy degrades
- **Data Drift**: Input feature distribution changes
- **Concept Drift**: Relationship between features and target shifts

**Severity Levels:**
| Level | Threshold | Action |
|-------|-----------|--------|
| Low | 5% degradation | Monitor |
| Medium | 10% degradation | Schedule retraining |
| High | 20% degradation | Retrain within 24h |
| Critical | 30% degradation | Immediate retraining |

**Usage:**
```python
from services.notification_ml import DriftDetector

detector = DriftDetector()
result = detector.check_performance_drift(
    model_version="v20260406",
    baseline_metrics={"accuracy_top1": 0.65},
    current_metrics={"accuracy_top1": 0.50}
)

if result.has_drift:
    print(result.recommendation)
```

### 7. Pipeline Orchestrator (`pipeline.py`)

Coordinates all components for end-to-end ML operations.

**Usage:**
```python
from services.notification_ml import NotificationMLPipeline, PipelineConfig

config = PipelineConfig(
    n_personas=5,
    model_type="gradient_boosting",
    feature_window_days=90
)

pipeline = NotificationMLPipeline(db_connection=db, config=config)

# Train
result = pipeline.train(recipient_type="customer")

# Predict
prediction, explanation = pipeline.predict(
    recipient_id="user_123",
    recipient_type="customer"
)

# Check drift
drift_result = pipeline.check_drift()

# Get accuracy report
report = pipeline.get_accuracy_report(days=30)
```

## API Endpoints

### Prediction Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ml/predict` | POST | Predict optimal delivery time for single recipient |
| `/ml/predict/batch` | POST | Predict for multiple recipients |

### Training Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ml/train` | POST | Train the ML model |
| `/ml/status` | GET | Get current model status |

### Persona Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ml/personas` | GET | List all personas |
| `/ml/personas/{id}` | GET | Get persona details |

### Monitoring Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ml/accuracy` | GET | Get accuracy report |
| `/ml/drift/check` | POST | Check for model drift |

### Model Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ml/models` | GET | List available model versions |
| `/ml/models/{version}/load` | POST | Load specific model version |

## A/B Testing Integration

The ML pipeline integrates with the A/B testing framework to validate predictions.

### Test Configuration

```python
from services.notification_ml.ab_integration import MLABTestIntegration, MLTestConfig

config = MLTestConfig(
    test_id="ml_timing_test_001",
    name="ML Optimized Delivery Timing",
    hypothesis="ML-predicted delivery times will increase open rates by 15%",
    recipient_type="customer",
    traffic_percentage=50,  # 50% treatment, 50% control
    duration_days=14,
    primary_metric="open_rate"
)

integration = MLABTestIntegration(pipeline, db)
test = integration.create_test(config)
integration.start_test(test.test_id)
```

### Getting Delivery Hour with A/B Test

```python
hour, variant_id, prediction = integration.get_delivery_hour(
    recipient_id="user_123",
    recipient_type="customer"
)

# Record outcome
integration.record_outcome(
    recipient_id="user_123",
    notification_id="notif_001",
    test_id=test.test_id,
    variant_id=variant_id,
    sent_at=datetime.utcnow(),
    was_opened=True
)
```

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `ml_personas` | Persona definitions |
| `ml_recipient_personas` | Recipient-to-persona assignments |
| `ml_delivery_predictions` | Prediction records with explanations |
| `ml_model_versions` | Model version history |
| `ml_prediction_accuracy` | Outcome tracking |
| `ml_daily_accuracy_summary` | Pre-aggregated daily metrics |
| `ml_model_drift` | Drift detection alerts |
| `ml_recipient_features` | Cached feature vectors |

## Model Card

### Model Details
- **Model Type**: Gradient Boosting Classifier (default)
- **Task**: Multi-class classification (24 classes = hours)
- **Input**: Recipient engagement features (50+ dimensions)
- **Output**: Recommended delivery hour (0-23) + confidence score

### Training Data
- **Source**: `notification_events` table
- **Window**: 90 days historical data
- **Minimum Events**: 5 per recipient
- **Validation**: Temporal split (train on past 60 days, validate on next 7)

### Performance Metrics
| Metric | Target | Description |
|--------|--------|-------------|
| Top-1 Accuracy | >50% | Exact hour match |
| Top-3 Accuracy | >80% | Within 3 hours |
| MAE | <2 hours | Mean absolute error |
| Inference Latency | <200ms | Prediction time |

### Limitations
- Requires minimum engagement history (5+ notifications)
- Low confidence for new recipients (<30 days history)
- May not capture sudden behavior changes
- Assumes consistent timezone behavior

### Ethical Considerations
- No demographic data used for predictions
- Predictions are suggestions, not mandates
- Users can override ML timing in preferences
- A/B testing ensures fair comparison

## Retraining Schedule

### Automatic Retraining
- **Frequency**: Weekly (every Sunday 2 AM UTC)
- **Trigger**: Scheduled or drift detection
- **Validation**: Automatic accuracy check

### Manual Retraining
```bash
# Via API
curl -X POST /api/ml/train \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"recipient_type": "customer", "n_personas": 5}'
```

## Monitoring & Alerts

### Key Metrics to Monitor
1. **Prediction Accuracy**: Daily open rate lift
2. **Model Confidence Distribution**: % of high-confidence predictions
3. **Persona Distribution**: Balance across personas
4. **Drift Alerts**: Performance degradation warnings

### Alert Thresholds
| Alert | Condition | Action |
|-------|-----------|--------|
| Low Accuracy | Lift < 5% for 7 days | Investigate + retrain |
| High Drift | >15% degradation | Immediate retrain |
| Imbalanced Personas | Any persona > 40% | Re-cluster |
| Low Confidence | >30% predictions < 0.5 confidence | Add more training data |

## Troubleshooting

### Common Issues

**Issue**: Low prediction confidence
- **Cause**: Insufficient engagement history
- **Solution**: Increase `min_events_per_recipient` threshold or use fallback timing

**Issue**: Persona imbalance
- **Cause**: Skewed engagement patterns in training data
- **Solution**: Adjust `n_personas` or use stratified sampling

**Issue**: Drift alerts not triggering
- **Cause**: Threshold too high
- **Solution**: Lower `drift_performance_threshold` in config

**Issue**: Slow inference
- **Cause**: Large feature vectors or model complexity
- **Solution**: Use `decision_tree` model type for faster inference

## File Structure

```
backend/
├── services/
│   └── notification_ml/
│       ├── __init__.py
│       ├── feature_engineering.py
│       ├── persona_clustering.py
│       ├── delivery_predictor.py
│       ├── explainability.py
│       ├── accuracy_tracker.py
│       ├── drift_detector.py
│       ├── pipeline.py
│       └── ab_integration.py
├── api/
│   └── notification_ml.py
└── tests/
    └── test_notification_ml.py

supabase/
└── migrations/
    └── 20260406_ml_notification_optimization.sql
```

## Dependencies

```
# requirements.txt additions
scikit-learn>=1.3.0
numpy>=1.24.0
scipy>=1.10.0
joblib>=1.3.0
```

## Quick Start

```python
from services.notification_ml import NotificationMLPipeline, PipelineConfig

# Initialize
config = PipelineConfig(
    n_personas=5,
    model_type="gradient_boosting"
)
pipeline = NotificationMLPipeline(db_connection=db, config=config)

# Train
result = pipeline.train(recipient_type="customer")
print(f"Trained {len(result.personas)} personas")

# Predict
prediction, explanation = pipeline.predict(
    recipient_id="user_123",
    recipient_type="customer"
)
print(f"Deliver at {prediction.recommended_hour}:00")
print(f"Reason: {explanation.reason}")
```

## Support

For issues or questions, contact the ML team or create an issue in the CONFIT repository.
