"""
CONFIT Backend — Predictive Recommendation Engine
=================================================
Intelligent recommendation system that analyzes 60-90 days of historical data
to automatically suggest personalized alert configurations for each store.

Features:
- Return pattern analysis with percentile-based thresholds
- AOV outlier detection
- Conversion rate anomaly detection
- Inventory velocity analysis
- Seasonal pattern detection
- Customer segment churn prediction
- Backtesting validation
"""

import logging
import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from database.models import (
    Order,
    OrderItem,
    Product,
    Store,
    Customer,
    ReturnRequest,
)
from database.sales_alert_models import SalesAlertPreferences, get_default_thresholds
from database.alert_recommendation_models import (
    AlertRecommendation,
    StorePatternAnalysis,
    RecommendationType,
    RecommendationStatus,
    ConfidenceLevel,
    ImpactEstimate,
)
from schemas.alert_recommendation_schemas import (
    ThresholdRecommendation,
    RecommendationExplanation,
    BacktestEvent,
    BacktestSummary,
    BacktestEventType,
)

logger = logging.getLogger(__name__)


# ─── Constants ─────────────────────────────────────────────────────────────────

MIN_DATA_DAYS = 15  # Minimum days of data for recommendations
DEFAULT_DATA_WINDOW = 60  # Default analysis window in days
MAX_DATA_WINDOW = 90  # Maximum analysis window

# Percentile thresholds for outlier detection
PERCENTILE_SPIKE = 80  # For catching spikes without noise
PERCENTILE_HIGH_VALUE = 85  # For high-value orders
PERCENTILE_CRITICAL = 90  # For critical anomalies

# EWMA smoothing factor (higher = more weight on recent data)
EWMA_ALPHA = 0.3


# ─── Helper Functions ───────────────────────────────────────────────────────────

def percentile(data: List[float], p: float) -> float:
    """Calculate the p-th percentile of a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def ewma(values: List[float], alpha: float = EWMA_ALPHA) -> List[float]:
    """Calculate exponential weighted moving average."""
    if not values:
        return []
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(alpha * values[i] + (1 - alpha) * result[-1])
    return result


def calculate_volatility(values: List[float]) -> float:
    """Calculate the standard deviation as a measure of volatility."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def coefficient_of_variation(values: List[float]) -> float:
    """Calculate CV (std/mean) for relative variability."""
    if not values or statistics.mean(values) == 0:
        return 0.0
    return statistics.stdev(values) / statistics.mean(values) if len(values) > 1 else 0.0


# ─── Pattern Analyzers ─────────────────────────────────────────────────────────

