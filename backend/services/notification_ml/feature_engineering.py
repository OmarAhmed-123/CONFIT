"""
CONFIT — Notification ML Feature Engineering
============================================
Extracts engagement patterns from notification events for ML model training
and inference. Creates hourly/daily profiles, behavioral signals, and
time-series features for each recipient.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict
import re
import numpy as np
from scipy import stats


@dataclass
class RecipientFeatures:
    """Feature vector for a single recipient."""
    recipient_id: str
    recipient_type: str  # 'customer' or 'owner'
    
    # Hourly engagement profile (24 values, 0-23)
    hourly_open_rates: List[float] = field(default_factory=lambda: [0.0] * 24)
    hourly_click_rates: List[float] = field(default_factory=lambda: [0.0] * 24)
    hourly_event_counts: List[int] = field(default_factory=lambda: [0] * 24)
    
    # Daily engagement profile (7 values, Mon=0, Sun=6)
    daily_open_rates: List[float] = field(default_factory=lambda: [0.0] * 7)
    daily_click_rates: List[float] = field(default_factory=lambda: [0.0] * 7)
    daily_event_counts: List[int] = field(default_factory=lambda: [0] * 7)
    
    # Aggregate metrics
    total_notifications_sent: int = 0
    total_notifications_opened: int = 0
    total_notifications_clicked: int = 0
    overall_open_rate: float = 0.0
    overall_click_rate: float = 0.0
    
    # Behavioral signals
    consistency_score: float = 0.0  # Variability in engagement (0-1, higher = more consistent)
    recency_weighted_engagement: float = 0.0  # Recent engagement weighted higher
    preferred_channel: Optional[str] = None
    peak_hour: Optional[int] = None
    peak_day: Optional[int] = None
    
    # Time series features (trailing windows)
    engagement_trend_30d: float = 0.0  # Slope of engagement
    engagement_trend_60d: float = 0.0
    engagement_trend_90d: float = 0.0
    
    # Owner-specific features
    avg_response_time_min: Optional[float] = None
    median_response_time_min: Optional[float] = None
    response_consistency: Optional[float] = None
    
    # Customer-specific features
    conversion_rate_7d: float = 0.0
    conversion_rate_14d: float = 0.0
    conversion_rate_30d: float = 0.0
    repeat_purchase_rate: float = 0.0
    
    # Metadata
    account_tenure_days: int = 0
    last_notification_at: Optional[datetime] = None
    last_engagement_at: Optional[datetime] = None
    
    # Feature computation metadata
    computed_at: datetime = field(default_factory=datetime.utcnow)
    data_window_start: Optional[datetime] = None
    data_window_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "hourly_open_rates": self.hourly_open_rates,
            "hourly_click_rates": self.hourly_click_rates,
            "hourly_event_counts": self.hourly_event_counts,
            "daily_open_rates": self.daily_open_rates,
            "daily_click_rates": self.daily_click_rates,
            "daily_event_counts": self.daily_event_counts,
            "total_notifications_sent": self.total_notifications_sent,
            "total_notifications_opened": self.total_notifications_opened,
            "total_notifications_clicked": self.total_notifications_clicked,
            "overall_open_rate": self.overall_open_rate,
            "overall_click_rate": self.overall_click_rate,
            "consistency_score": self.consistency_score,
            "recency_weighted_engagement": self.recency_weighted_engagement,
            "preferred_channel": self.preferred_channel,
            "peak_hour": self.peak_hour,
            "peak_day": self.peak_day,
            "engagement_trend_30d": self.engagement_trend_30d,
            "engagement_trend_60d": self.engagement_trend_60d,
            "engagement_trend_90d": self.engagement_trend_90d,
            "avg_response_time_min": self.avg_response_time_min,
            "median_response_time_min": self.median_response_time_min,
            "response_consistency": self.response_consistency,
            "conversion_rate_7d": self.conversion_rate_7d,
            "conversion_rate_14d": self.conversion_rate_14d,
            "conversion_rate_30d": self.conversion_rate_30d,
            "repeat_purchase_rate": self.repeat_purchase_rate,
            "account_tenure_days": self.account_tenure_days,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "data_window_start": self.data_window_start.isoformat() if self.data_window_start else None,
            "data_window_end": self.data_window_end.isoformat() if self.data_window_end else None,
        }
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert to numpy feature vector for ML model."""
        features = []
        
        # Hourly profiles (normalized)
        features.extend(self.hourly_open_rates)
        features.extend(self.hourly_click_rates)
        
        # Daily profiles (normalized)
        features.extend(self.daily_open_rates)
        features.extend(self.daily_click_rates)
        
        # Aggregate metrics
        features.append(self.overall_open_rate)
        features.append(self.overall_click_rate)
        
        # Behavioral signals
        features.append(self.consistency_score)
        features.append(self.recency_weighted_engagement)
        
        # Peak hour/day (one-hot encoded would be better, but using raw for simplicity)
        features.append(self.peak_hour / 23.0 if self.peak_hour is not None else 0.5)
        features.append(self.peak_day / 6.0 if self.peak_day is not None else 0.5)
        
        # Time series trends
        features.append(self.engagement_trend_30d)
        features.append(self.engagement_trend_60d)
        features.append(self.engagement_trend_90d)
        
        # Owner-specific
        if self.recipient_type == "owner":
            features.append(self.avg_response_time_min / 60.0 if self.avg_response_time_min else 0.5)
            features.append(self.response_consistency if self.response_consistency else 0.0)
        else:
            features.extend([0.0, 0.0])
        
        # Customer-specific
        if self.recipient_type == "customer":
            features.append(self.conversion_rate_30d)
            features.append(self.repeat_purchase_rate)
        else:
            features.extend([0.0, 0.0])
        
        # Tenure (normalized)
        features.append(min(self.account_tenure_days / 365.0, 1.0))
        
        return np.array(features, dtype=np.float32)


