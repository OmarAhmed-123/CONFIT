"""
CONFIT Backend - Preference Analytics Scheduled Jobs
=====================================================
Scheduled tasks for batch recommendation generation, engagement metric
aggregation, cohort updates, and A/B test monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.preference_analytics import (
    PreferenceAnalyticsService,
    RecipientType,
    Recommendation,
)
from services.preference_ab_testing import (
    PreferenceABTestingService,
    TestStatus,
)


logger = logging.getLogger(__name__)


class JobType(str, Enum):
    RECOMMENDATION_GENERATION = "recommendation_generation"
    ENGAGEMENT_AGGREGATION = "engagement_aggregation"
    COHORT_UPDATE = "cohort_update"
    AB_TEST_MONITORING = "ab_test_monitoring"
    FATIGUE_DETECTION = "fatigue_detection"
    PREFERENCE_DISTRIBUTION_SNAPSHOT = "preference_distribution_snapshot"
    BUSINESS_OUTCOME_AGGREGATION = "business_outcome_aggregation"


@dataclass
class JobResult:
    job_type: JobType
    started_at: datetime
    completed_at: Optional[datetime]
    success: bool
    records_processed: int
    records_failed: int
    details: Dict[str, Any]
    error: Optional[str] = None


class PreferenceScheduledJobs:
    """
    Scheduled jobs for preference analytics system.
    
    Jobs can be run individually or scheduled via APScheduler, Celery, or cron.
    """
    
    # Configuration
    BATCH_SIZE = 100  # Users per batch
    MAX_RECOMMENDATIONS_PER_USER = 5
    RECOMMENDATION_EXPIRY_DAYS = 30
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = PreferenceAnalyticsService(db)
        self.ab_test_service = PreferenceABTestingService(db)
    
    async def run_job(self, job_type: JobType, **kwargs) -> JobResult:
        """Run a specific job by type."""
        
        job_handlers = {
            JobType.RECOMMENDATION_GENERATION: self.generate_recommendations_batch,
            JobType.ENGAGEMENT_AGGREGATION: self.aggregate_engagement_metrics,
            JobType.COHORT_UPDATE: self.update_user_cohorts,
            JobType.AB_TEST_MONITORING: self.monitor_ab_tests,
            JobType.FATIGUE_DETECTION: self.detect_fatigue_users,
            JobType.PREFERENCE_DISTRIBUTION_SNAPSHOT: self.snapshot_preference_distribution,
            JobType.BUSINESS_OUTCOME_AGGREGATION: self.aggregate_business_outcomes,
        }
        
        handler = job_handlers.get(job_type)
        if not handler:
            return JobResult(
                job_type=job_type,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=0,
                records_failed=0,
                details={},
                error=f"Unknown job type: {job_type}",
            )
        
        return await handler(**kwargs)
    
    # -------------------------------------------------------------------------
    # RECOMMENDATION GENERATION
    # -------------------------------------------------------------------------
    
    async def generate_recommendations_batch(
        self,
        recipient_type: Optional[str] = None,
        limit: int = 1000,
        force_refresh: bool = False,
    ) -> JobResult:
        """
        Generate recommendations for users in batches.
        
        This job:
        1. Finds users without recent recommendations
        2. Calculates their engagement metrics
        3. Generates personalized recommendations
        4. Stores recommendations for later retrieval
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        records_failed = 0
        details = {
            "users_processed": 0,
            "recommendations_created": 0,
            "recommendations_skipped": 0,
        }
        
        try:
            # Find users needing recommendations
            users_query = text("""
                SELECT DISTINCT 
                    np.recipient_id,
                    np.recipient_type
                FROM notification_preferences np
                LEFT JOIN preference_recommendations pr 
                    ON pr.recipient_id = np.recipient_id 
                    AND pr.recipient_type = np.recipient_type
                    AND pr.status = 'pending'
                    AND pr.created_at >= :recent_date
                WHERE pr.id IS NULL
                  AND (:recipient_type IS NULL OR np.recipient_type = :recipient_type)
                LIMIT :limit
            """)
            
            result = await self.db.execute(users_query, {
                "recipient_type": recipient_type,
                "recent_date": datetime.utcnow() - timedelta(days=self.RECOMMENDATION_EXPIRY_DAYS),
                "limit": limit,
            })
            users = result.fetchall()
            
            logger.info(f"Found {len(users)} users needing recommendations")
            
            # Process users in batches
            for i in range(0, len(users), self.BATCH_SIZE):
                batch = users[i:i + self.BATCH_SIZE]
                
                for user in batch:
                    try:
                        rec_type = RecipientType(user.recipient_type)
                        
                        # Generate recommendations
                        recommendations = await self.analytics_service.generate_recommendations(
                            user.recipient_id,
                            rec_type,
                            force_refresh=force_refresh,
                        )
                        
                        details["recommendations_created"] += len(recommendations)
                        records_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to generate recommendations for {user.recipient_id}: {e}")
                        records_failed += 1
                
                # Commit after each batch
                await self.db.commit()
                
                logger.info(f"Processed batch {i // self.BATCH_SIZE + 1} of {(len(users) - 1) // self.BATCH_SIZE + 1}")
            
            details["users_processed"] = records_processed
            
            return JobResult(
                job_type=JobType.RECOMMENDATION_GENERATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Recommendation generation job failed: {e}")
            return JobResult(
                job_type=JobType.RECOMMENDATION_GENERATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
                error=str(e),
            )
    
    # -------------------------------------------------------------------------
    # ENGAGEMENT METRIC AGGREGATION
    # -------------------------------------------------------------------------
    
    async def aggregate_engagement_metrics(
        self,
        period_type: str = "daily",
        days_back: int = 7,
    ) -> JobResult:
        """
        Aggregate engagement metrics from notification events.
        
        This job:
        1. Calculates engagement metrics for each user
        2. Stores aggregated metrics in engagement_metrics table
        3. Updates cohort statistics
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        records_failed = 0
        details = {
            "period_type": period_type,
            "metrics_calculated": 0,
        }
        
        try:
            # Calculate date range
            end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - timedelta(days=days_back)
            
            # Aggregate metrics per user per period
            aggregate_query = text("""
                WITH user_metrics AS (
                    SELECT 
                        ne.recipient_id,
                        ne.recipient_type,
                        :period_type AS period_type,
                        :start_date::timestamp AS period_start,
                        :end_date::timestamp AS period_end,
                        COUNT(*) FILTER (WHERE ne.event_type = 'sent') AS total_sent,
                        COUNT(*) FILTER (WHERE ne.event_type = 'delivered') AS total_delivered,
                        COUNT(*) FILTER (WHERE ne.event_type = 'read') AS total_read,
                        COUNT(*) FILTER (WHERE ne.event_type = 'clicked') AS total_clicked,
                        COUNT(*) FILTER (WHERE ne.event_type = 'dismissed') AS total_dismissed,
                        ne.channel,
                        np.global_enabled,
                        np.in_app_enabled, np.in_app_frequency,
                        np.email_enabled, np.email_frequency,
                        np.push_enabled, np.push_frequency,
                        np.toast_enabled, np.toast_frequency,
                        np.notification_types,
                        np.batch_settings
                    FROM notification_events ne
                    JOIN notification_preferences np 
                        ON np.recipient_id = ne.recipient_id 
                        AND np.recipient_type = ne.recipient_type
                    WHERE ne.event_timestamp >= :start_date
                      AND ne.event_timestamp < :end_date
                    GROUP BY 
                        ne.recipient_id, ne.recipient_type, ne.channel,
                        np.global_enabled, np.in_app_enabled, np.in_app_frequency,
                        np.email_enabled, np.email_frequency,
                        np.push_enabled, np.push_frequency,
                        np.toast_enabled, np.toast_frequency,
                        np.notification_types, np.batch_settings
                )
                INSERT INTO engagement_metrics (
                    recipient_id, recipient_type, period_type, period_start, period_end,
                    total_sent, total_delivered, total_read, total_clicked, total_dismissed,
                    overall_open_rate, overall_click_rate, overall_ignore_rate,
                    engagement_score, channel, active_preferences
                )
                SELECT 
                    recipient_id, recipient_type, period_type, period_start, period_end,
                    total_sent, total_delivered, total_read, total_clicked, total_dismissed,
                    CASE WHEN total_delivered > 0 THEN total_read::FLOAT / total_delivered ELSE 0 END,
                    CASE WHEN total_read > 0 THEN total_clicked::FLOAT / total_read ELSE 0 END,
                    CASE WHEN total_delivered > 0 THEN total_dismissed::FLOAT / total_delivered ELSE 0 END,
                    calculate_engagement_score(
                        CASE WHEN total_delivered > 0 THEN total_read::FLOAT / total_delivered ELSE 0 END,
                        CASE WHEN total_read > 0 THEN total_clicked::FLOAT / total_read ELSE 0 END,
                        CASE WHEN total_delivered > 0 THEN total_dismissed::FLOAT / total_delivered ELSE 0 END,
                        0
                    ),
                    channel,
                    jsonb_build_object(
                        'global_enabled', global_enabled,
                        'channels', jsonb_build_object(
                            'in_app', jsonb_build_object('enabled', in_app_enabled, 'frequency', in_app_frequency),
                            'email', jsonb_build_object('enabled', email_enabled, 'frequency', email_frequency),
                            'push', jsonb_build_object('enabled', push_enabled, 'frequency', push_frequency),
                            'toast', jsonb_build_object('enabled', toast_enabled, 'frequency', toast_frequency)
                        ),
                        'notification_types', notification_types,
                        'batch_settings', batch_settings
                    )
                FROM user_metrics
                WHERE total_sent > 0
                ON CONFLICT (recipient_id, recipient_type, period_type, period_start) 
                DO UPDATE SET
                    total_sent = EXCLUDED.total_sent,
                    total_delivered = EXCLUDED.total_delivered,
                    total_read = EXCLUDED.total_read,
                    total_clicked = EXCLUDED.total_clicked,
                    total_dismissed = EXCLUDED.total_dismissed,
                    overall_open_rate = EXCLUDED.overall_open_rate,
                    overall_click_rate = EXCLUDED.overall_click_rate,
                    overall_ignore_rate = EXCLUDED.overall_ignore_rate,
                    engagement_score = EXCLUDED.engagement_score,
                    updated_at = NOW()
                RETURNING recipient_id
            """)
            
            result = await self.db.execute(aggregate_query, {
                "period_type": period_type,
                "start_date": start_date,
                "end_date": end_date,
            })
            
            inserted_ids = result.fetchall()
            records_processed = len(inserted_ids)
            details["metrics_calculated"] = records_processed
            
            await self.db.commit()
            
            logger.info(f"Aggregated engagement metrics for {records_processed} user-periods")
            
            return JobResult(
                job_type=JobType.ENGAGEMENT_AGGREGATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Engagement aggregation job failed: {e}")
            return JobResult(
                job_type=JobType.ENGAGEMENT_AGGREGATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
                error=str(e),
            )
    
    # -------------------------------------------------------------------------
    # COHORT UPDATE
    # -------------------------------------------------------------------------
    
    async def update_user_cohorts(
        self,
        batch_size: int = 500,
    ) -> JobResult:
        """
        Update cohort memberships for all users.
        
        This job:
        1. Evaluates each user against cohort definitions
        2. Adds/removes users from cohorts
        3. Updates cohort statistics
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        records_failed = 0
        details = {
            "users_assigned": 0,
            "cohorts_updated": 0,
        }
        
        try:
            # Get all users
            users_query = text("""
                SELECT recipient_id, recipient_type 
                FROM notification_preferences
            """)
            
            result = await self.db.execute(users_query)
            users = result.fetchall()
            
            logger.info(f"Updating cohorts for {len(users)} users")
            
            # Process in batches
            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                
                for user in batch:
                    try:
                        rec_type = RecipientType(user.recipient_type)
                        
                        cohorts = await self.analytics_service.assign_user_to_cohorts(
                            user.recipient_id,
                            rec_type,
                        )
                        
                        if cohorts:
                            details["users_assigned"] += 1
                        
                        records_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to update cohorts for {user.recipient_id}: {e}")
                        records_failed += 1
                
                await self.db.commit()
            
            # Update cohort statistics
            await self._update_cohort_statistics()
            
            details["cohorts_updated"] = await self._get_cohort_count()
            
            return JobResult(
                job_type=JobType.COHORT_UPDATE,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Cohort update job failed: {e}")
            return JobResult(
                job_type=JobType.COHORT_UPDATE,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
                error=str(e),
            )
    
    async def _update_cohort_statistics(self) -> None:
        """Update aggregate statistics for all cohorts."""
        
        update_query = text("""
            UPDATE user_cohorts uc
            SET 
                member_count = subq.member_count,
                avg_engagement_score = subq.avg_engagement,
                avg_open_rate = subq.avg_open_rate,
                avg_click_rate = subq.avg_click_rate,
                avg_ignore_rate = subq.avg_ignore_rate,
                avg_response_time_hours = subq.avg_response_time,
                avg_satisfaction_score = subq.avg_satisfaction,
                updated_at = NOW()
            FROM (
                SELECT 
                    ucm.cohort_id,
                    COUNT(*) AS member_count,
                    AVG(em.engagement_score) AS avg_engagement,
                    AVG(em.overall_open_rate) AS avg_open_rate,
                    AVG(em.overall_click_rate) AS avg_click_rate,
                    AVG(em.overall_ignore_rate) AS avg_ignore_rate,
                    AVG(bo.avg_response_time_hours) AS avg_response_time,
                    AVG(bo.avg_satisfaction_score) AS avg_satisfaction
                FROM user_cohort_membership ucm
                LEFT JOIN engagement_metrics em 
                    ON em.recipient_id = ucm.recipient_id 
                    AND em.recipient_type = ucm.recipient_type
                    AND em.period_type = 'weekly'
                LEFT JOIN business_outcomes bo 
                    ON bo.owner_id = ucm.recipient_id
                WHERE ucm.exited_at IS NULL
                GROUP BY ucm.cohort_id
            ) subq
            WHERE uc.id = subq.cohort_id
        """)
        
        await self.db.execute(update_query)
        await self.db.commit()
    
    async def _get_cohort_count(self) -> int:
        """Get total number of cohorts."""
        
        result = await self.db.execute(text("SELECT COUNT(*) FROM user_cohorts"))
        return result.scalar() or 0
    
    # -------------------------------------------------------------------------
    # A/B TEST MONITORING
    # -------------------------------------------------------------------------
    
    async def monitor_ab_tests(
        self,
    ) -> JobResult:
        """
        Monitor running A/B tests and auto-complete if duration expired.
        
        This job:
        1. Finds tests that have exceeded their duration
        2. Calculates final results
        3. Marks tests as completed
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        records_failed = 0
        details = {
            "tests_checked": 0,
            "tests_completed": 0,
            "tests_extended": 0,
        }
        
        try:
            # Find expired tests
            tests_query = text("""
                SELECT test_id, test_name, start_date, duration_days
                FROM preference_ab_test_results
                WHERE status = 'running'
                  AND start_date + duration_days * INTERVAL '1 day' <= NOW()
            """)
            
            result = await self.db.execute(tests_query)
            expired_tests = result.fetchall()
            
            details["tests_checked"] = len(expired_tests)
            
            for test in expired_tests:
                try:
                    # Complete the test
                    completion_result = await self.ab_test_service.complete_test(test.test_id)
                    
                    if completion_result.get("success"):
                        details["tests_completed"] += 1
                        logger.info(f"Completed A/B test: {test.test_name}")
                    else:
                        details["tests_extended"] += 1
                        logger.warning(f"Could not complete test {test.test_name}: {completion_result.get('error')}")
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to complete test {test.test_id}: {e}")
                    records_failed += 1
            
            return JobResult(
                job_type=JobType.AB_TEST_MONITORING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"A/B test monitoring job failed: {e}")
            return JobResult(
                job_type=JobType.AB_TEST_MONITORING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=records_failed,
                details=details,
                error=str(e),
            )
    
    # -------------------------------------------------------------------------
    # FATIGUE DETECTION
    # -------------------------------------------------------------------------
    
    async def detect_fatigue_users(
        self,
        ignore_rate_threshold: float = 0.5,
    ) -> JobResult:
        """
        Identify users showing notification fatigue.
        
        This job:
        1. Finds users with high ignore rates
        2. Flags them for recommendation priority
        3. Optionally creates fatigue prevention recommendations
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        details = {
            "fatigue_users_found": 0,
            "recommendations_created": 0,
        }
        
        try:
            # Find fatigue users
            fatigue_query = text("""
                SELECT 
                    em.recipient_id,
                    em.recipient_type,
                    em.overall_ignore_rate,
                    em.active_preferences
                FROM engagement_metrics em
                WHERE em.period_type = 'weekly'
                  AND em.period_start >= :recent_date
                  AND em.overall_ignore_rate >= :threshold
                ORDER BY em.overall_ignore_rate DESC
            """)
            
            result = await self.db.execute(fatigue_query, {
                "recent_date": datetime.utcnow().date() - timedelta(days=14),
                "threshold": ignore_rate_threshold,
            })
            fatigue_users = result.fetchall()
            
            details["fatigue_users_found"] = len(fatigue_users)
            records_processed = len(fatigue_users)
            
            # Create fatigue prevention recommendations for high-risk users
            for user in fatigue_users[:100]:  # Limit to top 100
                try:
                    prefs = user.active_preferences or {}
                    channels = prefs.get("channels", {})
                    
                    # Find the channel with real_time frequency
                    fatigue_channel = None
                    for ch, settings in channels.items():
                        if settings.get("enabled", True) and settings.get("frequency") == "real_time":
                            fatigue_channel = ch
                            break
                    
                    if fatigue_channel:
                        # Create recommendation
                        await self.db.execute(
                            text("""
                                INSERT INTO preference_recommendations (
                                    recipient_id, recipient_type, recommendation_type,
                                    title, description, suggested_changes, expected_outcome,
                                    expected_metrics, priority_score, status
                                ) VALUES (
                                    :recipient_id, :recipient_type, 'fatigue_prevention',
                                    'Reduce Notification Fatigue',
                                    :description, :suggested_changes, 'Reduce ignore rate and improve engagement',
                                    :expected_metrics, 90, 'pending'
                                )
                            """),
                            {
                                "recipient_id": user.recipient_id,
                                "recipient_type": user.recipient_type,
                                "description": f"You're ignoring {(user.overall_ignore_rate * 100):.0f}% of notifications. Consider switching {fatigue_channel} to daily digest.",
                                "suggested_changes": json.dumps({
                                    "channels": {
                                        fatigue_channel: {"frequency": "daily_digest"}
                                    }
                                }),
                                "expected_metrics": json.dumps({
                                    "ignore_rate_reduction": 0.3,
                                    "engagement_improvement": 0.25,
                                }),
                            },
                        )
                        details["recommendations_created"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to create fatigue recommendation: {e}")
            
            await self.db.commit()
            
            return JobResult(
                job_type=JobType.FATIGUE_DETECTION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=0,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Fatigue detection job failed: {e}")
            return JobResult(
                job_type=JobType.FATIGUE_DETECTION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=0,
                details=details,
                error=str(e),
            )
    
    # -------------------------------------------------------------------------
    # PREFERENCE DISTRIBUTION SNAPSHOT
    # -------------------------------------------------------------------------
    
    async def snapshot_preference_distribution(
        self,
    ) -> JobResult:
        """
        Take a daily snapshot of preference distribution.
        
        This job:
        1. Counts users by channel/frequency combinations
        2. Stores snapshot for trend analysis
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        details = {
            "snapshots_created": 0,
        }
        
        try:
            snapshot_query = text("""
                INSERT INTO preference_distribution_daily (
                    snapshot_date, recipient_type,
                    channel_distribution, frequency_distribution, type_distribution,
                    total_users
                )
                SELECT 
                    CURRENT_DATE AS snapshot_date,
                    recipient_type,
                    jsonb_build_object(
                        'in_app_enabled', COUNT(*) FILTER (WHERE in_app_enabled = true),
                        'email_enabled', COUNT(*) FILTER (WHERE email_enabled = true),
                        'push_enabled', COUNT(*) FILTER (WHERE push_enabled = true),
                        'toast_enabled', COUNT(*) FILTER (WHERE toast_enabled = true)
                    ) AS channel_distribution,
                    jsonb_build_object(
                        'email_real_time', COUNT(*) FILTER (WHERE email_frequency = 'real_time'),
                        'email_daily', COUNT(*) FILTER (WHERE email_frequency = 'daily_digest'),
                        'email_weekly', COUNT(*) FILTER (WHERE email_frequency = 'weekly_summary'),
                        'push_real_time', COUNT(*) FILTER (WHERE push_frequency = 'real_time'),
                        'push_daily', COUNT(*) FILTER (WHERE push_frequency = 'daily_digest')
                    ) AS frequency_distribution,
                    '{}'::jsonb AS type_distribution,
                    COUNT(*) AS total_users
                FROM notification_preferences
                GROUP BY recipient_type
                ON CONFLICT (snapshot_date, recipient_type) DO UPDATE SET
                    channel_distribution = EXCLUDED.channel_distribution,
                    frequency_distribution = EXCLUDED.frequency_distribution,
                    type_distribution = EXCLUDED.type_distribution,
                    total_users = EXCLUDED.total_users
                RETURNING snapshot_date
            """)
            
            result = await self.db.execute(snapshot_query)
            snapshots = result.fetchall()
            
            records_processed = len(snapshots)
            details["snapshots_created"] = records_processed
            
            await self.db.commit()
            
            return JobResult(
                job_type=JobType.PREFERENCE_DISTRIBUTION_SNAPSHOT,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=0,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Preference distribution snapshot job failed: {e}")
            return JobResult(
                job_type=JobType.PREFERENCE_DISTRIBUTION_SNAPSHOT,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=0,
                details=details,
                error=str(e),
            )
    
    # -------------------------------------------------------------------------
    # BUSINESS OUTCOME AGGREGATION
    # -------------------------------------------------------------------------
    
    async def aggregate_business_outcomes(
        self,
        days_back: int = 30,
    ) -> JobResult:
        """
        Aggregate business outcomes for store owners.
        
        This job:
        1. Calculates response times, satisfaction, order metrics
        2. Links to notification preferences
        3. Stores for analysis
        """
        
        started_at = datetime.utcnow()
        records_processed = 0
        details = {
            "owners_processed": 0,
        }
        
        try:
            aggregate_query = text("""
                INSERT INTO business_outcomes (
                    owner_id, store_id, period_start, period_end,
                    avg_order_response_time_hours, avg_satisfaction_score,
                    orders_received, orders_processed,
                    notification_action_rate, batch_inquiries_pct,
                    active_preferences
                )
                SELECT 
                    so.user_id AS owner_id,
                    so.store_id,
                    :start_date::timestamp AS period_start,
                    :end_date::timestamp AS period_end,
                    AVG(ort.response_time_hours) AS avg_response_time,
                    AVG(ort.satisfaction_score) AS avg_satisfaction,
                    COUNT(DISTINCT o.id) AS orders_received,
                    COUNT(DISTINCT o.id) FILTER (WHERE o.status = 'processed') AS orders_processed,
                    AVG(em.overall_click_rate) AS notification_action_rate,
                    AVG(CASE WHEN np.batch_settings->>'enabled' = 'true' THEN 1 ELSE 0 END) AS batch_inquiries_pct,
                    jsonb_build_object(
                        'global_enabled', np.global_enabled,
                        'channels', jsonb_build_object(
                            'email', jsonb_build_object('enabled', np.email_enabled, 'frequency', np.email_frequency),
                            'push', jsonb_build_object('enabled', np.push_enabled, 'frequency', np.push_frequency)
                        ),
                        'batch_settings', np.batch_settings
                    ) AS active_preferences
                FROM store_owners so
                LEFT JOIN owner_response_times ort ON ort.owner_id = so.user_id
                    AND ort.response_timestamp >= :start_date
                LEFT JOIN orders o ON o.store_id = so.store_id
                    AND o.created_at >= :start_date
                LEFT JOIN engagement_metrics em ON em.recipient_id = so.user_id
                    AND em.recipient_type = 'owner'
                    AND em.period_type = 'weekly'
                LEFT JOIN notification_preferences np ON np.recipient_id = so.user_id
                    AND np.recipient_type = 'owner'
                GROUP BY so.user_id, so.store_id, np.global_enabled, np.email_enabled, 
                         np.email_frequency, np.push_enabled, np.push_frequency, np.batch_settings
                ON CONFLICT (owner_id, store_id, period_start) DO UPDATE SET
                    avg_order_response_time_hours = EXCLUDED.avg_order_response_time_hours,
                    avg_satisfaction_score = EXCLUDED.avg_satisfaction_score,
                    orders_received = EXCLUDED.orders_received,
                    orders_processed = EXCLUDED.orders_processed,
                    notification_action_rate = EXCLUDED.notification_action_rate,
                    batch_inquiries_pct = EXCLUDED.batch_inquiries_pct,
                    active_preferences = EXCLUDED.active_preferences
                RETURNING owner_id
            """)
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            result = await self.db.execute(aggregate_query, {
                "start_date": start_date,
                "end_date": end_date,
            })
            
            owners = result.fetchall()
            records_processed = len(owners)
            details["owners_processed"] = records_processed
            
            await self.db.commit()
            
            return JobResult(
                job_type=JobType.BUSINESS_OUTCOME_AGGREGATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                records_processed=records_processed,
                records_failed=0,
                details=details,
            )
            
        except Exception as e:
            logger.error(f"Business outcome aggregation job failed: {e}")
            return JobResult(
                job_type=JobType.BUSINESS_OUTCOME_AGGREGATION,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                records_processed=records_processed,
                records_failed=0,
                details=details,
                error=str(e),
            )


# -------------------------------------------------------------------------
# SCHEDULER SETUP (for APScheduler)
# -------------------------------------------------------------------------

async def run_all_scheduled_jobs(db_url: str) -> Dict[str, JobResult]:
    """
    Run all scheduled jobs in sequence.
    
    This can be called from a cron job or scheduler.
    """
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        jobs = PreferenceScheduledJobs(session)
        
        results = {}
        
        # Run jobs in order of dependency
        results["engagement"] = await jobs.run_job(JobType.ENGAGEMENT_AGGREGATION)
        results["business"] = await jobs.run_job(JobType.BUSINESS_OUTCOME_AGGREGATION)
        results["cohorts"] = await jobs.run_job(JobType.COHORT_UPDATE)
        results["distribution"] = await jobs.run_job(JobType.PREFERENCE_DISTRIBUTION_SNAPSHOT)
        results["fatigue"] = await jobs.run_job(JobType.FATIGUE_DETECTION)
        results["recommendations"] = await jobs.run_job(JobType.RECOMMENDATION_GENERATION)
        results["ab_tests"] = await jobs.run_job(JobType.AB_TEST_MONITORING)
        
        return results


def run_jobs_sync(db_url: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for running all jobs.
    
    Can be called from a cron script:
        python -c "from services.preference_scheduled_jobs import run_jobs_sync; run_jobs_sync('postgresql+asyncpg://...')"
    """
    
    return asyncio.run(run_all_scheduled_jobs(db_url))


if __name__ == "__main__":
    import os
    import sys
    
    # Get database URL from environment or argument
    db_url = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not db_url:
        print("Usage: python -m services.preference_scheduled_jobs <database_url>")
        print("   or: DATABASE_URL=... python -m services.preference_scheduled_jobs")
        sys.exit(1)
    
    results = run_jobs_sync(db_url)
    
    print("\n=== Scheduled Jobs Results ===")
    for job_name, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"{status} {job_name}: {result.records_processed} processed, {result.records_failed} failed")
        if result.error:
            print(f"  Error: {result.error}")
    
    total_success = sum(1 for r in results.values() if r.success)
    print(f"\nTotal: {total_success}/{len(results)} jobs succeeded")
