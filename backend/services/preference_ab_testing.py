"""
CONFIT Backend - Preference A/B Testing Framework
=================================================
A/B testing infrastructure for validating preference recommendations
with statistical significance calculation.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import random
import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TestSegment(str, Enum):
    ALL_CUSTOMERS = "all_customers"
    ALL_OWNERS = "all_owners"
    COHORT = "cohort"
    CUSTOM = "custom"


class WinnerGroup(str, Enum):
    CONTROL = "control"
    TREATMENT = "treatment"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ABTestConfig:
    """A/B test configuration."""
    test_id: str
    test_name: str
    hypothesis: str
    recommendation_type: str
    segment_type: TestSegment
    segment_definition: Dict[str, Any]
    duration_days: int = 14
    traffic_percentage: int = 50
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: TestStatus = TestStatus.DRAFT
    
    # Suggested preference changes for treatment group
    treatment_changes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestAssignment:
    """User assignment to test group."""
    recipient_id: str
    recipient_type: str
    test_id: str
    test_group: str  # 'control' or 'treatment'
    assigned_at: datetime
    recommendation_id: Optional[str] = None


@dataclass
class TestResult:
    """A/B test result with statistical analysis."""
    test_id: str
    test_name: str
    status: TestStatus
    
    # Sample sizes
    control_sample_size: int
    treatment_sample_size: int
    
    # Control metrics
    control_open_rate: float
    control_click_rate: float
    control_engagement_score: float
    control_unsubscribe_rate: float
    control_response_time_hours: Optional[float] = None
    control_satisfaction: Optional[float] = None
    
    # Treatment metrics
    treatment_open_rate: float
    treatment_click_rate: float
    treatment_engagement_score: float
    treatment_unsubscribe_rate: float
    treatment_response_time_hours: Optional[float] = None
    treatment_satisfaction: Optional[float] = None
    
    # Statistical results
    open_rate_p_value: Optional[float] = None
    open_rate_effect_size: Optional[float] = None
    click_rate_p_value: Optional[float] = None
    click_rate_effect_size: Optional[float] = None
    engagement_p_value: Optional[float] = None
    engagement_effect_size: Optional[float] = None
    
    # Conclusion
    winner_group: Optional[WinnerGroup] = None
    confidence_level: float = 0.95
    is_significant: bool = False
    should_rollout: bool = False
    rollout_recommendation: Optional[str] = None


class PreferenceABTestingService:
    """
    A/B testing service for preference recommendations.
    
    Provides:
    - Test creation and management
    - User assignment to control/treatment groups
    - Statistical analysis of results
    - Rollout recommendations
    """
    
    MIN_SAMPLE_SIZE = 100  # Minimum users per group
    SIGNIFICANCE_LEVEL = 0.05  # 5% significance level
    MIN_EFFECT_SIZE = 0.2  # Small effect (Cohen's d)
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # -------------------------------------------------------------------------
    # TEST MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def create_test(
        self,
        config: ABTestConfig,
    ) -> str:
        """Create a new A/B test."""
        
        test_id = f"pref-ab-{int(datetime.utcnow().timestamp() * 1000)}"
        
        query = text("""
            INSERT INTO preference_ab_test_results (
                test_id, test_name, hypothesis, recommendation_type,
                segment_type, segment_definition, duration_days,
                start_date, end_date, status
            ) VALUES (
                :test_id, :test_name, :hypothesis, :recommendation_type,
                :segment_type, :segment_definition, :duration_days,
                :start_date, :end_date, 'draft'
            )
        """)
        
        await self.db.execute(query, {
            "test_id": test_id,
            "test_name": config.test_name,
            "hypothesis": config.hypothesis,
            "recommendation_type": config.recommendation_type,
            "segment_type": config.segment_type.value,
            "segment_definition": json.dumps(config.segment_definition),
            "duration_days": config.duration_days,
            "start_date": config.start_date,
            "end_date": config.end_date,
        })
        
        # Store treatment changes separately (could be in a config table)
        # For now, we'll track this via the recommendations table
        
        await self.db.commit()
        
        return test_id
    
    async def start_test(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Start an A/B test - assign users and begin tracking."""
        
        # Get test config
        test_query = text("""
            SELECT * FROM preference_ab_test_results WHERE test_id = :test_id
        """)
        
        result = await self.db.execute(test_query, {"test_id": test_id})
        test_row = result.fetchone()
        
        if not test_row:
            return {"success": False, "error": "Test not found"}
        
        if test_row.status != "draft":
            return {"success": False, "error": "Test is not in draft status"}
        
        # Get eligible users based on segment
        segment_type = test_row.segment_type
        segment_def = test_row.segment_definition
        
        eligible_users = await self._get_eligible_users(
            TestSegment(segment_type), segment_def
        )
        
        if len(eligible_users) < self.MIN_SAMPLE_SIZE * 2:
            return {
                "success": False,
                "error": f"Insufficient users ({len(eligible_users)}) for test. Need at least {self.MIN_SAMPLE_SIZE * 2}"
            }
        
        # Random assignment
        random.shuffle(eligible_users)
        
        split_point = len(eligible_users) // 2
        control_users = eligible_users[:split_point]
        treatment_users = eligible_users[split_point:]
        
        # Assign users to groups
        for user in control_users:
            await self._assign_user_to_test(
                user["recipient_id"],
                user["recipient_type"],
                test_id,
                "control",
            )
        
        for user in treatment_users:
            await self._assign_user_to_test(
                user["recipient_id"],
                user["recipient_type"],
                test_id,
                "treatment",
            )
        
        # Update test status
        await self.db.execute(
            text("""
                UPDATE preference_ab_test_results
                SET status = 'running', start_date = :start_date,
                    control_sample_size = :control_size,
                    treatment_sample_size = :treatment_size
                WHERE test_id = :test_id
            """),
            {
                "test_id": test_id,
                "start_date": datetime.utcnow(),
                "control_size": len(control_users),
                "treatment_size": len(treatment_users),
            },
        )
        
        await self.db.commit()
        
        return {
            "success": True,
            "test_id": test_id,
            "control_group_size": len(control_users),
            "treatment_group_size": len(treatment_users),
            "started_at": datetime.utcnow().isoformat(),
        }
    
    async def pause_test(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Pause a running test."""
        
        result = await self.db.execute(
            text("""
                UPDATE preference_ab_test_results
                SET status = 'paused'
                WHERE test_id = :test_id AND status = 'running'
            """),
            {"test_id": test_id},
        )
        
        if result.rowcount == 0:
            return {"success": False, "error": "Test not found or not running"}
        
        await self.db.commit()
        
        return {"success": True, "status": "paused"}
    
    async def complete_test(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Complete a test and calculate final results."""
        
        # Get test info
        test_result = await self.db.execute(
            text("SELECT * FROM preference_ab_test_results WHERE test_id = :test_id"),
            {"test_id": test_id},
        )
        test_row = test_result.fetchone()
        
        if not test_row:
            return {"success": False, "error": "Test not found"}
        
        # Calculate results
        results = await self._calculate_test_results(test_id)
        
        # Update test record
        await self.db.execute(
            text("""
                UPDATE preference_ab_test_results
                SET 
                    status = 'completed',
                    end_date = :end_date,
                    control_open_rate = :control_open_rate,
                    control_click_rate = :control_click_rate,
                    control_engagement_score = :control_engagement_score,
                    control_unsubscribe_rate = :control_unsubscribe_rate,
                    treatment_open_rate = :treatment_open_rate,
                    treatment_click_rate = :treatment_click_rate,
                    treatment_engagement_score = :treatment_engagement_score,
                    treatment_unsubscribe_rate = :treatment_unsubscribe_rate,
                    open_rate_p_value = :open_rate_p_value,
                    open_rate_effect_size = :open_rate_effect_size,
                    click_rate_p_value = :click_rate_p_value,
                    click_rate_effect_size = :click_rate_effect_size,
                    engagement_p_value = :engagement_p_value,
                    engagement_effect_size = :engagement_effect_size,
                    winner_group = :winner_group,
                    is_significant = :is_significant,
                    should_rollout = :should_rollout,
                    rollout_recommendation = :rollout_recommendation
                WHERE test_id = :test_id
            """),
            {
                "test_id": test_id,
                "end_date": datetime.utcnow(),
                **results,
            },
        )
        
        await self.db.commit()
        
        return {
            "success": True,
            "test_id": test_id,
            "results": results,
        }
    
    async def get_test_results(
        self,
        test_id: str,
    ) -> Optional[TestResult]:
        """Get results for a test."""
        
        result = await self.db.execute(
            text("SELECT * FROM preference_ab_test_results WHERE test_id = :test_id"),
            {"test_id": test_id},
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        return TestResult(
            test_id=row.test_id,
            test_name=row.test_name,
            status=TestStatus(row.status) if row.status else TestStatus.DRAFT,
            control_sample_size=row.control_sample_size or 0,
            treatment_sample_size=row.treatment_sample_size or 0,
            control_open_rate=row.control_open_rate or 0,
            control_click_rate=row.control_click_rate or 0,
            control_engagement_score=row.control_engagement_score or 0,
            control_unsubscribe_rate=row.control_unsubscribe_rate or 0,
            treatment_open_rate=row.treatment_open_rate or 0,
            treatment_click_rate=row.treatment_click_rate or 0,
            treatment_engagement_score=row.treatment_engagement_score or 0,
            treatment_unsubscribe_rate=row.treatment_unsubscribe_rate or 0,
            open_rate_p_value=row.open_rate_p_value,
            open_rate_effect_size=row.open_rate_effect_size,
            click_rate_p_value=row.click_rate_p_value,
            click_rate_effect_size=row.click_rate_effect_size,
            engagement_p_value=row.engagement_p_value,
            engagement_effect_size=row.engagement_effect_size,
            winner_group=WinnerGroup(row.winner_group) if row.winner_group else None,
            is_significant=row.is_significant or False,
            should_rollout=row.should_rollout or False,
            rollout_recommendation=row.rollout_recommendation,
        )
    
    async def list_tests(
        self,
        status: Optional[TestStatus] = None,
        limit: int = 50,
    ) -> List[TestResult]:
        """List all tests with optional status filter."""
        
        query = """
            SELECT * FROM preference_ab_test_results
            WHERE (:status IS NULL OR status = :status)
            ORDER BY created_at DESC
            LIMIT :limit
        """
        
        result = await self.db.execute(
            text(query),
            {"status": status.value if status else None, "limit": limit},
        )
        rows = result.fetchall()
        
        return [
            TestResult(
                test_id=row.test_id,
                test_name=row.test_name,
                status=TestStatus(row.status) if row.status else TestStatus.DRAFT,
                control_sample_size=row.control_sample_size or 0,
                treatment_sample_size=row.treatment_sample_size or 0,
                control_open_rate=row.control_open_rate or 0,
                control_click_rate=row.control_click_rate or 0,
                control_engagement_score=row.control_engagement_score or 0,
                control_unsubscribe_rate=row.control_unsubscribe_rate or 0,
                treatment_open_rate=row.treatment_open_rate or 0,
                treatment_click_rate=row.treatment_click_rate or 0,
                treatment_engagement_score=row.treatment_engagement_score or 0,
                treatment_unsubscribe_rate=row.treatment_unsubscribe_rate or 0,
                winner_group=WinnerGroup(row.winner_group) if row.winner_group else None,
                is_significant=row.is_significant or False,
                should_rollout=row.should_rollout or False,
            )
            for row in rows
        ]
    
    # -------------------------------------------------------------------------
    # USER ASSIGNMENT
    # -------------------------------------------------------------------------
    
    async def get_user_test_assignment(
        self,
        recipient_id: str,
        recipient_type: str,
    ) -> Optional[TestAssignment]:
        """Get the test assignment for a user."""
        
        result = await self.db.execute(
            text("""
                SELECT 
                    pr.recipient_id,
                    pr.recipient_type,
                    pr.ab_test_id,
                    pr.test_group,
                    pr.created_at,
                    pr.id AS recommendation_id
                FROM preference_recommendations pr
                WHERE pr.recipient_id = :recipient_id
                  AND pr.recipient_type = :recipient_type
                  AND pr.ab_test_id IS NOT NULL
                  AND pr.status IN ('pending', 'accepted', 'rejected')
                ORDER BY pr.created_at DESC
                LIMIT 1
            """),
            {"recipient_id": recipient_id, "recipient_type": recipient_type},
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        return TestAssignment(
            recipient_id=row.recipient_id,
            recipient_type=row.recipient_type,
            test_id=row.ab_test_id,
            test_group=row.test_group,
            assigned_at=row.created_at,
            recommendation_id=str(row.recommendation_id),
        )
    
    async def _assign_user_to_test(
        self,
        recipient_id: str,
        recipient_type: str,
        test_id: str,
        test_group: str,
    ) -> None:
        """Assign a user to a test group and create appropriate recommendation."""
        
        # For treatment group, create a recommendation
        if test_group == "treatment":
            # Get test details to determine what recommendation to create
            test_result = await self.db.execute(
                text("SELECT recommendation_type, hypothesis FROM preference_ab_test_results WHERE test_id = :test_id"),
                {"test_id": test_id},
            )
            test_row = test_result.fetchone()
            
            if test_row:
                # Create recommendation for treatment group
                await self.db.execute(
                    text("""
                        INSERT INTO preference_recommendations (
                            recipient_id, recipient_type, recommendation_type,
                            title, description, suggested_changes, expected_outcome,
                            expected_metrics, ab_test_id, test_group, status
                        ) VALUES (
                            :recipient_id, :recipient_type, :recommendation_type,
                            :title, :description, :suggested_changes, :expected_outcome,
                            :expected_metrics, :ab_test_id, :treatment, 'pending'
                        )
                    """),
                    {
                        "recipient_id": recipient_id,
                        "recipient_type": recipient_type,
                        "recommendation_type": test_row.recommendation_type,
                        "title": "A/B Test Recommendation",
                        "description": test_row.hypothesis,
                        "suggested_changes": "{}",  # Would be specific to test
                        "expected_outcome": "Testing improved preferences",
                        "expected_metrics": "{}",
                        "ab_test_id": test_id,
                    },
                )
        else:
            # Control group - just track assignment without recommendation
            await self.db.execute(
                text("""
                    INSERT INTO preference_recommendations (
                        recipient_id, recipient_type, recommendation_type,
                        title, description, suggested_changes, expected_outcome,
                        expected_metrics, ab_test_id, test_group, status
                    ) VALUES (
                        :recipient_id, :recipient_type, 'engagement_improvement',
                        'Control Group', 'You are in the control group for this test',
                        '{}', 'No changes', '{}', :ab_test_id, 'control', 'pending'
                    )
                """),
                {
                    "recipient_id": recipient_id,
                    "recipient_type": recipient_type,
                    "ab_test_id": test_id,
                },
            )
    
    async def _get_eligible_users(
        self,
        segment_type: TestSegment,
        segment_definition: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get users eligible for the test based on segment."""
        
        if segment_type == TestSegment.ALL_CUSTOMERS:
            query = text("""
                SELECT DISTINCT recipient_id, recipient_type
                FROM notification_preferences
                WHERE recipient_type = 'customer'
            """)
        elif segment_type == TestSegment.ALL_OWNERS:
            query = text("""
                SELECT DISTINCT recipient_id, recipient_type
                FROM notification_preferences
                WHERE recipient_type = 'owner'
            """)
        elif segment_type == TestSegment.COHORT:
            cohort_slug = segment_definition.get("cohort_slug")
            query = text("""
                SELECT ucm.recipient_id, ucm.recipient_type
                FROM user_cohort_membership ucm
                JOIN user_cohorts uc ON uc.id = ucm.cohort_id
                WHERE uc.cohort_slug = :cohort_slug
                  AND ucm.exited_at IS NULL
            """)
        else:
            # Custom segment - would need specific query logic
            query = text("""
                SELECT DISTINCT recipient_id, recipient_type
                FROM notification_preferences
                LIMIT 1000
            """)
        
        result = await self.db.execute(
            query,
            {"cohort_slug": segment_definition.get("cohort_slug")} if segment_type == TestSegment.COHORT else {},
        )
        
        return [
            {"recipient_id": row.recipient_id, "recipient_type": row.recipient_type}
            for row in result.fetchall()
        ]
    
    # -------------------------------------------------------------------------
    # STATISTICAL ANALYSIS
    # -------------------------------------------------------------------------
    
    async def _calculate_test_results(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Calculate test results with statistical analysis."""
        
        # Get metrics for control group
        control_metrics = await self._get_group_metrics(test_id, "control")
        
        # Get metrics for treatment group
        treatment_metrics = await self._get_group_metrics(test_id, "treatment")
        
        # Calculate p-values using two-proportion z-test
        open_rate_p = self._calculate_p_value(
            control_metrics["open_rate"], control_metrics["sample_size"],
            treatment_metrics["open_rate"], treatment_metrics["sample_size"],
        )
        
        click_rate_p = self._calculate_p_value(
            control_metrics["click_rate"], control_metrics["sample_size"],
            treatment_metrics["click_rate"], treatment_metrics["sample_size"],
        )
        
        engagement_p = self._calculate_p_value(
            control_metrics["engagement_score"] / 100, control_metrics["sample_size"],
            treatment_metrics["engagement_score"] / 100, treatment_metrics["sample_size"],
        )
        
        # Calculate effect sizes (Cohen's d)
        open_effect = self._calculate_cohens_d(
            control_metrics["open_rate"], 0.15,  # Approximate std
            treatment_metrics["open_rate"], 0.15,
            control_metrics["sample_size"],
            treatment_metrics["sample_size"],
        )
        
        engagement_effect = self._calculate_cohens_d(
            control_metrics["engagement_score"], 15,
            treatment_metrics["engagement_score"], 15,
            control_metrics["sample_size"],
            treatment_metrics["sample_size"],
        )
        
        # Determine winner
        is_significant = any([
            open_rate_p and open_rate_p < self.SIGNIFICANCE_LEVEL,
            engagement_p and engagement_p < self.SIGNIFICANCE_LEVEL,
        ])
        
        winner = self._determine_winner(
            control_metrics, treatment_metrics, is_significant
        )
        
        should_rollout = (
            is_significant and 
            winner == WinnerGroup.TREATMENT and
            treatment_metrics["engagement_score"] > control_metrics["engagement_score"] * 1.1
        )
        
        return {
            "control_open_rate": control_metrics["open_rate"],
            "control_click_rate": control_metrics["click_rate"],
            "control_engagement_score": control_metrics["engagement_score"],
            "control_unsubscribe_rate": control_metrics["unsubscribe_rate"],
            "treatment_open_rate": treatment_metrics["open_rate"],
            "treatment_click_rate": treatment_metrics["click_rate"],
            "treatment_engagement_score": treatment_metrics["engagement_score"],
            "treatment_unsubscribe_rate": treatment_metrics["unsubscribe_rate"],
            "open_rate_p_value": open_rate_p,
            "open_rate_effect_size": open_effect,
            "click_rate_p_value": click_rate_p,
            "click_rate_effect_size": 0,  # Placeholder
            "engagement_p_value": engagement_p,
            "engagement_effect_size": engagement_effect,
            "winner_group": winner.value if winner else None,
            "is_significant": is_significant,
            "should_rollout": should_rollout,
            "rollout_recommendation": self._generate_rollout_recommendation(
                winner, is_significant, treatment_metrics, control_metrics
            ),
        }
    
    async def _get_group_metrics(
        self,
        test_id: str,
        group: str,
    ) -> Dict[str, Any]:
        """Get aggregated metrics for a test group."""
        
        query = text("""
            WITH group_users AS (
                SELECT recipient_id, recipient_type
                FROM preference_recommendations
                WHERE ab_test_id = :test_id AND test_group = :group
            ),
            user_metrics AS (
                SELECT 
                    gu.recipient_id,
                    AVG(em.overall_open_rate) AS open_rate,
                    AVG(em.overall_click_rate) AS click_rate,
                    AVG(em.engagement_score) AS engagement_score,
                    SUM(em.unsubscribe_events) AS unsubscribes,
                    COUNT(*) AS period_count
                FROM group_users gu
                JOIN engagement_metrics em ON em.recipient_id = gu.recipient_id
                    AND em.recipient_type = gu.recipient_type
                WHERE em.period_start >= (
                    SELECT start_date FROM preference_ab_test_results WHERE test_id = :test_id
                )
                GROUP BY gu.recipient_id
            )
            SELECT 
                COUNT(*) AS sample_size,
                AVG(open_rate) AS avg_open_rate,
                AVG(click_rate) AS avg_click_rate,
                AVG(engagement_score) AS avg_engagement_score,
                SUM(unsubscribes)::FLOAT / COUNT(*) AS unsubscribe_rate
            FROM user_metrics
        """)
        
        result = await self.db.execute(query, {
            "test_id": test_id,
            "group": group,
        })
        row = result.fetchone()
        
        if not row or row.sample_size == 0:
            return {
                "sample_size": 0,
                "open_rate": 0,
                "click_rate": 0,
                "engagement_score": 0,
                "unsubscribe_rate": 0,
            }
        
        return {
            "sample_size": row.sample_size,
            "open_rate": float(row.avg_open_rate or 0),
            "click_rate": float(row.avg_click_rate or 0),
            "engagement_score": float(row.avg_engagement_score or 0),
            "unsubscribe_rate": float(row.unsubscribe_rate or 0),
        }
    
    def _calculate_p_value(
        self,
        p1: float,
        n1: int,
        p2: float,
        n2: int,
    ) -> Optional[float]:
        """
        Calculate two-proportion z-test p-value.
        
        Uses normal approximation for large samples.
        """
        
        if n1 == 0 or n2 == 0:
            return None
        
        # Pooled proportion
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        
        if p_pooled == 0 or p_pooled == 1:
            return None
        
        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
        
        if se == 0:
            return None
        
        # Z-score
        z = (p2 - p1) / se
        
        # Two-tailed p-value using normal CDF approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        
        return p_value
    
    def _normal_cdf(self, x: float) -> float:
        """Standard normal CDF approximation."""
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
    
    def _calculate_cohens_d(
        self,
        m1: float,
        s1: float,
        m2: float,
        s2: float,
        n1: int,
        n2: int,
    ) -> float:
        """Calculate Cohen's d effect size."""
        
        # Pooled standard deviation
        pooled_std = math.sqrt(
            ((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)
        )
        
        if pooled_std == 0:
            return 0
        
        return (m2 - m1) / pooled_std
    
    def _determine_winner(
        self,
        control: Dict[str, Any],
        treatment: Dict[str, Any],
        is_significant: bool,
    ) -> WinnerGroup:
        """Determine the winning group."""
        
        if not is_significant:
            return WinnerGroup.INCONCLUSIVE
        
        # Compare engagement scores
        if treatment["engagement_score"] > control["engagement_score"] * 1.05:
            return WinnerGroup.TREATMENT
        elif control["engagement_score"] > treatment["engagement_score"] * 1.05:
            return WinnerGroup.CONTROL
        else:
            return WinnerGroup.INCONCLUSIVE
    
    def _generate_rollout_recommendation(
        self,
        winner: Optional[WinnerGroup],
        is_significant: bool,
        treatment: Dict[str, Any],
        control: Dict[str, Any],
    ) -> Optional[str]:
        """Generate rollout recommendation text."""
        
        if not is_significant:
            return "Results are not statistically significant. Consider extending the test duration."
        
        if winner == WinnerGroup.TREATMENT:
            improvement = ((treatment["engagement_score"] - control["engagement_score"]) 
                          / control["engagement_score"] * 100) if control["engagement_score"] > 0 else 0
            return (
                f"Treatment group shows significant improvement. "
                f"Recommend rolling out preference changes to all users. "
                f"Expected engagement improvement: {improvement:.1f}%"
            )
        elif winner == WinnerGroup.CONTROL:
            return (
                "Control group performs better. Do not roll out the tested preference changes. "
                "Consider investigating why current preferences work better."
            )
        else:
            return "Results are inconclusive. No clear winner detected."
    
    # -------------------------------------------------------------------------
    # INTERIM ANALYSIS
    # -------------------------------------------------------------------------
    
    async def get_interim_results(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Get interim results for a running test (for monitoring)."""
        
        test_result = await self.db.execute(
            text("SELECT status, start_date FROM preference_ab_test_results WHERE test_id = :test_id"),
            {"test_id": test_id},
        )
        test_row = test_result.fetchone()
        
        if not test_row:
            return {"error": "Test not found"}
        
        # Get current metrics
        control_metrics = await self._get_group_metrics(test_id, "control")
        treatment_metrics = await self._get_group_metrics(test_id, "treatment")
        
        # Calculate early p-values (for monitoring, not decision-making)
        open_rate_p = self._calculate_p_value(
            control_metrics["open_rate"], control_metrics["sample_size"],
            treatment_metrics["open_rate"], treatment_metrics["sample_size"],
        )
        
        days_running = 0
        if test_row.start_date:
            days_running = (datetime.utcnow() - test_row.start_date).days
        
        return {
            "test_id": test_id,
            "status": test_row.status,
            "days_running": days_running,
            "control": {
                "sample_size": control_metrics["sample_size"],
                "open_rate": control_metrics["open_rate"],
                "engagement_score": control_metrics["engagement_score"],
            },
            "treatment": {
                "sample_size": treatment_metrics["sample_size"],
                "open_rate": treatment_metrics["open_rate"],
                "engagement_score": treatment_metrics["engagement_score"],
            },
            "early_p_value": open_rate_p,
            "note": "Interim results are for monitoring only. Do not make decisions before test completion.",
        }
    
    # -------------------------------------------------------------------------
    # ROLLOUT
    # -------------------------------------------------------------------------
    
    async def rollout_winning_preference(
        self,
        test_id: str,
    ) -> Dict[str, Any]:
        """Roll out the winning preference to all eligible users."""
        
        # Get test results
        test_result = await self.get_test_results(test_id)
        
        if not test_result:
            return {"success": False, "error": "Test not found"}
        
        if test_result.status != TestStatus.COMPLETED:
            return {"success": False, "error": "Test is not completed"}
        
        if not test_result.should_rollout:
            return {"success": False, "error": "Test results do not recommend rollout"}
        
        # Get the treatment preference changes
        # This would need to be stored during test creation
        # For now, we'll create recommendations for all eligible users
        
        # Get all users not in the test
        eligible_users = await self._get_eligible_users(
            TestSegment.ALL_CUSTOMERS,  # Would be from test config
            {},
        )
        
        # Exclude users already in test
        test_users = await self.db.execute(
            text("""
                SELECT DISTINCT recipient_id 
                FROM preference_recommendations 
                WHERE ab_test_id = :test_id
            """),
            {"test_id": test_id},
        )
        test_user_ids = {row.recipient_id for row in test_users.fetchall()}
        
        rollout_users = [
            u for u in eligible_users
            if u["recipient_id"] not in test_user_ids
        ]
        
        # Create recommendations for rollout users
        for user in rollout_users[:1000]:  # Limit for safety
            await self.db.execute(
                text("""
                    INSERT INTO preference_recommendations (
                        recipient_id, recipient_type, recommendation_type,
                        title, description, suggested_changes, expected_outcome,
                        expected_metrics, trigger_source, status
                    ) VALUES (
                        :recipient_id, :recipient_type, 'frequency_optimization',
                        'Recommended Preference Update',
                        'Based on A/B test results, this preference configuration improves engagement.',
                        '{}', 'Improved engagement based on validated test results',
                        '{}', 'ab_test_rollout', 'pending'
                    )
                """),
                {
                    "recipient_id": user["recipient_id"],
                    "recipient_type": user["recipient_type"],
                },
            )
        
        await self.db.commit()
        
        return {
            "success": True,
            "rolled_out_to": len(rollout_users[:1000]),
            "test_id": test_id,
        }
