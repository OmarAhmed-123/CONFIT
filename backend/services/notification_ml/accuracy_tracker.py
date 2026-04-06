"""
CONFIT — Notification ML Accuracy Tracker
=========================================
Tracks prediction accuracy over time and computes lift metrics
comparing ML-optimized delivery vs baseline timing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict
import numpy as np
from scipy import stats


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a time period."""
    period_start: datetime
    period_end: datetime
    persona_id: Optional[str]
    recipient_type: str
    
    # Prediction counts
    total_predictions: int = 0
    ml_timed_sent: int = 0
    baseline_timed_sent: int = 0
    
    # ML outcomes
    ml_open_rate: float = 0.0
    ml_click_rate: float = 0.0
    ml_conversion_rate: float = 0.0
    ml_avg_response_time: Optional[float] = None
    
    # Baseline outcomes
    baseline_open_rate: float = 0.0
    baseline_click_rate: float = 0.0
    baseline_conversion_rate: float = 0.0
    baseline_avg_response_time: Optional[float] = None
    
    # Lift metrics
    open_rate_lift: float = 0.0
    click_rate_lift: float = 0.0
    conversion_lift: float = 0.0
    response_time_improvement: float = 0.0
    
    # Statistical significance
    open_rate_p_value: Optional[float] = None
    click_rate_p_value: Optional[float] = None
    conversion_p_value: Optional[float] = None
    is_significant: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "persona_id": self.persona_id,
            "recipient_type": self.recipient_type,
            "total_predictions": self.total_predictions,
            "ml_timed_sent": self.ml_timed_sent,
            "baseline_timed_sent": self.baseline_timed_sent,
            "ml_open_rate": self.ml_open_rate,
            "ml_click_rate": self.ml_click_rate,
            "ml_conversion_rate": self.ml_conversion_rate,
            "ml_avg_response_time": self.ml_avg_response_time,
            "baseline_open_rate": self.baseline_open_rate,
            "baseline_click_rate": self.baseline_click_rate,
            "baseline_conversion_rate": self.baseline_conversion_rate,
            "baseline_avg_response_time": self.baseline_avg_response_time,
            "open_rate_lift": self.open_rate_lift,
            "click_rate_lift": self.click_rate_lift,
            "conversion_lift": self.conversion_lift,
            "response_time_improvement": self.response_time_improvement,
            "open_rate_p_value": self.open_rate_p_value,
            "click_rate_p_value": self.click_rate_p_value,
            "conversion_p_value": self.conversion_p_value,
            "is_significant": self.is_significant,
        }


@dataclass
class PredictionOutcome:
    """Outcome of a single prediction."""
    prediction_id: str
    recipient_id: str
    recipient_type: str
    persona_id: Optional[str]
    
    # Prediction details
    predicted_hour: int
    confidence_score: float
    model_version: str
    
    # Actual outcome
    sent_at: datetime
    actual_hour: int
    was_ml_timed: bool
    
    # Engagement outcomes
    was_opened: bool = False
    was_clicked: bool = False
    was_converted: bool = False
    response_time_min: Optional[float] = None
    
    # Baseline comparison
    baseline_hour: Optional[int] = None
    baseline_opened: Optional[bool] = None
    baseline_clicked: Optional[bool] = None
    baseline_converted: Optional[bool] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "persona_id": self.persona_id,
            "predicted_hour": self.predicted_hour,
            "confidence_score": self.confidence_score,
            "model_version": self.model_version,
            "sent_at": self.sent_at.isoformat(),
            "actual_hour": self.actual_hour,
            "was_ml_timed": self.was_ml_timed,
            "was_opened": self.was_opened,
            "was_clicked": self.was_clicked,
            "was_converted": self.was_converted,
            "response_time_min": self.response_time_min,
            "baseline_hour": self.baseline_hour,
            "baseline_opened": self.baseline_opened,
            "baseline_clicked": self.baseline_clicked,
            "baseline_converted": self.baseline_converted,
            "created_at": self.created_at.isoformat(),
        }


