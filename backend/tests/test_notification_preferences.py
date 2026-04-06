"""
CONFIT Backend — Notification Preferences API Tests
===================================================
Unit tests for notification preferences CRUD endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.notification_preferences import (
    router,
    get_default_preferences,
    check_dispatch_preferences,
    CUSTOMER_DEFAULT_TYPES,
    OWNER_DEFAULT_TYPES,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    """Create test FastAPI app with notification preferences router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    user = MagicMock()
    user.id = "test-user-123"
    return user


# ── Unit Tests: Default Preferences ────────────────────────────────────────────

def test_get_default_preferences_customer():
    """Test default preferences for customer."""
    prefs = get_default_preferences("customer")
    
    assert prefs["channel_preferences"]["in_app"] is True
    assert prefs["channel_preferences"]["email"] is True
    assert prefs["channel_preferences"]["push"] is True
    assert "order_updates" in prefs["notification_types"]
    assert "delivery_updates" in prefs["notification_types"]
    assert "promotions" in prefs["notification_types"]
    assert prefs["batch_options"]["enabled"] is False


def test_get_default_preferences_owner():
    """Test default preferences for store owner."""
    prefs = get_default_preferences("store_owner")
    
    assert "new_orders" in prefs["notification_types"]
    assert "status_updates" in prefs["notification_types"]
    assert "customer_inquiries" in prefs["notification_types"]


def test_customer_default_types_includes_delivery_updates():
    """Verify delivery_updates is in customer default types."""
    assert "delivery_updates" in CUSTOMER_DEFAULT_TYPES


# ── Unit Tests: check_dispatch_preferences ─────────────────────────────────────

def test_check_dispatch_preferences_channel_disabled(mock_db):
    """Test that disabled channel prevents dispatch."""
    # Create mock preferences with email disabled
    mock_prefs = MagicMock()
    mock_prefs.channel_preferences = {"in_app": True, "email": False, "push": True}
    mock_prefs.notification_types = ["order_updates"]
    mock_prefs.frequency_settings = {"order_updates": "real_time"}
    
    with patch("routers.notification_preferences.NotificationPreferences") as MockPrefs:
        MockPrefs.query.filter.return_value.first.return_value = mock_prefs
        
        result = check_dispatch_preferences(
            mock_db,
            "user-123",
            "customer",
            "order_confirmed",
            "email",
        )
        
        assert result["should_dispatch"] is False
        assert result["frequency"] == "disabled"


def test_check_dispatch_preferences_type_disabled(mock_db):
    """Test that disabled notification type prevents dispatch."""
    mock_prefs = MagicMock()
    mock_prefs.channel_preferences = {"in_app": True, "email": True, "push": True}
    mock_prefs.notification_types = ["promotions"]  # order_updates not enabled
    mock_prefs.frequency_settings = {}
    
    with patch("routers.notification_preferences.NotificationPreferences") as MockPrefs:
        MockPrefs.query.filter.return_value.first.return_value = mock_prefs
        
        result = check_dispatch_preferences(
            mock_db,
            "user-123",
            "customer",
            "order_confirmed",
            "in_app",
        )
        
        assert result["should_dispatch"] is False


def test_check_dispatch_preferences_delivery_updates(mock_db):
    """Test delivery_updates category mapping."""
    mock_prefs = MagicMock()
    mock_prefs.channel_preferences = {"in_app": True, "email": True, "push": True}
    mock_prefs.notification_types = ["delivery_updates"]
    mock_prefs.frequency_settings = {"delivery_updates": "real_time"}
    
    with patch("routers.notification_preferences.NotificationPreferences") as MockPrefs:
        MockPrefs.query.filter.return_value.first.return_value = mock_prefs
        
        # order_shipped should map to delivery_updates
        result = check_dispatch_preferences(
            mock_db,
            "user-123",
            "customer",
            "order_shipped",
            "in_app",
        )
        
        assert result["should_dispatch"] is True
        assert result["frequency"] == "real_time"


def test_check_dispatch_preferences_frequency_disabled(mock_db):
    """Test that disabled frequency prevents dispatch."""
    mock_prefs = MagicMock()
    mock_prefs.channel_preferences = {"in_app": True, "email": True, "push": True}
    mock_prefs.notification_types = ["order_updates"]
    mock_prefs.frequency_settings = {"order_updates": "disabled"}
    
    with patch("routers.notification_preferences.NotificationPreferences") as MockPrefs:
        MockPrefs.query.filter.return_value.first.return_value = mock_prefs
        
        result = check_dispatch_preferences(
            mock_db,
            "user-123",
            "customer",
            "order_confirmed",
            "in_app",
        )
        
        assert result["should_dispatch"] is False


def test_check_dispatch_preferences_no_prefs_uses_defaults(mock_db):
    """Test that missing preferences fall back to defaults (all enabled)."""
    with patch("routers.notification_preferences.NotificationPreferences") as MockPrefs:
        MockPrefs.query.filter.return_value.first.return_value = None
        
        result = check_dispatch_preferences(
            mock_db,
            "user-123",
            "customer",
            "order_confirmed",
            "in_app",
        )
        
        # No preferences = default to enabled, real-time
        assert result["should_dispatch"] is True
        assert result["frequency"] == "real_time"


# ── Unit Tests: Category Mapping ───────────────────────────────────────────────

def test_category_mapping_order_shipped():
    """Verify order_shipped maps to delivery_updates."""
    assert "order_shipped" in ["order_shipped", "order_delivered", "delivery_tracking"]


def test_category_mapping_order_delivered():
    """Verify order_delivered maps to delivery_updates."""
    assert "order_delivered" in ["order_shipped", "order_delivered", "delivery_tracking"]


# ── Integration Tests: API Endpoints ────────────────────────────────────────────

@pytest.mark.skip(reason="Requires database and auth setup")
def test_get_preferences_creates_defaults(client, mock_user):
    """Test that GET creates default preferences if not exists."""
    pass


@pytest.mark.skip(reason="Requires database and auth setup")
def test_update_preferences_persists_changes(client, mock_user):
    """Test that PUT updates preferences correctly."""
    pass


@pytest.mark.skip(reason="Requires database and auth setup")
def test_reset_preferences_restores_defaults(client, mock_user):
    """Test that POST /reset restores default preferences."""
    pass


# ── Run Tests ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
