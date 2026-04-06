"""
CONFIT Backend — Sales Alert Service
====================================
Intelligent real-time sales alert engine for store owners.
Monitors metrics and triggers alerts based on configurable thresholds.
"""

import logging
import json
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field, asdict

from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc, asc, case

from database.models import (
    SalesRecord,
    ReturnStatus,
    Store,
    User,
    Product,
    Order,
    OrderItem,
    Customer,
)
from infrastructure.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# ─── Enums ─────────────────────────────────────────────────────────────────────


class AlertType(str, Enum):
    HIGH_VALUE_ORDER = "high_value_order"
    UNUSUAL_RETURNS = "unusual_returns"
    INVENTORY_DEPLETION = "inventory_depletion"
    CONVERSION_ANOMALY = "conversion_anomaly"
    CUSTOMER_SEGMENT_CHANGE = "customer_segment_change"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ─── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class AlertThresholds:
    """Configurable thresholds for alert triggers."""
    high_value_aov_multiplier: float = 1.5
    inventory_threshold_units: int = 10
    inventory_threshold_percent: float = 20.0
    conversion_drop_threshold_percent: float = 15.0
    conversion_rise_threshold_percent: float = 20.0
    conversion_baseline_days: int = 7
    returns_spike_count: int = 5
    returns_spike_window_hours: int = 1
    returns_rate_increase_percent: float = 50.0
    vip_inactive_days: int = 30
    returning_to_inactive_days: int = 60


@dataclass
class AlertFrequency:
    """Frequency and throttling configuration."""
    mode: str = "throttled"  # real_time, batched, throttled
    max_alerts_per_hour: int = 10
    batch_interval_minutes: int = 30
    dedup_window_minutes: int = 60
    critical_mode: str = "real_time"
    warning_mode: str = "batched"
    info_mode: str = "batched"


@dataclass
class AlertPreferences:
    """Complete alert preferences for a store."""
    store_id: str
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    frequency: AlertFrequency = field(default_factory=AlertFrequency)
    enabled_types: List[AlertType] = field(default_factory=lambda: list(AlertType))
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SalesAlert:
    """Complete alert object."""
    id: str
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    title: str = ""
    message: str = ""
    rich_preview: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    store_id: str = ""
    store_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    read: bool = False
    dismissed: bool = False
    dedup_key: str = ""
    first_triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trigger_count: int = 1
    last_triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Alert Rule Engine ─────────────────────────────────────────────────────────


