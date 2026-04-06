# Notification ML Optimization Runbook

This runbook covers training, prediction, A/B integration, and monitoring for the notification delivery-time optimization system.

## What is deployed

- API router: `api/notification_ml.py` mounted at `/ml`
- Core pipeline: `services/notification_ml/`
- Analytics + A/B router: `api/notification_analytics.py`
- Model artifacts: `backend/models/notification_ml/<model_version>/`

## Training flow

1. Event data is loaded from `notification_events`.
2. Features are computed per recipient (hour/day profiles, trends, consistency, recency).
3. Recipients are clustered into personas.
4. Delivery model is trained to predict optimal hour (top-1 + top-3 ranking).
5. Persona model + predictor are serialized with versioned metadata.

## API usage

- Train model:
  - `POST /ml/train`
  - Optional payload:
    - `recipient_type`: `customer` or `owner`
    - `n_personas`: 3-10
    - `model_type`: `gradient_boosting` | `random_forest` | `decision_tree`
- Predict:
  - `POST /ml/predict`
  - Returns:
    - `recommended_hour`
    - `recommended_hours` (top-3)
    - `confidence_score`
    - explanation payload
- Accuracy report:
  - `GET /ml/accuracy?days=30`
- Drift check:
  - `POST /ml/drift/check`
- Personas:
  - `GET /ml/personas`

## A/B testing integration

When creating an analytics A/B test (`POST /analytics/notifications/ab-tests`):

- Set `use_ml_predictions=true` to add an "Use ML Predictions" timing variant.
- Optionally set `ml_confidence_threshold` (0.0-1.0).
- Treatment recipients are scheduled at ML-recommended times.
- Control recipients use default timing.

## Weekly retraining recommendation

- Schedule `POST /ml/train` once per week (off-peak).
- Keep the previous stable model version available for rollback via:
  - `POST /ml/models/{model_version}/load`

### Built-in scheduler (implemented)

The backend now includes a weekly retraining scheduler service:
- `services/notification_ml_scheduler.py`
- Auto-started in app lifespan when enabled.

Environment controls:
- `NOTIFICATION_ML_RETRAIN_ENABLED=true|false`
- `NOTIFICATION_ML_INTERNAL_BASE_URL=http://127.0.0.1:8000`
- `NOTIFICATION_ML_RETRAIN_DAY_OF_WEEK=sun`
- `NOTIFICATION_ML_RETRAIN_HOUR_UTC=03`
- `NOTIFICATION_ML_RETRAIN_MINUTE_UTC=00`
- `NOTIFICATION_ML_SNAPSHOT_PATH=backend/storage/notification_ml_accuracy_snapshots.jsonl`

On each run, the scheduler:
1. Calls `POST /ml/train`
2. Captures `GET /ml/status`
3. Captures `GET /ml/accuracy?days=30`
4. Appends a JSONL snapshot for audit/history

## Operational checks

- Verify `GET /ml/status` shows `is_trained=true`.
- Verify persona coverage in `GET /ml/personas`.
- Monitor lift metrics in A/B tests and `GET /ml/accuracy`.
- Run drift check weekly and retrain if drift is detected.

