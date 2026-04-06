"""
CONFIT Analytics Engine Tests
=============================
Unit and integration tests for the analytics engine.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import uuid

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.execute = Mock(return_value=Mock())
    db.scalar = Mock(return_value=0)
    db.query = Mock(return_value=Mock())
    db.commit = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    redis.hincrby = Mock(return_value=1)
    redis.hgetall = Mock(return_value={})
    redis.get = Mock(return_value=None)
    redis.set = Mock(return_value=True)
    redis.sadd = Mock(return_value=1)
    redis.scard = Mock(return_value=0)
    redis.expire = Mock(return_value=True)
    redis.incr = Mock(return_value=1)
    return redis


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_store_id():
    """Sample store UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_product_id():
    """Sample product UUID."""
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Analytics Service Tests
# -----------------------------------------------------------------------------

class TestAnalyticsService:
    """Tests for AnalyticsService."""
    
    @pytest.mark.asyncio
    async def test_track_event_basic(self, mock_db, sample_user_id):
        """Test basic event tracking."""
        from services.analytics_service import AnalyticsService, StandardEvent
        
        service = AnalyticsService()
        
        with patch.object(service, '_get_redis', return_value=None):
            with patch.object(service, '_persist_immediate') as mock_persist:
                result = await service.track(
                    event_name=StandardEvent.USER_LOGIN,
                    user_id=sample_user_id,
                    db=mock_db,
                )
        
        assert result is True
        mock_persist.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_event_with_properties(self, mock_db, sample_user_id, sample_store_id):
        """Test event tracking with custom properties."""
        from services.analytics_service import AnalyticsService, StandardEvent
        
        service = AnalyticsService()
        properties = {
            "sku": "SKU-12345",
            "category": "tops",
            "price_egp": 599.00,
        }
        
        with patch.object(service, '_get_redis', return_value=None):
            with patch.object(service, '_persist_immediate') as mock_persist:
                result = await service.track(
                    event_name=StandardEvent.PRODUCT_VIEWED,
                    user_id=sample_user_id,
                    store_id=sample_store_id,
                    properties=properties,
                    device="ios",
                    country="EG",
                    db=mock_db,
                )
        
        assert result is True
        call_kwargs = mock_persist.call_args[1]
        assert call_kwargs['event_name'] == "product_viewed"
        assert call_kwargs['properties']['sku'] == "SKU-12345"
    
    @pytest.mark.asyncio
    async def test_track_event_queues_celery_when_no_db(self, sample_user_id):
        """Test that event is queued via Celery when no db provided."""
        from services.analytics_service import AnalyticsService, StandardEvent
        
        service = AnalyticsService()
        
        with patch.object(service, '_get_redis', return_value=None):
            with patch('services.analytics_service.celery_app') as mock_celery:
                result = await service.track(
                    event_name=StandardEvent.USER_SIGNUP,
                    user_id=sample_user_id,
                )
        
        assert result is True
        mock_celery.send_task.assert_called_once()
    
    def test_update_realtime_counters(self, mock_redis, sample_store_id, sample_user_id):
        """Test Redis counter updates."""
        from services.analytics_service import AnalyticsService, StandardEvent
        
        service = AnalyticsService()
        
        with patch.object(service, '_get_redis', return_value=mock_redis):
            service._update_realtime_counters(
                event_name=StandardEvent.STORE_VISITED,
                store_id=sample_store_id,
                user_id=sample_user_id,
            )
        
        # Verify Redis calls
        mock_redis.hincrby.assert_called()
        mock_redis.sadd.assert_called()  # DAU tracking
    
    def test_get_realtime_counter(self, mock_redis):
        """Test getting realtime counter value."""
        from services.analytics_service import AnalyticsService
        
        mock_redis.get.return_value = b"42"
        service = AnalyticsService()
        
        with patch.object(service, '_get_redis', return_value=mock_redis):
            value = service.get_realtime_counter("test:key")
        
        assert value == 42
    
    def test_standard_event_enum_values(self):
        """Test StandardEvent enum has expected values."""
        from services.analytics_service import StandardEvent
        
        assert StandardEvent.USER_SIGNUP == "user_signup"
        assert StandardEvent.PRODUCT_VIEWED == "product_viewed"
        assert StandardEvent.TRY_ON_STARTED == "try_on_started"
        assert StandardEvent.ORDER_PLACED == "order_placed"
        assert StandardEvent.MIDWAY_REJECTION == "midway_rejection"