class AlertRuleEngine:
    """
    Core alert evaluation engine.
    Evaluates business metrics against configured thresholds.
    """

    def __init__(self, db: Session, preferences: AlertPreferences):
        self._db = db
        self._prefs = preferences

    # ─── High Value Order Detection ─────────────────────────────────────────────

    def check_high_value_order(self, order: Order, order_total: float) -> Optional[SalesAlert]:
        """
        Check if an order exceeds the AOV threshold.
        Trigger: Single order > AOV × multiplier
        """
        if AlertType.HIGH_VALUE_ORDER not in self._prefs.enabled_types:
            return None

        # Calculate store's AOV from recent orders
        store_id = str(order.store_id) if hasattr(order, 'store_id') else self._prefs.store_id
        
        # Get last 30 days of orders for AOV calculation
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_orders = self._db.query(Order).filter(
            Order.store_id == store_id,
            Order.created_at >= thirty_days_ago,
            Order.status != 'cancelled'
        ).all()

        if not recent_orders:
            # No baseline, use default threshold
            aov = 500.0  # Default AOV for new stores
        else:
            total_revenue = sum(float(o.total) for o in recent_orders if o.total)
            aov = total_revenue / len(recent_orders) if recent_orders else 500.0

        threshold = aov * self._prefs.thresholds.high_value_aov_multiplier

        if order_total > threshold:
            alert_id = self._generate_alert_id(AlertType.HIGH_VALUE_ORDER, str(order.id))
            
            # Get customer info
            customer_name = "Customer"
            customer_id = ""
            if hasattr(order, 'customer') and order.customer:
                customer_name = f"{order.customer.first_name or ''} {order.customer.last_name or ''}".strip()
                customer_id = str(order.customer.id)
            elif hasattr(order, 'customer_id') and order.customer_id:
                customer_id = str(order.customer_id)
                customer = self._db.query(Customer).filter(Customer.id == order.customer_id).first()
                if customer:
                    customer_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip()

            # Get order items
            items_data = []
            if hasattr(order, 'items'):
                for item in order.items[:5]:  # Limit to 5 items for preview
                    items_data.append({
                        "product_name": item.product_name if hasattr(item, 'product_name') else "",
                        "product_id": str(item.product_id) if hasattr(item, 'product_id') else "",
                        "quantity": item.quantity if hasattr(item, 'quantity') else 1,
                        "price": float(item.price) if hasattr(item, 'price') else 0,
                    })

            return SalesAlert(
                id=alert_id,
                type=AlertType.HIGH_VALUE_ORDER,
                severity=AlertSeverity.WARNING,
                title=f"High-Value Order Detected: ${order_total:,.2f}",
                message=f"Order #{order.order_number if hasattr(order, 'order_number') else order.id} exceeds your AOV threshold",
                rich_preview=f"Customer: {customer_name} | Order: #{order.order_number if hasattr(order, 'order_number') else order.id} | {len(items_data)} items",
                data={
                    "order_id": str(order.id),
                    "order_number": order.order_number if hasattr(order, 'order_number') else str(order.id),
                    "customer_name": customer_name,
                    "customer_id": customer_id,
                    "total_value": order_total,
                    "currency": "USD",
                    "aov_threshold": threshold,
                    "aov_multiplier": self._prefs.thresholds.high_value_aov_multiplier,
                    "items": items_data,
                },
                actions=[
                    {"type": "view_order", "label": "View Order", "primary": True, "target_path": f"/brand-dashboard/orders/{order.id}"},
                    {"type": "view_customer", "label": "View Customer", "target_path": f"/brand-dashboard/customers/{customer_id}"},
                    {"type": "dismiss", "label": "Dismiss"},
                ],
                store_id=store_id,
                store_name=self._get_store_name(store_id),
                dedup_key=f"high_value_order::{store_id}::{order.id}",
            )

        return None

    # ─── Unusual Returns Pattern Detection ───────────────────────────────────────

    def check_unusual_returns(self, product_id: str, time_window_hours: int = None) -> Optional[SalesAlert]:
        """
        Check if a product has unusual return patterns.
        Triggers: 5+ returns in 1 hour OR return rate jumps 50%+ vs baseline
        """
        if AlertType.UNUSUAL_RETURNS not in self._prefs.enabled_types:
            return None

        window_hours = time_window_hours or self._prefs.thresholds.returns_spike_window_hours
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Get product info
        product = self._db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        store_id = str(product.store_id) if hasattr(product, 'store_id') else self._prefs.store_id

        # Count recent returns for this product
        recent_returns = self._db.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.status == 'returned',
            Order.updated_at >= window_start
        ).count()

        # Check spike threshold
        if recent_returns < self._prefs.thresholds.returns_spike_count:
            return None

        # Calculate baseline return rate (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        total_orders_30d = self._db.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= thirty_days_ago
        ).count()

        returned_orders_30d = self._db.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.status == 'returned',
            Order.created_at >= thirty_days_ago
        ).count()

        baseline_rate = (returned_orders_30d / total_orders_30d * 100) if total_orders_30d > 0 else 0

        # Current window rate
        total_orders_window = self._db.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= window_start
        ).count()

        current_rate = (recent_returns / total_orders_window * 100) if total_orders_window > 0 else 0

        # Check if rate increase exceeds threshold
        rate_increase = ((current_rate - baseline_rate) / baseline_rate * 100) if baseline_rate > 0 else 0

        if recent_returns >= self._prefs.thresholds.returns_spike_count or rate_increase >= self._prefs.thresholds.returns_rate_increase_percent:
            alert_id = self._generate_alert_id(AlertType.UNUSUAL_RETURNS, product_id)

            return SalesAlert(
                id=alert_id,
                type=AlertType.UNUSUAL_RETURNS,
                severity=AlertSeverity.WARNING,
                title=f"Unusual Return Pattern: {product.name}",
                message=f"{recent_returns} returns detected in the last {window_hours} hour(s)",
                rich_preview=f"SKU: {product.sku or 'N/A'} | {recent_returns} returns in {window_hours}h | Rate: {current_rate:.1f}%",
                data={
                    "product_id": str(product_id),
                    "product_name": product.name,
                    "product_sku": product.sku or "",
                    "return_count": recent_returns,
                    "return_rate_percent": current_rate,
                    "baseline_return_rate_percent": baseline_rate,
                    "time_window_hours": window_hours,
                    "affected_orders": [],  # Would populate with actual order IDs
                },
                actions=[
                    {"type": "view_product", "label": "View Product", "primary": True, "target_path": f"/brand-dashboard/products/{product_id}"},
                    {"type": "analyze_returns", "label": "Analyze Returns", "target_path": f"/brand-dashboard/analytics/returns?product_id={product_id}"},
                    {"type": "dismiss", "label": "Dismiss"},
                ],
                store_id=store_id,
                store_name=self._get_store_name(store_id),
                dedup_key=f"unusual_returns::{store_id}::{product_id}",
            )

        return None

    # ─── Inventory Depletion Detection ───────────────────────────────────────────

    def check_inventory_depletion(self, product_id: str) -> Optional[SalesAlert]:
        """
        Check if product stock is below threshold.
        Triggers: Stock < configured threshold units
        """
        if AlertType.INVENTORY_DEPLETION not in self._prefs.enabled_types:
            return None

        product = self._db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        store_id = str(product.store_id) if hasattr(product, 'store_id') else self._prefs.store_id
        current_stock = product.stock if hasattr(product, 'stock') else 0

        threshold = self._prefs.thresholds.inventory_threshold_units

        if current_stock <= threshold:
            # Calculate days until stockout based on recent sales velocity
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_sales = self._db.query(OrderItem).join(Order).filter(
                OrderItem.product_id == product_id,
                Order.created_at >= seven_days_ago,
                Order.status != 'cancelled'
            ).count()

            daily_velocity = recent_sales / 7 if recent_sales > 0 else 0
            days_until_stockout = int(current_stock / daily_velocity) if daily_velocity > 0 else None

            # Determine severity based on urgency
            severity = AlertSeverity.CRITICAL if current_stock <= 5 or (days_until_stockout and days_until_stockout <= 3) else AlertSeverity.WARNING

            alert_id = self._generate_alert_id(AlertType.INVENTORY_DEPLETION, product_id)

            return SalesAlert(
                id=alert_id,
                type=AlertType.INVENTORY_DEPLETION,
                severity=severity,
                title=f"Low Stock Alert: {product.name}",
                message=f"Only {current_stock} units remaining",
                rich_preview=f"Stock: {current_stock} units | Threshold: {threshold} units" + (f" | ~{days_until_stockout} days to stockout" if days_until_stockout else ""),
                data={
                    "product_id": str(product_id),
                    "product_name": product.name,
                    "product_sku": product.sku or "",
                    "current_stock": current_stock,
                    "reorder_point": threshold,
                    "threshold_configured": threshold,
                    "days_until_stockout": days_until_stockout,
                    "product_image": product.image_url if hasattr(product, 'image_url') else None,
                },
                actions=[
                    {"type": "restock", "label": "Restock", "primary": True, "target_path": f"/brand-dashboard/inventory/restock?product_id={product_id}"},
                    {"type": "view_product", "label": "View Product", "target_path": f"/brand-dashboard/products/{product_id}"},
                    {"type": "dismiss", "label": "Dismiss"},
                ],
                store_id=store_id,
                store_name=self._get_store_name(store_id),
                dedup_key=f"inventory_depletion::{store_id}::{product_id}",
            )

        return None

    # ─── Conversion Rate Anomaly Detection ───────────────────────────────────────

    def check_conversion_anomaly(self, store_id: str) -> Optional[SalesAlert]:
        """
        Check for conversion rate deviations from baseline.
        Triggers: Conversion rate deviates >15% drop or >20% rise from 7-day rolling average
        """
        if AlertType.CONVERSION_ANOMALY not in self._prefs.enabled_types:
            return None

        # Calculate current conversion rate (last 24 hours)
        now = datetime.now(timezone.utc)
        twenty_four_hours_ago = now - timedelta(hours=24)

        # This would typically use analytics/session data
        # For now, we'll use order data as a proxy
        recent_orders = self._db.query(Order).filter(
            Order.store_id == store_id,
            Order.created_at >= twenty_four_hours_ago,
            Order.status != 'cancelled'
        ).count()

        # Calculate baseline (last 7 days, excluding last 24h)
        seven_days_ago = now - timedelta(days=7)
        baseline_orders = self._db.query(Order).filter(
            Order.store_id == store_id,
            Order.created_at >= seven_days_ago,
            Order.created_at < twenty_four_hours_ago,
            Order.status != 'cancelled'
        ).count()

        # Normalize to daily rate
        baseline_daily = baseline_orders / 6 if baseline_orders > 0 else 0
        current_daily = recent_orders  # Already 24h

        if baseline_daily == 0:
            return None  # No baseline to compare

        delta_percent = ((current_daily - baseline_daily) / baseline_daily) * 100

        # Check thresholds
        is_drop = delta_percent <= -self._prefs.thresholds.conversion_drop_threshold_percent
        is_rise = delta_percent >= self._prefs.thresholds.conversion_rise_threshold_percent

        if not (is_drop or is_rise):
            return None

        severity = AlertSeverity.CRITICAL if is_drop else AlertSeverity.INFO
        direction = "drop" if is_drop else "rise"

        alert_id = self._generate_alert_id(AlertType.CONVERSION_ANOMALY, store_id)

        return SalesAlert(
            id=alert_id,
            type=AlertType.CONVERSION_ANOMALY,
            severity=severity,
            title=f"Conversion {direction.title()}: {abs(delta_percent):.1f}%",
            message=f"Store conversion rate has {'dropped' if is_drop else 'risen'} significantly",
            rich_preview=f"Current: {current_daily:.1f}/day | Baseline: {baseline_daily:.1f}/day | Sessions: N/A",
            data={
                "current_rate": current_daily,
                "baseline_rate": baseline_daily,
                "delta_percent": delta_percent,
                "direction": direction,
                "time_window": "24h",
                "sessions_analyzed": 0,  # Would come from analytics
                "conversions_analyzed": recent_orders,
            },
            actions=[
                {"type": "view_analytics", "label": "View Analytics", "primary": True, "target_path": "/brand-dashboard/analytics/conversion"},
                {"type": "dismiss", "label": "Dismiss"},
            ],
            store_id=store_id,
            store_name=self._get_store_name(store_id),
            dedup_key=f"conversion_anomaly::{store_id}::store",
        )

    # ─── Customer Segment Change Detection ───────────────────────────────────────

    def check_customer_segment_change(self, customer_id: str) -> Optional[SalesAlert]:
        """
        Check for VIP churn or segment transitions.
        Triggers: VIP inactive >30 days, returning → inactive
        """
        if AlertType.CUSTOMER_SEGMENT_CHANGE not in self._prefs.enabled_types:
            return None

        customer = self._db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None

        # Determine current segment based on purchase history
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        ninety_days_ago = now - timedelta(days=90)

        # Get customer's orders
        orders = self._db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.status != 'cancelled'
        ).order_by(Order.created_at.desc()).all()

        last_order = orders[0] if orders else None
        last_purchase_date = last_order.created_at if last_order else None
        days_since_last_purchase = (now - last_purchase_date).days if last_purchase_date else 999

        # Calculate LTV
        total_lifetime_value = sum(float(o.total) for o in orders if o.total)

        # Determine segment
        previous_segment = getattr(customer, 'segment', 'new')
        
        # Segment logic
        if len(orders) >= 5 and total_lifetime_value >= 1000:
            current_segment = 'vip'
        elif len(orders) >= 2:
            current_segment = 'returning'
        elif len(orders) == 1:
            current_segment = 'new'
        else:
            current_segment = 'inactive'

        # Apply inactivity rules
        if previous_segment == 'vip' and days_since_last_purchase >= self._prefs.thresholds.vip_inactive_days:
            current_segment = 'inactive'
        elif previous_segment == 'returning' and days_since_last_purchase >= self._prefs.thresholds.returning_to_inactive_days:
            current_segment = 'inactive'

        # Check if there's a meaningful change
        if current_segment == previous_segment:
            return None

        # Only alert on concerning transitions
        concerning_transitions = [
            ('vip', 'inactive'),
            ('returning', 'inactive'),
            ('vip', 'returning'),
        ]

        if (previous_segment, current_segment) not in concerning_transitions:
            return None

        severity = AlertSeverity.CRITICAL if previous_segment == 'vip' else AlertSeverity.WARNING
        store_id = self._prefs.store_id
        alert_id = self._generate_alert_id(AlertType.CUSTOMER_SEGMENT_CHANGE, customer_id)

        customer_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip() or "Customer"

        return SalesAlert(
            id=alert_id,
            type=AlertType.CUSTOMER_SEGMENT_CHANGE,
            severity=severity,
            title=f"{'VIP Customer Inactive' if previous_segment == 'vip' else 'Customer Status Change'}: {customer_name}",
            message=f"Customer has transitioned from {previous_segment} to {current_segment}",
            rich_preview=f"Segment: {previous_segment} → {current_segment} | Last purchase: {last_purchase_date.strftime('%Y-%m-%d') if last_purchase_date else 'Never'} | LTV: ${total_lifetime_value:,.0f}",
            data={
                "customer_id": str(customer_id),
                "customer_name": customer_name,
                "previous_segment": previous_segment,
                "current_segment": current_segment,
                "last_purchase_date": last_purchase_date.isoformat() if last_purchase_date else None,
                "days_since_last_purchase": days_since_last_purchase,
                "total_lifetime_value": total_lifetime_value,
                "total_orders": len(orders),
            },
            actions=[
                {"type": "view_customer", "label": "View Profile", "primary": True, "target_path": f"/brand-dashboard/customers/{customer_id}"},
                {"type": "configure", "label": "Adjust Settings", "target_path": "/brand-dashboard/settings/alerts"},
                {"type": "dismiss", "label": "Dismiss"},
            ],
            store_id=store_id,
            store_name=self._get_store_name(store_id),
            dedup_key=f"customer_segment_change::{store_id}::{customer_id}",
        )

    # ─── Helper Methods ─────────────────────────────────────────────────────────

    def _generate_alert_id(self, alert_type: AlertType, identifier: str) -> str:
        """Generate a unique alert ID."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        random_suffix = hashlib.md5(f"{timestamp}-{identifier}".encode()).hexdigest()[:8]
        return f"alert-{alert_type.value}-{timestamp}-{random_suffix}"

    def _get_store_name(self, store_id: str) -> str:
        """Get store name by ID."""
        store = self._db.query(Store).filter(Store.id == store_id).first()
        return store.name if store else "Unknown Store"


# ─── Alert Throttling & Deduplication ───────────────────────────────────────────


class AlertThrottler:
    """
    Handles alert throttling and deduplication.
    Prevents notification fatigue through intelligent rate limiting.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local_cache: Dict[str, Tuple[str, float]] = {}  # Fallback if Redis unavailable

    def is_duplicate(self, dedup_key: str, window_minutes: int = 60) -> Tuple[bool, Optional[str]]:
        """
        Check if an alert with this dedup key was recently triggered.
        Returns (is_duplicate, existing_alert_id)
        """
        now = datetime.now(timezone.utc).timestamp()
        window_seconds = window_minutes * 60

        if self._redis:
            try:
                cached = self._redis.get(f"alert:dedup:{dedup_key}")
                if cached:
                    data = json.loads(cached)
                    return True, data.get("alert_id")
            except Exception as e:
                logger.warning(f"Redis dedup check failed: {e}")

        # Local fallback
        if dedup_key in self._local_cache:
            alert_id, timestamp = self._local_cache[dedup_key]
            if now - timestamp < window_seconds:
                return True, alert_id

        return False, None

    def record_trigger(self, dedup_key: str, alert_id: str, window_minutes: int = 60) -> None:
        """Record an alert trigger for deduplication."""
        data = json.dumps({"alert_id": alert_id, "timestamp": datetime.now(timezone.utc).isoformat()})

        if self._redis:
            try:
                self._redis.setex(f"alert:dedup:{dedup_key}", window_minutes * 60, data)
                return
            except Exception as e:
                logger.warning(f"Redis dedup record failed: {e}")

        self._local_cache[dedup_key] = (alert_id, datetime.now(timezone.utc).timestamp())

    def check_hourly_limit(self, store_id: str, max_per_hour: int) -> Tuple[bool, int]:
        """
        Check if store has exceeded hourly alert limit.
        Returns (is_allowed, remaining_count)
        """
        hour_key = f"alert:hourly:{store_id}:{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"

        if self._redis:
            try:
                current = int(self._redis.get(hour_key) or 0)
                remaining = max(0, max_per_hour - current)
                return current < max_per_hour, remaining
            except Exception as e:
                logger.warning(f"Redis hourly limit check failed: {e}")

        return True, max_per_hour  # Default to allowing if check fails

    def increment_hourly_count(self, store_id: str) -> None:
        """Increment the hourly alert count for a store."""
        hour_key = f"alert:hourly:{store_id}:{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"

        if self._redis:
            try:
                self._redis.incr(hour_key)
                self._redis.expire(hour_key, 3600)  # 1 hour TTL
            except Exception as e:
                logger.warning(f"Redis hourly count increment failed: {e}")