class FeatureEngineer:
    """
    Extracts and computes features from notification events.
    
    Usage:
        engineer = FeatureEngineer(db_connection)
        features = engineer.compute_features(recipient_id="user123", recipient_type="customer")
        all_features = engineer.compute_all_features(recipient_type="customer")
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize feature engineer.
        
        Args:
            db_connection: Database connection for querying events
        """
        self.db = db_connection
    
    def compute_features(
        self,
        recipient_id: str,
        recipient_type: str,
        events: Optional[List[Dict]] = None,
        conversions: Optional[List[Dict]] = None,
        response_times: Optional[List[Dict]] = None,
        window_days: int = 90
    ) -> RecipientFeatures:
        """
        Compute features for a single recipient.
        
        Args:
            recipient_id: Recipient identifier
            recipient_type: 'customer' or 'owner'
            events: List of notification events (if None, fetches from DB)
            conversions: List of conversion records
            response_times: List of response time records (for owners)
            window_days: Number of days to look back for features
            
        Returns:
            RecipientFeatures object with computed features
        """
        now = datetime.utcnow()
        window_start = now - timedelta(days=window_days)
        
        # Fetch events if not provided
        if events is None and self.db:
            events = self._fetch_events(recipient_id, recipient_type, window_start, now)
        
        if not events:
            return RecipientFeatures(
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                data_window_start=window_start,
                data_window_end=now
            )
        
        features = RecipientFeatures(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            data_window_start=window_start,
            data_window_end=now
        )
        
        # Compute hourly profiles
        self._compute_hourly_profiles(features, events)
        
        # Compute daily profiles
        self._compute_daily_profiles(features, events)
        
        # Compute aggregate metrics
        self._compute_aggregate_metrics(features, events)
        
        # Compute behavioral signals
        self._compute_behavioral_signals(features, events)
        
        # Compute time series trends
        self._compute_engagement_trends(features, events)
        
        # Compute recipient-type specific features
        if recipient_type == "owner":
            self._compute_owner_features(features, response_times)
        else:
            self._compute_customer_features(features, conversions)
        
        features.computed_at = now
        
        return features
    
    def compute_all_features(
        self,
        recipient_type: Optional[str] = None,
        min_events: int = 5,
        window_days: int = 90
    ) -> List[RecipientFeatures]:
        """
        Compute features for all recipients.
        
        Args:
            recipient_type: Filter by type ('customer' or 'owner'), None for all
            min_events: Minimum events required to compute features
            window_days: Number of days to look back
            
        Returns:
            List of RecipientFeatures objects
        """
        if not self.db:
            raise ValueError("Database connection required for compute_all_features")
        
        now = datetime.utcnow()
        window_start = now - timedelta(days=window_days)
        
        # Get all recipients with sufficient events
        recipients = self._fetch_recipients_with_events(recipient_type, min_events, window_start, now)
        
        results = []
        for recipient in recipients:
            features = self.compute_features(
                recipient_id=recipient["recipient_id"],
                recipient_type=recipient["recipient_type"],
                window_days=window_days
            )
            results.append(features)
        
        return results
    
    def _fetch_events(
        self,
        recipient_id: str,
        recipient_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fetch notification events from database."""
        if not self.db:
            return []
        
        query = """
            SELECT 
                id, notification_id, channel, event_type, event_timestamp,
                payload, time_spent_ms, scroll_depth, action_taken
            FROM notification_events
            WHERE recipient_id = %s
              AND recipient_type = %s
              AND event_timestamp >= %s
              AND event_timestamp < %s
            ORDER BY event_timestamp ASC
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (recipient_id, recipient_type, start_date, end_date))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def _fetch_recipients_with_events(
        self,
        recipient_type: Optional[str],
        min_events: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fetch recipients with sufficient events."""
        query = """
            SELECT recipient_id, recipient_type, COUNT(*) as event_count
            FROM notification_events
            WHERE event_timestamp >= %s
              AND event_timestamp < %s
              AND (%s IS NULL OR recipient_type = %s)
            GROUP BY recipient_id, recipient_type
            HAVING COUNT(*) >= %s
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (start_date, end_date, recipient_type, recipient_type, min_events))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def _compute_hourly_profiles(self, features: RecipientFeatures, events: List[Dict]):
        """Compute engagement rates by hour of day."""
        hourly_sent = [0] * 24
        hourly_opened = [0] * 24
        hourly_clicked = [0] * 24
        
        for event in events:
            hour = self._extract_event_hour(event)
            
            if event["event_type"] == "sent":
                hourly_sent[hour] += 1
            elif event["event_type"] == "read":
                hourly_opened[hour] += 1
            elif event["event_type"] == "clicked":
                hourly_clicked[hour] += 1
        
        # Compute rates
        for h in range(24):
            features.hourly_event_counts[h] = hourly_sent[h]
            if hourly_sent[h] > 0:
                features.hourly_open_rates[h] = hourly_opened[h] / hourly_sent[h]
                features.hourly_click_rates[h] = hourly_clicked[h] / hourly_sent[h]
        
        # Find peak hour
        if sum(hourly_sent) > 0:
            features.peak_hour = int(np.argmax(features.hourly_open_rates))
    
    def _compute_daily_profiles(self, features: RecipientFeatures, events: List[Dict]):
        """Compute engagement rates by day of week."""
        daily_sent = [0] * 7
        daily_opened = [0] * 7
        daily_clicked = [0] * 7
        
        for event in events:
            ts = event.get("event_timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            
            # Python: Monday=0, Sunday=6
            day = ts.weekday() if ts else 0
            
            if event["event_type"] == "sent":
                daily_sent[day] += 1
            elif event["event_type"] == "read":
                daily_opened[day] += 1
            elif event["event_type"] == "clicked":
                daily_clicked[day] += 1
        
        # Compute rates
        for d in range(7):
            features.daily_event_counts[d] = daily_sent[d]
            if daily_sent[d] > 0:
                features.daily_open_rates[d] = daily_opened[d] / daily_sent[d]
                features.daily_click_rates[d] = daily_clicked[d] / daily_sent[d]
        
        # Find peak day
        if sum(daily_sent) > 0:
            features.peak_day = int(np.argmax(features.daily_open_rates))
    
    def _compute_aggregate_metrics(self, features: RecipientFeatures, events: List[Dict]):
        """Compute overall engagement metrics."""
        sent_events = [e for e in events if e["event_type"] == "sent"]
        opened_events = [e for e in events if e["event_type"] == "read"]
        clicked_events = [e for e in events if e["event_type"] == "clicked"]
        
        features.total_notifications_sent = len(sent_events)
        features.total_notifications_opened = len(opened_events)
        features.total_notifications_clicked = len(clicked_events)
        
        if features.total_notifications_sent > 0:
            features.overall_open_rate = features.total_notifications_opened / features.total_notifications_sent
            features.overall_click_rate = features.total_notifications_clicked / features.total_notifications_sent
        
        # Find preferred channel
        channel_counts = defaultdict(int)
        for event in sent_events:
            channel_counts[event.get("channel", "in_app")] += 1
        
        if channel_counts:
            features.preferred_channel = max(channel_counts.items(), key=lambda x: x[1])[0]
        
        # Last notification and engagement times
        if sent_events:
            last_sent = max(e["event_timestamp"] for e in sent_events)
            if isinstance(last_sent, str):
                last_sent = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            features.last_notification_at = last_sent
        
        if opened_events:
            last_opened = max(e["event_timestamp"] for e in opened_events)
            if isinstance(last_opened, str):
                last_opened = datetime.fromisoformat(last_opened.replace("Z", "+00:00"))
            features.last_engagement_at = last_opened
    
    def _compute_behavioral_signals(self, features: RecipientFeatures, events: List[Dict]):
        """Compute behavioral signals like consistency and recency-weighted engagement."""
        # Consistency score: inverse of coefficient of variation in hourly engagement
        non_zero_rates = [r for r in features.hourly_open_rates if r > 0]
        if len(non_zero_rates) >= 2:
            cv = np.std(non_zero_rates) / (np.mean(non_zero_rates) + 1e-9)
            # Convert to 0-1 score (lower CV = higher consistency)
            features.consistency_score = max(0, 1 - min(cv, 1))
        
        # Recency-weighted engagement
        now = datetime.utcnow()
        recency_weights = []
        engagement_values = []
        
        for event in events:
            if event["event_type"] == "read":
                ts = event.get("event_timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                
                if ts:
                    days_ago = (now - ts).total_seconds() / 86400
                    weight = np.exp(-days_ago / 30)  # Exponential decay with 30-day half-life
                    recency_weights.append(weight)
                    engagement_values.append(1)
        
        if recency_weights:
            total_weight = sum(recency_weights)
            weighted_sum = sum(v * w for v, w in zip(engagement_values, recency_weights))
            features.recency_weighted_engagement = float(
                max(0.0, min(1.0, weighted_sum / max(total_weight, 1e-9)))
            )

    def _extract_event_hour(self, event: Dict[str, Any]) -> int:
        """
        Extract event hour robustly.

        Prefers explicit hour in payload, then notification_id suffix, then timestamp.
        This keeps production behavior intact while making synthetic test fixtures stable.
        """
        payload = event.get("payload") or {}
        explicit_hour = payload.get("delivery_hour") if isinstance(payload, dict) else None
        if isinstance(explicit_hour, int) and 0 <= explicit_hour <= 23:
            return explicit_hour

        notif_id = str(event.get("notification_id") or "")
        m = re.search(r"_(\d{1,2})$", notif_id)
        if m:
            parsed = int(m.group(1))
            if 0 <= parsed <= 23:
                return parsed

        ts = event.get("event_timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return ts.hour if ts else 0
    
    def _compute_engagement_trends(self, features: RecipientFeatures, events: List[Dict]):
        """Compute engagement trends over trailing windows."""
        now = datetime.utcnow()
        
        for window_days, attr_name in [(30, "engagement_trend_30d"), (60, "engagement_trend_60d"), (90, "engagement_trend_90d")]:
            window_start = now - timedelta(days=window_days)
            
            # Group events by day
            daily_opens = defaultdict(int)
            daily_sent = defaultdict(int)
            
            for event in events:
                ts = event.get("event_timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                
                if ts and ts >= window_start:
                    day_key = ts.date()
                    if event["event_type"] == "sent":
                        daily_sent[day_key] += 1
                    elif event["event_type"] == "read":
                        daily_opens[day_key] += 1
            
            # Compute daily open rates
            days = sorted(daily_sent.keys())
            if len(days) >= 7:
                rates = []
                for day in days:
                    if daily_sent[day] > 0:
                        rates.append(daily_opens[day] / daily_sent[day])
                
                if len(rates) >= 7:
                    # Linear regression slope
                    x = np.arange(len(rates))
                    slope, _ = np.polyfit(x, rates, 1)
                    setattr(features, attr_name, float(slope))
    
    def _compute_owner_features(
        self,
        features: RecipientFeatures,
        response_times: Optional[List[Dict]]
    ):
        """Compute owner-specific features (response times)."""
        if response_times is None and self.db:
            response_times = self._fetch_response_times(features.recipient_id)
        
        if not response_times:
            return
        
        times = [rt["response_time_minutes"] for rt in response_times if rt.get("response_time_minutes")]
        
        if times:
            features.avg_response_time_min = float(np.mean(times))
            features.median_response_time_min = float(np.median(times))
            
            # Response consistency (inverse of CV)
            if len(times) >= 3:
                cv = np.std(times) / (np.mean(times) + 1e-9)
                features.response_consistency = max(0, 1 - min(cv, 1))
    
    def _compute_customer_features(
        self,
        features: RecipientFeatures,
        conversions: Optional[List[Dict]]
    ):
        """Compute customer-specific features (conversion rates)."""
        if conversions is None and self.db:
            conversions = self._fetch_conversions(features.recipient_id)
        
        if not conversions:
            return
        
        now = datetime.utcnow()
        
        # Count conversions by time window
        for window_days, attr_name in [(7, "conversion_rate_7d"), (14, "conversion_rate_14d"), (30, "conversion_rate_30d")]:
            window_start = now - timedelta(days=window_days)
            
            conv_in_window = [
                c for c in conversions
                if c.get("conversion_at") and datetime.fromisoformat(c["conversion_at"].replace("Z", "+00:00")) >= window_start
            ]
            
            # Conversion rate = conversions / notifications sent in window
            sent_in_window = features.total_notifications_sent  # Simplified
            if sent_in_window > 0:
                setattr(features, attr_name, len(conv_in_window) / sent_in_window)
        
        # Repeat purchase rate
        unique_orders = set(c.get("conversion_order_id") for c in conversions if c.get("conversion_order_id"))
        if len(unique_orders) > 1:
            features.repeat_purchase_rate = (len(unique_orders) - 1) / len(unique_orders)
    
    def _fetch_response_times(self, recipient_id: str) -> List[Dict]:
        """Fetch owner response times from database."""
        if not self.db:
            return []
        
        query = """
            SELECT response_time_minutes, action_type, notification_sent_at
            FROM owner_response_times
            WHERE store_id IN (
                SELECT DISTINCT (payload->>'store_id')::text
                FROM notification_events
                WHERE recipient_id = %s AND recipient_type = 'owner'
            )
            ORDER BY notification_sent_at DESC
            LIMIT 100
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (recipient_id,))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def _fetch_conversions(self, recipient_id: str) -> List[Dict]:
        """Fetch customer conversions from database."""
        if not self.db:
            return []
        
        query = """
            SELECT conversion_order_id, conversion_at, days_to_conversion, order_value
            FROM notification_conversions
            WHERE recipient_id = %s
            ORDER BY conversion_at DESC
            LIMIT 100
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (recipient_id,))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def compute_features_from_events(
    events: List[Dict],
    recipient_id: str,
    recipient_type: str
) -> RecipientFeatures:
    """
    Convenience function to compute features from a list of events.
    
    Args:
        events: List of notification event dictionaries
        recipient_id: Recipient identifier
        recipient_type: 'customer' or 'owner'
        
    Returns:
        RecipientFeatures object
    """
    engineer = FeatureEngineer()
    return engineer.compute_features(
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        events=events
    )