# -----------------------------------------------------------------------------
# Convenience Function Tests
# -----------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for convenience tracking functions."""
    
    @pytest.mark.asyncio
    async def test_track_product_viewed(self, sample_user_id, sample_product_id):
        """Test track_product_viewed convenience function."""
        from services.analytics_service import track_product_viewed
        
        with patch('services.analytics_service.analytics_service.track') as mock_track:
            mock_track.return_value = True
            result = await track_product_viewed(
                user_id=sample_user_id,
                product_id=sample_product_id,
                sku="SKU-123",
            )
        
        assert result is True
        mock_track.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_order_placed(self, sample_user_id, sample_store_id):
        """Test track_order_placed convenience function."""
        from services.analytics_service import track_order_placed
        
        with patch('services.analytics_service.analytics_service.track') as mock_track:
            mock_track.return_value = True
            result = await track_order_placed(
                user_id=sample_user_id,
                order_id="ORD-12345",
                total_egp=1250.00,
                store_id=sample_store_id,
            )
        
        assert result is True
        call_args = mock_track.call_args
        assert call_args[1]['event_name'] == "order_placed"
        assert call_args[1]['store_id'] == sample_store_id
    
    @pytest.mark.asyncio
    async def test_track_midway_rejection(self):
        """Test track_midway_rejection convenience function."""
        from services.analytics_service import track_midway_rejection
        
        with patch('services.analytics_service.analytics_service.track') as mock_track:
            mock_track.return_value = True
            result = await track_midway_rejection(
                sku="SKU-123",
                stage="stitch",
                reason_code="stitch_loose_seam",
                brand_id="brand-luxelayers",
            )
        
        assert result is True
        call_args = mock_track.call_args
        assert call_args[1]['properties']['sku'] == "SKU-123"
        assert call_args[1]['properties']['stage'] == "stitch"


# -----------------------------------------------------------------------------
# Realtime Counters Tests
# -----------------------------------------------------------------------------

class TestRealtimeCounters:
    """Tests for RealtimeCounters."""
    
    def test_incr_store_visits(self, mock_redis, sample_store_id):
        """Test incrementing store visits counter."""
        from services.analytics_realtime import RealtimeCounters
        
        mock_redis.hincrby.return_value = 5
        counters = RealtimeCounters()
        
        with patch.object(counters, '_get_redis', return_value=mock_redis):
            value = counters.incr_store_visits(sample_store_id)
        
        assert value == 5
        mock_redis.hincrby.assert_called()
        mock_redis.expire.assert_called()
    
    def test_get_store_counters(self, mock_redis, sample_store_id):
        """Test getting store counters aggregation."""
        from services.analytics_realtime import RealtimeCounters
        
        mock_redis.hgetall.return_value = {b"visits": b"10", b"product_viewed": b"25"}
        counters = RealtimeCounters()
        
        with patch.object(counters, '_get_redis', return_value=mock_redis):
            result = counters.get_store_counters(sample_store_id, days=1)
        
        assert result["visits_today"] == 10
        assert result["events"]["product_viewed"] == 25
    
    def test_track_dau(self, mock_redis, sample_user_id):
        """Test DAU tracking."""
        from services.analytics_realtime import RealtimeCounters
        
        counters = RealtimeCounters()
        
        with patch.object(counters, '_get_redis', return_value=mock_redis):
            result = counters.track_dau(sample_user_id)
        
        assert result is True
        mock_redis.sadd.assert_called()
    
    def test_get_dau(self, mock_redis):
        """Test getting DAU count."""
        from services.analytics_realtime import RealtimeCounters
        
        mock_redis.scard.return_value = 150
        counters = RealtimeCounters()
        
        with patch.object(counters, '_get_redis', return_value=mock_redis):
            dau = counters.get_dau()
        
        assert dau == 150
    
    def test_incr_heatmap(self, mock_redis, sample_store_id):
        """Test heatmap counter increment."""
        from services.analytics_realtime import RealtimeCounters
        
        counters = RealtimeCounters()
        
        with patch.object(counters, '_get_redis', return_value=mock_redis):
            value = counters.incr_heatmap(sample_store_id, hour=14, day_of_week=4)
        
        mock_redis.hincrby.assert_called()
        # Verify field format is "hour:day_of_week"
        call_args = mock_redis.hincrby.call_args
        assert "14:4" in str(call_args)


# -----------------------------------------------------------------------------
# Store Analytics API Tests
# -----------------------------------------------------------------------------

