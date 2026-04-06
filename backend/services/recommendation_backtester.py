"""
CONFIT Backend — Recommendation Backtester
==========================================
Validates recommendations against historical data to prove their value.
Calculates precision, recall, false positive rate, and significant moments caught.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.models import Order, OrderItem, Product, Customer
from database.alert_recommendation_models import AlertRecommendation, RecommendationType
from schemas.alert_recommendation_schemas import (
    BacktestEvent,
    BacktestSummary,
    BacktestEventType,
)

logger = logging.getLogger(__name__)


# ─── Constants ─────────────────────────────────────────────────────────────────

# Minimum deviation to consider an event "significant"
SIGNIFICANT_DEVIATION_THRESHOLD = 0.5  # 50% deviation

# Actionability thresholds
ACTIONABLE_RETURN_SPIKE = 3  # 3+ returns in window is actionable
ACTIONABLE_AOV_MULTIPLIER = 1.3  # 30%+ above threshold is actionable


class RecommendationBacktester:
    """
    Backtests recommendations against historical data.
    Validates that recommended thresholds would have caught significant moments
    without generating excessive false positives.
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    def backtest_recommendation(
        self,
        recommendation: Dict[str, Any],
        store_id: str,
        data_window_days: int = 60,
    ) -> BacktestSummary:
        """
        Backtest a single recommendation against historical data.
        Returns summary of how the threshold would have performed.
        """
        rec_type = recommendation.get("type")
        
        if rec_type == RecommendationType.RETURN_SPIKE.value:
            return self._backtest_return_spike(recommendation, store_id, data_window_days)
        elif rec_type == RecommendationType.HIGH_VALUE_AOV.value:
            return self._backtest_aov_threshold(recommendation, store_id, data_window_days)
        elif rec_type == RecommendationType.CONVERSION_ANOMALY.value:
            return self._backtest_conversion_anomaly(recommendation, store_id, data_window_days)
        elif rec_type == RecommendationType.VIP_INACTIVITY.value:
            return self._backtest_vip_inactivity(recommendation, store_id, data_window_days)
        else:
            # Default backtest
            return self._create_empty_summary(data_window_days)
    
    def _backtest_return_spike(
        self,
        recommendation: Dict[str, Any],
        store_id: str,
        data_window_days: int,
    ) -> BacktestSummary:
        """Backtest return spike threshold recommendation."""
        window_start = datetime.now(timezone.utc) - timedelta(days=data_window_days)
        
        # Get recommended threshold
        threshold_data = recommendation.get("thresholds", [{}])[0]
        recommended_threshold = threshold_data.get("recommended_value", 20)
        
        # Get return data grouped by week
        returns = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == store_id,
            Order.status == 'returned',
            Order.updated_at >= window_start
        ).all()
        
        # Group by week
        weekly_returns = defaultdict(int)
        for order in returns:
            week_num = order.updated_at.isocalendar()[1]
            weekly_returns[week_num] += 1
        
        weekly_values = list(weekly_returns.values()) if weekly_returns else [0]
        baseline = statistics.mean(weekly_values) if weekly_values else 0
        
        # Calculate events
        events = []
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        significant_moments_caught = 0
        significant_moments_missed = 0
        
        for week, count in weekly_returns.items():
            would_alert = count >= recommended_threshold
            
            # Determine if this was a significant event
            is_significant = count >= baseline * (1 + SIGNIFICANT_DEVIATION_THRESHOLD)
            is_actionable = count >= ACTIONABLE_RETURN_SPIKE
            
            # Classify the event
            if would_alert and is_significant:
                event_type = BacktestEventType.TRUE_POSITIVE
                true_positives += 1
                if is_actionable:
                    significant_moments_caught += 1
            elif would_alert and not is_significant:
                event_type = BacktestEventType.FALSE_POSITIVE
                false_positives += 1
            elif not would_alert and not is_significant:
                event_type = BacktestEventType.TRUE_NEGATIVE
                true_negatives += 1
            else:  # not would_alert and is_significant
                event_type = BacktestEventType.FALSE_NEGATIVE
                false_negatives += 1
                if is_actionable:
                    significant_moments_missed += 1
            
            events.append(BacktestEvent(
                event_type=event_type,
                timestamp=datetime.now(timezone.utc() - timedelta(weeks=52-week)),  # Approximate
                actual_value=count,
                threshold_value=recommended_threshold,
                deviation_percent=((count - baseline) / baseline * 100) if baseline > 0 else 0,
                would_have_alerted=would_alert,
                was_actionable=is_actionable,
                context={"week": week, "baseline": baseline},
            ))
        
        return self._create_summary(
            events=events,
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
            significant_moments_caught=significant_moments_caught,
            significant_moments_missed=significant_moments_missed,
            data_window_days=data_window_days,
            data_points_analyzed=len(returns),
        )
    
    def _backtest_aov_threshold(
        self,
        recommendation: Dict[str, Any],
        store_id: str,
        data_window_days: int,
    ) -> BacktestSummary:
        """Backtest high-value AOV threshold recommendation."""
        window_start = datetime.now(timezone.utc) - timedelta(days=data_window_days)
        
        # Get recommended threshold
        threshold_data = recommendation.get("thresholds", [{}])[0]
        recommended_multiplier = threshold_data.get("recommended_value", 1.5)
        
        # Get orders
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        order_values = [float(o.total) for o in orders if o.total]
        
        if not order_values:
            return self._create_empty_summary(data_window_days)
        
        # Calculate baseline AOV and threshold
        baseline_aov = statistics.mean(order_values)
        threshold = baseline_aov * recommended_multiplier
        
        # Calculate events
        events = []
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        significant_moments_caught = 0
        significant_moments_missed = 0
        
        for i, order in enumerate(orders):
            if not order.total:
                continue
            
            value = float(order.total)
            would_alert = value >= threshold
            
            # Determine significance
            is_significant = value >= baseline_aov * (1 + SIGNIFICANT_DEVIATION_THRESHOLD)
            is_actionable = value >= threshold * ACTIONABLE_AOV_MULTIPLIER
            
            # Classify
            if would_alert and is_significant:
                event_type = BacktestEventType.TRUE_POSITIVE
                true_positives += 1
                if is_actionable:
                    significant_moments_caught += 1
            elif would_alert and not is_significant:
                event_type = BacktestEventType.FALSE_POSITIVE
                false_positives += 1
            elif not would_alert and not is_significant:
                event_type = BacktestEventType.TRUE_NEGATIVE
                true_negatives += 1
            else:
                event_type = BacktestEventType.FALSE_NEGATIVE
                false_negatives += 1
                if is_actionable:
                    significant_moments_missed += 1
            
            # Only record significant events for brevity
            if is_significant or would_alert:
                events.append(BacktestEvent(
                    event_type=event_type,
                    timestamp=order.created_at,
                    actual_value=value,
                    threshold_value=threshold,
                    deviation_percent=((value - baseline_aov) / baseline_aov * 100),
                    would_have_alerted=would_alert,
                    was_actionable=is_actionable,
                    context={"order_id": str(order.id), "order_number": order.order_number},
                ))
        
        return self._create_summary(
            events=events[:50],  # Limit to 50 events
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
            significant_moments_caught=significant_moments_caught,
            significant_moments_missed=significant_moments_missed,
            data_window_days=data_window_days,
            data_points_analyzed=len(orders),
        )
    
    def _backtest_conversion_anomaly(
        self,
        recommendation: Dict[str, Any],
        store_id: str,
        data_window_days: int,
    ) -> BacktestSummary:
        """Backtest conversion anomaly threshold recommendation."""
        window_start = datetime.now(timezone.utc) - timedelta(days=data_window_days)
        
        # Get recommended thresholds
        thresholds = recommendation.get("thresholds", [])
        drop_threshold = next(
            (t.get("recommended_value", 15) for t in thresholds if "drop" in t.get("parameter_name", "")),
            15
        )
        rise_threshold = next(
            (t.get("recommended_value", 20) for t in thresholds if "rise" in t.get("parameter_name", "")),
            20
        )
        
        # Get daily order counts
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Group by day
        daily_orders = defaultdict(int)
        for order in orders:
            day_key = order.created_at.date()
            daily_orders[day_key] += 1
        
        sorted_days = sorted(daily_orders.keys())
        daily_values = [daily_orders[d] for d in sorted_days]
        
        if len(daily_values) < 7:
            return self._create_empty_summary(data_window_days)
        
        baseline = statistics.mean(daily_values)
        
        # Calculate events
        events = []
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        significant_moments_caught = 0
        significant_moments_missed = 0
        
        for i, day in enumerate(sorted_days):
            if i < 7:  # Need 7 days for rolling baseline
                continue
            
            # Rolling baseline
            prev_7 = daily_values[max(0, i-7):i]
            rolling_baseline = statistics.mean(prev_7) if prev_7 else baseline
            
            current = daily_orders[day]
            deviation = ((current - rolling_baseline) / rolling_baseline * 100) if rolling_baseline > 0 else 0
            
            # Would alert?
            would_alert = deviation <= -drop_threshold or deviation >= rise_threshold
            
            # Is significant?
            is_significant = abs(deviation) >= SIGNIFICANT_DEVIATION_THRESHOLD * 100 * 0.5  # 25%
            is_actionable = abs(deviation) >= 30  # 30% deviation is actionable
            
            # Classify
            if would_alert and is_significant:
                event_type = BacktestEventType.TRUE_POSITIVE
                true_positives += 1
                if is_actionable:
                    significant_moments_caught += 1
            elif would_alert and not is_significant:
                event_type = BacktestEventType.FALSE_POSITIVE
                false_positives += 1
            elif not would_alert and not is_significant:
                event_type = BacktestEventType.TRUE_NEGATIVE
                true_negatives += 1
            else:
                event_type = BacktestEventType.FALSE_NEGATIVE
                false_negatives += 1
                if is_actionable:
                    significant_moments_missed += 1
            
            # Record significant events
            if is_significant or would_alert:
                events.append(BacktestEvent(
                    event_type=event_type,
                    timestamp=datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc),
                    actual_value=current,
                    threshold_value=rolling_baseline,
                    deviation_percent=deviation,
                    would_have_alerted=would_alert,
                    was_actionable=is_actionable,
                    context={"day": day.isoformat(), "rolling_baseline": rolling_baseline},
                ))
        
        return self._create_summary(
            events=events[:50],
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
            significant_moments_caught=significant_moments_caught,
            significant_moments_missed=significant_moments_missed,
            data_window_days=data_window_days,
            data_points_analyzed=len(orders),
        )
    
    def _backtest_vip_inactivity(
        self,
        recommendation: Dict[str, Any],
        store_id: str,
        data_window_days: int,
    ) -> BacktestSummary:
        """Backtest VIP inactivity threshold recommendation."""
        window_start = datetime.now(timezone.utc) - timedelta(days=data_window_days)
        
        # Get recommended threshold
        threshold_data = recommendation.get("thresholds", [{}])[0]
        recommended_days = threshold_data.get("recommended_value", 45)
        
        # Get VIP customers and their order history
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Group by customer
        customer_orders = defaultdict(list)
        for order in orders:
            if order.user_id:
                customer_orders[str(order.user_id)].append(order)
        
        # Identify VIPs (5+ orders, $1000+ LTV)
        vip_orders = defaultdict(list)
        for customer_id, order_list in customer_orders.items():
            ltv = sum(float(o.total) for o in order_list if o.total)
            if len(order_list) >= 5 and ltv >= 1000:
                vip_orders[customer_id] = order_list
        
        if not vip_orders:
            return self._create_empty_summary(data_window_days)
        
        # Calculate events
        events = []
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        significant_moments_caught = 0
        significant_moments_missed = 0
        
        now = datetime.now(timezone.utc)
        
        for customer_id, order_list in vip_orders.items():
            sorted_orders = sorted(order_list, key=lambda o: o.created_at)
            last_order = sorted_orders[-1].created_at
            
            days_since = (now - last_order).days
            would_alert = days_since >= recommended_days
            
            # Calculate typical cycle
            if len(sorted_orders) >= 2:
                cycles = []
                for i in range(1, len(sorted_orders)):
                    days = (sorted_orders[i].created_at - sorted_orders[i-1].created_at).days
                    cycles.append(days)
                avg_cycle = statistics.mean(cycles)
            else:
                avg_cycle = 30
            
            # Is significant?
            is_significant = days_since >= avg_cycle * 1.5
            is_actionable = days_since >= avg_cycle * 2  # 2x their cycle is very actionable
            
            # Classify
            if would_alert and is_significant:
                event_type = BacktestEventType.TRUE_POSITIVE
                true_positives += 1
                if is_actionable:
                    significant_moments_caught += 1
            elif would_alert and not is_significant:
                event_type = BacktestEventType.FALSE_POSITIVE
                false_positives += 1
            elif not would_alert and not is_significant:
                event_type = BacktestEventType.TRUE_NEGATIVE
                true_negatives += 1
            else:
                event_type = BacktestEventType.FALSE_NEGATIVE
                false_negatives += 1
                if is_actionable:
                    significant_moments_missed += 1
            
            events.append(BacktestEvent(
                event_type=event_type,
                timestamp=last_order,
                actual_value=days_since,
                threshold_value=recommended_days,
                deviation_percent=((days_since - avg_cycle) / avg_cycle * 100) if avg_cycle > 0 else 0,
                would_have_alerted=would_alert,
                was_actionable=is_actionable,
                context={"customer_id": customer_id, "avg_cycle": avg_cycle, "ltv": sum(float(o.total) for o in order_list if o.total)},
            ))
        
        return self._create_summary(
            events=events,
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
            significant_moments_caught=significant_moments_caught,
            significant_moments_missed=significant_moments_missed,
            data_window_days=data_window_days,
            data_points_analyzed=len(vip_orders),
        )
    
    def _create_summary(
        self,
        events: List[BacktestEvent],
        true_positives: int,
        false_positives: int,
        true_negatives: int,
        false_negatives: int,
        significant_moments_caught: int,
        significant_moments_missed: int,
        data_window_days: int,
        data_points_analyzed: int,
    ) -> BacktestSummary:
        """Create backtest summary with calculated metrics."""
        total = true_positives + false_positives + true_negatives + false_negatives
        
        # Calculate precision and recall
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        # F1 score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # False positive rate
        fpr = false_positives / (false_positives + true_negatives) if (false_positives + true_negatives) > 0 else 0
        
        return BacktestSummary(
            total_events=total,
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=true_negatives,
            false_negatives=false_negatives,
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            false_positive_rate=round(fpr, 3),
            significant_moments_caught=significant_moments_caught,
            significant_moments_missed=significant_moments_missed,
            analysis_period_days=data_window_days,
            data_points_analyzed=data_points_analyzed,
        )
    
    def _create_empty_summary(self, data_window_days: int) -> BacktestSummary:
        """Create an empty backtest summary for insufficient data."""
        return BacktestSummary(
            total_events=0,
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            false_positive_rate=0.0,
            significant_moments_caught=0,
            significant_moments_missed=0,
            analysis_period_days=data_window_days,
            data_points_analyzed=0,
        )
    
    def validate_false_positive_rate(
        self,
        summary: BacktestSummary,
        max_fpr: float = 0.10,  # 10% max false positive rate
    ) -> bool:
        """Validate that recommendation meets false positive rate threshold."""
        return summary.false_positive_rate <= max_fpr
    
    def generate_backtest_display(
        self,
        summary: BacktestSummary,
        events: List[BacktestEvent],
    ) -> Dict[str, Any]:
        """Generate display-ready backtest results for UI."""
        # Filter to true positives for display
        significant_events = [
            e for e in events
            if e.event_type == BacktestEventType.TRUE_POSITIVE and e.was_actionable
        ]
        
        return {
            "summary_text": f"This threshold would have alerted you to {summary.significant_moments_caught} significant moments with {summary.false_positive_rate*100:.1f}% false positive rate.",
            "metrics": {
                "precision": f"{summary.precision*100:.1f}%",
                "recall": f"{summary.recall*100:.1f}%",
                "false_positive_rate": f"{summary.false_positive_rate*100:.1f}%",
                "significant_moments_caught": summary.significant_moments_caught,
            },
            "significant_events": [
                {
                    "date": e.timestamp.strftime("%Y-%m-%d"),
                    "value": e.actual_value,
                    "threshold": e.threshold_value,
                    "deviation": f"{e.deviation_percent:+.1f}%",
                    "context": e.context,
                }
                for e in significant_events[:5]  # Top 5
            ],
            "passes_validation": self.validate_false_positive_rate(summary),
        }
