"""
CONFIT Backend — Fulfillment Service
====================================
Fulfillment workflow optimization:
- Delivery route optimization
- Inventory allocation
- Order fulfillment tracking
- Shipping carrier selection
- Pickup coordination
- Return logistics

Integrates with inventory and shipping providers.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
from enum import Enum

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db
from sqlalchemy import and_, or_, func

from database.models import Order, OrderItem, Store, Product

logger = logging.getLogger(__name__)


# ── Fulfillment Constants ───────────────────────────────────────────────

SHIPPING_CARRIERS = {
    "usps": {
        "name": "USPS",
        "standard_days": (5, 7),
        "express_days": (2, 3),
        "overnight_available": False,
        "tracking": True,
        "eco_score": 0.9,
    },
    "ups": {
        "name": "UPS",
        "standard_days": (3, 5),
        "express_days": (2, 3),
        "overnight_days": (1, 1),
        "tracking": True,
        "eco_score": 0.6,
    },
    "fedex": {
        "name": "FedEx",
        "standard_days": (3, 5),
        "express_days": (2, 2),
        "overnight_days": (1, 1),
        "tracking": True,
        "eco_score": 0.5,
    },
    "dhl": {
        "name": "DHL",
        "standard_days": (3, 5),
        "express_days": (2, 3),
        "overnight_days": (1, 1),
        "tracking": True,
        "eco_score": 0.55,
    },
}

FULFILLMENT_PRIORITIES = {
    "same_day": {"cutoff_hour": 14, "priority": 1},
    "next_day": {"cutoff_hour": 18, "priority": 2},
    "standard": {"cutoff_hour": 23, "priority": 3},
}

INVENTORY_SOURCES = {
    "warehouse": {"priority": 1, "shipping_origin": "distribution_center"},
    "store": {"priority": 2, "shipping_origin": "store_location"},
    "dropship": {"priority": 3, "shipping_origin": "vendor"},
}

ORDER_STATUS_WORKFLOW = {
    "pending": {"next": ["confirmed", "cancelled"], "auto_transition_minutes": 30},
    "confirmed": {"next": ["processing", "cancelled"], "auto_transition_minutes": 60},
    "processing": {"next": ["ready_to_ship", "on_hold"], "auto_transition_minutes": None},
    "ready_to_ship": {"next": ["shipped", "on_hold"], "auto_transition_minutes": 120},
    "shipped": {"next": ["in_transit", "delivered"], "auto_transition_minutes": None},
    "in_transit": {"next": ["out_for_delivery", "delivered"], "auto_transition_minutes": None},
    "out_for_delivery": {"next": ["delivered", "delivery_failed"], "auto_transition_minutes": None},
    "delivered": {"next": ["returned"], "auto_transition_minutes": None},
    "on_hold": {"next": ["processing", "cancelled"], "auto_transition_minutes": None},
    "cancelled": {"next": [], "auto_transition_minutes": None},
    "returned": {"next": [], "auto_transition_minutes": None},
    "delivery_failed": {"next": ["returned", "rescheduled"], "auto_transition_minutes": None},
}


class FulfillmentStatus(str, Enum):
    """Fulfillment status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class DeliveryMethod(str, Enum):
    """Delivery method enumeration."""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    PICKUP = "pickup"
    SAME_DAY = "same_day"


class FulfillmentAllocation:
    """Fulfillment allocation result."""
    
    def __init__(
        self,
        order_id: str,
        allocations: List[Dict[str, Any]],
        estimated_delivery: str,
        shipping_carrier: str,
        tracking_number: str,
        total_cost: float,
        optimization_score: float,
    ):
        self.order_id = order_id
        self.allocations = allocations
        self.estimated_delivery = estimated_delivery
        self.shipping_carrier = shipping_carrier
        self.tracking_number = tracking_number
        self.total_cost = total_cost
        self.optimization_score = optimization_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "allocations": self.allocations,
            "estimated_delivery": self.estimated_delivery,
            "shipping_carrier": self.shipping_carrier,
            "tracking_number": self.tracking_number,
            "total_cost": round(self.total_cost, 2),
            "optimization_score": round(self.optimization_score, 2),
        }