class TestStoreAnalyticsAPI:
    """Tests for Store Analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_store_dashboard(self, mock_db, sample_store_id):
        """Test store dashboard endpoint."""
        from routers.analytics_store import get_store_dashboard, StoreDashboardResponse
        from services.auth_service import UserProfile
        
        # Mock store
        mock_store = Mock()
        mock_store.id = sample_store_id
        mock_store.name = "Test Store"
        
        # Mock user
        mock_user = Mock(spec=UserProfile)
        mock_user.id = str(uuid.uuid4())
        
        # Setup mock queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_store
        mock_db.query.return_value.filter.return_value.scalar.return_value = 10
        mock_db.execute.return_value.all.return_value = []
        
        with patch('routers.analytics_store._check_store_access'):
            with patch('routers.analytics_store.realtime_counters.get_store_counters', return_value={}):
                response = await get_store_dashboard(
                    store_id=sample_store_id,
                    user=mock_user,
                    db=mock_db,
                )
        
        assert response.store_id == sample_store_id
        assert response.store_name == "Test Store"
    
    @pytest.mark.asyncio
    async def test_get_store_heatmap(self, mock_db, sample_store_id):
        """Test store heatmap endpoint."""
        from routers.analytics_store import get_store_heatmap
        from services.auth_service import UserProfile
        
        mock_store = Mock()
        mock_store.id = sample_store_id
        mock_store.name = "Test Store"
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = str(uuid.uuid4())
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_store
        
        with patch('routers.analytics_store._check_store_access'):
            with patch('routers.analytics_store.realtime_counters.get_heatmap', return_value={}):
                with patch('routers.analytics_store.text') as mock_text:
                    mock_db.execute.return_value.all.return_value = []
                    response = await get_store_heatmap(
                        store_id=sample_store_id,
                        user=mock_user,
                        db=mock_db,
                    )
        
        assert response.store_id == sample_store_id


# -----------------------------------------------------------------------------
# Brand Analytics API Tests
# -----------------------------------------------------------------------------

class TestBrandAnalyticsAPI:
    """Tests for Brand Analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_brand_dashboard(self, mock_db):
        """Test brand dashboard endpoint."""
        from routers.analytics_factory import get_brand_dashboard
        from services.auth_service import UserProfile
        
        brand_id = "brand-test"
        
        # Mock brand
        mock_brand = Mock()
        mock_brand.id = brand_id
        mock_brand.name = "Test Brand"
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = str(uuid.uuid4())
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_brand
        mock_db.query.return_value.filter.return_value.scalar.return_value = 100
        mock_db.execute.return_value.all.return_value = []
        
        with patch('routers.analytics_factory._check_brand_access'):
            response = await get_brand_dashboard(
                brand_id=brand_id,
                user=mock_user,
                db=mock_db,
            )
        
        assert response.brand_id == brand_id
        assert response.brand_name == "Test Brand"


# -----------------------------------------------------------------------------
# User Analytics API Tests
# -----------------------------------------------------------------------------