# ─── Main Alert Service ─────────────────────────────────────────────────────────


class SalesAlertService:
    """
    Main service for managing sales alerts.
    Coordinates rule evaluation, throttling, and delivery.
    """

    def __init__(self, db: Session, redis_client=None):
        self._db = db
        self._throttler = AlertThrottler(redis_client)
        self._preferences_cache: Dict[str, AlertPreferences] = {}

    def get_preferences(self, store_id: str) -> AlertPreferences:
        """Get alert preferences for a store (with caching)."""
        if store_id in self._preferences_cache:
            return self._preferences_cache[store_id]

        # Would load from database in production
        prefs = AlertPreferences(store_id=store_id)
        self._preferences_cache[store_id] = prefs
        return prefs

    def update_preferences(self, store_id: str, preferences: AlertPreferences) -> None:
        """Update alert preferences for a store."""
        preferences.updated_at = datetime.now(timezone.utc).isoformat()
        self._preferences_cache[store_id] = preferences
        # Would persist to database in production

    def evaluate_order(self, order: Order) -> List[SalesAlert]:
        """
        Evaluate all alert rules for a new order.
        Returns list of triggered alerts.
        """
        store_id = str(order.store_id) if hasattr(order, 'store_id') else None
        if not store_id:
            return []

        prefs = self.get_preferences(store_id)
        engine = AlertRuleEngine(self._db, prefs)
        alerts = []

        # Check high value order
        order_total = float(order.total) if hasattr(order, 'total') and order.total else 0
        alert = engine.check_high_value_order(order, order_total)
        if alert and self._should_deliver(alert, prefs):
            alerts.append(alert)

        return alerts

    def evaluate_product(self, product_id: str) -> List[SalesAlert]:
        """
        Evaluate alerts for product changes (inventory, returns).
        """
        product = self._db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return []

        store_id = str(product.store_id) if hasattr(product, 'store_id') else None
        if not store_id:
            return []

        prefs = self.get_preferences(store_id)
        engine = AlertRuleEngine(self._db, prefs)
        alerts = []

        # Check inventory depletion
        alert = engine.check_inventory_depletion(product_id)
        if alert and self._should_deliver(alert, prefs):
            alerts.append(alert)

        # Check unusual returns
        alert = engine.check_unusual_returns(product_id)
        if alert and self._should_deliver(alert, prefs):
            alerts.append(alert)

        return alerts

    def evaluate_store_metrics(self, store_id: str) -> List[SalesAlert]:
        """
        Evaluate store-level metrics (conversion rate).
        """
        prefs = self.get_preferences(store_id)
        engine = AlertRuleEngine(self._db, prefs)
        alerts = []

        # Check conversion anomaly
        alert = engine.check_conversion_anomaly(store_id)
        if alert and self._should_deliver(alert, prefs):
            alerts.append(alert)

        return alerts

    def evaluate_customer(self, customer_id: str, store_id: str) -> List[SalesAlert]:
        """
        Evaluate customer segment changes.
        """
        prefs = self.get_preferences(store_id)
        engine = AlertRuleEngine(self._db, prefs)
        alerts = []

        # Check segment change
        alert = engine.check_customer_segment_change(customer_id)
        if alert and self._should_deliver(alert, prefs):
            alerts.append(alert)

        return alerts

    def _should_deliver(self, alert: SalesAlert, prefs: AlertPreferences) -> bool:
        """
        Determine if an alert should be delivered based on throttling rules.
        """
        # Check deduplication
        is_dup, existing_id = self._throttler.is_duplicate(
            alert.dedup_key,
            prefs.frequency.dedup_window_minutes
        )
        if is_dup:
            logger.info(f"Alert deduplicated: {alert.dedup_key} (existing: {existing_id})")
            return False

        # Check hourly limit
        allowed, remaining = self._throttler.check_hourly_limit(
            alert.store_id,
            prefs.frequency.max_alerts_per_hour
        )
        if not allowed:
            logger.info(f"Hourly alert limit reached for store {alert.store_id}")
            return False

        # Record the trigger
        self._throttler.record_trigger(alert.dedup_key, alert.id, prefs.frequency.dedup_window_minutes)
        self._throttler.increment_hourly_count(alert.store_id)

        return True

    def get_alert_history(
        self,
        store_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SalesAlert]:
        """
        Get alert history for a store.
        Would query from database in production.
        """
        # Placeholder - would query from database
        return []

    def mark_alert_read(self, alert_id: str, store_id: str) -> bool:
        """Mark an alert as read."""
        # Would update database in production
        return True

    def dismiss_alert(self, alert_id: str, store_id: str) -> bool:
        """Dismiss an alert."""
        # Would update database in production
        return True


# ─── Service Factory ───────────────────────────────────────────────────────────


def get_sales_alert_service(db: Session) -> SalesAlertService:
    """Factory function for dependency injection."""
    try:
        redis_client = get_redis_client()
    except Exception:
        redis_client = None
    return SalesAlertService(db, redis_client)