class AccuracyTracker:
    """
    Tracks and analyzes prediction accuracy.
    
    Usage:
        tracker = AccuracyTracker(db_connection)
        tracker.record_outcome(outcome)
        metrics = tracker.compute_metrics(start_date, end_date)
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize accuracy tracker.
        
        Args:
            db_connection: Database connection for persistence
        """
        self.db = db_connection
        self._outcomes: List[PredictionOutcome] = []
    
    def record_outcome(
        self,
        prediction_id: str,
        recipient_id: str,
        recipient_type: str,
        persona_id: Optional[str],
        predicted_hour: int,
        confidence_score: float,
        model_version: str,
        sent_at: datetime,
        actual_hour: int,
        was_ml_timed: bool,
        was_opened: bool = False,
        was_clicked: bool = False,
        was_converted: bool = False,
        response_time_min: Optional[float] = None,
        baseline_hour: Optional[int] = None,
        baseline_outcome: Optional[Dict] = None
    ) -> PredictionOutcome:
        """
        Record the outcome of a prediction.
        
        Args:
            prediction_id: ID of the prediction
            recipient_id: Recipient identifier
            recipient_type: 'customer' or 'owner'
            persona_id: Assigned persona ID
            predicted_hour: Predicted optimal hour
            confidence_score: Prediction confidence
            model_version: Model version used
            sent_at: When notification was sent
            actual_hour: Hour notification was actually sent
            was_ml_timed: Whether sent at ML-predicted time
            was_opened: Whether notification was opened
            was_clicked: Whether notification was clicked
            was_converted: Whether conversion occurred
            response_time_min: Response time for owners
            baseline_hour: Default hour that would have been used
            baseline_outcome: Expected outcome at baseline hour
            
        Returns:
            PredictionOutcome object
        """
        outcome = PredictionOutcome(
            prediction_id=prediction_id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            persona_id=persona_id,
            predicted_hour=predicted_hour,
            confidence_score=confidence_score,
            model_version=model_version,
            sent_at=sent_at,
            actual_hour=actual_hour,
            was_ml_timed=was_ml_timed,
            was_opened=was_opened,
            was_clicked=was_clicked,
            was_converted=was_converted,
            response_time_min=response_time_min,
            baseline_hour=baseline_hour,
            baseline_opened=baseline_outcome.get("opened") if baseline_outcome else None,
            baseline_clicked=baseline_outcome.get("clicked") if baseline_outcome else None,
            baseline_converted=baseline_outcome.get("converted") if baseline_outcome else None,
        )
        
        self._outcomes.append(outcome)
        
        # Persist to database if available
        if self.db:
            self._persist_outcome(outcome)
        
        return outcome
    
    def compute_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        persona_id: Optional[str] = None,
        recipient_type: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> AccuracyMetrics:
        """
        Compute accuracy metrics for a time period.
        
        Args:
            start_date: Start of period
            end_date: End of period
            persona_id: Filter by persona (optional)
            recipient_type: Filter by recipient type (optional)
            model_version: Filter by model version (optional)
            
        Returns:
            AccuracyMetrics object
        """
        # Filter outcomes
        outcomes = [
            o for o in self._outcomes
            if start_date <= o.sent_at <= end_date
        ]
        
        if persona_id:
            outcomes = [o for o in outcomes if o.persona_id == persona_id]
        if recipient_type:
            outcomes = [o for o in outcomes if o.recipient_type == recipient_type]
        if model_version:
            outcomes = [o for o in outcomes if o.model_version == model_version]
        
        if not outcomes:
            return AccuracyMetrics(
                period_start=start_date,
                period_end=end_date,
                persona_id=persona_id,
                recipient_type=recipient_type or "unknown"
            )
        
        # Separate ML-timed and baseline-timed
        ml_outcomes = [o for o in outcomes if o.was_ml_timed]
        baseline_outcomes = [o for o in outcomes if not o.was_ml_timed]
        
        # Compute metrics
        metrics = AccuracyMetrics(
            period_start=start_date,
            period_end=end_date,
            persona_id=persona_id,
            recipient_type=outcomes[0].recipient_type if outcomes else "unknown",
            total_predictions=len(outcomes),
            ml_timed_sent=len(ml_outcomes),
            baseline_timed_sent=len(baseline_outcomes),
        )
        
        # ML outcomes
        if ml_outcomes:
            metrics.ml_open_rate = np.mean([o.was_opened for o in ml_outcomes])
            metrics.ml_click_rate = np.mean([o.was_clicked for o in ml_outcomes])
            metrics.ml_conversion_rate = np.mean([o.was_converted for o in ml_outcomes])
            
            response_times = [o.response_time_min for o in ml_outcomes if o.response_time_min]
            if response_times:
                metrics.ml_avg_response_time = np.mean(response_times)
        
        # Baseline outcomes
        if baseline_outcomes:
            metrics.baseline_open_rate = np.mean([o.was_opened for o in baseline_outcomes])
            metrics.baseline_click_rate = np.mean([o.was_clicked for o in baseline_outcomes])
            metrics.baseline_conversion_rate = np.mean([o.was_converted for o in baseline_outcomes])
            
            response_times = [o.response_time_min for o in baseline_outcomes if o.response_time_min]
            if response_times:
                metrics.baseline_avg_response_time = np.mean(response_times)
        
        # Compute lift
        if metrics.baseline_open_rate > 0:
            metrics.open_rate_lift = (metrics.ml_open_rate - metrics.baseline_open_rate) / metrics.baseline_open_rate
        if metrics.baseline_click_rate > 0:
            metrics.click_rate_lift = (metrics.ml_click_rate - metrics.baseline_click_rate) / metrics.baseline_click_rate
        if metrics.baseline_conversion_rate > 0:
            metrics.conversion_lift = (metrics.ml_conversion_rate - metrics.baseline_conversion_rate) / metrics.baseline_conversion_rate
        
        if metrics.ml_avg_response_time and metrics.baseline_avg_response_time:
            metrics.response_time_improvement = metrics.baseline_avg_response_time - metrics.ml_avg_response_time
        
        # Statistical significance tests
        if len(ml_outcomes) >= 10 and len(baseline_outcomes) >= 10:
            # Open rate significance
            ml_opens = [1 if o.was_opened else 0 for o in ml_outcomes]
            baseline_opens = [1 if o.was_opened else 0 for o in baseline_outcomes]
            _, metrics.open_rate_p_value = stats.ttest_ind(ml_opens, baseline_opens)
            
            # Click rate significance
            ml_clicks = [1 if o.was_clicked else 0 for o in ml_outcomes]
            baseline_clicks = [1 if o.was_clicked else 0 for o in baseline_outcomes]
            _, metrics.click_rate_p_value = stats.ttest_ind(ml_clicks, baseline_clicks)
            
            # Conversion significance
            ml_convs = [1 if o.was_converted else 0 for o in ml_outcomes]
            baseline_convs = [1 if o.was_converted else 0 for o in baseline_outcomes]
            _, metrics.conversion_p_value = stats.ttest_ind(ml_convs, baseline_convs)
            
            # Overall significance
            metrics.is_significant = any(
                p < 0.05 for p in [
                    metrics.open_rate_p_value,
                    metrics.click_rate_p_value,
                    metrics.conversion_p_value
                ] if p is not None
            )
        
        return metrics
    
    def compute_daily_metrics(
        self,
        days: int = 30,
        persona_id: Optional[str] = None
    ) -> List[AccuracyMetrics]:
        """
        Compute daily accuracy metrics for the past N days.
        
        Args:
            days: Number of days to compute
            persona_id: Filter by persona
            
        Returns:
            List of AccuracyMetrics, one per day
        """
        end_date = datetime.utcnow()
        metrics_list = []
        
        for i in range(days):
            day_start = end_date - timedelta(days=i+1)
            day_end = end_date - timedelta(days=i)
            
            metrics = self.compute_metrics(
                start_date=day_start,
                end_date=day_end,
                persona_id=persona_id
            )
            metrics_list.append(metrics)
        
        return metrics_list[::-1]  # Oldest first
    
    def get_accuracy_trend(
        self,
        days: int = 30,
        metric: str = "open_rate_lift"
    ) -> Dict[str, Any]:
        """
        Get trend of accuracy metrics over time.
        
        Args:
            days: Number of days to analyze
            metric: Metric to track ('open_rate_lift', 'click_rate_lift', etc.)
            
        Returns:
            Dictionary with trend data
        """
        daily_metrics = self.compute_daily_metrics(days=days)
        
        values = []
        dates = []
        
        for m in daily_metrics:
            value = getattr(m, metric, 0)
            values.append(value)
            dates.append(m.period_start.date().isoformat())
        
        # Compute trend (linear regression slope)
        if len(values) >= 7:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            trend = "improving" if slope > 0.01 else "declining" if slope < -0.01 else "stable"
        else:
            slope = 0
            trend = "insufficient_data"
        
        return {
            "metric": metric,
            "values": values,
            "dates": dates,
            "trend": trend,
            "slope": slope,
            "mean": np.mean(values) if values else 0,
            "std": np.std(values) if values else 0,
        }
    
    def get_persona_performance(
        self,
        days: int = 30
    ) -> Dict[str, AccuracyMetrics]:
        """
        Get performance metrics by persona.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary mapping persona_id to AccuracyMetrics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get unique personas
        personas = set(
            o.persona_id for o in self._outcomes
            if o.persona_id and start_date <= o.sent_at < end_date
        )
        
        performance = {}
        for persona_id in personas:
            metrics = self.compute_metrics(
                start_date=start_date,
                end_date=end_date,
                persona_id=persona_id
            )
            performance[persona_id] = metrics
        
        return performance
    
    def _persist_outcome(self, outcome: PredictionOutcome) -> None:
        """Persist outcome to database."""
        if not self.db:
            return
        
        query = """
            INSERT INTO ml_prediction_accuracy (
                prediction_id, persona_id, model_version,
                was_opened, was_clicked, was_converted, response_time_min,
                baseline_hour, baseline_outcome,
                open_rate_lift, click_rate_lift, conversion_lift, response_time_improvement,
                notification_id, sent_at, opened_at, clicked_at, converted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (prediction_id) DO UPDATE SET
                was_opened = EXCLUDED.was_opened,
                was_clicked = EXCLUDED.was_clicked,
                was_converted = EXCLUDED.was_converted
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                outcome.prediction_id,
                outcome.persona_id,
                outcome.model_version,
                outcome.was_opened,
                outcome.was_clicked,
                outcome.was_converted,
                outcome.response_time_min,
                outcome.baseline_hour,
                {
                    "opened": outcome.baseline_opened,
                    "clicked": outcome.baseline_clicked,
                    "converted": outcome.baseline_converted,
                },
                # Lift calculations would be done separately
                None, None, None, None,
                outcome.prediction_id,  # Using prediction_id as notification_id
                outcome.sent_at,
                None, None, None
            ))
            self.db.commit()
    
    def load_outcomes_from_db(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Load outcomes from database.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Number of outcomes loaded
        """
        if not self.db:
            return 0
        
        query = """
            SELECT 
                pa.id as prediction_id,
                dp.recipient_id,
                dp.recipient_type,
                dp.persona_id,
                dp.recommended_hour as predicted_hour,
                dp.confidence_score,
                dp.model_version,
                pa.sent_at,
                dp.recommended_hour as actual_hour,
                pa.was_opened,
                pa.was_clicked,
                pa.was_converted,
                pa.response_time_min,
                pa.baseline_hour
            FROM ml_prediction_accuracy pa
            JOIN ml_delivery_predictions dp ON pa.prediction_id = dp.id
            WHERE (%s IS NULL OR pa.sent_at >= %s)
              AND (%s IS NULL OR pa.sent_at < %s)
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (start_date, start_date, end_date, end_date))
            rows = cur.fetchall()
            
            for row in rows:
                outcome = PredictionOutcome(
                    prediction_id=row[0],
                    recipient_id=row[1],
                    recipient_type=row[2],
                    persona_id=row[3],
                    predicted_hour=row[4],
                    confidence_score=row[5],
                    model_version=row[6],
                    sent_at=row[7],
                    actual_hour=row[8],
                    was_ml_timed=True,  # Assume ML-timed if in accuracy table
                    was_opened=row[9],
                    was_clicked=row[10],
                    was_converted=row[11],
                    response_time_min=row[12],
                    baseline_hour=row[13],
                )
                self._outcomes.append(outcome)
        
        return len(rows)
