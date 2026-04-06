"""
CONFIT — Notification ML A/B Testing Integration
================================================
Integrates ML predictions with the A/B testing framework to enable
ML-optimized delivery timing experiments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import logging
import uuid

from .pipeline import NotificationMLPipeline
from .delivery_predictor import DeliveryPrediction
from .accuracy_tracker import AccuracyTracker, PredictionOutcome

logger = logging.getLogger(__name__)


@dataclass
class MLTestConfig:
    """Configuration for ML A/B test."""
    test_id: str
    name: str
    hypothesis: str
    recipient_type: str  # 'customer' or 'owner'
    
    # Traffic allocation
    traffic_percentage: int = 50  # % of recipients in ML treatment
    control_percentage: int = 50  # % in control (default timing)
    
    # Test duration
    duration_days: int = 14
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Success metrics
    primary_metric: str = "open_rate"  # 'open_rate', 'click_rate', 'conversion_rate', 'response_time'
    significance_threshold: float = 0.05  # p-value threshold
    
    # Timing configuration
    default_hour: int = 10  # Default hour for control group
    ml_confidence_threshold: float = 0.3  # Minimum confidence to use ML prediction
    
    status: str = "draft"  # 'draft', 'running', 'paused', 'completed', 'archived'


@dataclass
class MLTestVariant:
    """Variant configuration for ML A/B test."""
    variant_id: str
    variant_type: str  # 'control' or 'ml_treatment'
    name: str
    
    # For control
    default_hour: Optional[int] = None
    
    # For treatment
    use_ml_predictions: bool = False
    confidence_threshold: float = 0.3
    
    # Results
    sample_size: int = 0
    open_count: int = 0
    click_count: int = 0
    conversion_count: int = 0
    total_response_time_min: float = 0.0
    
    @property
    def open_rate(self) -> float:
        return self.open_count / self.sample_size if self.sample_size > 0 else 0.0
    
    @property
    def click_rate(self) -> float:
        return self.click_count / self.sample_size if self.sample_size > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return self.conversion_count / self.sample_size if self.sample_size > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        return self.total_response_time_min / self.sample_size if self.sample_size > 0 else 0.0


@dataclass
class MLTestResult:
    """Result of an ML A/B test."""
    test_id: str
    status: str
    
    # Variant results
    control: MLTestVariant
    treatment: MLTestVariant
    
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
    confidence_level: float = 0.0
    
    # Winner
    winner: Optional[str] = None  # 'control', 'treatment', or None (inconclusive)
    
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "status": self.status,
            "control": {
                "sample_size": self.control.sample_size,
                "open_rate": self.control.open_rate,
                "click_rate": self.control.click_rate,
                "conversion_rate": self.control.conversion_rate,
                "avg_response_time": self.control.avg_response_time,
            },
            "treatment": {
                "sample_size": self.treatment.sample_size,
                "open_rate": self.treatment.open_rate,
                "click_rate": self.treatment.click_rate,
                "conversion_rate": self.treatment.conversion_rate,
                "avg_response_time": self.treatment.avg_response_time,
            },
            "lift": {
                "open_rate": self.open_rate_lift,
                "click_rate": self.click_rate_lift,
                "conversion": self.conversion_lift,
                "response_time": self.response_time_improvement,
            },
            "significance": {
                "open_rate_p_value": self.open_rate_p_value,
                "click_rate_p_value": self.click_rate_p_value,
                "conversion_p_value": self.conversion_p_value,
                "is_significant": self.is_significant,
                "confidence_level": self.confidence_level,
            },
            "winner": self.winner,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class MLABTestIntegration:
    """
    Integrates ML predictions with A/B testing framework.
    
    Enables administrators to test ML-optimized delivery times against
    default timing strategies.
    
    Usage:
        integration = MLABTestIntegration(pipeline, db)
        
        # Create test
        test = integration.create_test(config)
        
        # Get delivery hour for recipient
        hour, variant = integration.get_delivery_hour(recipient_id, test_id)
        
        # Record outcome
        integration.record_outcome(recipient_id, notification_id, outcome)
        
        # Get results
        results = integration.get_test_results(test_id)
    """
    
    def __init__(
        self,
        pipeline: NotificationMLPipeline,
        db_connection=None
    ):
        """
        Initialize ML A/B test integration.
        
        Args:
            pipeline: Trained NotificationMLPipeline
            db_connection: Database connection for persistence
        """
        self.pipeline = pipeline
        self.db = db_connection
        self.accuracy_tracker = AccuracyTracker(db_connection=db_connection)
        
        # Active tests
        self._tests: Dict[str, MLTestConfig] = {}
        self._test_results: Dict[str, MLTestResult] = {}
        
        # Recipient assignments (recipient_id -> (test_id, variant_id))
        self._assignments: Dict[str, Tuple[str, str]] = {}
    
    def create_test(self, config: MLTestConfig) -> MLTestConfig:
        """
        Create a new ML A/B test.
        
        Args:
            config: Test configuration
            
        Returns:
            Created MLTestConfig with status set to 'draft'
        """
        config.status = "draft"
        config.test_id = config.test_id or f"ml_test_{uuid.uuid4().hex[:8]}"
        
        self._tests[config.test_id] = config
        
        # Initialize result structure
        control = MLTestVariant(
            variant_id=f"{config.test_id}_control",
            variant_type="control",
            name="Default Timing",
            default_hour=config.default_hour
        )
        
        treatment = MLTestVariant(
            variant_id=f"{config.test_id}_treatment",
            variant_type="ml_treatment",
            name="ML Optimized",
            use_ml_predictions=True,
            confidence_threshold=config.ml_confidence_threshold
        )
        
        self._test_results[config.test_id] = MLTestResult(
            test_id=config.test_id,
            status="draft",
            control=control,
            treatment=treatment
        )
        
        # Persist to database
        if self.db:
            self._persist_test(config)
        
        logger.info(f"Created ML A/B test: {config.test_id}")
        return config
    
    def start_test(self, test_id: str) -> MLTestConfig:
        """
        Start an ML A/B test.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Updated MLTestConfig with status 'running'
        """
        if test_id not in self._tests:
            raise ValueError(f"Test {test_id} not found")
        
        config = self._tests[test_id]
        config.status = "running"
        config.start_date = datetime.utcnow()
        config.end_date = config.start_date + timedelta(days=config.duration_days)
        
        self._test_results[test_id].status = "running"
        
        if self.db:
            self._update_test_status(config)
        
        logger.info(f"Started ML A/B test: {test_id}")
        return config
    
    def pause_test(self, test_id: str) -> MLTestConfig:
        """Pause a running test."""
        if test_id not in self._tests:
            raise ValueError(f"Test {test_id} not found")
        
        config = self._tests[test_id]
        config.status = "paused"
        self._test_results[test_id].status = "paused"
        
        if self.db:
            self._update_test_status(config)
        
        return config
    
    def complete_test(self, test_id: str) -> MLTestResult:
        """
        Complete a test and compute final results.
        
        Args:
            test_id: Test identifier
            
        Returns:
            MLTestResult with final metrics and significance
        """
        if test_id not in self._tests:
            raise ValueError(f"Test {test_id} not found")
        
        config = self._tests[test_id]
        config.status = "completed"
        
        result = self._test_results[test_id]
        result.status = "completed"
        result.completed_at = datetime.utcnow()
        
        # Compute lift metrics
        if result.control.sample_size > 0 and result.treatment.sample_size > 0:
            if result.control.open_rate > 0:
                result.open_rate_lift = (result.treatment.open_rate - result.control.open_rate) / result.control.open_rate
            
            if result.control.click_rate > 0:
                result.click_rate_lift = (result.treatment.click_rate - result.control.click_rate) / result.control.click_rate
            
            if result.control.conversion_rate > 0:
                result.conversion_lift = (result.treatment.conversion_rate - result.control.conversion_rate) / result.control.conversion_rate
            
            if result.control.avg_response_time > 0:
                result.response_time_improvement = result.control.avg_response_time - result.treatment.avg_response_time
        
        # Compute statistical significance
        result.is_significant, result.confidence_level = self._compute_significance(result)
        
        # Determine winner
        if result.is_significant:
            if result.open_rate_lift > 0 or result.click_rate_lift > 0:
                result.winner = "treatment"
            else:
                result.winner = "control"
        
        if self.db:
            self._update_test_status(config)
            self._persist_result(result)
        
        logger.info(f"Completed ML A/B test: {test_id}, winner: {result.winner}")
        return result
    
    def get_delivery_hour(
        self,
        recipient_id: str,
        recipient_type: str,
        test_id: Optional[str] = None,
        notification_type: Optional[str] = None
    ) -> Tuple[int, str, Optional[DeliveryPrediction]]:
        """
        Get the delivery hour for a recipient based on A/B test assignment.
        
        Args:
            recipient_id: Recipient identifier
            recipient_type: 'customer' or 'owner'
            test_id: Specific test ID, or None to use active test
            notification_type: Type of notification
            
        Returns:
            Tuple of (hour, variant_id, prediction)
        """
        # Find active test if not specified
        if test_id is None:
            test_id = self._get_active_test_for_recipient_type(recipient_type)
        
        if test_id is None or test_id not in self._tests:
            # No active test, use ML prediction if available
            if self.pipeline.is_trained:
                prediction, _ = self.pipeline.predict(
                    recipient_id=recipient_id,
                    recipient_type=recipient_type,
                    notification_type=notification_type
                )
                return prediction.recommended_hour, "ml_default", prediction
            return 10, "default", None  # Fallback to 10 AM
        
        config = self._tests[test_id]
        
        if config.status != "running":
            # Test not running, use default
            return config.default_hour, f"{test_id}_control", None
        
        # Assign recipient to variant
        variant_id = self._assign_recipient(recipient_id, test_id, config)
        
        if "treatment" in variant_id:
            # Use ML prediction
            try:
                prediction, _ = self.pipeline.predict(
                    recipient_id=recipient_id,
                    recipient_type=recipient_type,
                    notification_type=notification_type
                )
                
                # Check confidence threshold
                if prediction.confidence_score >= config.ml_confidence_threshold:
                    return prediction.recommended_hour, variant_id, prediction
                else:
                    # Low confidence, fall back to default
                    logger.info(f"Low confidence ({prediction.confidence_score}) for {recipient_id}, using default")
                    return config.default_hour, variant_id, prediction
            except Exception as e:
                logger.error(f"ML prediction failed for {recipient_id}: {e}")
                return config.default_hour, variant_id, None
        else:
            # Control group - use default timing
            return config.default_hour, variant_id, None
    
    def record_outcome(
        self,
        recipient_id: str,
        notification_id: str,
        test_id: str,
        variant_id: str,
        sent_at: datetime,
        was_opened: bool = False,
        was_clicked: bool = False,
        was_converted: bool = False,
        response_time_min: Optional[float] = None,
        prediction: Optional[DeliveryPrediction] = None
    ) -> None:
        """
        Record the outcome of a notification for A/B test tracking.
        
        Args:
            recipient_id: Recipient identifier
            notification_id: Notification identifier
            test_id: Test identifier
            variant_id: Variant identifier
            sent_at: When notification was sent
            was_opened: Whether notification was opened
            was_clicked: Whether notification was clicked
            was_converted: Whether conversion occurred
            response_time_min: Response time for owners
            prediction: The prediction used (if ML treatment)
        """
        if test_id not in self._test_results:
            return
        
        result = self._test_results[test_id]
        
        # Update variant metrics
        if "treatment" in variant_id:
            variant = result.treatment
        else:
            variant = result.control
        
        variant.sample_size += 1
        if was_opened:
            variant.open_count += 1
        if was_clicked:
            variant.click_count += 1
        if was_converted:
            variant.conversion_count += 1
        if response_time_min:
            variant.total_response_time_min += response_time_min
        
        # Record in accuracy tracker for ML treatment
        if "treatment" in variant_id and prediction:
            self.accuracy_tracker.record_outcome(
                prediction_id=prediction.recipient_id,  # Using recipient_id as prediction_id
                recipient_id=recipient_id,
                recipient_type="customer" if "customer" in test_id else "owner",
                persona_id=prediction.persona_id,
                predicted_hour=prediction.recommended_hour,
                confidence_score=prediction.confidence_score,
                model_version=prediction.model_version,
                sent_at=sent_at,
                actual_hour=sent_at.hour,
                was_ml_timed=True,
                was_opened=was_opened,
                was_clicked=was_clicked,
                was_converted=was_converted,
                response_time_min=response_time_min
            )
        
        # Persist to database
        if self.db:
            self._persist_outcome(test_id, variant_id, recipient_id, notification_id, {
                "sent_at": sent_at,
                "was_opened": was_opened,
                "was_clicked": was_clicked,
                "was_converted": was_converted,
                "response_time_min": response_time_min,
            })
    
    def get_test_results(self, test_id: str) -> MLTestResult:
        """
        Get current results for a test.
        
        Args:
            test_id: Test identifier
            
        Returns:
            MLTestResult with current metrics
        """
        if test_id not in self._test_results:
            raise ValueError(f"Test {test_id} not found")
        
        return self._test_results[test_id]
    
    def get_active_tests(self, recipient_type: Optional[str] = None) -> List[MLTestConfig]:
        """
        Get all active tests.
        
        Args:
            recipient_type: Filter by recipient type
            
        Returns:
            List of active MLTestConfig objects
        """
        tests = [
            t for t in self._tests.values()
            if t.status == "running"
        ]
        
        if recipient_type:
            tests = [t for t in tests if t.recipient_type == recipient_type]
        
        return tests
    
    def _assign_recipient(
        self,
        recipient_id: str,
        test_id: str,
        config: MLTestConfig
    ) -> str:
        """Assign recipient to a test variant."""
        # Check existing assignment
        if recipient_id in self._assignments:
            existing_test, existing_variant = self._assignments[recipient_id]
            if existing_test == test_id:
                return existing_variant
        
        # Deterministic assignment based on recipient_id hash
        import hashlib
        hash_input = f"{test_id}:{recipient_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Assign based on traffic percentage
        if (hash_value % 100) < config.traffic_percentage:
            variant_id = f"{test_id}_treatment"
        else:
            variant_id = f"{test_id}_control"
        
        self._assignments[recipient_id] = (test_id, variant_id)
        
        return variant_id
    
    def _get_active_test_for_recipient_type(self, recipient_type: str) -> Optional[str]:
        """Get active test for a recipient type."""
        for test_id, config in self._tests.items():
            if config.status == "running" and config.recipient_type == recipient_type:
                return test_id
        return None
    
    def _compute_significance(self, result: MLTestResult) -> Tuple[bool, float]:
        """Compute statistical significance using t-test."""
        from scipy import stats
        
        # Need minimum sample sizes
        if result.control.sample_size < 30 or result.treatment.sample_size < 30:
            return False, 0.0
        
        # Simulate individual outcomes for t-test
        control_opens = [1] * result.control.open_count + [0] * (result.control.sample_size - result.control.open_count)
        treatment_opens = [1] * result.treatment.open_count + [0] * (result.treatment.sample_size - result.treatment.open_count)
        
        _, p_value = stats.ttest_ind(control_opens, treatment_opens)
        
        is_significant = p_value < 0.05
        confidence = 1 - p_value
        
        return is_significant, confidence
    
    def _persist_test(self, config: MLTestConfig) -> None:
        """Persist test configuration to database."""
        if not self.db:
            return
        
        query = """
            INSERT INTO ab_tests (
                id, name, hypothesis, variable, status, segment,
                traffic_percentage, duration_days, start_date, end_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                config.test_id,
                config.name,
                config.hypothesis,
                "timing",
                config.status,
                f"all_{config.recipient_type}s",
                config.traffic_percentage,
                config.duration_days,
                config.start_date,
                config.end_date
            ))
            self.db.commit()
    
    def _update_test_status(self, config: MLTestConfig) -> None:
        """Update test status in database."""
        if not self.db:
            return
        
        query = """
            UPDATE ab_tests SET status = %s, updated_at = NOW()
            WHERE id = %s
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (config.status, config.test_id))
            self.db.commit()
    
    def _persist_result(self, result: MLTestResult) -> None:
        """Persist test result to database."""
        if not self.db:
            return
        
        query = """
            UPDATE ab_tests SET
                winner_variant_id = %s,
                confidence_level = %s,
                p_value = %s,
                is_significant = %s,
                status = 'completed',
                end_date = %s
            WHERE id = %s
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                f"{result.test_id}_{result.winner}" if result.winner else None,
                result.confidence_level,
                result.open_rate_p_value,
                result.is_significant,
                result.completed_at,
                result.test_id
            ))
            self.db.commit()
    
    def _persist_outcome(
        self,
        test_id: str,
        variant_id: str,
        recipient_id: str,
        notification_id: str,
        outcome: Dict[str, Any]
    ) -> None:
        """Persist outcome to database."""
        if not self.db:
            return
        
        query = """
            INSERT INTO notification_events (
                id, notification_id, recipient_id, recipient_type, channel,
                event_type, event_timestamp, payload, ab_test_id, variant_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        event_type = "read" if outcome.get("was_opened") else "sent"
        
        with self.db.cursor() as cur:
            cur.execute(query, (
                str(uuid.uuid4()),
                notification_id,
                recipient_id,
                "customer" if "customer" in test_id else "owner",
                "in_app",
                event_type,
                outcome.get("sent_at"),
                outcome,
                test_id,
                variant_id
            ))
            self.db.commit()


def create_ml_ab_variant_config() -> Dict[str, Any]:
    """
    Create variant configuration for ML A/B test.
    
    This can be used when creating an A/B test through the dashboard
    to add an "ML Predictions" variant option.
    """
    return {
        "variant_type": "ml_treatment",
        "name": "Use ML Predictions",
        "description": "Deliver notifications at ML-predicted optimal times for each recipient",
        "config": {
            "use_ml_predictions": True,
            "confidence_threshold": 0.3,
            "fallback_hour": 10,
        },
        "requires_model": True,
        "model_version": "latest",
    }