class ReturnPatternAnalyzer:
    """Analyzes return patterns to recommend optimal thresholds."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze return patterns and generate insights."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get all returns in the window
        returns = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status == 'returned',
            Order.updated_at >= window_start
        ).all()
        
        # Group returns by week
        weekly_returns = defaultdict(int)
        product_returns = defaultdict(list)
        
        for order in returns:
            week_start = order.updated_at.isocalendar()[1]
            weekly_returns[week_start] += 1
            
            for item in order.items:
                if item.product_id:
                    product_returns[str(item.product_id)].append(order.updated_at)
        
        # Calculate baseline and volatility
        weekly_values = list(weekly_returns.values()) if weekly_returns else [0]
        baseline = statistics.mean(weekly_values) if weekly_values else 0
        volatility = calculate_volatility(weekly_values)
        cv = coefficient_of_variation(weekly_values)
        
        # Calculate percentile thresholds
        spike_80 = percentile(weekly_values, PERCENTILE_SPIKE)
        spike_90 = percentile(weekly_values, PERCENTILE_CRITICAL)
        
        # Identify products with high return velocity
        high_velocity_products = []
        for product_id, return_dates in product_returns.items():
            if len(return_dates) >= 3:  # At least 3 returns
                # Calculate velocity (returns per week)
                first_return = min(return_dates)
                last_return = max(return_dates)
                days_span = max(1, (last_return - first_return).days)
                velocity = len(return_dates) / (days_span / 7)
                
                if velocity > baseline * 1.5:  # 50% above baseline
                    product = self._db.query(Product).filter(Product.id == product_id).first()
                    if product:
                        high_velocity_products.append({
                            "product_id": product_id,
                            "product_name": product.name if hasattr(product, 'name') else "Unknown",
                            "return_count": len(return_dates),
                            "velocity_per_week": round(velocity, 2),
                        })
        
        # Sort by velocity
        high_velocity_products.sort(key=lambda x: x["velocity_per_week"], reverse=True)
        
        # Seasonal patterns (by month)
        monthly_returns = defaultdict(int)
        for order in returns:
            month_key = order.updated_at.strftime("%Y-%m")
            monthly_returns[month_key] += 1
        
        return {
            "baseline_weekly_returns": round(baseline, 2),
            "return_volatility": round(volatility, 2),
            "coefficient_of_variation": round(cv, 3),
            "spike_threshold_80th": round(spike_80),
            "spike_threshold_90th": round(spike_90),
            "products_with_high_return_velocity": high_velocity_products[:10],  # Top 10
            "seasonal_return_patterns": dict(monthly_returns),
            "total_returns_analyzed": len(returns),
            "weeks_analyzed": len(weekly_values),
        }


class AOVPatternAnalyzer:
    """Analyzes Average Order Value patterns to recommend thresholds."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze AOV patterns and generate insights."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get all completed orders
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        order_values = [float(o.total) for o in orders if o.total]
        
        if not order_values:
            return {
                "baseline_aov": 0,
                "aov_range_low": 0,
                "aov_range_high": 0,
                "outlier_threshold_85th": 0,
                "outlier_threshold_90th": 0,
                "high_value_order_frequency": 0,
                "seasonal_aov_patterns": {},
                "total_orders_analyzed": 0,
            }
        
        # Calculate baseline AOV
        baseline_aov = statistics.mean(order_values)
        aov_std = statistics.stdev(order_values) if len(order_values) > 1 else 0
        
        # Range (IQR-based)
        sorted_values = sorted(order_values)
        q1 = percentile(sorted_values, 25)
        q3 = percentile(sorted_values, 75)
        
        # Percentile thresholds for high-value
        threshold_85 = percentile(sorted_values, PERCENTILE_HIGH_VALUE)
        threshold_90 = percentile(sorted_values, PERCENTILE_CRITICAL)
        
        # Count high-value orders (above 85th percentile)
        high_value_orders = [v for v in order_values if v >= threshold_85]
        high_value_frequency = len(high_value_orders) / (self._data_window_days / 30)  # Per month
        
        # Seasonal patterns (by month)
        monthly_aov = defaultdict(list)
        for order in orders:
            if order.total:
                month_key = order.created_at.strftime("%Y-%m")
                monthly_aov[month_key].append(float(order.total))
        
        seasonal_patterns = {
            month: round(statistics.mean(values), 2)
            for month, values in monthly_aov.items()
        }
        
        return {
            "baseline_aov": round(baseline_aov, 2),
            "aov_range_low": round(q1, 2),
            "aov_range_high": round(q3, 2),
            "aov_std_dev": round(aov_std, 2),
            "outlier_threshold_85th": round(threshold_85, 2),
            "outlier_threshold_90th": round(threshold_90, 2),
            "high_value_order_frequency": round(high_value_frequency, 2),
            "seasonal_aov_patterns": seasonal_patterns,
            "total_orders_analyzed": len(orders),
        }


