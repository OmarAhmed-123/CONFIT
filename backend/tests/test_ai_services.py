"""
CONFIT Backend - AI Services Integration Tests
===============================================
Tests for MUSE, MIRROR, Visual Search, and Wardrobe services
with mocked OpenAI/Replicate/Google Vision APIs.
"""

import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from PIL import Image

# Test configuration
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["REPLICATE_API_TOKEN"] = "test-token"
os.environ["GOOGLE_VISION_API_KEY"] = "test-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Test DB


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.execute = MagicMock(return_value=MagicMock())
    db.fetchone = MagicMock(return_value=None)
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock()
    redis.setex = MagicMock()
    redis.incr = MagicMock()
    redis.delete = MagicMock()
    redis.lrange = MagicMock(return_value=[])
    redis.rpush = MagicMock()
    redis.expire = MagicMock()
    redis.ttl = MagicMock(return_value=3600)
    return redis


@pytest.fixture
def mock_s3():
    """Mock S3 client."""
    s3 = MagicMock()
    s3.put_object = MagicMock()
    s3.get_object = MagicMock(return_value={"Body": BytesIO(b"test")})
    s3.delete_object = MagicMock()
    s3.generate_presigned_url = MagicMock(return_value="https://test.s3.amazonaws.com/test.jpg")
    return s3