class TestUserAnalyticsAPI:
    """Tests for User Analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_user_summary(self, mock_db, sample_user_id):
        """Test user summary endpoint."""
        from routers.analytics_user import get_user_summary
        from services.auth_service import UserProfile
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = sample_user_id
        
        # Mock user record
        mock_user_record = Mock()
        mock_user_record.created_at = datetime.now(timezone.utc)
        
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_record
        
        response = await get_user_summary(
            user=mock_user,
            db=mock_db,
        )
        
        assert response.user_id == sample_user_id
    
    @pytest.mark.asyncio
    async def test_get_wardrobe_stats(self, mock_db, sample_user_id):
        """Test wardrobe stats endpoint."""
        from routers.analytics_user import get_wardrobe_stats
        from services.auth_service import UserProfile
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = sample_user_id
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        
        response = await get_wardrobe_stats(
            user=mock_user,
            db=mock_db,
        )
        
        assert response["user_id"] == sample_user_id
        assert "sustainability_impact" in response


# -----------------------------------------------------------------------------
# Admin Analytics API Tests
# -----------------------------------------------------------------------------

class TestAdminAnalyticsAPI:
    """Tests for Admin Analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_admin_overview_requires_admin(self, mock_db, sample_user_id):
        """Test admin overview requires admin role."""
        from routers.analytics_admin import get_admin_overview
        from services.auth_service import UserProfile
        from fastapi import HTTPException
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = sample_user_id
        
        # Mock non-admin user
        mock_user_role = Mock()
        mock_user_role.role = Mock()
        mock_user_role.role.value = "user"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_role
        
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_overview(user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_admin_overview_success(self, mock_db, sample_user_id):
        """Test admin overview with admin role."""
        from routers.analytics_admin import get_admin_overview
        from services.auth_service import UserProfile
        from database.models import AppRole
        
        mock_user = Mock(spec=UserProfile)
        mock_user.id = sample_user_id
        
        # Mock admin user
        mock_user_role = Mock()
        mock_user_role.role = AppRole.admin
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_role
        mock_db.query.return_value.filter.return_value.scalar.return_value = 100
        
        with patch('routers.analytics_admin.realtime_counters.get_dau', return_value=50):
            response = await get_admin_overview(user=mock_user, db=mock_db)
        
        assert response.dau == 50


# -----------------------------------------------------------------------------
# Celery Task Tests
# -----------------------------------------------------------------------------

class TestAnalyticsTasks:
    """Tests for Celery analytics tasks."""
    
    def test_persist_event_task(self, mock_db):
        """Test persist_event Celery task."""
        from workers.analytics_tasks import persist_event
        
        with patch('workers.analytics_tasks.SessionLocal', return_value=mock_db):
            result = persist_event(
                event_name="user_login",
                user_id=str(uuid.uuid4()),
                properties={"method": "google"},
            )
        
        assert result is True
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
    
    def test_aggregate_daily_summaries_task(self, mock_db):
        """Test aggregate_daily_summaries Celery task."""
        from workers.analytics_tasks import aggregate_daily_summaries
        
        # Mock store query
        mock_db.execute.return_value.all.return_value = []
        
        with patch('workers.analytics_tasks.SessionLocal', return_value=mock_db):
            result = aggregate_daily_summaries(target_date="2024-01-15")
        
        assert "store_summaries" in result
        assert "brand_summaries" in result
        assert "user_summaries" in result
    
    def test_archive_old_events_task(self, mock_db):
        """Test archive_old_events Celery task."""
        from workers.analytics_tasks import archive_old_events
        
        mock_db.execute.return_value.scalar.return_value = 1000
        
        with patch('workers.analytics_tasks.SessionLocal', return_value=mock_db):
            result = archive_old_events(days=180)
        
        assert result["archived_count"] == 1000


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestStoreDashboardIntegration:
    """Integration test for store dashboard flow."""
    
    @pytest.mark.asyncio
    async def test_full_store_dashboard_flow(self, mock_redis):
        """
        Full integration test for store dashboard:
        1. Track events (store visit, product view, try-on, order)
        2. Verify Redis counters updated
        3. Query dashboard data
        """
        from services.analytics_service import AnalyticsService, StandardEvent
        
        store_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        
        service = AnalyticsService()
        
        # Mock Redis for realtime counters
        with patch.object(service, '_get_redis', return_value=mock_redis):
            # 1. Track store visit
            await service.track(
                event_name=StandardEvent.STORE_VISITED,
                user_id=user_id,
                store_id=store_id,
                properties={"visit_type": "app_ping"},
            )
            
            # 2. Track product views
            await service.track(
                event_name=StandardEvent.PRODUCT_VIEWED,
                user_id=user_id,
                store_id=store_id,
                product_id=product_id,
                properties={"sku": "SKU-123", "category": "tops"},
            )
            
            # 3. Track try-on
            session_id = str(uuid.uuid4())
            await service.track(
                event_name=StandardEvent.TRY_ON_STARTED,
                user_id=user_id,
                store_id=store_id,
                product_id=product_id,
                session_id=session_id,
                properties={"garment_category": "tops"},
            )
            
            await service.track(
                event_name=StandardEvent.TRY_ON_COMPLETED,
                user_id=user_id,
                store_id=store_id,
                product_id=product_id,
                session_id=session_id,
                properties={"quality_score": 0.95},
            )
            
            # 4. Track order
            await service.track(
                event_name=StandardEvent.ORDER_PLACED,
                user_id=user_id,
                store_id=store_id,
                properties={
                    "order_id": "ORD-12345",
                    "total_egp": 1250.00,
                    "from_try_on": True,
                    "session_id": session_id,
                },
            )
        
        # Verify Redis counter calls
        assert mock_redis.hincrby.call_count >= 5  # Multiple event counters
        assert mock_redis.sadd.called  # DAU tracking
        
        # Verify store-specific counter keys were used
        hincrby_calls = mock_redis.hincrby.call_args_list
        store_keys = [call[0][0] for call in hincrby_calls if store_id in str(call[0][0])]
        assert len(store_keys) >= 3  # Multiple store events


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