class ConversionPatternAnalyzer:
    """Analyzes conversion rate patterns to detect anomalies."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze conversion patterns using order count as proxy."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get daily order counts as conversion proxy
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Group by day
        daily_orders = defaultdict(int)
        for order in orders:
            day_key = order.created_at.date()
            daily_orders[day_key] += 1
        
        daily_values = list(daily_orders.values()) if daily_orders else [0]
        
        # Calculate 7-day rolling average baseline
        baseline = statistics.mean(daily_values) if daily_values else 0
        variance = calculate_volatility(daily_values)
        
        # Calculate deviation thresholds
        # For drops: use lower standard deviation
        # For rises: use upper standard deviation
        drop_threshold = min(15, max(5, (variance / baseline * 100) * 1.5)) if baseline > 0 else 15
        rise_threshold = min(20, max(10, (variance / baseline * 100) * 2)) if baseline > 0 else 20
        
        # Identify historical anomalies
        anomalies = []
        sorted_days = sorted(daily_orders.keys())
        
        for i, day in enumerate(sorted_days):
            if i < 7:  # Need at least 7 days for baseline
                continue
            
            # Calculate 7-day rolling baseline
            prev_7_days = sorted_days[max(0, i-7):i]
            rolling_baseline = statistics.mean([daily_orders[d] for d in prev_7_days])
            
            current = daily_orders[day]
            if rolling_baseline > 0:
                deviation = ((current - rolling_baseline) / rolling_baseline) * 100
                
                if abs(deviation) >= drop_threshold:
                    anomalies.append({
                        "date": day.isoformat(),
                        "value": current,
                        "baseline": round(rolling_baseline, 2),
                        "deviation_percent": round(deviation, 1),
                        "type": "drop" if deviation < 0 else "rise",
                    })
        
        # Seasonal patterns (by week of year)
        weekly_orders = defaultdict(list)
        for day, count in daily_orders.items():
            week_key = day.isocalendar()[1]
            weekly_orders[week_key].append(count)
        
        seasonal_patterns = {
            f"week_{week}": round(statistics.mean(counts), 2)
            for week, counts in weekly_orders.items()
        }
        
        return {
            "baseline_conversion_rate": round(baseline, 2),  # Orders/day as proxy
            "rolling_7day_variance": round(variance, 2),
            "deviation_threshold_drop": round(drop_threshold, 1),
            "deviation_threshold_rise": round(rise_threshold, 1),
            "historical_anomalies": anomalies[:20],  # Top 20
            "seasonal_conversion_patterns": seasonal_patterns,
            "total_days_analyzed": len(daily_values),
        }


class InventoryVelocityAnalyzer:
    """Analyzes inventory depletion patterns by category."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze inventory velocity by product category."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get products for this store
        products = self._db.query(Product).filter(
            Product.store_id == self._store_id
        ).all()
        
        # Get order items for velocity calculation
        order_items = self._db.query(OrderItem).join(Order).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Calculate velocity by category
        category_sales = defaultdict(int)
        product_sales = defaultdict(int)
        
        for item in order_items:
            product = self._db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                category = getattr(product, 'category', 'uncategorized') or 'uncategorized'
                category_sales[category] += item.quantity if item.quantity else 1
                product_sales[str(item.product_id)] += item.quantity if item.quantity else 1
        
        # Calculate weekly velocity per category
        weeks = self._data_window_days / 7
        category_velocities = {
            cat: round(sales / weeks, 2)
            for cat, sales in category_sales.items()
        }
        
        # Determine fast/slow movers
        velocities = list(category_velocities.values()) if category_velocities else [0]
        mean_velocity = statistics.mean(velocities) if velocities else 0
        
        fast_mover_threshold = mean_velocity * 1.5 if mean_velocity > 0 else 10
        slow_mover_threshold = mean_velocity * 0.5 if mean_velocity > 0 else 2
        
        # Recommend stock thresholds based on velocity
        recommended_thresholds = {}
        for category, velocity in category_velocities.items():
            # Higher velocity = higher threshold (more buffer)
            # Threshold = velocity * 2 weeks of buffer
            if velocity > fast_mover_threshold:
                recommended_thresholds[category] = round(velocity * 2)  # 2 weeks buffer
            elif velocity < slow_mover_threshold:
                recommended_thresholds[category] = max(5, round(velocity * 3))  # 3 weeks, min 5
            else:
                recommended_thresholds[category] = round(velocity * 2.5)  # 2.5 weeks
        
        return {
            "category_velocities": category_velocities,
            "fast_mover_threshold": round(fast_mover_threshold, 2),
            "slow_mover_threshold": round(slow_mover_threshold, 2),
            "recommended_stock_thresholds": recommended_thresholds,
            "total_products": len(products),
            "total_items_sold": sum(product_sales.values()),
        }


