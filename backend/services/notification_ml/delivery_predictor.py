"""
CONFIT — Notification ML Delivery Time Predictor
================================================
Predicts optimal notification delivery times for each recipient based on
their persona and engagement history. Uses interpretable models for explainability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, top_k_accuracy_score
import joblib
import os


@dataclass
class DeliveryPrediction:
    """Prediction result for optimal delivery time."""
    recipient_id: str
    recipient_type: str
    persona_id: Optional[str]
    
    # Primary recommendation
    recommended_hour: int
    confidence_score: float
    
    # Top-3 recommendations
    recommended_hours: List[Dict[str, Any]] = field(default_factory=list)
    
    # Explainability
    explanation: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    notification_type: Optional[str] = None
    channel: Optional[str] = None
    
    # Model metadata
    model_version: str = ""
    feature_values: Dict[str, float] = field(default_factory=dict)
    
    # Validity
    predicted_at: datetime = field(default_factory=datetime.utcnow)
    valid_for_hours: int = 24
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.predicted_at + timedelta(hours=self.valid_for_hours)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "persona_id": self.persona_id,
            "recommended_hour": self.recommended_hour,
            "confidence_score": self.confidence_score,
            "recommended_hours": self.recommended_hours,
            "explanation": self.explanation,
            "notification_type": self.notification_type,
            "channel": self.channel,
            "model_version": self.model_version,
            "feature_values": self.feature_values,
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
            "valid_for_hours": self.valid_for_hours,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class TrainingResult:
    """Result of model training."""
    model_version: str
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    training_samples: int
    validation_samples: int
    training_period: Tuple[datetime, datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "metrics": self.metrics,
            "feature_importance": self.feature_importance,
            "training_samples": self.training_samples,
            "validation_samples": self.validation_samples,
            "training_period": [
                self.training_period[0].isoformat(),
                self.training_period[1].isoformat()
            ],
        }


class DeliveryPredictor:
    """
    Predicts optimal delivery hour for notifications.
    
    Uses a multi-class classification approach where each hour (0-23) is a class.
    The model learns from historical engagement data which hours lead to the
    highest engagement for each recipient profile.
    
    Usage:
        predictor = DeliveryPredictor()
        result = predictor.train(features_list, optimal_hours)
        prediction = predictor.predict(features, persona_id)
    """
    
    # Feature names for interpretability
    FEATURE_NAMES = [
        "hourly_open_0", "hourly_open_1", "hourly_open_2", "hourly_open_3",
        "hourly_open_4", "hourly_open_5", "hourly_open_6", "hourly_open_7",
        "hourly_open_8", "hourly_open_9", "hourly_open_10", "hourly_open_11",
        "hourly_open_12", "hourly_open_13", "hourly_open_14", "hourly_open_15",
        "hourly_open_16", "hourly_open_17", "hourly_open_18", "hourly_open_19",
        "hourly_open_20", "hourly_open_21", "hourly_open_22", "hourly_open_23",
        "daily_open_mon", "daily_open_tue", "daily_open_wed", "daily_open_thu",
        "daily_open_fri", "daily_open_sat", "daily_open_sun",
        "overall_open_rate", "overall_click_rate",
        "consistency_score", "recency_weighted_engagement",
        "peak_hour_norm", "peak_day_norm",
        "trend_30d", "trend_60d", "trend_90d",
        "response_time_norm", "response_consistency",
        "conversion_rate_30d", "repeat_purchase_rate",
        "tenure_norm",
    ]
    
    def __init__(
        self,
        model_type: str = "gradient_boosting",
        model_version: Optional[str] = None,
        random_state: int = 42
    ):
        """
        Initialize delivery predictor.
        
        Args:
            model_type: Type of model ('gradient_boosting', 'random_forest', 'decision_tree')
            model_version: Version string for the model
            random_state: Random seed for reproducibility
        """
        self.model_type = model_type
        self.model_version = model_version or f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.random_state = random_state
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance: Dict[str, float] = {}
        self.is_fitted = False
    
    def _create_model(self):
        """Create the underlying ML model."""
        if self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=self.random_state,
                validation_fraction=0.1,
                n_iter_no_change=10
            )
        elif self.model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=self.random_state,
                n_jobs=-1
            )
        else:  # decision_tree for maximum interpretability
            return DecisionTreeClassifier(
                max_depth=8,
                random_state=self.random_state
            )
    
    def train(
        self,
        features_list: List["RecipientFeatures"],
        engagement_records: List[Dict],
        validation_days: int = 7
    ) -> TrainingResult:
        """
        Train the delivery time prediction model.
        
        Args:
            features_list: List of RecipientFeatures objects
            engagement_records: List of engagement records with optimal_hour
            validation_days: Number of days for temporal validation
            
        Returns:
            TrainingResult with metrics and feature importance
        """
        # Prepare training data
        X, y, periods = self._prepare_training_data(features_list, engagement_records)
        
        if len(X) < 100:
            raise ValueError(f"Need at least 100 training samples, got {len(X)}")
        
        # Temporal split
        cutoff_date = datetime.utcnow() - timedelta(days=validation_days)
        train_mask = np.array([p < cutoff_date for p in periods])
        val_mask = ~train_mask
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_val, y_val = X[val_mask], y[val_mask]
        
        if len(X_train) < 10 or len(X_val) < 10:
            # Fall back to random split if temporal split doesn't work
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=self.random_state
            )

        if len(X_train) == 0 or len(X_val) == 0:
            raise ValueError("Unable to create non-empty train/validation splits")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_train_scaled, y_train)
        
        # Compute metrics
        y_pred = self.model.predict(X_val_scaled)
        y_proba = self.model.predict_proba(X_val_scaled)
        
        # Accuracy metrics
        top1_acc = accuracy_score(y_val, y_pred)
        
        # Top-3 accuracy (within 3 hours of optimal)
        top3_acc = self._compute_top_k_accuracy(y_val, y_pred, k=3)
        
        # Mean absolute error in hours
        mae = np.mean(np.abs(y_val - y_pred))
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            self.feature_importance = {
                name: float(imp) 
                for name, imp in zip(self.FEATURE_NAMES[:len(importances)], importances)
            }
        
        self.is_fitted = True
        
        training_period = (
            min(periods) if periods else datetime.utcnow() - timedelta(days=90),
            max(periods) if periods else datetime.utcnow()
        )
        
        return TrainingResult(
            model_version=self.model_version,
            metrics={
                "accuracy_top1": float(top1_acc),
                "accuracy_top3": float(top3_acc),
                "mae_hours": float(mae),
                "n_classes": len(np.unique(y)),
            },
            feature_importance=self.feature_importance,
            training_samples=len(X_train),
            validation_samples=len(X_val),
            training_period=training_period
        )
    
    def _prepare_training_data(
        self,
        features_list: List["RecipientFeatures"],
        engagement_records: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray, List[datetime]]:
        """
        Prepare training data from features and engagement records.
        
        The target variable is the hour with highest engagement for each record.
        """
        # Build lookup for features
        features_lookup = {f.recipient_id: f for f in features_list}
        
        X = []
        y = []
        periods = []
        
        for record in engagement_records:
            recipient_id = record.get("recipient_id")
            if recipient_id not in features_lookup:
                continue
            
            features = features_lookup[recipient_id]
            
            # Determine optimal hour from engagement data
            optimal_hour = self._compute_optimal_hour(record)
            if optimal_hour is None:
                continue
            
            X.append(features.to_feature_vector())
            y.append(optimal_hour)
            
            # Get timestamp for temporal split
            ts = record.get("event_timestamp") or record.get("engagement_at")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            periods.append(ts or datetime.utcnow())
        
        return np.array(X), np.array(y), periods
    
    def _compute_optimal_hour(self, record: Dict) -> Optional[int]:
        """Compute optimal hour from engagement record."""
        # If record has explicit optimal_hour
        if "optimal_hour" in record:
            return record["optimal_hour"]
        
        # Compute from engagement by hour
        hourly_engagement = record.get("hourly_engagement", {})
        if hourly_engagement:
            best_hour = max(hourly_engagement.items(), key=lambda x: x[1])
            return int(best_hour[0])
        
        # Use hour of highest engagement event
        engagement_events = record.get("engagement_events", [])
        if engagement_events:
            hours = []
            for event in engagement_events:
                ts = event.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts and event.get("opened") or event.get("clicked"):
                    hours.append(ts.hour)
            
            if hours:
                # Return most common hour
                return max(set(hours), key=hours.count)
        
        return None
    
    def _compute_top_k_accuracy(self, y_true: np.ndarray, y_pred: np.ndarray, k: int = 3) -> float:
        """Compute accuracy within k hours."""
        within_k = np.abs(y_true - y_pred) <= k
        # Handle wrap-around (e.g., 23 and 0 are 1 hour apart)
        wrap_around = np.abs(y_true - y_pred - 24) <= k
        wrap_around_neg = np.abs(y_true - y_pred + 24) <= k
        
        return float(np.mean(within_k | wrap_around | wrap_around_neg))
    
    def predict(
        self,
        features: "RecipientFeatures",
        persona_id: Optional[str] = None,
        notification_type: Optional[str] = None,
        channel: Optional[str] = None
    ) -> DeliveryPrediction:
        """
        Predict optimal delivery hour for a recipient.
        
        Args:
            features: RecipientFeatures object
            persona_id: Assigned persona ID
            notification_type: Type of notification (optional context)
            channel: Notification channel (optional context)
            
        Returns:
            DeliveryPrediction with recommended hour and explanation
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call train() first.")
        
        # Prepare input
        X = features.to_feature_vector().reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions
        predicted_hour = int(self.model.predict(X_scaled)[0])
        probabilities = self.model.predict_proba(X_scaled)[0]
        
        # Confidence score
        confidence = float(probabilities.max())
        
        # Top-3 recommendations
        top3_indices = np.argsort(probabilities)[-3:][::-1]
        recommended_hours = [
            {"hour": int(idx), "score": float(probabilities[idx])}
            for idx in top3_indices
        ]
        
        # Feature values for explanation
        feature_values = {
            name: float(val) 
            for name, val in zip(self.FEATURE_NAMES[:len(X[0])], X[0])
        }
        
        # Create prediction
        prediction = DeliveryPrediction(
            recipient_id=features.recipient_id,
            recipient_type=features.recipient_type,
            persona_id=persona_id,
            recommended_hour=predicted_hour,
            confidence_score=confidence,
            recommended_hours=recommended_hours,
            notification_type=notification_type,
            channel=channel,
            model_version=self.model_version,
            feature_values=feature_values
        )
        
        return prediction
    
    def predict_batch(
        self,
        features_list: List["RecipientFeatures"],
        persona_assignments: Optional[Dict[str, str]] = None
    ) -> List[DeliveryPrediction]:
        """
        Predict optimal delivery hours for multiple recipients.
        
        Args:
            features_list: List of RecipientFeatures objects
            persona_assignments: Optional mapping of recipient_id to persona_id
            
        Returns:
            List of DeliveryPrediction objects
        """
        if persona_assignments is None:
            persona_assignments = {}
        
        predictions = []
        for features in features_list:
            persona_id = persona_assignments.get(features.recipient_id)
            pred = self.predict(features, persona_id)
            predictions.append(pred)
        
        return predictions
    
    def save_model(self, path: str) -> None:
        """Save model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_importance": self.feature_importance,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "random_state": self.random_state,
            "is_fitted": self.is_fitted,
        }
        
        joblib.dump(model_data, path)
    
    def load_model(self, path: str) -> None:
        """Load model from disk."""
        model_data = joblib.load(path)
        
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_importance = model_data.get("feature_importance", {})
        self.model_type = model_data.get("model_type", "gradient_boosting")
        self.model_version = model_data["model_version"]
        self.random_state = model_data.get("random_state", 42)
        self.is_fitted = model_data.get("is_fitted", True)


def compute_optimal_hour_from_events(
    events: List[Dict],
    recipient_id: str
) -> Optional[int]:
    """
    Compute optimal delivery hour from engagement events.
    
    Args:
        events: List of notification events
        recipient_id: Recipient identifier
        
    Returns:
        Optimal hour (0-23) or None if insufficient data
    """
    hourly_engagement = defaultdict(lambda: {"sent": 0, "opened": 0, "clicked": 0})
    
    for event in events:
        if event.get("recipient_id") != recipient_id:
            continue
        
        ts = event.get("event_timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if not ts:
            continue
        
        hour = ts.hour
        event_type = event.get("event_type")
        
        if event_type == "sent":
            hourly_engagement[hour]["sent"] += 1
        elif event_type == "read":
            hourly_engagement[hour]["opened"] += 1
        elif event_type == "clicked":
            hourly_engagement[hour]["clicked"] += 1
    
    # Compute engagement scores
    best_hour = None
    best_score = -1
    
    for hour, counts in hourly_engagement.items():
        if counts["sent"] < 3:  # Need minimum samples
            continue
        
        # Weighted engagement score
        open_rate = counts["opened"] / counts["sent"] if counts["sent"] > 0 else 0
        click_rate = counts["clicked"] / counts["sent"] if counts["sent"] > 0 else 0
        score = open_rate * 0.6 + click_rate * 0.4
        
        if score > best_score:
            best_score = score
            best_hour = hour
    
    return best_hour


from collections import defaultdict