class DeliveryEstimate:
    """Delivery estimate result."""
    
    def __init__(
        self,
        method: str,
        carrier: str,
        estimated_min: datetime,
        estimated_max: datetime,
        cost: float,
        eco_score: float,
        guaranteed: bool,
    ):
        self.method = method
        self.carrier = carrier
        self.estimated_min = estimated_min
        self.estimated_max = estimated_max
        self.cost = cost
        self.eco_score = eco_score
        self.guaranteed = guaranteed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "carrier": self.carrier,
            "estimated_min": self.estimated_min.isoformat(),
            "estimated_max": self.estimated_max.isoformat(),
            "estimated_range": f"{self.estimated_min.strftime('%b %d')} - {self.estimated_max.strftime('%b %d')}",
            "cost": round(self.cost, 2),
            "eco_score": round(self.eco_score, 2),
            "guaranteed": self.guaranteed,
        }


class FulfillmentService:
    """
    Fulfillment workflow optimization service.
    
    Features:
    - Multi-source inventory allocation
    - Carrier selection optimization
    - Delivery time estimation
    - Pickup coordination
    - Order tracking
    - Return logistics
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Order Fulfillment ────────────────────────────────────────────────
    
    def allocate_fulfillment(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        delivery_method: str = "standard",
        preferences: Dict[str, Any] = None,
    ) -> FulfillmentAllocation:
        """
        Allocate order items to optimal fulfillment sources.
        
        Strategy:
        1. Check local store inventory for pickup
        2. Check warehouse availability
        3. Consider dropship for out-of-stock items
        4. Optimize for speed or cost based on preferences
        """
        allocations = []
        total_cost = 0.0
        optimization_score = 100.0
        
        prefs = preferences or {}
        prioritize_speed = prefs.get("prioritize_speed", False)
        prioritize_eco = prefs.get("prioritize_eco", False)
        
        for item in items:
            product_id = item.get("productId") or item.get("product_id")
            quantity = item.get("quantity", 1)
            
            # Find best source for this item
            source = self._find_best_source(
                product_id=product_id,
                quantity=quantity,
                shipping_address=shipping_address,
                prioritize_speed=prioritize_speed,
            )
            
            allocations.append({
                "item_id": product_id,
                "quantity": quantity,
                "source_type": source["type"],
                "source_id": source["id"],
                "source_name": source["name"],
                "available": source["available"],
                "shipping_from": source["location"],
            })
            
            # Adjust optimization score based on source quality
            if not source["available"]:
                optimization_score -= 10
        
        # Select best carrier
        carrier = self._select_carrier(
            delivery_method=delivery_method,
            shipping_address=shipping_address,
            prioritize_eco=prioritize_eco,
        )
        
        # Calculate shipping cost
        shipping_cost = self._calculate_shipping_cost(
            allocations=allocations,
            carrier=carrier,
            delivery_method=delivery_method,
        )
        total_cost = shipping_cost
        
        # Generate tracking number
        tracking_number = self._generate_tracking_number(carrier)
        
        # Estimate delivery
        estimated_delivery = self._estimate_delivery_date(
            carrier=carrier,
            method=delivery_method,
            shipping_address=shipping_address,
        )
        
        return FulfillmentAllocation(
            order_id=order_id,
            allocations=allocations,
            estimated_delivery=estimated_delivery,
            shipping_carrier=carrier,
            tracking_number=tracking_number,
            total_cost=total_cost,
            optimization_score=optimization_score,
        )
    
    def _find_best_source(
        self,
        product_id: str,
        quantity: int,
        shipping_address: Dict[str, Any],
        prioritize_speed: bool = False,
    ) -> Dict[str, Any]:
        """Find the best inventory source for a product."""
        
        # Check stores near shipping address first (for speed)
        if prioritize_speed and shipping_address:
            nearby_stores = self._find_nearby_stores(shipping_address)
            for store in nearby_stores:
                availability = self._check_store_availability(product_id, store["id"])
                if availability >= quantity:
                    return {
                        "type": "store",
                        "id": store["id"],
                        "name": store["name"],
                        "available": True,
                        "location": store.get("address", "Store location"),
                        "quantity": availability,
                    }
        
        # Check warehouse (default)
        warehouse_availability = self._check_warehouse_availability(product_id)
        if warehouse_availability >= quantity:
            return {
                "type": "warehouse",
                "id": "main_dc",
                "name": "Distribution Center",
                "available": True,
                "location": "Regional Warehouse",
                "quantity": warehouse_availability,
            }
        
        # Fall back to dropship
        return {
            "type": "dropship",
            "id": "vendor",
            "name": "Direct from Supplier",
            "available": True,
            "location": "Vendor Warehouse",
            "quantity": 999,  # Assume available
        }
    
    def _find_nearby_stores(self, address: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find stores near the given address."""
        # In production, would use geolocation
        stores = self._db.query(Store).limit(5).all()
        
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "address": s.address,
                "city": s.city,
            }
            for s in stores
        ]
    
    def _check_store_availability(self, product_id: str, store_id: str) -> int:
        """Check product availability at a specific store."""
        # Simplified - would query inventory system
        return 10  # Assume available
    
    def _check_warehouse_availability(self, product_id: str) -> int:
        """Check product availability in warehouse."""
        # Simplified - would query inventory system
        return 50  # Assume available
    
    def _select_carrier(
        self,
        delivery_method: str,
        shipping_address: Dict[str, Any],
        prioritize_eco: bool = False,
    ) -> str:
        """Select optimal shipping carrier."""
        
        if prioritize_eco:
            return "usps"  # USPS has best eco score
        
        if delivery_method == "overnight":
            return "fedex"  # FedEx best for overnight
        
        if delivery_method == "express":
            return "ups"  # UPS reliable for express
        
        return "usps"  # Default to USPS for standard
    
    def _calculate_shipping_cost(
        self,
        allocations: List[Dict[str, Any]],
        carrier: str,
        delivery_method: str,
    ) -> float:
        """Calculate shipping cost based on allocations and method."""
        base_costs = {
            "standard": 5.99,
            "express": 12.99,
            "overnight": 24.99,
            "pickup": 0,
            "same_day": 19.99,
        }
        
        base = base_costs.get(delivery_method, 5.99)
        
        # Adjust for number of packages/sources
        unique_sources = set(a["source_type"] for a in allocations)
        if len(unique_sources) > 1:
            base += (len(unique_sources) - 1) * 2.99  # Multi-package surcharge
        
        return base
    
    def _generate_tracking_number(self, carrier: str) -> str:
        """Generate a tracking number for the shipment."""
        import random
        import string
        
        prefixes = {
            "usps": "9400",
            "ups": "1Z",
            "fedex": "794",
            "dhl": "420",
        }
        
        prefix = prefixes.get(carrier, "TRK")
        suffix = ''.join(random.choices(string.digits, k=12))
        
        return f"{prefix}{suffix}"
    
    def _estimate_delivery_date(
        self,
        carrier: str,
        method: str,
        shipping_address: Dict[str, Any],
    ) -> str:
        """Estimate delivery date range."""
        carrier_info = SHIPPING_CARRIERS.get(carrier, SHIPPING_CARRIERS["usps"])
        
        if method == "overnight":
            days = carrier_info.get("overnight_days", (1, 1))
        elif method == "express":
            days = carrier_info.get("express_days", (2, 3))
        else:
            days = carrier_info.get("standard_days", (5, 7))
        
        min_days, max_days = days
        
        min_date = datetime.now(timezone.utc) + timedelta(days=min_days)
        max_date = datetime.now(timezone.utc) + timedelta(days=max_days)
        
        return f"{min_date.strftime('%b %d')} - {max_date.strftime('%b %d')}"
    
    # ── Delivery Estimates ───────────────────────────────────────────────
    
    def get_delivery_estimates(
        self,
        shipping_address: Dict[str, Any],
        items: List[Dict[str, Any]],
    ) -> List[DeliveryEstimate]:
        """
        Get all available delivery options with estimates.
        """
        estimates = []
        
        # Standard delivery
        estimates.append(self._create_estimate(
            method="standard",
            carrier="usps",
            days_range=(5, 7),
            base_cost=5.99,
            guaranteed=False,
        ))
        
        # Express delivery
        estimates.append(self._create_estimate(
            method="express",
            carrier="ups",
            days_range=(2, 3),
            base_cost=12.99,
            guaranteed=True,
        ))
        
        # Overnight delivery
        estimates.append(self._create_estimate(
            method="overnight",
            carrier="fedex",
            days_range=(1, 1),
            base_cost=24.99,
            guaranteed=True,
        ))
        
        # Check for pickup availability
        if shipping_address:
            nearby_stores = self._find_nearby_stores(shipping_address)
            if nearby_stores:
                estimates.append(self._create_estimate(
                    method="pickup",
                    carrier="store",
                    days_range=(0, 1),
                    base_cost=0,
                    guaranteed=True,
                ))
        
        return estimates
    
    def _create_estimate(
        self,
        method: str,
        carrier: str,
        days_range: Tuple[int, int],
        base_cost: float,
        guaranteed: bool,
    ) -> DeliveryEstimate:
        """Create a delivery estimate object."""
        min_days, max_days = days_range
        
        carrier_info = SHIPPING_CARRIERS.get(carrier, {})
        eco_score = carrier_info.get("eco_score", 0.5) if carrier != "store" else 1.0
        
        return DeliveryEstimate(
            method=method,
            carrier=carrier,
            estimated_min=datetime.now(timezone.utc) + timedelta(days=min_days),
            estimated_max=datetime.now(timezone.utc) + timedelta(days=max_days),
            cost=base_cost,
            eco_score=eco_score,
            guaranteed=guaranteed,
        )
    
    # ── Order Status Management ──────────────────────────────────────────
    
    def update_order_status(
        self,
        order_id: str,
        new_status: str,
        notes: str = None,
    ) -> Dict[str, Any]:
        """Update order status with workflow validation."""
        order = self._db.query(Order).filter_by(id=order_id).first()
        
        if not order:
            return {"success": False, "error": "Order not found"}
        
        current_status = order.status
        workflow = ORDER_STATUS_WORKFLOW.get(current_status, {})
        
        # Validate transition
        if new_status not in workflow.get("next", []):
            return {
                "success": False,
                "error": f"Cannot transition from {current_status} to {new_status}",
                "valid_transitions": workflow.get("next", []),
            }
        
        # Update status
        order.status = new_status
        self._db.commit()
        
        # Log status change
        logger.info(f"Order {order_id} status changed: {current_status} -> {new_status}")
        
        return {
            "success": True,
            "previous_status": current_status,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }
    
    def get_order_timeline(self, order_id: str) -> List[Dict[str, Any]]:
        """Get order fulfillment timeline with milestones."""
        order = self._db.query(Order).filter_by(id=order_id).first()
        
        if not order:
            return []
        
        timeline = []
        status = order.status
        placed_at = order.placed_at
        
        # Build timeline based on current status
        milestones = [
            {"status": "confirmed", "label": "Order Confirmed", "completed": True},
            {"status": "processing", "label": "Processing", "completed": status not in ["pending", "confirmed"]},
            {"status": "ready_to_ship", "label": "Ready to Ship", "completed": False},
            {"status": "shipped", "label": "Shipped", "completed": False},
            {"status": "in_transit", "label": "In Transit", "completed": False},
            {"status": "out_for_delivery", "label": "Out for Delivery", "completed": False},
            {"status": "delivered", "label": "Delivered", "completed": False},
        ]
        
        # Mark completed milestones
        status_order = ["confirmed", "processing", "ready_to_ship", "shipped", "in_transit", "out_for_delivery", "delivered"]
        current_idx = status_order.index(status) if status in status_order else -1
        
        for i, milestone in enumerate(milestones):
            milestone_idx = status_order.index(milestone["status"]) if milestone["status"] in status_order else 999
            milestone["completed"] = milestone_idx <= current_idx
            
            if milestone["completed"]:
                milestone["timestamp"] = placed_at.isoformat() if i == 0 else None
            
            timeline.append(milestone)
        
        return timeline
    
    # ── Pickup Coordination ───────────────────────────────────────────────
    
    def coordinate_pickup(
        self,
        order_id: str,
        store_id: str,
        pickup_time: str = None,
    ) -> Dict[str, Any]:
        """Coordinate in-store pickup for an order."""
        store = self._db.query(Store).filter_by(id=store_id).first()
        
        if not store:
            return {"success": False, "error": "Store not found"}
        
        # Generate pickup code
        pickup_code = self._generate_pickup_code()
        
        # Calculate pickup window
        pickup_window = self._calculate_pickup_window(store)
        
        return {
            "success": True,
            "order_id": order_id,
            "store": {
                "id": str(store.id),
                "name": store.name,
                "address": store.address,
                "phone": store.phone,
                "hours": store.hours,
            },
            "pickup_code": pickup_code,
            "pickup_window": pickup_window,
            "instructions": [
                "Bring your pickup code and ID",
                "Order will be held for 7 days",
                "Call store if you need to reschedule",
            ],
        }
    
    def _generate_pickup_code(self) -> str:
        """Generate a pickup code."""
        import random
        import string
        
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    def _calculate_pickup_window(self, store: Store) -> Dict[str, Any]:
        """Calculate pickup availability window."""
        now = datetime.now(timezone.utc)
        
        # Store hours would determine availability
        # Simplified: assume ready in 2 hours if before 6pm
        if now.hour < 18:
            ready_time = now + timedelta(hours=2)
        else:
            # Next day
            ready_time = (now + timedelta(days=1)).replace(hour=10, minute=0)
        
        return {
            "ready_after": ready_time.isoformat(),
            "expires_after": (now + timedelta(days=7)).isoformat(),
            "store_hours": store.hours,
        }
    
    # ── Return Logistics ──────────────────────────────────────────────────
    
    def process_return_request(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        reason: str,
        return_method: str = "ship",
    ) -> Dict[str, Any]:
        """Process a return request and generate return shipping."""
        
        # Generate return label
        if return_method == "ship":
            return_label = self._generate_return_label(order_id)
        else:
            return_label = None
        
        # Calculate refund estimate
        refund_estimate = self._calculate_refund_estimate(items)
        
        # Find nearest drop-off location
        drop_off_locations = self._find_drop_off_locations()
        
        return {
            "success": True,
            "order_id": order_id,
            "return_id": f"RET-{order_id}",
            "return_method": return_method,
            "return_label": return_label,
            "refund_estimate": refund_estimate,
            "drop_off_locations": drop_off_locations[:3],
            "instructions": self._get_return_instructions(return_method),
            "status": "pending_shipment" if return_method == "ship" else "pending_dropoff",
        }
    
    def _generate_return_label(self, order_id: str) -> Dict[str, Any]:
        """Generate a return shipping label."""
        return {
            "carrier": "usps",
            "tracking_number": f"RET{order_id}US",
            "label_url": f"/api/fulfillment/return-label/{order_id}",
            "expires": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
    
    def _calculate_refund_estimate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate estimated refund amount."""
        subtotal = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
        
        # Deductions
        restocking_fee = 0  # No restocking fee for most items
        shipping_deduction = 0  # Original shipping not refunded
        
        return {
            "subtotal": round(subtotal, 2),
            "restocking_fee": restocking_fee,
            "shipping_deduction": shipping_deduction,
            "total_estimate": round(subtotal - restocking_fee, 2),
            "refund_method": "original_payment",
        }
    
    def _find_drop_off_locations(self) -> List[Dict[str, Any]]:
        """Find nearby drop-off locations for returns."""
        return [
            {
                "type": "ups_store",
                "name": "UPS Store",
                "address": "123 Main St",
                "distance_miles": 1.2,
            },
            {
                "type": "usps",
                "name": "Post Office",
                "address": "456 Oak Ave",
                "distance_miles": 0.8,
            },
            {
                "type": "store",
                "name": "CONFIT Store",
                "address": "789 Fashion Blvd",
                "distance_miles": 2.5,
            },
        ]
    
    def _get_return_instructions(self, method: str) -> List[str]:
        """Get return instructions based on method."""
        if method == "ship":
            return [
                "Pack items in original packaging if possible",
                "Attach return label to package",
                "Drop off at any USPS location",
                "Keep tracking number for reference",
                "Refund processed within 5-7 days of receipt",
            ]
        return [
            "Bring items to store with order confirmation",
            "Show return code at checkout",
            "Instant refund to original payment method",
        ]
    
    # ── Inventory Optimization ───────────────────────────────────────────
    
    def get_inventory_recommendations(self, product_id: str) -> Dict[str, Any]:
        """Get inventory optimization recommendations."""
        return {
            "product_id": product_id,
            "current_stock": 45,
            "safety_stock": 10,
            "reorder_point": 15,
            "recommended_order": 30,
            "turnover_rate": 4.2,
            "days_of_stock": 12,
            "locations": [
                {"location": "DC East", "quantity": 25},
                {"location": "Store NYC", "quantity": 10},
                {"location": "Store LA", "quantity": 10},
            ],
        }


def get_fulfillment_service(db: Session = Depends(get_db)) -> FulfillmentService:
    return FulfillmentService(db)
