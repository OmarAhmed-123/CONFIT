"""
CONFIT Analytics Service
========================
High-volume event tracking service for dashboards and reporting.
Supports async non-blocking writes via Celery, Redis counters, and Mixpanel forwarding.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Feature flags
ANALYTICS_FORWARD_ENABLED = os.getenv("ANALYTICS_FORWARD_ENABLED", "false").lower() == "true"
MIXPANEL_TOKEN = os.getenv("MIXPANEL_TOKEN", "")


class StandardEvent(str, Enum):
    """Standard analytics event names (snake_case convention)."""
    # User lifecycle
    USER_SIGNUP = "user_signup"
    USER_LOGIN = "user_login"
    
    # Product engagement
    PRODUCT_VIEWED = "product_viewed"
    PRODUCT_ADDED_TO_CART = "product_added_to_cart"
    
    # Try-on flow
    TRY_ON_STARTED = "try_on_started"
    TRY_ON_COMPLETED = "try_on_completed"
    TRY_ON_ADDED_TO_BAG = "try_on_added_to_bag"
    
    # Muse AI
    MUSE_QUERY_SENT = "muse_query_sent"
    MUSE_OUTFIT_GENERATED = "muse_outfit_generated"
    
    # Outfit actions
    OUTFIT_SAVED = "outfit_saved"
    OUTFIT_SHARED = "outfit_shared"
    
    # Checkout & payments
    CHECKOUT_STARTED = "checkout_started"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    
    # Orders
    ORDER_PLACED = "order_placed"
    ORDER_DELIVERED = "order_delivered"
    ORDER_RETURNED = "order_returned"
    
    # Quality control
    MIDWAY_REJECTION = "midway_rejection"
    
    # Coupons
    COUPON_APPLIED = "coupon_applied"
    COUPON_REDEEMED = "coupon_redeemed"
    
    # Store visits
    STORE_VISITED = "store_visited"
    
    # Donor system
    DONOR_COUPON_CREATED = "donor_coupon_created"
    DONOR_COUPON_REDEEMED = "donor_coupon_redeemed"


class AnalyticsService:
    """
    Analytics event tracking service.
    
    Features:
    - Non-blocking async writes via Celery
    - Redis real-time counters
    - Optional Mixpanel/PostHog forwarding
    - PII minimization (hashed user_id for external services)
    """
    
    _instance: Optional['AnalyticsService'] = None
    
    def __new__(cls) -> 'AnalyticsService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._redis_client = None
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'AnalyticsService':
        """Get singleton instance."""
        return cls()
    
    def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis_client is None:
            try:
                import redis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self._redis_client = redis.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis not available for analytics: {e}")
                self._redis_client = None
        return self._redis_client
    
    async def track(
        self,
        event_name: str,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        *,
        session_id: Optional[str] = None,
        store_id: Optional[str] = None,
        product_id: Optional[str] = None,
        device: Optional[str] = None,
        country: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """
        Track an analytics event.
        
        Non-blocking: queues via Celery if db not provided.
        Updates Redis counters for real-time dashboards.
        Optionally forwards to Mixpanel.
        
        Args:
            event_name: Event name (use StandardEvent enum for consistency)
            user_id: User UUID (nullable for anonymous events)
            properties: Event-specific properties dict
            session_id: Session identifier
            store_id: Store UUID if store-related
            product_id: Product UUID if product-related
            device: Device type (ios, android, web)
            country: Country code (EG, SA, etc.)
            db: Optional database session for immediate write
            
        Returns:
            True if event was tracked successfully
        """
        properties = properties or {}
        timestamp = datetime.now(timezone.utc)
        
        # Update Redis real-time counters
        self._update_realtime_counters(event_name, store_id, user_id)
        
        # Queue async write via Celery (non-blocking)
        if db is None:
            try:
                from workers.celery_app import celery_app
                celery_app.send_task(
                    "workers.analytics_tasks.persist_event",
                    kwargs={
                        "event_name": event_name,
                        "user_id": user_id,
                        "session_id": session_id,
                        "store_id": store_id,
                        "product_id": product_id,
                        "properties": properties,
                        "timestamp": timestamp.isoformat(),
                        "device": device,
                        "country": country,
                    },
                    queue="analytics",
                )
            except Exception as e:
                logger.warning(f"Failed to queue analytics event: {e}")
                return False
        else:
            # Immediate write (for tests or explicit sync)
            self._persist_immediate(
                db=db,
                event_name=event_name,
                user_id=user_id,
                session_id=session_id,
                store_id=store_id,
                product_id=product_id,
                properties=properties,
                timestamp=timestamp,
                device=device,
                country=country,
            )
        
        # Forward to Mixpanel if enabled
        if ANALYTICS_FORWARD_ENABLED and MIXPANEL_TOKEN:
            self._forward_to_mixpanel(
                event_name=event_name,
                user_id=user_id,
                properties=properties,
                timestamp=timestamp,
            )
        
        return True
    
    def _update_realtime_counters(
        self,
        event_name: str,
        store_id: Optional[str],
        user_id: Optional[str],
    ) -> None:
        """Update Redis counters for real-time dashboards."""
        redis_client = self._get_redis()
        if redis_client is None:
            return
        
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Global event counter
            redis_client.hincrby(f"analytics:events:{today}", event_name, 1)
            
            # Store-specific counters
            if store_id:
                redis_client.hincrby(f"analytics:store:{store_id}:{today}", event_name, 1)
                if event_name == StandardEvent.STORE_VISITED:
                    redis_client.incr(f"analytics:store:{store_id}:visits:today")
            
            # Daily active users
            if user_id:
                redis_client.sadd(f"analytics:dau:{today}", user_id)
            
            # Set TTL to end of day (86400s = 24h, we use 36h for safety)
            ttl = 129600  # 36 hours
            for key in [
                f"analytics:events:{today}",
                f"analytics:dau:{today}",
            ]:
                redis_client.expire(key, ttl, nx=True)
            
            if store_id:
                redis_client.expire(f"analytics:store:{store_id}:{today}", ttl, nx=True)
                redis_client.expire(f"analytics:store:{store_id}:visits:today", ttl, nx=True)
                
        except Exception as e:
            logger.warning(f"Failed to update Redis counters: {e}")
    
    def _persist_immediate(
        self,
        db: Session,
        event_name: str,
        user_id: Optional[str],
        session_id: Optional[str],
        store_id: Optional[str],
        product_id: Optional[str],
        properties: Dict[str, Any],
        timestamp: datetime,
        device: Optional[str],
        country: Optional[str],
    ) -> None:
        """Persist event immediately to database."""
        try:
            query = text("""
                INSERT INTO analytics_events (
                    id, event_name, user_id, session_id, store_id, product_id,
                    properties, timestamp, device, country
                ) VALUES (
                    :id, :event_name, :user_id, :session_id, :store_id, :product_id,
                    :properties, :timestamp, :device, :country
                )
            """)
            
            import uuid
            db.execute(query, {
                "id": str(uuid.uuid4()),
                "event_name": event_name,
                "user_id": user_id,
                "session_id": session_id,
                "store_id": store_id,
                "product_id": product_id,
                "properties": properties,
                "timestamp": timestamp,
                "device": device,
                "country": country,
            })
            # Note: Caller must commit
        except Exception as e:
            logger.warning(f"Failed to persist analytics event: {e}")
    
    def _forward_to_mixpanel(
        self,
        event_name: str,
        user_id: Optional[str],
        properties: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Forward event to Mixpanel (PII minimized - hashed user_id)."""
        try:
            # Hash user_id for PII minimization
            distinct_id = hashlib.sha256(user_id.encode()).hexdigest()[:64] if user_id else "anonymous"
            
            # Remove PII from properties
            safe_properties = {
                k: v for k, v in properties.items()
                if k not in ("email", "phone", "name", "address")
            }
            
            # Queue for async send via Celery
            from workers.celery_app import celery_app
            celery_app.send_task(
                "workers.analytics_tasks.send_to_mixpanel",
                kwargs={
                    "token": MIXPANEL_TOKEN,
                    "event_name": event_name,
                    "distinct_id": distinct_id,
                    "properties": safe_properties,
                    "timestamp": timestamp.isoformat(),
                },
                queue="analytics",
            )
        except Exception as e:
            logger.warning(f"Failed to queue Mixpanel forward: {e}")
    
    def get_realtime_counter(self, key: str) -> int:
        """Get a real-time counter value from Redis."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        try:
            value = redis_client.get(key)
            return int(value) if value else 0
        except Exception:
            return 0
    
    def get_realtime_hash(self, key: str) -> Dict[str, int]:
        """Get all values from a Redis hash."""
        redis_client = self._get_redis()
        if redis_client is None:
            return {}
        try:
            data = redis_client.hgetall(key)
            return {k.decode(): int(v) for k, v in data.items()}
        except Exception:
            return {}


# Singleton instance
analytics_service = AnalyticsService.get_instance()


# Convenience functions for common events
async def track_user_signup(user_id: str, **kwargs) -> bool:
    """Track user signup event."""
    return await analytics_service.track(
        StandardEvent.USER_SIGNUP,
        user_id=user_id,
        properties=kwargs,
    )


async def track_user_login(user_id: str, **kwargs) -> bool:
    """Track user login event."""
    return await analytics_service.track(
        StandardEvent.USER_LOGIN,
        user_id=user_id,
        properties=kwargs,
    )


async def track_product_viewed(
    user_id: str,
    product_id: str,
    sku: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track product viewed event."""
    properties = {"sku": sku, **kwargs} if sku else kwargs
    return await analytics_service.track(
        StandardEvent.PRODUCT_VIEWED,
        user_id=user_id,
        product_id=product_id,
        properties=properties,
    )