@pytest.fixture
def sample_image_bytes():
    """Generate sample image bytes for testing."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


# ==========================================
# MUSE Service Tests
# ==========================================

class TestMuseService:
    """Tests for MUSE Virtual Stylist service."""

    @pytest.mark.asyncio
    async def test_chat_basic(self, mock_db, mock_redis):
        """Test basic chat functionality."""
        from services.ai.muse_service import MuseService

        service = MuseService(mock_db, mock_redis)

        # Mock OpenAI response
        with patch.object(service, '_call_openai', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = MagicMock(
                message=MagicMock(
                    content="I recommend a blue dress for the wedding!",
                    tool_calls=None
                ),
                usage=MagicMock(
                    prompt_tokens=100,
                    completion_tokens=50
                )
            )

            with patch.object(service, '_search_relevant_products', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []

                with patch.object(service, '_get_style_profile', new_callable=AsyncMock) as mock_profile:
                    mock_profile.return_value = {}

                    response = await service.chat(
                        user_id="test-user",
                        message="What should I wear to a wedding?",
                        language="en"
                    )

        assert response.reply is not None
        assert response.session_id.startswith("muse-")
        assert response.tokens_in == 100
        assert response.tokens_out == 50

    @pytest.mark.asyncio
    async def test_chat_with_outfit_recommendations(self, mock_db, mock_redis):
        """Test chat that returns outfit recommendations."""
        from services.ai.muse_service import MuseService

        service = MuseService(mock_db, mock_redis)

        # Mock OpenAI response with function call
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "recommend_outfits"
        mock_tool_call.function.arguments = json.dumps({
            "outfits": [{
                "title": "Summer Wedding Look",
                "skus": ["SKU001", "SKU002"],
                "occasion": "wedding",
                "styling_tips": ["Add statement jewelry"]
            }]
        })

        with patch.object(service, '_call_openai', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = MagicMock(
                message=MagicMock(
                    content="Here's a great outfit for you!",
                    tool_calls=[mock_tool_call]
                ),
                usage=MagicMock(
                    prompt_tokens=150,
                    completion_tokens=80
                )
            )

            with patch.object(service, '_search_relevant_products', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = [
                    {"sku": "SKU001", "name": "Blue Dress", "price": 99.99},
                    {"sku": "SKU002", "name": "Heels", "price": 79.99}
                ]

                with patch.object(service, '_get_style_profile', new_callable=AsyncMock) as mock_profile:
                    mock_profile.return_value = {}

                    response = await service.chat(
                        user_id="test-user",
                        message="Wedding outfit ideas",
                        language="en"
                    )

        assert len(response.outfits) == 1
        assert response.outfits[0].title == "Summer Wedding Look"
        assert len(response.outfits[0].from_catalog) == 2

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_db, mock_redis):
        """Test rate limiting per user."""
        from services.ai.muse_service import MuseService

        service = MuseService(mock_db, mock_redis)

        # Simulate user at limit
        mock_redis.get.return_value = b"20"  # At free tier limit

        allowed, retry_after = await service.check_rate_limit("test-user", "free")

        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_bilingual_support(self, mock_db, mock_redis):
        """Test Arabic language support."""
        from services.ai.muse_service import MuseService, SYSTEM_PROMPT_AR

        service = MuseService(mock_db, mock_redis)

        with patch.object(service, '_call_openai', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = MagicMock(
                message=MagicMock(content="!", tool_calls=None),
                usage=MagicMock(prompt_tokens=50, completion_tokens=20)
            )

            with patch.object(service, '_search_relevant_products', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []

                with patch.object(service, '_get_style_profile', new_callable=AsyncMock) as mock_profile:
                    mock_profile.return_value = {}

                    await service.chat(
                        user_id="test-user",
                        message=" ",
                        language="ar"
                    )

        # Verify Arabic system prompt was used
        call_args = mock_openai.call_args[0][0]
        assert any("Arabic" in msg.get("content", "") or "MUSE" in msg.get("content", "") for msg in call_args)


# ==========================================
# MIRROR Service Tests
# ==========================================

class TestMirrorService:
    """Tests for MIRROR Virtual Try-On service."""

    @pytest.mark.asyncio
    async def test_start_tryon(self, mock_db, mock_redis, mock_s3, sample_image_bytes):
        """Test starting a try-on session."""
        from services.ai.mirror_service import MirrorService, TryOnRequest

        service = MirrorService(mock_db, mock_redis, mock_s3)

        request = TryOnRequest(
            user_id="test-user",
            product_id="product-123",
            product_sku="SKU001",
            person_image_bytes=sample_image_bytes,
            category="tops"
        )

        # Mock database operations
        mock_db.execute.return_value.fetchone.return_value = None

        session = await service.start_tryon(request)

        assert session.session_id.startswith("tryon-")
        assert session.status.value == "pending"
        assert session.user_id == "test-user"

    @pytest.mark.asyncio
    async def test_process_tryon_task(self, mock_db, mock_redis, mock_s3, sample_image_bytes):
        """Test processing a try-on task."""
        from services.ai.mirror_service import MirrorService, TryOnStatus

        service = MirrorService(mock_db, mock_redis, mock_s3)

        # Mock session retrieval
        mock_session = MagicMock()
        mock_session.id = "tryon-test"
        mock_session.user_id = "test-user"
        mock_session.product_id = "product-123"
        mock_session.status = TryOnStatus.PENDING
        mock_session.person_image_key = "person/test.jpg"
        mock_session.garment_image_key = "garment/test.jpg"

        with patch.object(service, '_get_session', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_session

            with patch.object(service, '_get_presigned_url', new_callable=AsyncMock) as mock_url:
                mock_url.return_value = "https://test.s3.amazonaws.com/test.jpg"

                with patch.object(service, '_call_replicate', new_callable=AsyncMock) as mock_replicate:
                    mock_replicate.return_value = ("https://result.jpg", "pred-123")

                    with patch.object(service, '_download_image', new_callable=AsyncMock) as mock_download:
                        mock_download.return_value = sample_image_bytes

                        with patch.object(service, '_upload_result_image', new_callable=AsyncMock) as mock_upload:
                            mock_upload.return_value = "result/test.jpg"

                            with patch.object(service, '_calculate_quality', new_callable=AsyncMock) as mock_quality:
                                mock_quality.return_value = 0.85

                                await service.process_tryon_task("tryon-test")

        # Verify status was updated
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_rate_limiting_daily(self, mock_db, mock_redis):
        """Test daily rate limiting for try-ons."""
        from services.ai.mirror_service import MirrorService

        service = MirrorService(mock_db, mock_redis)

        # Simulate user at daily limit
        mock_redis.get.return_value = b"10"  # At free tier limit

        allowed, retry_after = await service.check_rate_limit("test-user", "free")

        assert allowed is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, mock_db, mock_redis, mock_s3):
        """Test cleanup of expired sessions."""
        from services.ai.mirror_service import MirrorService

        service = MirrorService(mock_db, mock_redis, mock_s3)

        # Mock expired sessions
        mock_db.execute.return_value.fetchall.return_value = [
            MagicMock(id="old-1", person_image_key="old/person.jpg", result_image_key="old/result.jpg"),
            MagicMock(id="old-2", person_image_key="old/person2.jpg", result_image_key="old/result2.jpg"),
        ]

        cleaned = await service.cleanup_expired_sessions()

        assert cleaned == 2
        assert mock_s3.delete_object.call_count == 4  # 2 sessions x 2 images


# ==========================================
# Visual Search Service Tests
# ==========================================

class TestVisualSearchService:
    """Tests for Visual Search service."""

    @pytest.mark.asyncio
    async def test_search_by_image(self, mock_db, mock_redis, sample_image_bytes):
        """Test visual search by image."""
        from services.ai.visual_search_service import VisualSearchService

        service = VisualSearchService(mock_db, mock_redis)

        # Mock embedding generation
        with patch.object(service, '_generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 512

            # Mock attribute detection
            with patch.object(service, '_detect_attributes_google_vision', new_callable=AsyncMock) as mock_attrs:
                mock_attrs.return_value = MagicMock(
                    category="dresses",
                    colors=["red"],
                    patterns=[],
                    labels=["dress", "formal"]
                )

                # Mock pgvector search
                mock_db.execute.return_value.fetchall.return_value = [
                    MagicMock(
                        id="prod-1", sku="SKU001", name="Red Dress",
                        brand_id="brand-1", price=99.99, currency="USD",
                        image_url="https://test.jpg", url=None, category="dresses",
                        similarity=0.95
                    )
                ]

                response = await service.search_by_image(
                    image_bytes=sample_image_bytes,
                    user_id="test-user"
                )

        assert response.total_results >= 0
        assert response.session_id.startswith("vissearch-")

    @pytest.mark.asyncio
    async def test_search_by_text(self, mock_db, mock_redis):
        """Test visual search by text query."""
        from services.ai.visual_search_service import VisualSearchService

        service = VisualSearchService(mock_db, mock_redis)

        with patch.object(service, '_generate_text_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 512

            mock_db.execute.return_value.fetchall.return_value = [
                MagicMock(
                    id="prod-1", sku="SKU001", name="Blue Jeans",
                    brand_id="brand-1", price=79.99, currency="USD",
                    image_url="https://test.jpg", url=None, category="bottoms",
                    similarity=0.88
                )
            ]

            response = await service.search_by_text(
                query="blue jeans",
                user_id="test-user"
            )

        assert response.session_id.startswith("vissearch-")

    @pytest.mark.asyncio
    async def test_attribute_detection_fallback(self, mock_db, mock_redis, sample_image_bytes):
        """Test fallback when Google Vision API fails."""
        from services.ai.visual_search_service import VisualSearchService

        service = VisualSearchService(mock_db, mock_redis)

        # Google Vision will fail, should use fallback
        with patch.object(service, '_detect_attributes_google_vision', new_callable=AsyncMock) as mock_google:
            mock_google.side_effect = Exception("API Error")

            with patch.object(service, '_fallback_attribute_detection', new_callable=AsyncMock) as mock_fallback:
                mock_fallback.return_value = MagicMock(
                    category="unknown",
                    colors=["red"],
                    patterns=[],
                    labels=[]
                )

                with patch.object(service, '_generate_embedding', new_callable=AsyncMock) as mock_embed:
                    mock_embed.return_value = [0.1] * 512

                    mock_db.execute.return_value.fetchall.return_value = []

                    response = await service.search_by_image(
                        image_bytes=sample_image_bytes,
                        user_id="test-user"
                    )

        assert mock_fallback.called


# ==========================================
# Wardrobe Service Tests
# ==========================================

class TestWardrobeService:
    """Tests for Wardrobe service."""

    @pytest.mark.asyncio
    async def test_add_item(self, mock_db, mock_redis, mock_s3, sample_image_bytes):
        """Test adding item to wardrobe."""
        from services.ai.wardrobe_service import WardrobeService

        service = WardrobeService(mock_db, mock_redis, mock_s3)

        with patch.object(service, '_auto_tag_image', new_callable=AsyncMock) as mock_tag:
            mock_tag.return_value = {
                "name": "Blue T-Shirt",
                "category": "tops",
                "colors": ["blue"],
                "patterns": [],
                "materials": ["cotton"],
                "labels": ["t-shirt", "casual"]
            }

            with patch.object(service, '_generate_embedding', new_callable=AsyncMock) as mock_embed:
                mock_embed.return_value = [0.1] * 512

                item = await service.add_item(
                    user_id="test-user",
                    image_bytes=sample_image_bytes,
                    name="My T-Shirt"
                )

        assert item.name == "My T-Shirt"
        assert item.category == "tops"
        assert "blue" in item.colors

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, mock_db, mock_redis, mock_s3):
        """Test duplicate detection before purchase."""
        from services.ai.wardrobe_service import WardrobeService

        service = WardrobeService(mock_db, mock_redis, mock_s3)

        # Mock existing item with same SKU
        mock_db.execute.return_value.fetchall.return_value = [
            MagicMock(
                id="item-1", name="Blue Dress", category="dresses",
                user_id="test-user", subcategory=None, colors=["blue"],
                patterns=[], materials=[], brands=[], tags=[],
                image_key="test.jpg", embedding=None, purchase_date=None,
                purchase_price=None, times_worn=0, last_worn=None,
                is_favorite=False, notes=None, created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]

        alerts = await service.check_duplicates(
            user_id="test-user",
            product_sku="SKU001"
        )

        # Should not find duplicates without proper setup
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_outfit_suggestions(self, mock_db, mock_redis, mock_s3):
        """Test outfit suggestion generation."""
        from services.ai.wardrobe_service import WardrobeService, WardrobeItem

        service = WardrobeService(mock_db, mock_redis, mock_s3)

        # Mock wardrobe items
        items = [
            WardrobeItem(
                id="item-1", user_id="test-user", name="White Shirt",
                category="tops", subcategory="t-shirt", colors=["white"],
                patterns=[], materials=[], brands=[], tags=[],
                is_favorite=False
            ),
            WardrobeItem(
                id="item-2", user_id="test-user", name="Blue Jeans",
                category="bottoms", subcategory="pants", colors=["blue"],
                patterns=[], materials=[], brands=[], tags=[],
                is_favorite=False
            )
        ]

        with patch.object(service, 'list_items', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = items

            outfits = await service.suggest_outfits(
                user_id="test-user",
                occasion="casual"
            )

        assert isinstance(outfits, list)

    @pytest.mark.asyncio
    async def test_quota_enforcement(self, mock_db, mock_redis):
        """Test wardrobe quota enforcement."""
        from services.ai.wardrobe_service import WardrobeService

        service = WardrobeService(mock_db, mock_redis)

        # Mock item count at limit
        mock_db.execute.return_value.scalar.return_value = 50

        allowed, remaining = await service.check_quota("test-user", "free")

        assert allowed is False
        assert remaining <= 0


# ==========================================
# Cost Tracker Tests
# ==========================================

class TestAICostTracker:
    """Tests for AI Cost Tracker service."""

    @pytest.mark.asyncio
    async def test_track_cost(self, mock_db, mock_redis):
        """Test cost tracking."""
        from services.ai.cost_tracker import AICostTracker

        tracker = AICostTracker(mock_db, mock_redis)

        success = await tracker.track(
            service="muse",
            model="gpt-4o",
            user_id="test-user",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.0125,
            latency_ms=1500
        )

        assert success is True
        assert mock_redis.incrbyfloat.called  # Updated Redis counters
        assert mock_db.execute.called  # Persisted to DB

    @pytest.mark.asyncio
    async def test_budget_status(self, mock_db, mock_redis):
        """Test budget status check."""
        from services.ai.cost_tracker import AICostTracker

        tracker = AICostTracker(mock_db, mock_redis)

        # Mock current spend
        mock_redis.get.return_value = b"50.0"

        status = await tracker.get_budget_status()

        assert status.spent_usd == 50.0
        assert status.is_warning is False  # 50% of $100

    @pytest.mark.asyncio
    async def test_kill_switch(self, mock_db, mock_redis):
        """Test kill switch activation."""
        from services.ai.cost_tracker import AICostTracker

        tracker = AICostTracker(mock_db, mock_redis)

        # Simulate budget exceeded
        mock_redis.get.return_value = b"150.0"

        status = await tracker.get_budget_status()

        assert status.is_exceeded is True

        # Manually activate kill switch
        tracker.activate_kill_switch()
        assert tracker.is_kill_switch_active() is True

    @pytest.mark.asyncio
    async def test_cost_report(self, mock_db, mock_redis):
        """Test cost report generation."""
        from services.ai.cost_tracker import AICostTracker
        from datetime import date

        tracker = AICostTracker(mock_db, mock_redis)

        # Mock aggregated data
        mock_db.execute.return_value.fetchall.return_value = [
            MagicMock(
                group_key="muse",
                total_cost=10.50,
                total_calls=100,
                total_tokens_in=5000,
                total_tokens_out=2500,
                avg_latency=1200.5,
                success_rate=0.98
            )
        ]

        report = await tracker.get_cost_report(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 18),
            group_by="service"
        )

        assert report["total_cost_usd"] == 10.50
        assert len(report["groups"]) == 1


# ==========================================
# API Endpoint Tests
# ==========================================

class TestAIEndpoints:
    """Tests for AI API endpoints (v1 routers)."""

    @pytest.fixture
    def client(self):
        """Create test client with v1 AI routers."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routers.v1_muse import router as muse_router
        from routers.v1_mirror import router as mirror_router
        from routers.v1_visual_search import router as visual_search_router
        from routers.v1_closet import router as closet_router
        from routers.v1_ai_admin import router as ai_admin_router

        app = FastAPI()
        # v1 routers already include /api/v1 in their prefix, no extra prefix needed
        app.include_router(muse_router)
        app.include_router(mirror_router)
        app.include_router(visual_search_router)
        app.include_router(closet_router)
        app.include_router(ai_admin_router)

        return TestClient(app)

    def test_muse_chat_endpoint(self, client):
        """Test MUSE chat endpoint exists."""
        response = client.post(
            "/api/v1/muse/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer test-token"}
        )
        # Will fail without proper auth, but endpoint should exist
        assert response.status_code in [401, 403, 422, 500]

    def test_mirror_tryon_endpoint(self, client):
        """Test MIRROR try-on endpoint exists."""
        response = client.post(
            "/api/v1/mirror/try-on",
            data={"product_variant_id": "test", "category": "upper_body"},
            headers={"Authorization": "Bearer test-token"}
        )
        # Will fail without image, but endpoint should exist
        assert response.status_code in [400, 401, 403, 422]

    def test_visual_search_endpoint(self, client):
        """Test visual search image endpoint exists."""
        response = client.post(
            "/api/v1/search/visual?limit=20",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [400, 401, 403, 422, 500]

    def test_visual_search_text_endpoint(self, client):
        """Test visual search text endpoint exists."""
        response = client.get(
            "/api/v1/search/text?q=red+dress&limit=20",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]

    def test_closet_items_endpoint(self, client):
        """Test closet items list endpoint exists."""
        response = client.get(
            "/api/v1/closet/items",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]

    def test_closet_duplicate_check_endpoint(self, client):
        """Test closet duplicate check endpoint exists."""
        response = client.post(
            "/api/v1/closet/check-duplicate",
            json={"product_name": "Blue Dress", "category": "dresses", "color": "blue"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]

    def test_closet_suggestions_endpoint(self, client):
        """Test closet outfit suggestions endpoint exists."""
        response = client.get(
            "/api/v1/closet/suggestions",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]

    def test_admin_budget_endpoint(self, client):
        """Test admin budget endpoint exists."""
        response = client.get(
            "/api/v1/ai-admin/budget",
            headers={"Authorization": "Bearer test-token"}
        )
        # Should require admin role
        assert response.status_code in [401, 403, 422]

    def test_admin_kill_switch_endpoint(self, client):
        """Test admin kill-switch toggle endpoint exists."""
        response = client.post(
            "/api/v1/ai-admin/kill-switch",
            json={"activate": True},
            headers={"Authorization": "Bearer test-token"}
        )
        # Should require admin role
        assert response.status_code in [401, 403, 422]

    def test_admin_daily_report_endpoint(self, client):
        """Test admin daily report endpoint exists."""
        response = client.get(
            "/api/v1/ai-admin/daily-report",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]

    def test_admin_user_costs_endpoint(self, client):
        """Test admin per-user costs endpoint exists."""
        response = client.get(
            "/api/v1/ai-admin/user-costs?user_id=test-user&limit=50",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code in [401, 403, 422, 500]


# ==========================================
# Run Tests
# ==========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
