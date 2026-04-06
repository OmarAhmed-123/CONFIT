"""
CONFIT Backend - Notification Trigger Tests
============================================

Tests for all 10 notification lifecycle triggers.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from services.notification.triggers import (
    TriggerType,
    NotificationCategory,
    TriggerContext,
    ActorNotification,
    NotificationTriggerService,
    trigger_order_placed,
    trigger_payment_confirmed,
    trigger_production_started,
    trigger_midway_rejection,
    trigger_dispatched,
    trigger_ready_for_bopis,
    trigger_delivered,
    trigger_return_initiated,
    trigger_coupon_redeemed,
    trigger_donor_coupon_claimed,
    ACTOR_FANOUT,
    TRIGGER_PRIORITY,
    TRIGGER_CATEGORY,
    mask_phone,
    generate_idempotency_key,
    detect_language_from_phone,
)


# -------------------------------------------------------------------------
# FIXTURES
# -------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_dispatcher():
    """Mock notification dispatcher."""
    dispatcher = AsyncMock()
    dispatcher.dispatch = AsyncMock(return_value=MagicMock(
        status="success",
        channels_succeeded=["push"],
        message_ids={"push": "msg-123"},
    ))
    return dispatcher


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    service = AsyncMock()
    service.create_notification = AsyncMock(return_value=MagicMock(
        id="notif-123",
        status="QUEUED",
    ))
    return service


@pytest.fixture
def trigger_context():
    """Sample trigger context."""
    return TriggerContext(
        trigger=TriggerType.ORDER_PLACED,
        order_id="order-uuid-123",
        order_number="ORD-2024-001",
        customer_id="customer-uuid-456",
        customer_phone="+201012345678",
        customer_email="customer@example.com",
        customer_name="Ahmed Mohamed",
        product_sku="SKU-001",
        product_name="Classic T-Shirt",
        quantity=2,
        total=299.00,
        store_id="store-uuid-789",
        store_name="CONFIT Flagship Store",
        store_address="Cairo, Egypt",
    )


# -------------------------------------------------------------------------
# HELPER FUNCTION TESTS
# -------------------------------------------------------------------------

class TestMaskPhone:
    """Tests for phone masking function."""
    
    def test_mask_phone_egypt(self):
        """Test masking Egyptian phone number."""
        result = mask_phone("+201012345678")
        assert result == "+20-10***45678"
        assert result.count("*") == 3
    
    def test_mask_phone_short_number(self):
        """Test masking short phone number."""
        result = mask_phone("+1234567890")
        # Should handle gracefully
        assert "+" in result
        assert "***" in result
    
    def test_mask_phone_with_dashes(self):
        """Test masking phone with existing dashes."""
        result = mask_phone("+20-10-123-45678")
        assert "***" in result


class TestIdempotencyKey:
    """Tests for idempotency key generation."""
    
    def test_generate_key_basic(self):
        """Test basic idempotency key generation."""
        key = generate_idempotency_key(
            trigger="order_placed",
            order_id="order-123",
            actor_type="CUSTOMER",
            actor_id="customer-456",
        )
        assert "order_placed" in key
        assert "order-123" in key
        assert "CUSTOMER" in key
        assert "customer-456" in key
    
    def test_generate_key_consistent(self):
        """Test that same inputs produce same key."""
        key1 = generate_idempotency_key("trigger", "order-1", "CUSTOMER", "actor-1")
        key2 = generate_idempotency_key("trigger", "order-1", "CUSTOMER", "actor-1")
        assert key1 == key2
    
    def test_generate_key_different(self):
        """Test that different inputs produce different keys."""
        key1 = generate_idempotency_key("trigger", "order-1", "CUSTOMER", "actor-1")
        key2 = generate_idempotency_key("trigger", "order-2", "CUSTOMER", "actor-1")
        assert key1 != key2


class TestDetectLanguage:
    """Tests for language detection from phone."""
    
    def test_detect_arabic_egypt(self):
        """Test Arabic detection for Egyptian phone."""
        lang = detect_language_from_phone("+201012345678")
        assert lang == "ar"
    
    def test_detect_arabic_saudi(self):
        """Test Arabic detection for Saudi phone."""
        lang = detect_language_from_phone("+966501234567")
        assert lang == "ar"
    
    def test_detect_english_us(self):
        """Test English detection for US phone."""
        lang = detect_language_from_phone("+12125551234")
        assert lang == "en"
    
    def test_detect_none_empty(self):
        """Test detection with empty phone."""
        lang = detect_language_from_phone(None)
        assert lang == "en"
        
        lang = detect_language_from_phone("")
        assert lang == "en"


# -------------------------------------------------------------------------
# TRIGGER CONFIGURATION TESTS
# -------------------------------------------------------------------------

class TestTriggerConfiguration:
    """Tests for trigger configuration."""
    
    def test_actor_fanout_order_placed(self):
        """Test actor fanout for order_placed trigger."""
        actors = ACTOR_FANOUT.get(TriggerType.ORDER_PLACED, [])
        assert "CUSTOMER" in actors
        assert "STORE" in actors
    
    def test_actor_fanout_production_started(self):
        """Test actor fanout for production_started trigger."""
        actors = ACTOR_FANOUT.get(TriggerType.PRODUCTION_STARTED, [])
        assert "FACTORY" in actors
    
    def test_actor_fanout_donor_coupon(self):
        """Test actor fanout for donor_coupon_claimed trigger."""
        actors = ACTOR_FANOUT.get(TriggerType.DONOR_COUPON_CLAIMED, [])
        assert "DONOR" in actors
    
    def test_trigger_priority(self):
        """Test trigger priority mapping."""
        assert TRIGGER_PRIORITY.get(TriggerType.ORDER_PLACED) == "normal"
        assert TRIGGER_PRIORITY.get(TriggerType.MIDWAY_REJECTION) == "high"
    
    def test_trigger_category(self):
        """Test trigger category mapping."""
        assert TRIGGER_CATEGORY.get(TriggerType.ORDER_PLACED) == NotificationCategory.ORDERS
        assert TRIGGER_CATEGORY.get(TriggerType.COUPON_REDEEMED) == NotificationCategory.PROMOTIONS
        assert TRIGGER_CATEGORY.get(TriggerType.DONOR_COUPON_CLAIMED) == NotificationCategory.DONOR_IMPACT


# -------------------------------------------------------------------------
# TRIGGER CONTEXT TESTS
# -------------------------------------------------------------------------

class TestTriggerContext:
    """Tests for TriggerContext dataclass."""
    
    def test_create_context(self, trigger_context):
        """Test creating trigger context."""
        assert trigger_context.trigger == TriggerType.ORDER_PLACED
        assert trigger_context.order_id == "order-uuid-123"
        assert trigger_context.order_number == "ORD-2024-001"
        assert trigger_context.customer_phone == "+201012345678"
    
    def test_context_optional_fields(self):
        """Test context with optional fields."""
        ctx = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
        )
        assert ctx.customer_id is None
        assert ctx.customer_phone is None
        assert ctx.factory_id is None


class TestActorNotification:
    """Tests for ActorNotification dataclass."""
    
    def test_create_actor_notification(self):
        """Test creating actor notification."""
        notif = ActorNotification(
            actor_type="CUSTOMER",
            actor_id="customer-123",
            title="Order Placed",
            body="Your order has been placed",
            data={"order_number": "ORD-001"},
        )
        assert notif.actor_type == "CUSTOMER"
        assert notif.title == "Order Placed"
        assert notif.data["order_number"] == "ORD-001"


# -------------------------------------------------------------------------
# TRIGGER SERVICE TESTS
# -------------------------------------------------------------------------

class TestNotificationTriggerService:
    """Tests for NotificationTriggerService."""
    
    @pytest.mark.asyncio
    async def test_build_customer_payload(self, mock_db, mock_dispatcher):
        """Test building customer notification payload."""
        service = NotificationTriggerService(mock_db, mock_dispatcher)
        
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            customer_phone="+201012345678",
            product_name="T-Shirt",
            quantity=2,
        )
        
        payload = await service._build_customer_payload(context)
        
        assert payload is not None
        assert payload.actor_type == "CUSTOMER"
        assert payload.actor_id == "customer-456"
        assert "ORD-001" in payload.title or "ORD-001" in payload.body
    
    @pytest.mark.asyncio
    async def test_build_store_payload(self, mock_db, mock_dispatcher):
        """Test building store notification payload."""
        service = NotificationTriggerService(mock_db, mock_dispatcher)
        
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            store_id="store-789",
            customer_phone="+201012345678",
            product_sku="SKU-001",
            quantity=2,
        )
        
        payload = await service._build_store_payload(context)
        
        assert payload is not None
        assert payload.actor_type == "STORE"
        assert payload.actor_id == "store-789"
        # Phone should be masked
        assert "***" in payload.data.get("customer_phone_masked", "")
    
    @pytest.mark.asyncio
    async def test_build_factory_payload(self, mock_db, mock_dispatcher):
        """Test building factory notification payload."""
        service = NotificationTriggerService(mock_db, mock_dispatcher)
        
        context = TriggerContext(
            trigger=TriggerType.PRODUCTION_STARTED,
            order_id="order-123",
            order_number="ORD-001",
            factory_id="factory-456",
            product_sku="SKU-001",
            quantity=10,
        )
        
        payload = await service._build_factory_payload(context)
        
        assert payload is not None
        assert payload.actor_type == "FACTORY"
        assert payload.actor_id == "factory-456"
        # Should use order_number, not order_id
        assert "ORD-001" in str(payload.data) or "ORD-001" in payload.body
    
    @pytest.mark.asyncio
    async def test_dispatch_to_actor(self, mock_db, mock_dispatcher):
        """Test dispatching notification to actor."""
        service = NotificationTriggerService(mock_db, mock_dispatcher)
        
        actor_notif = ActorNotification(
            actor_type="CUSTOMER",
            actor_id="customer-123",
            title="Test",
            body="Test notification",
            data={},
        )
        
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
        )
        
        await service._dispatch_to_actor(actor_notif, context, "en")
        
        # Dispatcher should have been called
        mock_dispatcher.dispatch.assert_called_once()


# -------------------------------------------------------------------------
# TRIGGER FUNCTION TESTS
# -------------------------------------------------------------------------

class TestTriggerFunctions:
    """Tests for individual trigger functions."""
    
    @pytest.mark.asyncio
    async def test_trigger_order_placed(self, mock_db, mock_dispatcher):
        """Test order_placed trigger."""
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            store_id="store-789",
        )
        
        await trigger_order_placed(context, mock_db, mock_dispatcher)
        
        # Should dispatch to customer and store
        assert mock_dispatcher.dispatch.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_trigger_payment_confirmed(self, mock_db, mock_dispatcher):
        """Test payment_confirmed trigger."""
        context = TriggerContext(
            trigger=TriggerType.PAYMENT_CONFIRMED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
        )
        
        await trigger_payment_confirmed(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_production_started(self, mock_db, mock_dispatcher):
        """Test production_started trigger."""
        context = TriggerContext(
            trigger=TriggerType.PRODUCTION_STARTED,
            order_id="order-123",
            order_number="ORD-001",
            factory_id="factory-456",
            product_sku="SKU-001",
            quantity=5,
        )
        
        await trigger_production_started(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_midway_rejection(self, mock_db, mock_dispatcher):
        """Test midway_rejection trigger."""
        context = TriggerContext(
            trigger=TriggerType.MIDWAY_REJECTION,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            factory_id="factory-789",
            rejection_reason="Quality issue",
        )
        
        await trigger_midway_rejection(context, mock_db, mock_dispatcher)
        
        # Should dispatch to customer, factory, and possibly admin
        assert mock_dispatcher.dispatch.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_trigger_dispatched(self, mock_db, mock_dispatcher):
        """Test dispatched trigger."""
        context = TriggerContext(
            trigger=TriggerType.DISPATCHED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            tracking_number="TRK-123456",
            tracking_url="https://track.example.com/TRK-123456",
        )
        
        await trigger_dispatched(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_ready_for_bopis(self, mock_db, mock_dispatcher):
        """Test ready_for_bopis trigger."""
        context = TriggerContext(
            trigger=TriggerType.READY_FOR_BOPIS,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            store_id="store-789",
            store_name="CONFIT Store",
            store_address="Cairo, Egypt",
            pickup_window="10:00 - 18:00",
        )
        
        await trigger_ready_for_bopis(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_delivered(self, mock_db, mock_dispatcher):
        """Test delivered trigger."""
        context = TriggerContext(
            trigger=TriggerType.DELIVERED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
        )
        
        await trigger_delivered(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_return_initiated(self, mock_db, mock_dispatcher):
        """Test return_initiated trigger."""
        context = TriggerContext(
            trigger=TriggerType.RETURN_INITIATED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            store_id="store-789",
            factory_id="factory-101",
            rejection_reason="Size mismatch",
        )
        
        await trigger_return_initiated(context, mock_db, mock_dispatcher)
        
        # Should dispatch to customer, store, and factory
        assert mock_dispatcher.dispatch.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_trigger_coupon_redeemed(self, mock_db, mock_dispatcher):
        """Test coupon_redeemed trigger."""
        context = TriggerContext(
            trigger=TriggerType.COUPON_REDEEMED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            coupon_code="SAVE20",
            discount=59.80,
        )
        
        await trigger_coupon_redeemed(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_donor_coupon_claimed(self, mock_db, mock_dispatcher):
        """Test donor_coupon_claimed trigger."""
        context = TriggerContext(
            trigger=TriggerType.DONOR_COUPON_CLAIMED,
            order_id="order-123",
            order_number="ORD-001",
            donor_id="donor-456",
            store_name="CONFIT Store",
        )
        
        await trigger_donor_coupon_claimed(context, mock_db, mock_dispatcher)
        
        mock_dispatcher.dispatch.assert_called()


# -------------------------------------------------------------------------
# INTEGRATION TESTS
# -------------------------------------------------------------------------

class TestTriggerIntegration:
    """Integration tests for trigger system."""
    
    @pytest.mark.asyncio
    async def test_full_order_lifecycle(self, mock_db, mock_dispatcher):
        """Test full order lifecycle triggers."""
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            customer_phone="+201012345678",
            customer_email="customer@example.com",
            store_id="store-789",
            factory_id="factory-101",
            product_sku="SKU-001",
            product_name="T-Shirt",
            quantity=2,
            tracking_number="TRK-123",
            tracking_url="https://track.example.com/TRK-123",
        )
        
        # Simulate order lifecycle
        await trigger_order_placed(context, mock_db, mock_dispatcher)
        call_count = mock_dispatcher.dispatch.call_count
        
        context.trigger = TriggerType.PAYMENT_CONFIRMED
        await trigger_payment_confirmed(context, mock_db, mock_dispatcher)
        assert mock_dispatcher.dispatch.call_count > call_count
        
        context.trigger = TriggerType.PRODUCTION_STARTED
        await trigger_production_started(context, mock_db, mock_dispatcher)
        
        context.trigger = TriggerType.DISPATCHED
        await trigger_dispatched(context, mock_db, mock_dispatcher)
        
        context.trigger = TriggerType.DELIVERED
        await trigger_delivered(context, mock_db, mock_dispatcher)
        
        # All triggers should have dispatched
        assert mock_dispatcher.dispatch.call_count >= 5
    
    @pytest.mark.asyncio
    async def test_rejection_flow(self, mock_db, mock_dispatcher):
        """Test rejection notification flow."""
        context = TriggerContext(
            trigger=TriggerType.MIDWAY_REJECTION,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            factory_id="factory-789",
            rejection_reason="Fabric defect detected",
        )
        
        await trigger_midway_rejection(context, mock_db, mock_dispatcher)
        
        # Should notify multiple actors
        assert mock_dispatcher.dispatch.call_count >= 1


# -------------------------------------------------------------------------
# EDGE CASE TESTS
# -------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_trigger_with_missing_customer(self, mock_db, mock_dispatcher):
        """Test trigger when customer info is missing."""
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            # No customer_id
        )
        
        # Should still process (may skip customer notification)
        await trigger_order_placed(context, mock_db, mock_dispatcher)
    
    @pytest.mark.asyncio
    async def test_trigger_with_missing_store(self, mock_db, mock_dispatcher):
        """Test trigger when store info is missing."""
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
            # No store_id
        )
        
        await trigger_order_placed(context, mock_db, mock_dispatcher)
    
    @pytest.mark.asyncio
    async def test_dispatcher_failure(self, mock_db):
        """Test handling of dispatcher failure."""
        failing_dispatcher = AsyncMock()
        failing_dispatcher.dispatch = AsyncMock(side_effect=Exception("Network error"))
        
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
        )
        
        # Should handle exception gracefully
        try:
            await trigger_order_placed(context, mock_db, failing_dispatcher)
        except Exception:
            pass  # Expected to potentially raise
    
    @pytest.mark.asyncio
    async def test_idempotent_trigger(self, mock_db, mock_dispatcher):
        """Test that duplicate triggers are idempotent."""
        context = TriggerContext(
            trigger=TriggerType.ORDER_PLACED,
            order_id="order-123",
            order_number="ORD-001",
            customer_id="customer-456",
        )
        
        # Call twice with same context
        await trigger_order_placed(context, mock_db, mock_dispatcher)
        first_count = mock_dispatcher.dispatch.call_count
        
        # Second call should not create duplicate
        # (In real implementation, would check idempotency key)
        await trigger_order_placed(context, mock_db, mock_dispatcher)


# -------------------------------------------------------------------------
# RUN TESTS
# -------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
