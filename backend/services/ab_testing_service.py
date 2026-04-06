"""
CONFIT Backend — A/B Testing Service
====================================
Manages A/B test experiments for the recommendation engine.
Tracks metrics, calculates statistical significance, and reports results.
"""

import logging
import hashlib
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import statistics
import math

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.alert_recommendation_models import (
    ABTestExperiment,
    ABTestAssignment,
    ABTestInteractionEvent,
    ABTestGroup,
)
from database.models import Store
from schemas.alert_recommendation_schemas import ABTestMetrics

logger = logging.getLogger(__name__)


# ─── Constants ─────────────────────────────────────────────────────────────────

# Minimum sample size for statistical significance
MIN_SAMPLE_SIZE = 30

# Significance level for p-value threshold
SIGNIFICANCE_ALPHA = 0.05

# Minimum experiment duration in days
MIN_EXPERIMENT_DURATION = 14


class ABTestingService:
    """
    Service for managing A/B tests for recommendation effectiveness.
    
    Features:
    - Experiment creation and management
    - Store assignment to groups
    - Interaction event tracking
    - Metric aggregation
    - Statistical significance calculation
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    # ─── Experiment Management ─────────────────────────────────────────────────
    
    def create_experiment(
        self,
        name: str,
        description: str,
        control_group_size: int,
        treatment_group_size: int,
        min_duration_days: int = 30,
    ) -> ABTestExperiment:
        """Create a new A/B test experiment."""
        experiment = ABTestExperiment(
            name=name,
            description=description,
            control_group_size=control_group_size,
            treatment_group_size=treatment_group_size,
            start_date=date.today(),
            min_duration_days=min_duration_days,
            is_active=True,
            is_paused=False,
            control_metrics={},
            treatment_metrics={},
            is_significant=False,
        )
        
        self._db.add(experiment)
        self._db.commit()
        self._db.refresh(experiment)
        
        logger.info(f"Created A/B test experiment: {name}")
        return experiment
    
    def get_active_experiment(self) -> Optional[ABTestExperiment]:
        """Get the currently active experiment."""
        return self._db.query(ABTestExperiment).filter(
            ABTestExperiment.is_active == True,
            ABTestExperiment.is_paused == False,
        ).first()
    
    def pause_experiment(self, experiment_id: str) -> Optional[ABTestExperiment]:
        """Pause an experiment."""
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if experiment:
            experiment.is_paused = True
            experiment.updated_at = datetime.now(timezone.utc)
            self._db.commit()
            self._db.refresh(experiment)
        
        return experiment
    
    def resume_experiment(self, experiment_id: str) -> Optional[ABTestExperiment]:
        """Resume a paused experiment."""
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if experiment:
            experiment.is_paused = False
            experiment.updated_at = datetime.now(timezone.utc)
            self._db.commit()
            self._db.refresh(experiment)
        
        return experiment
    
    def end_experiment(
        self,
        experiment_id: str,
        end_date: Optional[date] = None,
    ) -> Optional[ABTestExperiment]:
        """End an experiment."""
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if experiment:
            experiment.is_active = False
            experiment.end_date = end_date or date.today()
            experiment.updated_at = datetime.now(timezone.utc)
            self._db.commit()
            self._db.refresh(experiment)
        
        return experiment
    
    # ─── Store Assignment ─────────────────────────────────────────────────────
    
    def assign_store_to_group(
        self,
        experiment_id: str,
        store_id: str,
    ) -> ABTestAssignment:
        """
        Assign a store to an A/B test group.
        Uses deterministic hashing for consistent assignment.
        """
        # Check if already assigned
        existing = self._db.query(ABTestAssignment).filter(
            ABTestAssignment.experiment_id == experiment_id,
            ABTestAssignment.store_id == store_id,
        ).first()
        
        if existing:
            return existing
        
        # Get experiment to determine group sizes
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Count current assignments
        control_count = self._db.query(ABTestAssignment).filter(
            ABTestAssignment.experiment_id == experiment_id,
            ABTestAssignment.group == ABTestGroup.CONTROL,
        ).count()
        
        treatment_count = self._db.query(ABTestAssignment).filter(
            ABTestAssignment.experiment_id == experiment_id,
            ABTestAssignment.group == ABTestGroup.TREATMENT,
        ).count()
        
        # Determine group based on balance and hash
        group = self._determine_group(
            store_id,
            experiment_id,
            control_count,
            treatment_count,
            experiment.control_group_size,
            experiment.treatment_group_size,
        )
        
        # Create assignment
        assignment = ABTestAssignment(
            experiment_id=experiment_id,
            store_id=store_id,
            group=group,
            metrics={},
        )
        
        self._db.add(assignment)
        self._db.commit()
        self._db.refresh(assignment)
        
        logger.info(f"Assigned store {store_id} to {group.value} group for experiment {experiment_id}")
        return assignment
    
    def _determine_group(
        self,
        store_id: str,
        experiment_id: str,
        control_count: int,
        treatment_count: int,
        control_target: int,
        treatment_target: int,
    ) -> ABTestGroup:
        """
        Determine which group to assign a store to.
        Uses hash-based assignment with balance enforcement.
        """
        # If one group is full, assign to the other
        if control_count >= control_target and treatment_count < treatment_target:
            return ABTestGroup.TREATMENT
        if treatment_count >= treatment_target and control_count < control_target:
            return ABTestGroup.CONTROL
        
        # Hash-based assignment for balanced distribution
        hash_input = f"{experiment_id}:{store_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Determine ratio
        total_target = control_target + treatment_target
        control_ratio = control_target / total_target if total_target > 0 else 0.5
        
        # Assign based on hash
        if (hash_value % 100) / 100 < control_ratio:
            return ABTestGroup.CONTROL
        else:
            return ABTestGroup.TREATMENT
    
    def get_store_assignment(
        self,
        store_id: str,
        experiment_id: Optional[str] = None,
    ) -> Optional[ABTestAssignment]:
        """Get a store's A/B test assignment."""
        query = self._db.query(ABTestAssignment).filter(
            ABTestAssignment.store_id == store_id,
        )
        
        if experiment_id:
            query = query.filter(ABTestAssignment.experiment_id == experiment_id)
        
        # Get most recent active experiment assignment
        query = query.join(ABTestExperiment).filter(
            ABTestExperiment.is_active == True,
        ).order_by(ABTestAssignment.assigned_at.desc())
        
        return query.first()
    
    def get_store_group(self, store_id: str) -> ABTestGroup:
        """
        Get a store's A/B test group.
        Returns CONTROL by default if not assigned.
        """
        assignment = self.get_store_assignment(store_id)
        return assignment.group if assignment else ABTestGroup.CONTROL
    
    # ─── Event Tracking ───────────────────────────────────────────────────────
    
    def track_interaction(
        self,
        experiment_id: str,
        store_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track an interaction event for A/B testing."""
        # Get assignment
        assignment = self.get_store_assignment(store_id, experiment_id)
        
        if not assignment:
            logger.warning(f"No assignment found for store {store_id} in experiment {experiment_id}")
            group = ABTestGroup.CONTROL
        else:
            group = assignment.group
        
        # Create event
        event = ABTestInteractionEvent(
            experiment_id=experiment_id,
            store_id=store_id,
            group=group,
            event_type=event_type,
            event_data=event_data or {},
            session_id=session_id,
        )
        
        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)
        
        return event
    
    def track_recommendation_shown(
        self,
        experiment_id: str,
        store_id: str,
        recommendation_id: str,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when a recommendation is shown to a user."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="recommendation_shown",
            event_data={"recommendation_id": recommendation_id},
            session_id=session_id,
        )
    
    def track_recommendation_accepted(
        self,
        experiment_id: str,
        store_id: str,
        recommendation_id: str,
        time_to_action_seconds: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when a recommendation is accepted."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="recommendation_accepted",
            event_data={
                "recommendation_id": recommendation_id,
                "time_to_action_seconds": time_to_action_seconds,
            },
            session_id=session_id,
        )
    
    def track_recommendation_dismissed(
        self,
        experiment_id: str,
        store_id: str,
        recommendation_id: str,
        time_to_action_seconds: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when a recommendation is dismissed."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="recommendation_dismissed",
            event_data={
                "recommendation_id": recommendation_id,
                "time_to_action_seconds": time_to_action_seconds,
            },
            session_id=session_id,
        )
    
    def track_alert_received(
        self,
        experiment_id: str,
        store_id: str,
        alert_id: str,
        alert_type: str,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when an alert is received."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="alert_received",
            event_data={
                "alert_id": alert_id,
                "alert_type": alert_type,
            },
            session_id=session_id,
        )
    
    def track_alert_action(
        self,
        experiment_id: str,
        store_id: str,
        alert_id: str,
        action_type: str,
        time_to_action_seconds: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when an alert action is taken."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="alert_action",
            event_data={
                "alert_id": alert_id,
                "action_type": action_type,
                "time_to_action_seconds": time_to_action_seconds,
            },
            session_id=session_id,
        )
    
    def track_threshold_change(
        self,
        experiment_id: str,
        store_id: str,
        threshold_name: str,
        old_value: Any,
        new_value: Any,
        was_automatic: bool = False,
        session_id: Optional[str] = None,
    ) -> ABTestInteractionEvent:
        """Track when a threshold is changed."""
        return self.track_interaction(
            experiment_id=experiment_id,
            store_id=store_id,
            event_type="threshold_change",
            event_data={
                "threshold_name": threshold_name,
                "old_value": old_value,
                "new_value": new_value,
                "was_automatic": was_automatic,
            },
            session_id=session_id,
        )
    
    # ─── Metric Aggregation ───────────────────────────────────────────────────
    
    def aggregate_metrics(
        self,
        experiment_id: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Aggregate metrics for both groups in an experiment.
        Returns (control_metrics, treatment_metrics).
        """
        # Get all events for this experiment
        events = self._db.query(ABTestInteractionEvent).filter(
            ABTestInteractionEvent.experiment_id == experiment_id,
        ).all()
        
        # Separate by group
        control_events = [e for e in events if e.group == ABTestGroup.CONTROL]
        treatment_events = [e for e in events if e.group == ABTestGroup.TREATMENT]
        
        # Aggregate each group
        control_metrics = self._aggregate_group_metrics(control_events)
        treatment_metrics = self._aggregate_group_metrics(treatment_events)
        
        # Update experiment
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id,
        ).first()
        
        if experiment:
            experiment.control_metrics = control_metrics
            experiment.treatment_metrics = treatment_metrics
            experiment.updated_at = datetime.now(timezone.utc)
            self._db.commit()
        
        return control_metrics, treatment_metrics
    
    def _aggregate_group_metrics(
        self,
        events: List[ABTestInteractionEvent],
    ) -> Dict[str, Any]:
        """Aggregate metrics for a group of events."""
        if not events:
            return {}
        
        # Count unique stores
        unique_stores = set(e.store_id for e in events)
        
        # Recommendation metrics
        shown_events = [e for e in events if e.event_type == "recommendation_shown"]
        accepted_events = [e for e in events if e.event_type == "recommendation_accepted"]
        dismissed_events = [e for e in events if e.event_type == "recommendation_dismissed"]
        
        # Time to action
        acceptance_times = [
            e.event_data.get("time_to_action_seconds")
            for e in accepted_events
            if e.event_data.get("time_to_action_seconds")
        ]
        
        # Alert metrics
        alert_received_events = [e for e in events if e.event_type == "alert_received"]
        alert_action_events = [e for e in events if e.event_type == "alert_action"]
        
        alert_action_times = [
            e.event_data.get("time_to_action_seconds")
            for e in alert_action_events
            if e.event_data.get("time_to_action_seconds")
        ]
        
        # Threshold changes
        threshold_changes = [e for e in events if e.event_type == "threshold_change"]
        manual_changes = [e for e in threshold_changes if not e.event_data.get("was_automatic", False)]
        
        # Calculate metrics
        adoption_rate = len(accepted_events) / len(shown_events) if shown_events else 0
        alert_actionability = len(alert_action_events) / len(alert_received_events) if alert_received_events else 0
        
        return {
            "total_events": len(events),
            "unique_stores": len(unique_stores),
            
            # Recommendation metrics
            "recommendations_shown": len(shown_events),
            "recommendations_accepted": len(accepted_events),
            "recommendations_dismissed": len(dismissed_events),
            "recommendation_adoption_rate": round(adoption_rate, 3),
            
            # Time metrics
            "avg_time_to_accept_seconds": round(statistics.mean(acceptance_times), 1) if acceptance_times else None,
            "median_time_to_accept_seconds": round(statistics.median(acceptance_times), 1) if acceptance_times else None,
            
            # Alert metrics
            "alerts_received": len(alert_received_events),
            "alert_actions_taken": len(alert_action_events),
            "alert_actionability_rate": round(alert_actionability, 3),
            
            "avg_time_to_alert_action_seconds": round(statistics.mean(alert_action_times), 1) if alert_action_times else None,
            "median_time_to_alert_action_seconds": round(statistics.median(alert_action_times), 1) if alert_action_times else None,
            
            # Configuration metrics
            "threshold_changes": len(threshold_changes),
            "manual_threshold_changes": len(manual_changes),
            "configuration_churn_count": len(manual_changes),
        }
    
    # ─── Statistical Significance ─────────────────────────────────────────────
    
    def calculate_significance(
        self,
        experiment_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate statistical significance for an experiment.
        Uses two-proportion z-test for adoption rate comparison.
        """
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id,
        ).first()
        
        if not experiment:
            return None
        
        control_metrics = experiment.control_metrics or {}
        treatment_metrics = experiment.treatment_metrics or {}
        
        # Need minimum sample size
        control_shown = control_metrics.get("recommendations_shown", 0)
        treatment_shown = treatment_metrics.get("recommendations_shown", 0)
        
        if control_shown < MIN_SAMPLE_SIZE or treatment_shown < MIN_SAMPLE_SIZE:
            return {
                "is_significant": False,
                "p_value": None,
                "reason": "Insufficient sample size",
                "control_sample": control_shown,
                "treatment_sample": treatment_shown,
                "min_required": MIN_SAMPLE_SIZE,
            }
        
        # Calculate z-test for adoption rate
        control_accepted = control_metrics.get("recommendations_accepted", 0)
        treatment_accepted = treatment_metrics.get("recommendations_accepted", 0)
        
        p1 = control_accepted / control_shown if control_shown > 0 else 0
        p2 = treatment_accepted / treatment_shown if treatment_shown > 0 else 0
        
        # Pooled proportion
        p_pooled = (control_accepted + treatment_accepted) / (control_shown + treatment_shown)
        
        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/control_shown + 1/treatment_shown))
        
        # Z-score
        if se > 0:
            z = (p2 - p1) / se
            # Two-tailed p-value approximation
            p_value = 2 * (1 - self._normal_cdf(abs(z)))
        else:
            z = 0
            p_value = 1.0
        
        is_significant = p_value < SIGNIFICANCE_ALPHA
        
        # Update experiment
        experiment.p_value = p_value
        experiment.significance_level = SIGNIFICANCE_ALPHA
        experiment.is_significant = is_significant
        self._db.commit()
        
        return {
            "is_significant": is_significant,
            "p_value": round(p_value, 4),
            "z_score": round(z, 3),
            "control_rate": round(p1, 3),
            "treatment_rate": round(p2, 3),
            "relative_lift": round((p2 - p1) / p1 * 100, 1) if p1 > 0 else 0,
            "control_sample": control_shown,
            "treatment_sample": treatment_shown,
        }
    
    def _normal_cdf(self, x: float) -> float:
        """
        Approximate the cumulative distribution function of the standard normal distribution.
        Uses the error function approximation.
        """
        # Constants for approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911
        
        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)
    
    # ─── Reporting ─────────────────────────────────────────────────────────────
    
    def get_experiment_report(
        self,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """Generate a comprehensive report for an experiment."""
        experiment = self._db.query(ABTestExperiment).filter(
            ABTestExperiment.id == experiment_id,
        ).first()
        
        if not experiment:
            return {"error": "Experiment not found"}
        
        # Aggregate metrics
        control_metrics, treatment_metrics = self.aggregate_metrics(experiment_id)
        
        # Calculate significance
        significance = self.calculate_significance(experiment_id)
        
        # Get assignments
        assignments = self._db.query(ABTestAssignment).filter(
            ABTestAssignment.experiment_id == experiment_id,
        ).all()
        
        control_stores = [a for a in assignments if a.group == ABTestGroup.CONTROL]
        treatment_stores = [a for a in assignments if a.group == ABTestGroup.TREATMENT]
        
        # Calculate experiment duration
        start = experiment.start_date
        end = experiment.end_date or date.today()
        duration_days = (end - start).days
        
        return {
            "experiment": experiment.to_dict(),
            "duration_days": duration_days,
            "control_group": {
                "store_count": len(control_stores),
                "metrics": control_metrics,
            },
            "treatment_group": {
                "store_count": len(treatment_stores),
                "metrics": treatment_metrics,
            },
            "significance": significance,
            "recommendations": self._generate_recommendations(
                control_metrics, treatment_metrics, significance
            ),
        }
    
    def _generate_recommendations(
        self,
        control_metrics: Dict[str, Any],
        treatment_metrics: Dict[str, Any],
        significance: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Generate actionable recommendations based on experiment results."""
        recommendations = []
        
        if not significance:
            return ["Insufficient data for recommendations"]
        
        if significance.get("is_significant"):
            lift = significance.get("relative_lift", 0)
            if lift > 0:
                recommendations.append(
                    f"Treatment group shows {lift:.1f}% improvement in adoption rate. "
                    "Consider rolling out to all stores."
                )
            else:
                recommendations.append(
                    f"Control group performs better. Keep current approach."
                )
        else:
            recommendations.append(
                "No statistically significant difference detected. "
                "Continue experiment or consider alternative treatments."
            )
        
        # Time-based recommendations
        control_time = control_metrics.get("median_time_to_accept_seconds")
        treatment_time = treatment_metrics.get("median_time_to_accept_seconds")
        
        if control_time and treatment_time:
            if treatment_time < control_time * 0.8:
                recommendations.append(
                    "Treatment group makes decisions 20%+ faster. "
                    "This indicates better UX or recommendation quality."
                )
        
        # Alert actionability
        control_action = control_metrics.get("alert_actionability_rate", 0)
        treatment_action = treatment_metrics.get("alert_actionability_rate", 0)
        
        if treatment_action > control_action + 0.1:
            recommendations.append(
                "Treatment group shows higher alert actionability. "
                "Recommendations are leading to better alert responses."
            )
        
        return recommendations
    
    def get_all_experiments_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments."""
        experiments = self._db.query(ABTestExperiment).all()
        
        active = [e for e in experiments if e.is_active and not e.is_paused]
        paused = [e for e in experiments if e.is_active and e.is_paused]
        completed = [e for e in experiments if not e.is_active]
        
        return {
            "total_experiments": len(experiments),
            "active_count": len(active),
            "paused_count": len(paused),
            "completed_count": len(completed),
            "experiments": [e.to_dict() for e in experiments],
        }
