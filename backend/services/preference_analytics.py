"""
CONFIT Backend - Preference Analytics & Recommendation Service
===============================================================
Intelligent preference pattern analysis, cohort detection, engagement
correlation, and personalized recommendation generation.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from collections import defaultdict
import statistics

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RecipientType(str, Enum):
    CUSTOMER = "customer"
    OWNER = "owner"


class RecommendationType(str, Enum):
    FREQUENCY_OPTIMIZATION = "frequency_optimization"
    CHANNEL_OPTIMIZATION = "channel_optimization"
    FATIGUE_PREVENTION = "fatigue_prevention"
    ENGAGEMENT_IMPROVEMENT = "engagement_improvement"
    BATCH_VS_REALTIME = "batch_vs_realtime"
    TYPE_SELECTION = "type_selection"


class CohortType(str, Enum):
    FREQUENCY_PATTERN = "frequency_pattern"
    CHANNEL_PREFERENCE = "channel_preference"
    NOTIFICATION_TYPE = "notification_type"
    ENGAGEMENT_LEVEL = "engagement_level"
    BEHAVIORAL = "behavioral"
    CUSTOM = "custom"


@dataclass
class PreferenceSnapshot:
    """Snapshot of user's notification preferences."""
    recipient_id: str
    recipient_type: RecipientType
    global_enabled: bool = True
    channels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    notification_types: Dict[str, Any] = field(default_factory=dict)
    batch_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "global_enabled": self.global_enabled,
            "channels": self.channels,
            "notification_types": self.notification_types,
            "batch_settings": self.batch_settings,
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any], recipient_id: str, recipient_type: str) -> "PreferenceSnapshot":
        return cls(
            recipient_id=recipient_id,
            recipient_type=RecipientType(recipient_type),
            global_enabled=data.get("global_enabled", True),
            channels=data.get("channels", {}),
            notification_types=data.get("notification_types", {}),
            batch_settings=data.get("batch_settings", {}),
        )


@dataclass
class EngagementMetrics:
    """User engagement metrics for a period."""
    recipient_id: str
    recipient_type: RecipientType
    period_start: datetime
    period_end: datetime
    total_sent: int = 0
    total_delivered: int = 0
    total_read: int = 0
    total_clicked: int = 0
    total_dismissed: int = 0
    unsubscribe_events: int = 0
    channel_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    @property
    def open_rate(self) -> float:
        return self.total_read / self.total_delivered if self.total_delivered > 0 else 0
    
    @property
    def click_rate(self) -> float:
        return self.total_clicked / self.total_read if self.total_read > 0 else 0
    
    @property
    def ignore_rate(self) -> float:
        return self.total_dismissed / self.total_delivered if self.total_delivered > 0 else 0
    
    @property
    def engagement_score(self) -> float:
        """Calculate composite engagement score (0-100)."""
        score = (
            self.open_rate * 40 +
            self.click_rate * 30 +
            (1 - self.ignore_rate) * 20 +
            (10 if self.unsubscribe_events == 0 else 0)
        )
        return min(max(score, 0), 100)


@dataclass
class BusinessOutcome:
    """Business outcomes for store owners."""
    owner_id: str
    store_id: str
    period_start: datetime
    period_end: datetime
    avg_response_time_hours: Optional[float] = None
    avg_satisfaction_score: Optional[float] = None
    orders_received: int = 0
    orders_processed: int = 0
    notification_action_rate: float = 0
    batch_inquiries_pct: float = 0


@dataclass
class Recommendation:
    """Personalized preference recommendation."""
    recipient_id: str
    recipient_type: RecipientType
    recommendation_type: RecommendationType
    title: str
    description: str
    suggested_changes: Dict[str, Any]
    expected_outcome: str
    expected_metrics: Dict[str, float]
    cohort_basis: Optional[str] = None
    similar_users_count: int = 0
    similar_users_improvement: float = 0
    priority_score: float = 50
    relevance_reason: Optional[str] = None


@dataclass
class PreferencePattern:
    """Discovered preference pattern."""
    pattern_name: str
    pattern_type: str
    recipient_type: Optional[RecipientType]
    pattern_definition: Dict[str, Any]
    prevalence_pct: float
    avg_engagement_score: float
    engagement_correlation: float
    is_recommendation_candidate: bool = False