async def track_try_on_started(
    user_id: str,
    product_id: str,
    session_id: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track try-on started event."""
    return await analytics_service.track(
        StandardEvent.TRY_ON_STARTED,
        user_id=user_id,
        product_id=product_id,
        session_id=session_id,
        properties=kwargs,
    )


async def track_try_on_completed(
    user_id: str,
    product_id: str,
    session_id: Optional[str] = None,
    quality_score: Optional[float] = None,
    **kwargs,
) -> bool:
    """Track try-on completed event."""
    properties = kwargs
    if quality_score is not None:
        properties["quality_score"] = quality_score
    return await analytics_service.track(
        StandardEvent.TRY_ON_COMPLETED,
        user_id=user_id,
        product_id=product_id,
        session_id=session_id,
        properties=properties,
    )


async def track_outfit_saved(user_id: str, outfit_id: str, **kwargs) -> bool:
    """Track outfit saved event."""
    return await analytics_service.track(
        StandardEvent.OUTFIT_SAVED,
        user_id=user_id,
        properties={"outfit_id": outfit_id, **kwargs},
    )


async def track_order_placed(
    user_id: str,
    order_id: str,
    total_egp: float,
    store_id: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track order placed event."""
    return await analytics_service.track(
        StandardEvent.ORDER_PLACED,
        user_id=user_id,
        store_id=store_id,
        properties={"order_id": order_id, "total_egp": total_egp, **kwargs},
    )


async def track_midway_rejection(
    sku: str,
    stage: str,
    reason_code: str,
    brand_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track midway rejection event for quality control."""
    return await analytics_service.track(
        StandardEvent.MIDWAY_REJECTION,
        user_id=user_id,
        properties={
            "sku": sku,
            "stage": stage,
            "reason_code": reason_code,
            "brand_id": brand_id,
            **kwargs,
        },
    )


async def track_store_visited(
    user_id: str,
    store_id: str,
    visit_type: str = "app_ping",  # or "bopis_checkin"
    **kwargs,
) -> bool:
    """Track store visited event (BOPIS check-in or app location ping)."""
    return await analytics_service.track(
        StandardEvent.STORE_VISITED,
        user_id=user_id,
        store_id=store_id,
        properties={"visit_type": visit_type, **kwargs},
    )


async def track_coupon_applied(
    user_id: str,
    coupon_code: str,
    discount_egp: float,
    store_id: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track coupon applied event."""
    return await analytics_service.track(
        StandardEvent.COUPON_APPLIED,
        user_id=user_id,
        store_id=store_id,
        properties={"coupon_code": coupon_code, "discount_egp": discount_egp, **kwargs},
    )


async def track_donor_coupon_redeemed(
    user_id: str,
    donor_id: str,
    amount_egp: float,
    store_id: Optional[str] = None,
    **kwargs,
) -> bool:
    """Track donor coupon redeemed event."""
    return await analytics_service.track(
        StandardEvent.DONOR_COUPON_REDEEMED,
        user_id=user_id,
        store_id=store_id,
        properties={"donor_id": donor_id, "amount_egp": amount_egp, **kwargs},
    )
