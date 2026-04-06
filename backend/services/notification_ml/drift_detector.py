"""
CONFIT — Notification ML Drift Detector
======================================
Detects model performance degradation and data drift.
Triggers alerts when retraining is needed.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import numpy as np
from scipy import stats


@dataclass
class DriftAlert:
    """Alert for detected drift."""
    id: str
    model_version: str
    detected_at: datetime
    
    # Drift details
    drift_type: str  # 'performance', 'data', 'concept'
    severity: str  # 'low', 'medium', 'high', 'critical'
    
    # Metrics
    baseline_metric: float
    current_metric: float
    drift_percentage: float
    
    # Affected segments
    affected_personas: List[str] = field(default_factory=list)
    affected_recipient_types: List[str] = field(default_factory=list)
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Resolution
    status: str = "open"
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    retraining_triggered: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_version": self.model_version,
            "detected_at": self.detected_at.isoformat(),
            "drift_type": self.drift_type,
            "severity": self.severity,
            "baseline_metric": self.baseline_metric,
            "current_metric": self.current_metric,
            "drift_percentage": self.drift_percentage,
            "affected_personas": self.affected_personas,
            "affected_recipient_types": self.affected_recipient_types,
            "details": self.details,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "retraining_triggered": self.retraining_triggered,
        }


@dataclass
class DriftCheckResult:
    """Result of a drift check."""
    has_drift: bool
    alerts: List[DriftAlert] = field(default_factory=list)
    metrics_compared: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_drift": self.has_drift,
            "alerts": [a.to_dict() for a in self.alerts],
            "metrics_compared": {
                k: {"baseline": v[0], "current": v[1]}
                for k, v in self.metrics_compared.items()
            },
            "recommendation": self.recommendation,
        }


class DriftDetector:
    """
    Detects model drift and performance degradation.
    
    Types of drift detected:
    - Performance drift: Model accuracy degrades over time
    - Data drift: Input feature distribution changes
    - Concept drift: Relationship between features and target changes
    
    Usage:
        detector = DriftDetector()
        result = detector.check_performance_drift(
            baseline_metrics={...},
            current_metrics={...}
        )
    """
    
    # Thresholds for drift severity
    SEVERITY_THRESHOLDS = {
        "low": 0.05,      # 5% degradation
        "medium": 0.10,   # 10% degradation
        "high": 0.20,     # 20% degradation
        "critical": 0.30, # 30% degradation
    }
    
    def __init__(
        self,
        performance_threshold: float = 0.10,
        data_threshold: float = 0.15,
        window_days: int = 7,
        db_connection=None
    ):
        """
        Initialize drift detector.
        
        Args:
            performance_threshold: Threshold for performance drift (fraction)
            data_threshold: Threshold for data drift (KS statistic)
            window_days: Window size for drift detection
            db_connection: Database connection for persistence
        """
        self.performance_threshold = performance_threshold
        self.data_threshold = data_threshold
        self.window_days = window_days
        self.db = db_connection
        
        self._alerts: List[DriftAlert] = []
    
    def check_performance_drift(
        self,
        model_version: str,
        baseline_metrics: Dict[str, float],
        current_metrics: Dict[str, float],
        persona_metrics: Optional[Dict[str, Dict[str, float]]] = None
    ) -> DriftCheckResult:
        """
        Check for performance drift.
        
        Args:
            model_version: Model version to check
            baseline_metrics: Baseline metrics from training
            current_metrics: Current metrics from production
            persona_metrics: Metrics broken down by persona
            
        Returns:
            DriftCheckResult with any detected alerts
        """
        alerts = []
        metrics_compared = {}
        
        # Check overall metrics
        for metric_name in ["accuracy_top1", "accuracy_top3", "mae_hours"]:
            if metric_name in baseline_metrics and metric_name in current_metrics:
                baseline = baseline_metrics[metric_name]
                current = current_metrics[metric_name]
                metrics_compared[metric_name] = (baseline, current)
                
                # For MAE, higher is worse
                if metric_name == "mae_hours":
                    drift = (current - baseline) / baseline if baseline > 0 else 0
                else:
                    drift = (baseline - current) / baseline if baseline > 0 else 0
                
                if drift > self.performance_threshold:
                    severity = self._classify_severity(drift)
                    alert = DriftAlert(
                        id=f"perf_{model_version}_{metric_name}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                        model_version=model_version,
                        detected_at=datetime.utcnow(),
                        drift_type="performance",
                        severity=severity,
                        baseline_metric=baseline,
                        current_metric=current,
                        drift_percentage=drift * 100,
                        details={"metric": metric_name},
                    )
                    alerts.append(alert)
        
        # Check persona-level metrics
        if persona_metrics:
            for persona_id, metrics in persona_metrics.items():
                if "baseline" in metrics and "current" in metrics:
                    baseline = metrics["baseline"].get("open_rate", 0)
                    current = metrics["current"].get("open_rate", 0)
                    
                    if baseline > 0:
                        drift = (baseline - current) / baseline
                        
                        if drift > self.performance_threshold:
                            alert = DriftAlert(
                                id=f"perf_{model_version}_{persona_id}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                                model_version=model_version,
                                detected_at=datetime.utcnow(),
                                drift_type="performance",
                                severity=self._classify_severity(drift),
                                baseline_metric=baseline,
                                current_metric=current,
                                drift_percentage=drift * 100,
                                affected_personas=[persona_id],
                                details={"persona_id": persona_id},
                            )
                            alerts.append(alert)
        
        has_drift = len(alerts) > 0
        recommendation = None
        
        if has_drift:
            critical_alerts = [a for a in alerts if a.severity == "critical"]
            high_alerts = [a for a in alerts if a.severity == "high"]
            
            if critical_alerts:
                recommendation = "Immediate retraining required. Critical performance degradation detected."
            elif high_alerts:
                recommendation = "Schedule retraining within 24 hours. Significant performance degradation detected."
            else:
                recommendation = "Monitor closely and schedule retraining within 1 week."
        
        result = DriftCheckResult(
            has_drift=has_drift,
            alerts=alerts,
            metrics_compared=metrics_compared,
            recommendation=recommendation
        )
        
        # Persist alerts
        for alert in alerts:
            self._alerts.append(alert)
            if self.db:
                self._persist_alert(alert)
        
        return result
    
    def check_data_drift(
        self,
        model_version: str,
        baseline_features: np.ndarray,
        current_features: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> DriftCheckResult:
        """
        Check for data drift using KS test.
        
        Args:
            model_version: Model version to check
            baseline_features: Feature matrix from training data
            current_features: Feature matrix from recent production data
            feature_names: Names of features for reporting
            
        Returns:
            DriftCheckResult with any detected alerts
        """
        alerts = []
        metrics_compared = {}
        
        if baseline_features.shape[1] != current_features.shape[1]:
            return DriftCheckResult(
                has_drift=False,
                recommendation="Feature dimension mismatch. Cannot check drift."
            )
        
        n_features = baseline_features.shape[1]
        
        # Check each feature
        drifted_features = []
        for i in range(n_features):
            baseline_col = baseline_features[:, i]
            current_col = current_features[:, i]
            
            # KS test for distribution difference
            ks_stat, p_value = stats.ks_2samp(baseline_col, current_col)
            
            feature_name = feature_names[i] if feature_names and i < len(feature_names) else f"feature_{i}"
            metrics_compared[feature_name] = (float(ks_stat), float(p_value))
            
            if ks_stat > self.data_threshold:
                drifted_features.append(feature_name)
        
        if drifted_features:
            # Compute overall drift severity
            drift_ratio = len(drifted_features) / n_features
            severity = self._classify_severity(drift_ratio)
            
            alert = DriftAlert(
                id=f"data_{model_version}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                model_version=model_version,
                detected_at=datetime.utcnow(),
                drift_type="data",
                severity=severity,
                baseline_metric=0,
                current_metric=len(drifted_features),
                drift_percentage=drift_ratio * 100,
                details={
                    "drifted_features": drifted_features[:10],  # Top 10
                    "n_features_drifted": len(drifted_features),
                    "total_features": n_features,
                },
            )
            alerts.append(alert)
        
        has_drift = len(alerts) > 0
        recommendation = None
        
        if has_drift:
            if len(drifted_features) > n_features * 0.3:
                recommendation = "Significant data drift detected. Retraining recommended with recent data."
            else:
                recommendation = f"Data drift detected in {len(drifted_features)} features. Monitor and consider retraining."
        
        result = DriftCheckResult(
            has_drift=has_drift,
            alerts=alerts,
            metrics_compared=metrics_compared,
            recommendation=recommendation
        )
        
        for alert in alerts:
            self._alerts.append(alert)
            if self.db:
                self._persist_alert(alert)
        
        return result
    
    def check_engagement_pattern_shift(
        self,
        model_version: str,
        baseline_hourly_rates: List[float],
        current_hourly_rates: List[float],
        recipient_type: str
    ) -> DriftCheckResult:
        """
        Check for shifts in engagement patterns (concept drift).
        
        Args:
            model_version: Model version to check
            baseline_hourly_rates: Average hourly engagement rates at training
            current_hourly_rates: Current average hourly engagement rates
            recipient_type: 'customer' or 'owner'
            
        Returns:
            DriftCheckResult
        """
        alerts = []
        metrics_compared = {}
        
        baseline = np.array(baseline_hourly_rates)
        current = np.array(current_hourly_rates)
        
        # Check for peak hour shift
        baseline_peak = np.argmax(baseline)
        current_peak = np.argmax(current)
        
        peak_shift = abs(baseline_peak - current_peak)
        peak_shift = min(peak_shift, 24 - peak_shift)  # Handle wrap-around
        
        metrics_compared["peak_hour_shift"] = (float(baseline_peak), float(current_peak))
        
        if peak_shift > 3:  # More than 3 hours shift
            alert = DriftAlert(
                id=f"concept_{model_version}_peak_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                model_version=model_version,
                detected_at=datetime.utcnow(),
                drift_type="concept",
                severity="medium" if peak_shift <= 6 else "high",
                baseline_metric=float(baseline_peak),
                current_metric=float(current_peak),
                drift_percentage=float(peak_shift),
                affected_recipient_types=[recipient_type],
                details={
                    "shift_type": "peak_hour_shift",
                    "baseline_peak": int(baseline_peak),
                    "current_peak": int(current_peak),
                },
            )
            alerts.append(alert)
        
        # Check for overall pattern similarity
        correlation = np.corrcoef(baseline, current)[0, 1]
        metrics_compared["pattern_correlation"] = (1.0, float(correlation))
        
        if correlation < 0.5:
            alert = DriftAlert(
                id=f"concept_{model_version}_pattern_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                model_version=model_version,
                detected_at=datetime.utcnow(),
                drift_type="concept",
                severity="high" if correlation < 0.3 else "medium",
                baseline_metric=1.0,
                current_metric=float(correlation),
                drift_percentage=(1 - correlation) * 100,
                affected_recipient_types=[recipient_type],
                details={
                    "shift_type": "pattern_correlation",
                    "correlation": float(correlation),
                },
            )
            alerts.append(alert)
        
        has_drift = len(alerts) > 0
        recommendation = None
        
        if has_drift:
            recommendation = "Engagement patterns have shifted. Recalibrate model with recent engagement data."
        
        return DriftCheckResult(
            has_drift=has_drift,
            alerts=alerts,
            metrics_compared=metrics_compared,
            recommendation=recommendation
        )
    
    def get_active_alerts(
        self,
        model_version: Optional[str] = None,
        min_severity: str = "low"
    ) -> List[DriftAlert]:
        """
        Get active (unresolved) alerts.
        
        Args:
            model_version: Filter by model version
            min_severity: Minimum severity level
            
        Returns:
            List of active DriftAlert objects
        """
        severity_order = ["low", "medium", "high", "critical"]
        min_idx = severity_order.index(min_severity)
        
        alerts = [
            a for a in self._alerts
            if a.status == "open"
            and severity_order.index(a.severity) >= min_idx
        ]
        
        if model_version:
            alerts = [a for a in alerts if a.model_version == model_version]
        
        return sorted(alerts, key=lambda a: (severity_order.index(a.severity), a.detected_at), reverse=True)
    
    def resolve_alert(
        self,
        alert_id: str,
        resolution_notes: str,
        trigger_retraining: bool = False
    ) -> Optional[DriftAlert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of alert to resolve
            resolution_notes: Notes explaining resolution
            trigger_retraining: Whether retraining was triggered
            
        Returns:
            Updated DriftAlert or None if not found
        """
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = "resolved"
                alert.resolved_at = datetime.utcnow()
                alert.resolution_notes = resolution_notes
                alert.retraining_triggered = trigger_retraining
                
                if self.db:
                    self._update_alert_status(alert)
                
                return alert
        
        return None
    
    def _classify_severity(self, drift: float) -> str:
        """Classify drift severity based on magnitude."""
        drift_pct = abs(drift)
        
        if drift_pct >= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif drift_pct >= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif drift_pct >= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"
    
    def _persist_alert(self, alert: DriftAlert) -> None:
        """Persist alert to database."""
        if not self.db:
            return
        
        query = """
            INSERT INTO ml_model_drift (
                id, model_version, detected_at, drift_type, severity,
                baseline_metric, current_metric, drift_percentage,
                affected_personas, affected_recipient_types, details, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                alert.id,
                alert.model_version,
                alert.detected_at,
                alert.drift_type,
                alert.severity,
                alert.baseline_metric,
                alert.current_metric,
                alert.drift_percentage,
                alert.affected_personas,
                alert.affected_recipient_types,
                alert.details,
                alert.status
            ))
            self.db.commit()
    
    def _update_alert_status(self, alert: DriftAlert) -> None:
        """Update alert status in database."""
        if not self.db:
            return
        
        query = """
            UPDATE ml_model_drift
            SET status = %s, resolved_at = %s, resolution_notes = %s, retraining_triggered = %s
            WHERE id = %s
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                alert.status,
                alert.resolved_at,
                alert.resolution_notes,
                alert.retraining_triggered,
                alert.id
            ))
            self.db.commit()