class PreferenceAnalyticsService:
    """
    Core service for preference analytics and recommendation generation.
    """
    
    # Thresholds for recommendations
    FATIGUE_IGNORE_RATE_THRESHOLD = 0.5
    LOW_ENGAGEMENT_SCORE_THRESHOLD = 40
    HIGH_ENGAGEMENT_SCORE_THRESHOLD = 70
    MIN_SIMILAR_USERS_FOR_RECOMMENDATION = 10
    MIN_IMPROVEMENT_PCT_FOR_RECOMMENDATION = 15
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # -------------------------------------------------------------------------
    # PREFERENCE TRACKING & PATTERN ANALYSIS
    # -------------------------------------------------------------------------
    
    async def track_preference_change(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        change_category: str,
        field_path: str,
        old_value: Any,
        new_value: Any,
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        trigger_source: str = "user_initiated",
        device_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        ab_test_id: Optional[str] = None,
    ) -> None:
        """Track a preference configuration change."""
        
        query = text("""
            INSERT INTO preference_history (
                recipient_id, recipient_type, change_category, field_path,
                old_value, new_value, previous_state, new_state, trigger_source,
                device_id, recommendation_id, ab_test_id
            ) VALUES (
                :recipient_id, :recipient_type, :change_category, :field_path,
                :old_value, :new_value, :previous_state, :new_state, :trigger_source,
                :device_id, :recommendation_id, :ab_test_id
            )
        """)
        
        await self.db.execute(query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
            "change_category": change_category,
            "field_path": field_path,
            "old_value": json.dumps(old_value) if old_value is not None else None,
            "new_value": json.dumps(new_value) if new_value is not None else None,
            "previous_state": json.dumps(previous_state),
            "new_state": json.dumps(new_state),
            "trigger_source": trigger_source,
            "device_id": device_id,
            "recommendation_id": recommendation_id,
            "ab_test_id": ab_test_id,
        })
        await self.db.commit()
    
    async def analyze_preference_patterns(
        self,
        recipient_type: Optional[RecipientType] = None,
        min_prevalence: float = 5.0,
    ) -> List[PreferencePattern]:
        """
        Analyze preference configurations to identify patterns.
        
        Returns patterns with prevalence and engagement correlation.
        """
        
        # Get all current preferences with engagement metrics
        query = text("""
            SELECT 
                np.recipient_id,
                np.recipient_type,
                jsonb_build_object(
                    'global_enabled', np.global_enabled,
                    'channels', jsonb_build_object(
                        'in_app', jsonb_build_object('enabled', np.in_app_enabled, 'frequency', np.in_app_frequency),
                        'email', jsonb_build_object('enabled', np.email_enabled, 'frequency', np.email_frequency),
                        'push', jsonb_build_object('enabled', np.push_enabled, 'frequency', np.push_frequency),
                        'toast', jsonb_build_object('enabled', np.toast_enabled, 'frequency', np.toast_frequency)
                    ),
                    'notification_types', np.notification_types,
                    'batch_settings', np.batch_settings
                ) AS preferences,
                COALESCE(em.engagement_score, 50) AS engagement_score,
                COALESCE(em.overall_open_rate, 0) AS open_rate,
                COALESCE(em.overall_click_rate, 0) AS click_rate
            FROM notification_preferences np
            LEFT JOIN LATERAL (
                SELECT engagement_score, overall_open_rate, overall_click_rate
                FROM engagement_metrics em
                WHERE em.recipient_id = np.recipient_id
                  AND em.recipient_type = np.recipient_type
                  AND em.period_type = 'weekly'
                ORDER BY em.period_start DESC
                LIMIT 1
            ) em ON true
            WHERE (:recipient_type IS NULL OR np.recipient_type = :recipient_type)
        """)
        
        result = await self.db.execute(query, {
            "recipient_type": recipient_type.value if recipient_type else None
        })
        rows = result.fetchall()
        
        if not rows:
            return []
        
        total_users = len(rows)
        patterns_found = []
        
        # Analyze frequency patterns
        frequency_patterns = defaultdict(list)
        for row in rows:
            prefs = row.preferences
            channels = prefs.get("channels", {})
            
            # Create frequency signature
            freq_signature = []
            for channel, settings in channels.items():
                if settings.get("enabled", True):
                    freq_signature.append(f"{channel}:{settings.get('frequency', 'real_time')}")
            
            freq_key = "|".join(sorted(freq_signature))
            frequency_patterns[freq_key].append({
                "recipient_id": row.recipient_id,
                "engagement_score": row.engagement_score,
                "open_rate": row.open_rate,
                "click_rate": row.click_rate,
            })
        
        # Convert to pattern objects
        for freq_key, users in frequency_patterns.items():
            prevalence = len(users) / total_users * 100
            if prevalence >= min_prevalence:
                engagement_scores = [u["engagement_score"] for u in users]
                open_rates = [u["open_rate"] for u in users]
                
                avg_engagement = statistics.mean(engagement_scores) if engagement_scores else 0
                
                patterns_found.append(PreferencePattern(
                    pattern_name=f"Frequency: {freq_key}",
                    pattern_type="frequency_pattern",
                    recipient_type=recipient_type,
                    pattern_definition={"frequency_signature": freq_key},
                    prevalence_pct=prevalence,
                    avg_engagement_score=avg_engagement,
                    engagement_correlation=0,  # Would need more analysis
                    is_recommendation_candidate=avg_engagement > 60,
                ))
        
        # Analyze channel patterns
        channel_patterns = defaultdict(list)
        for row in rows:
            prefs = row.preferences
            channels = prefs.get("channels", {})
            
            # Create channel signature
            channel_sig = []
            for channel, settings in channels.items():
                if settings.get("enabled", True):
                    channel_sig.append(channel)
            
            channel_key = ",".join(sorted(channel_sig))
            channel_patterns[channel_key].append({
                "recipient_id": row.recipient_id,
                "engagement_score": row.engagement_score,
            })
        
        for channel_key, users in channel_patterns.items():
            prevalence = len(users) / total_users * 100
            if prevalence >= min_prevalence:
                engagement_scores = [u["engagement_score"] for u in users]
                avg_engagement = statistics.mean(engagement_scores) if engagement_scores else 0
                
                patterns_found.append(PreferencePattern(
                    pattern_name=f"Channels: {channel_key}",
                    pattern_type="channel_preference",
                    recipient_type=recipient_type,
                    pattern_definition={"channels": channel_key.split(",")},
                    prevalence_pct=prevalence,
                    avg_engagement_score=avg_engagement,
                    engagement_correlation=0,
                    is_recommendation_candidate=avg_engagement > 60,
                ))
        
        return patterns_found
    
    async def detect_preference_drift(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Analyze how a user's preferences have evolved over time.
        
        Returns drift analysis with trend indicators.
        """
        
        query = text("""
            SELECT 
                created_at,
                change_category,
                field_path,
                old_value,
                new_value,
                trigger_source
            FROM preference_history
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
              AND created_at >= :start_date
            ORDER BY created_at ASC
        """)
        
        result = await self.db.execute(query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
            "start_date": datetime.utcnow() - timedelta(days=days),
        })
        rows = result.fetchall()
        
        if not rows:
            return {"has_drift": False, "changes": []}
        
        # Analyze change patterns
        changes_by_category = defaultdict(list)
        for row in rows:
            changes_by_category[row.change_category].append({
                "timestamp": row.created_at.isoformat(),
                "field": row.field_path,
                "trigger": row.trigger_source,
            })
        
        # Detect trends
        trends = {}
        
        # Frequency drift: real_time -> digest pattern?
        frequency_changes = changes_by_category.get("frequency_adjustment", [])
        if len(frequency_changes) >= 2:
            # Check if moving towards batched
            trends["frequency_trend"] = "batching" if len(frequency_changes) >= 2 else "stable"
        
        # Channel drift: disabling channels?
        channel_changes = changes_by_category.get("channel_toggle", [])
        disabled_count = sum(1 for c in channel_changes if "disabled" in str(c.get("field", "")).lower())
        if disabled_count > 0:
            trends["channel_trend"] = "reducing"
        
        return {
            "has_drift": len(rows) > 0,
            "total_changes": len(rows),
            "changes_by_category": {k: len(v) for k, v in changes_by_category.items()},
            "trends": trends,
            "recent_changes": rows[-5:] if len(rows) > 5 else rows,
        }
    
    # -------------------------------------------------------------------------
    # BEHAVIORAL ENGAGEMENT CORRELATION
    # -------------------------------------------------------------------------
    
    async def calculate_engagement_metrics(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        period_start: datetime,
        period_end: datetime,
    ) -> EngagementMetrics:
        """Calculate engagement metrics for a user over a period."""
        
        query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE event_type = 'sent') AS total_sent,
                COUNT(*) FILTER (WHERE event_type = 'delivered') AS total_delivered,
                COUNT(*) FILTER (WHERE event_type = 'read') AS total_read,
                COUNT(*) FILTER (WHERE event_type = 'clicked') AS total_clicked,
                COUNT(*) FILTER (WHERE event_type = 'dismissed') AS total_dismissed,
                channel,
                jsonb_object_agg(event_type, cnt) AS channel_stats
            FROM notification_events
            LEFT JOIN LATERAL (
                SELECT channel, event_type, COUNT(*) AS cnt
                FROM notification_events ne2
                WHERE ne2.recipient_id = :recipient_id
                  AND ne2.recipient_type = :recipient_type
                  AND ne2.event_timestamp >= :period_start
                  AND ne2.event_timestamp < :period_end
                GROUP BY channel, event_type
            ) channel_stats ON true
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
              AND event_timestamp >= :period_start
              AND event_timestamp < :period_end
            GROUP BY channel
        """)
        
        result = await self.db.execute(query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
            "period_start": period_start,
            "period_end": period_end,
        })
        rows = result.fetchall()
        
        # Get unsubscribe events
        unsub_query = text("""
            SELECT COUNT(*) AS unsubscribe_count, channel
            FROM engagement_metrics
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
              AND period_start >= :period_start
            GROUP BY channel
        """)
        
        unsub_result = await self.db.execute(unsub_query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
            "period_start": period_start,
        })
        unsub_rows = unsub_result.fetchall()
        
        total_unsubscribes = sum(r.unsubscribe_count or 0 for r in unsub_rows)
        
        # Aggregate metrics
        total_sent = sum(r.total_sent or 0 for r in rows)
        total_delivered = sum(r.total_delivered or 0 for r in rows)
        total_read = sum(r.total_read or 0 for r in rows)
        total_clicked = sum(r.total_clicked or 0 for r in rows)
        total_dismissed = sum(r.total_dismissed or 0 for r in rows)
        
        # Channel metrics
        channel_metrics = {}
        for row in rows:
            if row.channel:
                channel_metrics[row.channel] = {
                    "sent": row.total_sent or 0,
                    "delivered": row.total_delivered or 0,
                    "read": row.total_read or 0,
                    "clicked": row.total_clicked or 0,
                    "dismissed": row.total_dismissed or 0,
                }
        
        return EngagementMetrics(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            period_start=period_start,
            period_end=period_end,
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_read=total_read,
            total_clicked=total_clicked,
            total_dismissed=total_dismissed,
            unsubscribe_events=total_unsubscribes,
            channel_metrics=channel_metrics,
        )
    
    async def correlate_preferences_with_engagement(
        self,
        recipient_type: Optional[RecipientType] = None,
    ) -> Dict[str, Any]:
        """
        Analyze correlation between preference configurations and engagement.
        
        Returns heatmap-style data showing which preferences correlate with
        high/low engagement.
        """
        
        query = text("""
            SELECT 
                em.recipient_id,
                em.recipient_type,
                em.active_preferences,
                em.engagement_score,
                em.overall_open_rate,
                em.overall_click_rate,
                em.overall_ignore_rate,
                em.unsubscribe_events
            FROM engagement_metrics em
            WHERE em.period_type = 'weekly'
              AND em.period_start >= :recent_date
              AND (:recipient_type IS NULL OR em.recipient_type = :recipient_type)
        """)
        
        result = await self.db.execute(query, {
            "recent_date": datetime.utcnow() - timedelta(days=30),
            "recipient_type": recipient_type.value if recipient_type else None,
        })
        rows = result.fetchall()
        
        if not rows:
            return {"correlations": {}, "sample_size": 0}
        
        # Analyze by email frequency
        email_freq_engagement = defaultdict(list)
        for row in rows:
            prefs = row.active_preferences
            channels = prefs.get("channels", {})
            email_freq = channels.get("email", {}).get("frequency", "real_time")
            email_freq_engagement[email_freq].append({
                "engagement_score": row.engagement_score,
                "open_rate": row.overall_open_rate,
                "ignore_rate": row.overall_ignore_rate,
            })
        
        # Calculate averages
        frequency_correlations = {}
        for freq, data in email_freq_engagement.items():
            if len(data) >= 5:  # Minimum sample
                frequency_correlations[freq] = {
                    "user_count": len(data),
                    "avg_engagement": statistics.mean(d["engagement_score"] for d in data),
                    "avg_open_rate": statistics.mean(d["open_rate"] for d in data),
                    "avg_ignore_rate": statistics.mean(d["ignore_rate"] for d in data),
                }
        
        # Analyze by channel combination
        channel_combo_engagement = defaultdict(list)
        for row in rows:
            prefs = row.active_preferences
            channels = prefs.get("channels", {})
            enabled_channels = tuple(sorted([
                ch for ch, settings in channels.items()
                if settings.get("enabled", True)
            ]))
            channel_combo_engagement[enabled_channels].append(row.engagement_score)
        
        channel_correlations = {}
        for combo, scores in channel_combo_engagement.items():
            if len(scores) >= 5:
                channel_correlations[", ".join(combo)] = {
                    "user_count": len(scores),
                    "avg_engagement": statistics.mean(scores),
                }
        
        # Identify fatigue signals
        fatigue_users = [
            row for row in rows
            if row.overall_ignore_rate > self.FATIGUE_IGNORE_RATE_THRESHOLD
               or row.unsubscribe_events > 0
        ]
        
        fatigue_prefs = defaultdict(int)
        for row in fatigue_users:
            prefs = row.active_preferences
            channels = prefs.get("channels", {})
            for ch, settings in channels.items():
                if settings.get("enabled", True) and settings.get("frequency") == "real_time":
                    fatigue_prefs[f"{ch}_real_time"] += 1
        
        return {
            "correlations": {
                "by_frequency": frequency_correlations,
                "by_channel_combo": channel_correlations,
            },
            "fatigue_signals": dict(fatigue_users[:10]) if fatigue_users else {},
            "fatigue_preference_patterns": dict(fatigue_prefs),
            "sample_size": len(rows),
        }
    
    async def get_business_outcomes_for_owner(
        self,
        owner_id: str,
        store_id: str,
        period_days: int = 30,
    ) -> Optional[BusinessOutcome]:
        """Get business outcome metrics for a store owner."""
        
        query = text("""
            SELECT 
                owner_id,
                store_id,
                period_start,
                period_end,
                avg_order_response_time_hours,
                avg_satisfaction_score,
                orders_received,
                orders_processed,
                notification_action_rate,
                batch_inquiries_pct,
                active_preferences
            FROM business_outcomes
            WHERE owner_id = :owner_id
              AND store_id = :store_id
              AND period_start >= :start_date
            ORDER BY period_start DESC
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "owner_id": owner_id,
            "store_id": store_id,
            "start_date": datetime.utcnow() - timedelta(days=period_days),
        })
        row = result.fetchone()
        
        if not row:
            return None
        
        return BusinessOutcome(
            owner_id=row.owner_id,
            store_id=row.store_id,
            period_start=row.period_start,
            period_end=row.period_end,
            avg_response_time_hours=row.avg_order_response_time_hours,
            avg_satisfaction_score=row.avg_satisfaction_score,
            orders_received=row.orders_received,
            orders_processed=row.orders_processed,
            notification_action_rate=row.notification_action_rate,
            batch_inquiries_pct=row.batch_inquiries_pct,
        )
    
    # -------------------------------------------------------------------------
    # RECOMMENDATION ENGINE
    # -------------------------------------------------------------------------
    
    async def generate_recommendations(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        force_refresh: bool = False,
    ) -> List[Recommendation]:
        """
        Generate personalized preference recommendations.
        
        Recommendations are based on:
        - User's current engagement metrics
        - Similar users' preferences and outcomes
        - Identified patterns and correlations
        """
        
        # Check for existing pending recommendations
        if not force_refresh:
            existing = await self._get_pending_recommendations(recipient_id, recipient_type)
            if existing:
                return existing
        
        # Get user's current preferences and engagement
        current_prefs = await self._get_current_preferences(recipient_id, recipient_type)
        engagement = await self.calculate_engagement_metrics(
            recipient_id, recipient_type,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow(),
        )
        
        recommendations = []
        
        # Generate frequency optimization recommendations
        freq_rec = await self._generate_frequency_recommendation(
            recipient_id, recipient_type, current_prefs, engagement
        )
        if freq_rec:
            recommendations.append(freq_rec)
        
        # Generate fatigue prevention recommendations
        fatigue_rec = await self._generate_fatigue_recommendation(
            recipient_id, recipient_type, current_prefs, engagement
        )
        if fatigue_rec:
            recommendations.append(fatigue_rec)
        
        # Generate channel optimization recommendations
        channel_rec = await self._generate_channel_recommendation(
            recipient_id, recipient_type, current_prefs, engagement
        )
        if channel_rec:
            recommendations.append(channel_rec)
        
        # For owners: generate batch vs real-time recommendations
        if recipient_type == RecipientType.OWNER:
            batch_rec = await self._generate_batch_recommendation(
                recipient_id, recipient_type, current_prefs, engagement
            )
            if batch_rec:
                recommendations.append(batch_rec)
        
        # Store recommendations
        for rec in recommendations:
            await self._store_recommendation(rec)
        
        return recommendations
    
    async def _generate_frequency_recommendation(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        current_prefs: PreferenceSnapshot,
        engagement: EngagementMetrics,
    ) -> Optional[Recommendation]:
        """Generate frequency optimization recommendation."""
        
        # Check if user has low engagement with real-time emails
        email_settings = current_prefs.channels.get("email", {})
        email_freq = email_settings.get("frequency", "real_time")
        
        if email_freq != "real_time":
            return None  # Already optimized
        
        # Find similar users with weekly digest who have higher engagement
        similar_users = await self._find_similar_users_with_better_engagement(
            recipient_id, recipient_type, current_prefs,
            target_pref={"channels": {"email": {"frequency": "weekly_summary"}}},
            metric="engagement_score",
        )
        
        if len(similar_users) < self.MIN_SIMILAR_USERS_FOR_RECOMMENDATION:
            return None
        
        improvement = similar_users[0]["improvement_pct"] if similar_users else 0
        if improvement < self.MIN_IMPROVEMENT_PCT_FOR_RECOMMENDATION:
            return None
        
        return Recommendation(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            recommendation_type=RecommendationType.FREQUENCY_OPTIMIZATION,
            title="Try Weekly Email Digests",
            description=(
                f"Users similar to you who switched from real-time emails to weekly digests "
                f"show {improvement:.0f}% higher engagement. Get a curated summary instead of "
                f"individual emails—stay informed without the noise."
            ),
            suggested_changes={
                "channels": {
                    "email": {"frequency": "weekly_summary"}
                }
            },
            expected_outcome=f"Expected {improvement:.0f}% improvement in engagement",
            expected_metrics={
                "engagement_improvement_pct": improvement,
                "open_rate_improvement": 0.15,
            },
            cohort_basis="weekly_digest_users",
            similar_users_count=len(similar_users),
            similar_users_improvement=improvement,
            priority_score=70 + min(improvement / 2, 20),  # Scale with improvement
            relevance_reason="Your current email open rate suggests you might benefit from batched delivery",
        )
    
    async def _generate_fatigue_recommendation(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        current_prefs: PreferenceSnapshot,
        engagement: EngagementMetrics,
    ) -> Optional[Recommendation]:
        """Generate fatigue prevention recommendation."""
        
        # Check for fatigue signals
        if engagement.ignore_rate < self.FATIGUE_IGNORE_RATE_THRESHOLD:
            return None
        
        # Identify which channel has highest ignore rate
        channel_ignore_rates = {}
        for channel, metrics in engagement.channel_metrics.items():
            delivered = metrics.get("delivered", 0)
            dismissed = metrics.get("dismissed", 0)
            if delivered > 0:
                channel_ignore_rates[channel] = dismissed / delivered
        
        if not channel_ignore_rates:
            return None
        
        worst_channel = max(channel_ignore_rates, key=channel_ignore_rates.get)
        worst_rate = channel_ignore_rates[worst_channel]
        
        if worst_rate < 0.4:  # Not severe enough
            return None
        
        # Check if this channel is set to real_time
        channel_settings = current_prefs.channels.get(worst_channel, {})
        if channel_settings.get("frequency") != "real_time":
            return None
        
        return Recommendation(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            recommendation_type=RecommendationType.FATIGUE_PREVENTION,
            title=f"Reduce {worst_channel.replace('_', ' ').title()} Fatigue",
            description=(
                f"You're ignoring {worst_rate*100:.0f}% of {worst_channel.replace('_', ' ')} notifications. "
                f"Consider switching to daily digests to reduce notification overload while staying informed."
            ),
            suggested_changes={
                "channels": {
                    worst_channel: {"frequency": "daily_digest"}
                }
            },
            expected_outcome="Reduce notification fatigue and improve relevance",
            expected_metrics={
                "ignore_rate_reduction": 0.3,
                "engagement_improvement_pct": 20,
            },
            priority_score=85,  # High priority for fatigue
            relevance_reason=f"Your {worst_channel} ignore rate of {worst_rate*100:.0f}% indicates notification fatigue",
        )
    
    async def _generate_channel_recommendation(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        current_prefs: PreferenceSnapshot,
        engagement: EngagementMetrics,
    ) -> Optional[Recommendation]:
        """Generate channel optimization recommendation."""
        
        # Find best performing channel
        best_channel = None
        best_open_rate = 0
        
        for channel, metrics in engagement.channel_metrics.items():
            delivered = metrics.get("delivered", 0)
            read = metrics.get("read", 0)
            if delivered >= 5:  # Minimum sample
                open_rate = read / delivered
                if open_rate > best_open_rate:
                    best_open_rate = open_rate
                    best_channel = channel
        
        if not best_channel or best_open_rate < 0.3:
            return None
        
        # Check if other channels are underperforming
        underperforming = []
        for channel, metrics in engagement.channel_metrics.items():
            if channel == best_channel:
                continue
            delivered = metrics.get("delivered", 0)
            read = metrics.get("read", 0)
            if delivered >= 5:
                open_rate = read / delivered
                if open_rate < best_open_rate * 0.5:  # Significantly worse
                    underperforming.append(channel)
        
        if not underperforming:
            return None
        
        return Recommendation(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            recommendation_type=RecommendationType.CHANNEL_OPTIMIZATION,
            title="Optimize Your Notification Channels",
            description=(
                f"You engage most with {best_channel.replace('_', ' ')} notifications "
                f"({best_open_rate*100:.0f}% open rate). Consider disabling underperforming channels "
                f"({', '.join(underperforming)}) to focus on what works for you."
            ),
            suggested_changes={
                "channels": {
                    ch: {"enabled": False} for ch in underperforming
                }
            },
            expected_outcome="Focus on channels you actually use",
            expected_metrics={
                "engagement_improvement_pct": 15,
            },
            priority_score=60,
            relevance_reason=f"Your {best_channel} engagement is {best_open_rate/best_open_rate:.1f}x higher than other channels",
        )
    
    async def _generate_batch_recommendation(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        current_prefs: PreferenceSnapshot,
        engagement: EngagementMetrics,
    ) -> Optional[Recommendation]:
        """Generate batch vs real-time recommendation for store owners."""
        
        # Get business outcomes
        business = await self.get_business_outcomes_for_owner(recipient_id, "default_store")
        
        if not business:
            return None
        
        batch_settings = current_prefs.batch_settings
        batch_enabled = batch_settings.get("enabled", False)
        
        # If response time is high and not batching, suggest batching
        if not batch_enabled and business.avg_response_time_hours and business.avg_response_time_hours > 2:
            # Find similar owners who batch and have better outcomes
            similar_batchers = await self._find_owners_with_better_outcomes(
                recipient_id,
                target_pref={"batch_settings": {"enabled": True}},
            )
            
            if similar_batchers:
                improvement = similar_batchers[0].get("response_time_improvement", 25)
                
                return Recommendation(
                    recipient_id=recipient_id,
                    recipient_type=recipient_type,
                    recommendation_type=RecommendationType.BATCH_VS_REALTIME,
                    title="Try Batch Processing for Customer Inquiries",
                    description=(
                        f"Your current response time is {business.avg_response_time_hours:.1f} hours. "
                        f"Store owners who batch customer inquiries into daily summaries maintain 95%+ "
                        f"satisfaction but improve efficiency by {improvement:.0f}%. "
                        f"Estimated response time with batching: {business.avg_response_time_hours * 0.75:.1f} hours."
                    ),
                    suggested_changes={
                        "batch_settings": {
                            "enabled": True,
                            "frequency": "daily_digest",
                        }
                    },
                    expected_outcome=f"Reduce response time by ~{improvement:.0f}%",
                    expected_metrics={
                        "response_time_improvement_pct": improvement,
                        "efficiency_gain": 0.25,
                    },
                    cohort_basis="batch_processing_owners",
                    similar_users_count=len(similar_batchers),
                    similar_users_improvement=improvement,
                    priority_score=75,
                    relevance_reason=f"Your response time of {business.avg_response_time_hours:.1f}h is above optimal",
                )
        
        # If response time is good but satisfaction is low, suggest real-time
        if batch_enabled and business.avg_satisfaction_score and business.avg_satisfaction_score < 3.5:
            return Recommendation(
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                recommendation_type=RecommendationType.BATCH_VS_REALTIME,
                title="Switch to Real-Time Notifications",
                description=(
                    f"Your satisfaction score is {business.avg_satisfaction_score:.1f}/5. "
                    f"Switching to real-time notifications may help you respond faster to urgent "
                    f"customer inquiries and improve satisfaction."
                ),
                suggested_changes={
                    "batch_settings": {"enabled": False}
                },
                expected_outcome="Improve customer satisfaction",
                expected_metrics={
                    "satisfaction_improvement": 0.5,
                },
                priority_score=70,
                relevance_reason=f"Your satisfaction score of {business.avg_satisfaction_score:.1f} suggests room for improvement",
            )
        
        return None
    
    async def _find_similar_users_with_better_engagement(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        current_prefs: PreferenceSnapshot,
        target_pref: Dict[str, Any],
        metric: str = "engagement_score",
    ) -> List[Dict[str, Any]]:
        """Find users with similar base preferences but target_pref who have better engagement."""
        
        query = text("""
            WITH similar_users AS (
                SELECT 
                    em.recipient_id,
                    em.engagement_score,
                    em.overall_open_rate,
                    em.overall_click_rate,
                    em.active_preferences
                FROM engagement_metrics em
                WHERE em.recipient_type = :recipient_type
                  AND em.period_type = 'weekly'
                  AND em.period_start >= :recent_date
                  AND em.recipient_id != :recipient_id
                  AND em.active_preferences->>'global_enabled' = 'true'
            ),
            target_users AS (
                SELECT 
                    su.recipient_id,
                    su.engagement_score,
                    su.overall_open_rate,
                    su.active_preferences
                FROM similar_users su
                WHERE su.active_preferences @> :target_pref::jsonb
            )
            SELECT 
                COUNT(*) AS user_count,
                AVG(engagement_score) AS avg_engagement,
                AVG(overall_open_rate) AS avg_open_rate
            FROM target_users
        """)
        
        result = await self.db.execute(query, {
            "recipient_type": recipient_type.value,
            "recipient_id": recipient_id,
            "recent_date": datetime.utcnow() - timedelta(days=30),
            "target_pref": json.dumps(target_pref),
        })
        row = result.fetchone()
        
        if not row or row.user_count < self.MIN_SIMILAR_USERS_FOR_RECOMMENDATION:
            return []
        
        # Get current user's engagement for comparison
        current_engagement = await self.calculate_engagement_metrics(
            recipient_id, recipient_type,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow(),
        )
        
        improvement = 0
        if current_engagement.engagement_score > 0:
            improvement = ((row.avg_engagement or 0) - current_engagement.engagement_score) / current_engagement.engagement_score * 100
        
        return [{
            "user_count": row.user_count,
            "avg_engagement": row.avg_engagement,
            "avg_open_rate": row.avg_open_rate,
            "improvement_pct": max(improvement, 0),
        }]
    
    async def _find_owners_with_better_outcomes(
        self,
        owner_id: str,
        target_pref: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find store owners with target preferences who have better business outcomes."""
        
        query = text("""
            SELECT 
                COUNT(*) AS owner_count,
                AVG(avg_response_time_hours) AS avg_response_time,
                AVG(avg_satisfaction_score) AS avg_satisfaction
            FROM business_outcomes bo
            JOIN notification_preferences np ON np.recipient_id = bo.owner_id
            WHERE bo.owner_id != :owner_id
              AND np.batch_settings @> :target_pref::jsonb
              AND bo.period_start >= :recent_date
        """)
        
        result = await self.db.execute(query, {
            "owner_id": owner_id,
            "target_pref": json.dumps(target_pref),
            "recent_date": datetime.utcnow() - timedelta(days=30),
        })
        row = result.fetchone()
        
        if not row or row.owner_count < 5:
            return []
        
        return [{
            "owner_count": row.owner_count,
            "avg_response_time": row.avg_response_time,
            "avg_satisfaction": row.avg_satisfaction,
            "response_time_improvement": 25,  # Estimated improvement
        }]
    
    async def _get_current_preferences(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
    ) -> PreferenceSnapshot:
        """Get user's current preferences."""
        
        query = text("""
            SELECT 
                global_enabled,
                in_app_enabled, in_app_frequency,
                email_enabled, email_frequency,
                push_enabled, push_frequency,
                toast_enabled, toast_frequency,
                notification_types,
                batch_settings
            FROM notification_preferences
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
        """)
        
        result = await self.db.execute(query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
        })
        row = result.fetchone()
        
        if not row:
            return PreferenceSnapshot(
                recipient_id=recipient_id,
                recipient_type=recipient_type,
            )
        
        return PreferenceSnapshot(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            global_enabled=row.global_enabled,
            channels={
                "in_app": {"enabled": row.in_app_enabled, "frequency": row.in_app_frequency},
                "email": {"enabled": row.email_enabled, "frequency": row.email_frequency},
                "push": {"enabled": row.push_enabled, "frequency": row.push_frequency},
                "toast": {"enabled": row.toast_enabled, "frequency": row.toast_frequency},
            },
            notification_types=row.notification_types or {},
            batch_settings=row.batch_settings or {},
        )
    
    async def _get_pending_recommendations(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
    ) -> List[Recommendation]:
        """Get existing pending recommendations for a user."""
        
        query = text("""
            SELECT 
                id,
                recommendation_type,
                title,
                description,
                suggested_changes,
                expected_outcome,
                expected_metrics,
                cohort_basis,
                similar_users_count,
                similar_users_improvement,
                priority_score,
                relevance_reason
            FROM preference_recommendations
            WHERE recipient_id = :recipient_id
              AND recipient_type = :recipient_type
              AND status = 'pending'
              AND expires_at > NOW()
            ORDER BY priority_score DESC
        """)
        
        result = await self.db.execute(query, {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
        })
        rows = result.fetchall()
        
        return [
            Recommendation(
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                recommendation_type=RecommendationType(row.recommendation_type),
                title=row.title,
                description=row.description,
                suggested_changes=row.suggested_changes,
                expected_outcome=row.expected_outcome,
                expected_metrics=row.expected_metrics,
                cohort_basis=row.cohort_basis,
                similar_users_count=row.similar_users_count,
                similar_users_improvement=row.similar_users_improvement,
                priority_score=row.priority_score,
                relevance_reason=row.relevance_reason,
            )
            for row in rows
        ]
    
    async def _store_recommendation(self, recommendation: Recommendation) -> str:
        """Store a recommendation in the database."""
        
        query = text("""
            INSERT INTO preference_recommendations (
                recipient_id, recipient_type, recommendation_type,
                title, description, suggested_changes,
                expected_outcome, expected_metrics,
                cohort_basis, similar_users_count, similar_users_improvement,
                priority_score, relevance_reason, status
            ) VALUES (
                :recipient_id, :recipient_type, :recommendation_type,
                :title, :description, :suggested_changes,
                :expected_outcome, :expected_metrics,
                :cohort_basis, :similar_users_count, :similar_users_improvement,
                :priority_score, :relevance_reason, 'pending'
            )
            RETURNING id
        """)
        
        result = await self.db.execute(query, {
            "recipient_id": recommendation.recipient_id,
            "recipient_type": recommendation.recipient_type.value,
            "recommendation_type": recommendation.recommendation_type.value,
            "title": recommendation.title,
            "description": recommendation.description,
            "suggested_changes": json.dumps(recommendation.suggested_changes),
            "expected_outcome": recommendation.expected_outcome,
            "expected_metrics": json.dumps(recommendation.expected_metrics),
            "cohort_basis": recommendation.cohort_basis,
            "similar_users_count": recommendation.similar_users_count,
            "similar_users_improvement": recommendation.similar_users_improvement,
            "priority_score": recommendation.priority_score,
            "relevance_reason": recommendation.relevance_reason,
        })
        await self.db.commit()
        
        return str(result.fetchone().id)
    
    async def accept_recommendation(
        self,
        recommendation_id: str,
        recipient_id: str,
    ) -> Dict[str, Any]:
        """Accept and apply a recommendation."""
        
        # Get recommendation
        query = text("""
            SELECT * FROM preference_recommendations
            WHERE id = :id AND recipient_id = :recipient_id AND status = 'pending'
        """)
        
        result = await self.db.execute(query, {
            "id": recommendation_id,
            "recipient_id": recipient_id,
        })
        row = result.fetchone()
        
        if not row:
            return {"success": False, "error": "Recommendation not found or already processed"}
        
        # Apply the suggested changes
        changes = row.suggested_changes
        
        # Update preferences
        update_result = await self._apply_preference_changes(
            recipient_id,
            RecipientType(row.recipient_type),
            changes,
            trigger_source="system_recommended",
            recommendation_id=recommendation_id,
        )
        
        # Mark recommendation as accepted
        await self.db.execute(
            text("""
                UPDATE preference_recommendations
                SET status = 'accepted', responded_at = NOW(), applied_at = NOW()
                WHERE id = :id
            """),
            {"id": recommendation_id},
        )
        
        await self.db.commit()
        
        return {
            "success": True,
            "applied_changes": changes,
            "new_preferences": update_result,
        }
    
    async def reject_recommendation(
        self,
        recommendation_id: str,
        recipient_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject a recommendation."""
        
        query = text("""
            UPDATE preference_recommendations
            SET status = 'rejected', responded_at = NOW()
            WHERE id = :id AND recipient_id = :recipient_id AND status = 'pending'
        """)
        
        result = await self.db.execute(query, {
            "id": recommendation_id,
            "recipient_id": recipient_id,
        })
        
        if result.rowcount == 0:
            return {"success": False, "error": "Recommendation not found or already processed"}
        
        await self.db.commit()
        
        return {"success": True}
    
    async def _apply_preference_changes(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        changes: Dict[str, Any],
        trigger_source: str = "user_initiated",
        recommendation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply preference changes to database."""
        
        # Build update query based on changes
        update_fields = []
        params = {
            "recipient_id": recipient_id,
            "recipient_type": recipient_type.value,
        }
        
        if "channels" in changes:
            for channel, settings in changes["channels"].items():
                if "enabled" in settings:
                    update_fields.append(f"{channel}_enabled = :{channel}_enabled")
                    params[f"{channel}_enabled"] = settings["enabled"]
                if "frequency" in settings:
                    update_fields.append(f"{channel}_frequency = :{channel}_frequency")
                    params[f"{channel}_frequency"] = settings["frequency"]
        
        if "batch_settings" in changes:
            update_fields.append("batch_settings = :batch_settings")
            params["batch_settings"] = json.dumps(changes["batch_settings"])
        
        if not update_fields:
            return {}
        
        update_fields.append("updated_at = NOW()")
        
        query = text(f"""
            UPDATE notification_preferences
            SET {', '.join(update_fields)}
            WHERE recipient_id = :recipient_id AND recipient_type = :recipient_type
            RETURNING *
        """)
        
        result = await self.db.execute(query, params)
        row = result.fetchone()
        
        return dict(row._mapping) if row else {}
    
    # -------------------------------------------------------------------------
    # COHORT MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def assign_user_to_cohorts(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
    ) -> List[str]:
        """Assign user to appropriate cohorts based on their preferences."""
        
        prefs = await self._get_current_preferences(recipient_id, recipient_type)
        
        # Get all applicable cohorts
        query = text("""
            SELECT id, cohort_name, cohort_slug, definition
            FROM user_cohorts
            WHERE recipient_type IS NULL OR recipient_type = :recipient_type
        """)
        
        result = await self.db.execute(query, {
            "recipient_type": recipient_type.value,
        })
        cohorts = result.fetchall()
        
        assigned_cohorts = []
        
        for cohort in cohorts:
            definition = cohort.definition
            
            # Check if user matches cohort definition
            matches = self._matches_cohort(prefs, definition)
            
            if matches:
                # Add to cohort membership
                await self.db.execute(
                    text("""
                        INSERT INTO user_cohort_membership (cohort_id, recipient_id, recipient_type)
                        VALUES (:cohort_id, :recipient_id, :recipient_type)
                        ON CONFLICT (cohort_id, recipient_id, recipient_type, joined_at) 
                        DO UPDATE SET exited_at = NULL
                    """),
                    {
                        "cohort_id": cohort.id,
                        "recipient_id": recipient_id,
                        "recipient_type": recipient_type.value,
                    },
                )
                assigned_cohorts.append(cohort.cohort_slug)
            else:
                # Remove from cohort if currently member
                await self.db.execute(
                    text("""
                        UPDATE user_cohort_membership
                        SET exited_at = NOW()
                        WHERE cohort_id = :cohort_id
                          AND recipient_id = :recipient_id
                          AND recipient_type = :recipient_type
                          AND exited_at IS NULL
                    """),
                    {
                        "cohort_id": cohort.id,
                        "recipient_id": recipient_id,
                        "recipient_type": recipient_type.value,
                    },
                )
        
        await self.db.commit()
        
        return assigned_cohorts
    
    def _matches_cohort(
        self,
        prefs: PreferenceSnapshot,
        definition: Dict[str, Any],
    ) -> bool:
        """Check if preferences match cohort definition."""
        
        for key, value in definition.items():
            if key.endswith("_min") or key.endswith("_max"):
                continue  # Skip comparison keys
            
            if key == "email_frequency":
                actual = prefs.channels.get("email", {}).get("frequency")
                if actual != value:
                    return False
            elif key == "push_enabled":
                actual = prefs.channels.get("push", {}).get("enabled", True)
                if actual != value:
                    return False
            elif key == "in_app_enabled":
                actual = prefs.channels.get("in_app", {}).get("enabled", True)
                if actual != value:
                    return False
            elif key == "batch_settings":
                batch_def = value
                actual_batch = prefs.batch_settings
                for bk, bv in batch_def.items():
                    if actual_batch.get(bk) != bv:
                        return False
        
        return True
    
    async def get_cohort_statistics(
        self,
        cohort_slug: str,
    ) -> Dict[str, Any]:
        """Get statistics for a cohort."""
        
        query = text("""
            SELECT 
                uc.cohort_name,
                uc.member_count,
                uc.avg_engagement_score,
                uc.avg_open_rate,
                uc.avg_click_rate,
                uc.avg_ignore_rate,
                uc.avg_response_time_hours,
                uc.avg_satisfaction_score
            FROM user_cohorts uc
            WHERE uc.cohort_slug = :cohort_slug
        """)
        
        result = await self.db.execute(query, {"cohort_slug": cohort_slug})
        row = result.fetchone()
        
        if not row:
            return {}
        
        return {
            "cohort_name": row.cohort_name,
            "member_count": row.member_count,
            "avg_engagement_score": row.avg_engagement_score,
            "avg_open_rate": row.avg_open_rate,
            "avg_click_rate": row.avg_click_rate,
            "avg_ignore_rate": row.avg_ignore_rate,
            "avg_response_time_hours": row.avg_response_time_hours,
            "avg_satisfaction_score": row.avg_satisfaction_score,
        }