class SeasonalPatternAnalyzer:
    """Detects seasonal patterns in store metrics."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Detect seasonal patterns from historical data."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get orders for seasonal analysis
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Group by month
        monthly_metrics = defaultdict(lambda: {"order_count": 0, "total_revenue": 0})
        
        for order in orders:
            month = order.created_at.month
            monthly_metrics[month]["order_count"] += 1
            monthly_metrics[month]["total_revenue"] += float(order.total) if order.total else 0
        
        # Calculate monthly averages
        monthly_order_counts = [m["order_count"] for m in monthly_metrics.values()]
        monthly_revenues = [m["total_revenue"] for m in monthly_metrics.values()]
        
        avg_orders = statistics.mean(monthly_order_counts) if monthly_order_counts else 0
        avg_revenue = statistics.mean(monthly_revenues) if monthly_revenues else 0
        
        # Identify peak seasons (months > 15% above average)
        peak_months = []
        peak_conversion_lift = 0
        peak_aov_lift = 0
        
        for month, metrics in monthly_metrics.items():
            order_lift = ((metrics["order_count"] - avg_orders) / avg_orders * 100) if avg_orders > 0 else 0
            revenue_lift = ((metrics["total_revenue"] - avg_revenue) / avg_revenue * 100) if avg_revenue > 0 else 0
            
            if order_lift > 15:
                peak_months.append(str(month))
                peak_conversion_lift = max(peak_conversion_lift, order_lift)
                peak_aov_lift = max(peak_aov_lift, revenue_lift)
        
        # Determine if Q4 is peak (common in retail)
        is_q4_peak = any(m in peak_months for m in ['10', '11', '12'])
        
        # Recommended temporary adjustments
        adjustments = {}
        if is_q4_peak and peak_conversion_lift > 15:
            adjustments = {
                "conversion_drop_threshold_percent": 20,  # More lenient during peak
                "conversion_rise_threshold_percent": 15,  # More sensitive to rises
                "period": "Q4 (Oct-Dec)",
                "auto_revert_date": "January 15",
            }
        
        return {
            "peak_seasons": peak_months,
            "peak_conversion_lift_percent": round(peak_conversion_lift, 1),
            "peak_aov_lift_percent": round(peak_aov_lift, 1),
            "is_q4_peak": is_q4_peak,
            "recommended_temporary_adjustments": adjustments,
            "months_analyzed": len(monthly_metrics),
        }


class CustomerSegmentAnalyzer:
    """Analyzes customer segment behavior for churn prediction."""
    
    def __init__(self, db: Session, store_id: str, data_window_days: int = DEFAULT_DATA_WINDOW):
        self._db = db
        self._store_id = store_id
        self._data_window_days = data_window_days
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze customer purchase cycles by segment."""
        window_start = datetime.now(timezone.utc) - timedelta(days=self._data_window_days)
        
        # Get orders with customer info
        orders = self._db.query(Order).join(OrderItem).join(Product).filter(
            Product.store_id == self._store_id,
            Order.status != 'cancelled',
            Order.created_at >= window_start
        ).all()
        
        # Group orders by customer
        customer_orders = defaultdict(list)
        for order in orders:
            if order.user_id:
                customer_orders[str(order.user_id)].append(order)
        
        # Calculate purchase cycles
        vip_cycles = []
        returning_cycles = []
        customer_segments = {}
        
        for customer_id, customer_order_list in customer_orders.items():
            # Sort by date
            sorted_orders = sorted(customer_order_list, key=lambda o: o.created_at)
            
            # Calculate LTV
            ltv = sum(float(o.total) for o in sorted_orders if o.total)
            
            # Determine segment
            if len(sorted_orders) >= 5 and ltv >= 1000:
                segment = "vip"
            elif len(sorted_orders) >= 2:
                segment = "returning"
            else:
                segment = "new"
            
            customer_segments[customer_id] = {
                "segment": segment,
                "order_count": len(sorted_orders),
                "ltv": ltv,
                "last_order_date": sorted_orders[-1].created_at.isoformat() if sorted_orders else None,
            }
            
            # Calculate purchase cycle (days between orders)
            if len(sorted_orders) >= 2:
                cycles = []
                for i in range(1, len(sorted_orders)):
                    days = (sorted_orders[i].created_at - sorted_orders[i-1].created_at).days
                    cycles.append(days)
                
                avg_cycle = statistics.mean(cycles) if cycles else 0
                
                if segment == "vip":
                    vip_cycles.append(avg_cycle)
                elif segment == "returning":
                    returning_cycles.append(avg_cycle)
        
        # Calculate average cycles
        avg_vip_cycle = statistics.mean(vip_cycles) if vip_cycles else 30
        avg_returning_cycle = statistics.mean(returning_cycles) if returning_cycles else 60
        
        # Recommend inactivity thresholds based on individual cycles
        recommended_vip_days = round(avg_vip_cycle * 1.5)  # 1.5x their typical cycle
        recommended_returning_days = round(avg_returning_cycle * 1.5)
        
        # Identify at-risk customers
        now = datetime.now(timezone.utc)
        at_risk = []
        
        for customer_id, data in customer_segments.items():
            if data["segment"] in ["vip", "returning"] and data["last_order_date"]:
                last_order = datetime.fromisoformat(data["last_order_date"].replace('Z', '+00:00'))
                days_since = (now - last_order).days
                
                threshold = recommended_vip_days if data["segment"] == "vip" else recommended_returning_days
                
                if days_since >= threshold * 0.8:  # Approaching threshold
                    at_risk.append({
                        "customer_id": customer_id,
                        "segment": data["segment"],
                        "days_since_last_order": days_since,
                        "ltv": data["ltv"],
                    })
        
        # Sort by LTV (highest value at-risk first)
        at_risk.sort(key=lambda x: x["ltv"], reverse=True)
        
        return {
            "vip_avg_purchase_cycle_days": round(avg_vip_cycle, 1),
            "returning_avg_purchase_cycle_days": round(avg_returning_cycle, 1),
            "recommended_vip_inactivity_days": recommended_vip_days,
            "recommended_returning_inactivity_days": recommended_returning_days,
            "at_risk_customers": at_risk[:10],  # Top 10
            "total_customers_analyzed": len(customer_segments),
            "vip_count": sum(1 for d in customer_segments.values() if d["segment"] == "vip"),
            "returning_count": sum(1 for d in customer_segments.values() if d["segment"] == "returning"),
        }


# ─── Main Recommendation Engine ───────────────────────────────────────────────

class PredictiveRecommendationEngine:
    """
    Main engine for generating personalized alert recommendations.
    Coordinates pattern analyzers and generates actionable recommendations.
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    def analyze_store_patterns(
        self,
        store_id: str,
        data_window_days: int = DEFAULT_DATA_WINDOW,
    ) -> Dict[str, Any]:
        """
        Perform complete pattern analysis for a store.
        Returns all pattern analysis results.
        """
        # Initialize analyzers
        return_analyzer = ReturnPatternAnalyzer(self._db, store_id, data_window_days)
        aov_analyzer = AOVPatternAnalyzer(self._db, store_id, data_window_days)
        conversion_analyzer = ConversionPatternAnalyzer(self._db, store_id, data_window_days)
        inventory_analyzer = InventoryVelocityAnalyzer(self._db, store_id, data_window_days)
        seasonal_analyzer = SeasonalPatternAnalyzer(self._db, store_id, data_window_days)
        customer_analyzer = CustomerSegmentAnalyzer(self._db, store_id, data_window_days)
        
        # Run all analyses
        return_patterns = return_analyzer.analyze()
        aov_patterns = aov_analyzer.analyze()
        conversion_patterns = conversion_analyzer.analyze()
        inventory_patterns = inventory_analyzer.analyze()
        seasonal_patterns = seasonal_analyzer.analyze()
        customer_patterns = customer_analyzer.analyze()
        
        # Calculate data quality score
        data_quality = self._calculate_data_quality(
            return_patterns, aov_patterns, conversion_patterns
        )
        
        return {
            "store_id": store_id,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "data_window_days": data_window_days,
            "return_patterns": return_patterns,
            "aov_patterns": aov_patterns,
            "conversion_patterns": conversion_patterns,
            "inventory_patterns": inventory_patterns,
            "seasonal_patterns": seasonal_patterns,
            "customer_segment_patterns": customer_patterns,
            "data_quality_score": data_quality,
            "has_sufficient_data": data_quality >= 0.5,
        }
    
    def _calculate_data_quality(
        self,
        return_patterns: Dict,
        aov_patterns: Dict,
        conversion_patterns: Dict,
    ) -> float:
        """Calculate a data quality score (0-1) based on data availability."""
        scores = []
        
        # Order count score
        order_count = aov_patterns.get("total_orders_analyzed", 0)
        if order_count >= 100:
            scores.append(1.0)
        elif order_count >= 50:
            scores.append(0.7)
        elif order_count >= 20:
            scores.append(0.4)
        else:
            scores.append(0.1)
        
        # Days analyzed score
        days_analyzed = conversion_patterns.get("total_days_analyzed", 0)
        if days_analyzed >= 45:
            scores.append(1.0)
        elif days_analyzed >= 30:
            scores.append(0.7)
        elif days_analyzed >= 15:
            scores.append(0.4)
        else:
            scores.append(0.1)
        
        # Return data score
        returns_analyzed = return_patterns.get("total_returns_analyzed", 0)
        if returns_analyzed >= 20:
            scores.append(1.0)
        elif returns_analyzed >= 10:
            scores.append(0.6)
        else:
            scores.append(0.3)
        
        return round(statistics.mean(scores), 2)
    
    def generate_recommendations(
        self,
        store_id: str,
        current_preferences: Optional[Dict] = None,
        data_window_days: int = DEFAULT_DATA_WINDOW,
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations for a store.
        Returns list of recommendation objects.
        """
        # Get pattern analysis
        patterns = self.analyze_store_patterns(store_id, data_window_days)
        
        if not patterns["has_sufficient_data"]:
            return []  # Insufficient data
        
        recommendations = []
        current_thresholds = current_preferences or get_default_thresholds()
        
        # Generate return spike recommendation
        rec = self._generate_return_spike_recommendation(
            patterns["return_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Generate AOV recommendation
        rec = self._generate_aov_recommendation(
            patterns["aov_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Generate conversion anomaly recommendation
        rec = self._generate_conversion_recommendation(
            patterns["conversion_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Generate inventory recommendation
        rec = self._generate_inventory_recommendation(
            patterns["inventory_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Generate seasonal recommendation
        rec = self._generate_seasonal_recommendation(
            patterns["seasonal_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Generate VIP inactivity recommendation
        rec = self._generate_vip_inactivity_recommendation(
            patterns["customer_segment_patterns"], current_thresholds, store_id
        )
        if rec:
            recommendations.append(rec)
        
        # Sort by impact and confidence
        recommendations.sort(key=lambda r: r["rank_score"], reverse=True)
        
        return recommendations
    
    def _generate_return_spike_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate return spike threshold recommendation."""
        if patterns["total_returns_analyzed"] < 10:
            return None
        
        baseline = patterns["baseline_weekly_returns"]
        spike_80 = patterns["spike_threshold_80th"]
        
        # Only recommend if spike threshold is meaningfully different
        current_spike = current.get("returns_spike_count", 5)
        
        if spike_80 <= current_spike * 1.2:  # Within 20% of current
            return None
        
        confidence = ConfidenceLevel.HIGH if patterns["coefficient_of_variation"] > 0.3 else ConfidenceLevel.MEDIUM
        impact = ImpactEstimate.HIGH if baseline > 15 else ImpactEstimate.MEDIUM
        
        return {
            "id": f"rec-{store_id}-return-spike-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.RETURN_SPIKE,
            "status": RecommendationStatus.PENDING,
            "title": "Return Spike Alert Threshold",
            "description": f"Optimize return alert threshold based on your store's patterns",
            "thresholds": [
                {
                    "parameter_name": "returns_spike_count",
                    "current_value": current_spike,
                    "recommended_value": int(spike_80),
                    "unit": "returns/week",
                    "percentile_used": PERCENTILE_SPIKE,
                }
            ],
            "confidence": confidence,
            "confidence_score": 0.85 if confidence == ConfidenceLevel.HIGH else 0.65,
            "impact_estimate": impact,
            "explanation": {
                "summary": f"Based on {patterns['weeks_analyzed']} weeks of data, your store typically sees {baseline:.0f} returns/week with occasional spikes to {spike_80:.0f}. A threshold of {int(spike_80)} would catch spikes without false alarms.",
                "data_points": {
                    "baseline_weekly_returns": baseline,
                    "spike_threshold": spike_80,
                    "volatility": patterns["return_volatility"],
                },
                "methodology": "80th percentile of weekly return counts over 60 days",
                "historical_examples": patterns["products_with_high_return_velocity"][:3],
            },
            "rank_score": 0.9 if impact == ImpactEstimate.HIGH else 0.7,
        }
    
    def _generate_aov_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate high-value AOV threshold recommendation."""
        if patterns["total_orders_analyzed"] < 20:
            return None
        
        baseline_aov = patterns["baseline_aov"]
        threshold_85 = patterns["outlier_threshold_85th"]
        
        # Current threshold calculation
        current_multiplier = current.get("high_value_aov_multiplier", 1.5)
        current_threshold = baseline_aov * current_multiplier
        
        # Recommended threshold
        recommended_multiplier = threshold_85 / baseline_aov if baseline_aov > 0 else 1.5
        
        if abs(recommended_multiplier - current_multiplier) < 0.2:
            return None  # Already close enough
        
        confidence = ConfidenceLevel.HIGH if patterns["total_orders_analyzed"] >= 50 else ConfidenceLevel.MEDIUM
        impact = ImpactEstimate.HIGH if threshold_85 > baseline_aov * 2 else ImpactEstimate.MEDIUM
        
        return {
            "id": f"rec-{store_id}-aov-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.HIGH_VALUE_AOV,
            "status": RecommendationStatus.PENDING,
            "title": "High-Value Order Threshold",
            "description": f"Optimize AOV threshold to catch significant orders",
            "thresholds": [
                {
                    "parameter_name": "high_value_aov_multiplier",
                    "current_value": current_multiplier,
                    "recommended_value": round(recommended_multiplier, 2),
                    "unit": "x AOV",
                    "percentile_used": PERCENTILE_HIGH_VALUE,
                }
            ],
            "confidence": confidence,
            "confidence_score": 0.8,
            "impact_estimate": impact,
            "explanation": {
                "summary": f"Your AOV is ${baseline_aov:.0f}. Orders above ${threshold_85:.0f} (85th percentile) represent significant opportunities. We detected {patterns['high_value_order_frequency']:.1f} such orders/month.",
                "data_points": {
                    "baseline_aov": baseline_aov,
                    "threshold_85th": threshold_85,
                    "high_value_frequency": patterns["high_value_order_frequency"],
                },
                "methodology": "85th percentile of order values, converted to AOV multiplier",
                "historical_examples": [],
            },
            "rank_score": 0.95,  # High-value orders are top priority
        }
    
    def _generate_conversion_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate conversion anomaly threshold recommendation."""
        if patterns["total_days_analyzed"] < 14:
            return None
        
        recommended_drop = patterns["deviation_threshold_drop"]
        recommended_rise = patterns["deviation_threshold_rise"]
        
        current_drop = current.get("conversion_drop_threshold_percent", 15)
        current_rise = current.get("conversion_rise_threshold_percent", 20)
        
        # Check if recommendations are meaningfully different
        if abs(recommended_drop - current_drop) < 3 and abs(recommended_rise - current_rise) < 3:
            return None
        
        anomaly_count = len(patterns["historical_anomalies"])
        confidence = ConfidenceLevel.HIGH if anomaly_count >= 5 else ConfidenceLevel.MEDIUM
        
        return {
            "id": f"rec-{store_id}-conversion-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.CONVERSION_ANOMALY,
            "status": RecommendationStatus.PENDING,
            "title": "Conversion Rate Anomaly Threshold",
            "description": "Optimize conversion deviation thresholds to reduce noise",
            "thresholds": [
                {
                    "parameter_name": "conversion_drop_threshold_percent",
                    "current_value": current_drop,
                    "recommended_value": round(recommended_drop),
                    "unit": "%",
                },
                {
                    "parameter_name": "conversion_rise_threshold_percent",
                    "current_value": current_rise,
                    "recommended_value": round(recommended_rise),
                    "unit": "%",
                },
            ],
            "confidence": confidence,
            "confidence_score": 0.75,
            "impact_estimate": ImpactEstimate.MEDIUM,
            "explanation": {
                "summary": f"Your baseline is {patterns['baseline_conversion_rate']:.1f} orders/day with variance of {patterns['rolling_7day_variance']:.1f}. Thresholds of ±{recommended_drop:.0f}% would have caught {anomaly_count} significant anomalies.",
                "data_points": {
                    "baseline_rate": patterns["baseline_conversion_rate"],
                    "variance": patterns["rolling_7day_variance"],
                    "anomalies_detected": anomaly_count,
                },
                "methodology": "Standard deviation-based thresholds adjusted for noise reduction",
                "historical_examples": patterns["historical_anomalies"][:3],
            },
            "rank_score": 0.75,
        }
    
    def _generate_inventory_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate inventory threshold recommendations by category."""
        if not patterns["category_velocities"]:
            return None
        
        recommended = patterns["recommended_stock_thresholds"]
        current_units = current.get("inventory_threshold_units", 10)
        
        # Find categories where recommendation differs significantly
        significant_categories = {
            cat: threshold for cat, threshold in recommended.items()
            if abs(threshold - current_units) >= 5
        }
        
        if not significant_categories:
            return None
        
        return {
            "id": f"rec-{store_id}-inventory-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.INVENTORY_DEPLETION,
            "status": RecommendationStatus.PENDING,
            "title": "Inventory Threshold by Category",
            "description": "Category-specific stock thresholds based on sales velocity",
            "thresholds": [
                {
                    "parameter_name": f"inventory_threshold_{cat}",
                    "current_value": current_units,
                    "recommended_value": threshold,
                    "unit": "units",
                }
                for cat, threshold in list(significant_categories.items())[:5]  # Top 5 categories
            ],
            "confidence": ConfidenceLevel.MEDIUM,
            "confidence_score": 0.7,
            "impact_estimate": ImpactEstimate.MEDIUM,
            "explanation": {
                "summary": f"Fast-moving categories need higher thresholds. We analyzed {patterns['total_products']} products selling {patterns['total_items_sold']} units.",
                "data_points": {
                    "category_velocities": patterns["category_velocities"],
                    "fast_mover_threshold": patterns["fast_mover_threshold"],
                },
                "methodology": "Sales velocity per category, 2-week buffer for fast movers",
                "historical_examples": [],
            },
            "rank_score": 0.65,
        }
    
    def _generate_seasonal_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate seasonal adjustment recommendation."""
        if not patterns["peak_seasons"]:
            return None
        
        adjustments = patterns["recommended_temporary_adjustments"]
        if not adjustments:
            return None
        
        return {
            "id": f"rec-{store_id}-seasonal-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.SEASONAL_ADJUSTMENT,
            "status": RecommendationStatus.PENDING,
            "title": f"Q4 Seasonal Adjustment",
            "description": "Temporarily adjust thresholds for peak season",
            "thresholds": [
                {
                    "parameter_name": "conversion_drop_threshold_percent",
                    "current_value": current.get("conversion_drop_threshold_percent", 15),
                    "recommended_value": adjustments["conversion_drop_threshold_percent"],
                    "unit": "%",
                    "temporary": True,
                    "revert_date": adjustments["auto_revert_date"],
                }
            ],
            "confidence": ConfidenceLevel.MEDIUM,
            "confidence_score": 0.65,
            "impact_estimate": ImpactEstimate.HIGH,
            "explanation": {
                "summary": f"Q4 shows {patterns['peak_conversion_lift_percent']:.0f}% higher conversion. Adjust thresholds to reduce noise during peak.",
                "data_points": {
                    "peak_months": patterns["peak_seasons"],
                    "conversion_lift": patterns["peak_conversion_lift_percent"],
                    "aov_lift": patterns["peak_aov_lift_percent"],
                },
                "methodology": "Month-over-month comparison to identify peak seasons",
                "historical_examples": [],
            },
            "rank_score": 0.8,
        }
    
    def _generate_vip_inactivity_recommendation(
        self,
        patterns: Dict,
        current: Dict,
        store_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate VIP inactivity threshold recommendation."""
        if patterns["vip_count"] < 3:
            return None
        
        recommended_vip = patterns["recommended_vip_inactivity_days"]
        current_vip = current.get("vip_inactive_days", 30)
        
        if abs(recommended_vip - current_vip) < 7:
            return None  # Within a week
        
        at_risk_count = len(patterns["at_risk_customers"])
        
        return {
            "id": f"rec-{store_id}-vip-{int(datetime.now().timestamp())}",
            "store_id": store_id,
            "type": RecommendationType.VIP_INACTIVITY,
            "status": RecommendationStatus.PENDING,
            "title": "VIP Customer Inactivity Threshold",
            "description": "Personalized VIP inactivity threshold based on purchase cycles",
            "thresholds": [
                {
                    "parameter_name": "vip_inactive_days",
                    "current_value": current_vip,
                    "recommended_value": recommended_vip,
                    "unit": "days",
                }
            ],
            "confidence": ConfidenceLevel.HIGH,
            "confidence_score": 0.85,
            "impact_estimate": ImpactEstimate.HIGH,
            "explanation": {
                "summary": f"Your VIPs typically purchase every {patterns['vip_avg_purchase_cycle_days']:.0f} days. A {recommended_vip}-day threshold catches at-risk VIPs earlier. {at_risk_count} VIPs currently at risk.",
                "data_points": {
                    "avg_vip_cycle": patterns["vip_avg_purchase_cycle_days"],
                    "vip_count": patterns["vip_count"],
                    "at_risk_count": at_risk_count,
                },
                "methodology": "1.5x average VIP purchase cycle",
                "historical_examples": patterns["at_risk_customers"][:3],
            },
            "rank_score": 0.88,
        }
