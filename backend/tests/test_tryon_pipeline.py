"""
CONFIT Backend — Try-On Pipeline Tests
========================================
Tests for MCP pipeline, orchestrator, model router,
cache layer, GPU scheduler, and security middleware.
"""

import asyncio
import base64
import os
import sys
import time
import pytest

# Ensure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════════
# MODEL ROUTER TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestModelRouter:
    """Test model backend selection logic."""

    def test_import(self):
        from services.mcp.model_router import ModelRouter
        router = ModelRouter()
        assert router is not None

    def test_local_always_available(self):
        from services.mcp.model_router import ModelRouter, ModelBackend
        router = ModelRouter()
        assert router.is_available(ModelBackend.LOCAL)

    def test_select_returns_valid_backend(self):
        from services.mcp.model_router import ModelRouter, ModelBackend
        router = ModelRouter()
        backend = router.select()
        assert backend in (ModelBackend.ADVANCED, ModelBackend.HUGGINGFACE, ModelBackend.LOCAL)

    def test_fast_quality_returns_local(self):
        from services.mcp.model_router import ModelRouter, ModelBackend
        router = ModelRouter()
        backend = router.select(quality="fast")
        assert backend == ModelBackend.LOCAL

    def test_mark_unavailable(self):
        from services.mcp.model_router import ModelRouter, ModelBackend
        router = ModelRouter()
        router.mark_unavailable(ModelBackend.ADVANCED)
        assert not router.is_available(ModelBackend.ADVANCED)

    def test_available_backends_list(self):
        from services.mcp.model_router import ModelRouter
        router = ModelRouter()
        backends = router.available_backends()
        assert isinstance(backends, list)
        assert len(backends) >= 1  # At least local

    def test_stats(self):
        from services.mcp.model_router import ModelRouter
        router = ModelRouter()
        stats = router.stats()
        assert "available_backends" in stats
        assert "default_selection" in stats


# ═══════════════════════════════════════════════════════════════════════════
# CACHE LAYER TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestCacheLayer:
    """Test in-memory cache (Redis not required for tests)."""

    @pytest.fixture
    def cache(self):
        from services.mcp.cache_layer import TryOnCache
        return TryOnCache()

    def test_import(self, cache):
        assert cache is not None

    @pytest.mark.asyncio
    async def test_set_and_get_result(self, cache):
        key = "test:result:abc"
        value = "base64_image_data_here"
        await cache.set_result(key, value, ttl=60)
        result = await cache.get_result(key)
        assert result == value

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        result = await cache.get_result("nonexistent:key")
        assert result is None

    def test_hash_image(self, cache):
        from services.mcp.cache_layer import TryOnCache
        h = TryOnCache.hash_image("some_base64_data")
        assert isinstance(h, str)
        assert len(h) == 16

    def test_hash_options(self, cache):
        from services.mcp.cache_layer import TryOnCache
        h1 = TryOnCache.hash_options({"quality": "high"})
        h2 = TryOnCache.hash_options({"quality": "low"})
        assert h1 != h2
        h3 = TryOnCache.hash_options(None)
        assert h3 == "default"

    def test_make_result_key(self, cache):
        from services.mcp.cache_layer import TryOnCache
        key = TryOnCache.make_result_key("img_hash", "garment_1", "opts_hash")
        assert key.startswith("tryon:result:")

    def test_stats(self, cache):
        stats = cache.stats()
        assert stats["backend"] == "memory"
        assert stats["hits"] == 0

    @pytest.mark.asyncio
    async def test_hit_rate(self, cache):
        await cache.set_result("test:hit", "data", ttl=60)
        await cache.get_result("test:hit")     # hit
        await cache.get_result("test:miss")    # miss
        assert cache.hit_rate == pytest.approx(0.5, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# GPU SCHEDULER TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGPUScheduler:
    """Test GPU scheduler submission and concurrency."""

    def test_import(self):
        from services.mcp.gpu_scheduler import GPUScheduler
        scheduler = GPUScheduler()
        assert scheduler is not None

    def test_device_detection(self):
        from services.mcp.gpu_scheduler import GPUScheduler
        scheduler = GPUScheduler()
        assert scheduler.device in ("cpu", "cuda", "mps")

    def test_can_accept_job(self):
        from services.mcp.gpu_scheduler import GPUScheduler
        scheduler = GPUScheduler(max_queue_size=10)
        assert scheduler.can_accept_job()

    @pytest.mark.asyncio
    async def test_submit_sync_function(self):
        from services.mcp.gpu_scheduler import GPUScheduler, Priority
        scheduler = GPUScheduler()
        result = await scheduler.submit(
            job_id="test_sync",
            func=lambda x: x * 2,
            args=(21,),
            priority=Priority.STANDARD,
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_submit_async_function(self):
        from services.mcp.gpu_scheduler import GPUScheduler, Priority

        async def async_double(x):
            return x * 2

        scheduler = GPUScheduler()
        result = await scheduler.submit(
            job_id="test_async",
            func=async_double,
            args=(21,),
            priority=Priority.INTERACTIVE,
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_submit_error_propagation(self):
        from services.mcp.gpu_scheduler import GPUScheduler

        def failing_func():
            raise ValueError("intentional error")

        scheduler = GPUScheduler()
        with pytest.raises(ValueError, match="intentional error"):
            await scheduler.submit(job_id="test_fail", func=failing_func)

    def test_stats(self):
        from services.mcp.gpu_scheduler import GPUScheduler
        scheduler = GPUScheduler()
        stats = scheduler.stats()
        assert "device" in stats
        assert "total_processed" in stats


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestOrchestrator:
    """Test TryOnOrchestrator validation and category detection."""

    def test_import(self):
        from services.mcp.orchestrator import TryOnOrchestrator
        orch = TryOnOrchestrator()
        assert orch is not None

    def test_category_detection(self):
        from services.mcp.orchestrator import detect_garment_category
        assert detect_garment_category("Classic Blue T-Shirt") == "tops"
        assert detect_garment_category("Slim Fit Jeans") == "bottoms"
        assert detect_garment_category("Evening Gown") == "dresses"
        assert detect_garment_category("Leather Jacket") == "outerwear"
        assert detect_garment_category("Running Sneakers") == "shoes"
        assert detect_garment_category("Gold Necklace") == "accessories"
        assert detect_garment_category("Unknown Item") == "tops"  # default

    @pytest.mark.asyncio
    async def test_validation_empty_image(self):
        from services.mcp.orchestrator import TryOnOrchestrator
        orch = TryOnOrchestrator()
        result = await orch.process(
            user_image_base64="",
            garment_image_url="https://example.com/garment.jpg",
            garment_name="Test Shirt",
        )
        assert not result.success
        assert "Invalid" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_validation_bad_url(self):
        from services.mcp.orchestrator import TryOnOrchestrator
        orch = TryOnOrchestrator()
        result = await orch.process(
            user_image_base64="a" * 200,
            garment_image_url="not-a-url",
            garment_name="Test Shirt",
        )
        assert not result.success
        assert "URL" in (result.error_message or "")


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPipeline:
    """Test ModelControlPipeline initialization and stats."""

    def test_singleton(self):
        from services.mcp.pipeline import ModelControlPipeline
        p1 = ModelControlPipeline.get_instance()
        p2 = ModelControlPipeline.get_instance()
        assert p1 is p2

    def test_stats(self):
        from services.mcp.pipeline import ModelControlPipeline
        # Reset singleton for clean test
        ModelControlPipeline._instance = None
        p = ModelControlPipeline.get_instance()
        stats = p.stats()
        assert "router" in stats
        assert "cache" in stats
        assert "scheduler" in stats


# ═══════════════════════════════════════════════════════════════════════════
# SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestTryOnSecurity:
    """Test image validation, signed URLs, and cleanup."""

    def test_validate_empty(self):
        from middleware.tryon_security import validate_upload_image
        valid, msg = validate_upload_image("")
        assert not valid

    def test_validate_too_small(self):
        from middleware.tryon_security import validate_upload_image
        tiny = base64.b64encode(b"tiny").decode()
        valid, msg = validate_upload_image(tiny)
        assert not valid

    def test_validate_valid_jpeg(self):
        from middleware.tryon_security import validate_upload_image
        # Create minimal valid JPEG header
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        b64 = base64.b64encode(jpeg_header).decode()
        valid, msg = validate_upload_image(b64)
        assert valid

    def test_validate_valid_png(self):
        from middleware.tryon_security import validate_upload_image
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
        b64 = base64.b64encode(png_header).decode()
        valid, msg = validate_upload_image(b64)
        assert valid

    def test_validate_script_injection(self):
        from middleware.tryon_security import validate_upload_image
        # JPEG header but with script tag
        malicious = b"\xff\xd8\xff\xe0" + b"<script>alert(1)</script>" + b"\x00" * 200
        b64 = base64.b64encode(malicious).decode()
        valid, msg = validate_upload_image(b64)
        assert not valid
        assert "suspicious" in msg.lower()

    def test_validate_data_url_prefix(self):
        from middleware.tryon_security import validate_upload_image
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        b64 = "data:image/jpeg;base64," + base64.b64encode(jpeg_header).decode()
        valid, msg = validate_upload_image(b64)
        assert valid

    def test_validate_bad_mime(self):
        from middleware.tryon_security import validate_upload_image
        data = base64.b64encode(b"\x00" * 200).decode()
        b64 = "data:text/html;base64," + data
        valid, msg = validate_upload_image(b64)
        assert not valid

    def test_signed_url_generation(self):
        from middleware.tryon_security import generate_signed_url
        url = generate_signed_url("result_123")
        assert "result_123" in url
        assert "sig=" in url
        assert "expires=" in url

    def test_signed_url_verification(self):
        import time as t
        from middleware.tryon_security import generate_signed_url, verify_signed_url
        url = generate_signed_url("result_abc", expires_in=3600)
        # Parse sig and expires from URL
        parts = url.split("?")[1].split("&")
        params = dict(p.split("=") for p in parts)
        assert verify_signed_url("result_abc", int(params["expires"]), params["sig"])

    def test_signed_url_expired(self):
        from middleware.tryon_security import verify_signed_url
        # Expired timestamp
        expired = int(time.time()) - 100
        assert not verify_signed_url("result_xyz", expired, "fake_sig")

    def test_cleanup_tracker(self):
        from middleware.tryon_security import ImageCleanupTracker
        tracker = ImageCleanupTracker()
        tracker.register("/tmp/nonexistent_test_file.jpg", ttl=0)
        cleaned = tracker.cleanup_expired()
        # File doesn't exist so cleanup just removes tracking
        assert cleaned == 0


# ═══════════════════════════════════════════════════════════════════════════
# MODULE IMPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestTryOnSelfCheck:
    """Self-healing mask / quad helpers."""

    def test_center_inside_torso_mask(self):
        from services.tryon.validation import TryOnSelfCheck
        import numpy as np

        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[40:80, 40:80] = 255
        assert TryOnSelfCheck.center_inside_mask(60.0, 60.0, mask, erode_px=0)
        assert not TryOnSelfCheck.center_inside_mask(5.0, 5.0, mask, erode_px=0)

    def test_garment_centroid(self):
        from services.tryon.validation import TryOnSelfCheck
        import numpy as np

        a = np.zeros((50, 50), dtype=np.uint8)
        a[20:30, 20:30] = 200
        cx, cy = TryOnSelfCheck.garment_centroid(a)
        assert 20 <= cx <= 30 and 20 <= cy <= 30

    def test_nudge_quad_toward_torso(self):
        from services.tryon.validation import TryOnSelfCheck
        import numpy as np

        q = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]], dtype=np.float32)
        out = TryOnSelfCheck.nudge_quad_toward_torso(q, 5.0, 5.0, step=0.1)
        assert out.shape == q.shape


class TestQualityEvaluator:
    """Weighted quality evaluation (face excluded from edge/lighting ROIs)."""

    def test_evaluate_tryon_quality_runs(self):
        import numpy as np
        from services.tryon.quality import evaluate_tryon_quality
        from services.tryon.segmentation.body import SegmentationPack
        from services.tryon.vision.pose import PoseResult

        h, w = 64, 64
        blended = np.full((h, w, 3), 120, dtype=np.uint8)
        original = np.full((h, w, 3), 118, dtype=np.uint8)
        gmask = np.zeros((h, w), dtype=np.uint8)
        gmask[20:50, 22:42] = 200
        pm = np.zeros((h, w), dtype=np.uint8)
        pm[10:55, 18:46] = 255
        torso = np.zeros((h, w), dtype=np.uint8)
        torso[22:48, 20:44] = 220
        seg = SegmentationPack(
            person_mask=pm,
            torso_mask=torso,
            arms_mask=np.zeros((h, w), np.uint8),
            face_mask=np.zeros((h, w), np.uint8),
            hair_mask=np.zeros((h, w), np.uint8),
            garment_clip_mask=torso,
            segmentation_confidence=0.62,
            segmentation_source="grabcut",
        )
        pose = PoseResult(
            success=True,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.72,
        )
        ev = evaluate_tryon_quality(blended, original, gmask, pose, seg)
        assert 0.0 <= ev.overall <= 1.0
        assert "pose_alignment" in ev.weights_used


class TestRegionCompositor:
    """Region-based blend: face/hair must not receive full-frame garment alpha."""

    def test_face_protected_from_full_garment_alpha(self):
        import cv2
        import numpy as np
        from PIL import Image

        from services.tryon.blending.compositor import ImageBlender
        from services.tryon.blending.region_compositor import blend_fullframe_region_safe_sync
        from services.tryon.segmentation.body import SegmentationPack
        from services.tryon.vision.pose import PoseResult

        h, w = 128, 128
        person = np.zeros((h, w, 3), dtype=np.uint8)
        person[:, :] = [50, 60, 70]
        face = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(face, (64, 28), 18, 255, -1)
        hair = np.zeros((h, w), dtype=np.uint8)
        arms = np.zeros((h, w), dtype=np.uint8)
        torso = np.zeros((h, w), dtype=np.uint8)
        torso[40:120, 30:98] = 255
        g = np.zeros((h, w, 4), dtype=np.uint8)
        g[:, :, :3] = 200
        g[:, :, 3] = 255

        seg = SegmentationPack(
            person_mask=np.ones((h, w), dtype=np.uint8) * 255,
            torso_mask=torso,
            arms_mask=arms,
            face_mask=face,
            hair_mask=hair,
            garment_clip_mask=torso,
        )
        pose = PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.0,
        )
        blender = ImageBlender()
        pil = Image.fromarray(person, "RGB")
        res = blend_fullframe_region_safe_sync(blender, pil, g, pose, seg)
        assert res.success and res.image is not None
        out = np.array(res.image)
        diff = np.mean(
            np.abs(out[22:34, 56:72].astype(np.float32) - person[22:34, 56:72].astype(np.float32))
        )
        assert diff < 35.0


class TestGarmentIsolation:
    """Garment isolation should suppress leaked model skin blobs from catalog photos."""

    def test_suppress_human_parts_from_tops(self):
        import numpy as np
        from services.tryon.warping.garment import GarmentCategory, _suppress_human_parts_from_garment

        h, w = 120, 100
        rgb = np.full((h, w, 3), 245, dtype=np.uint8)
        alpha = np.zeros((h, w), dtype=np.uint8)
        # Main garment body
        rgb[25:110, 20:80] = [70, 100, 200]
        alpha[25:110, 20:80] = 255
        # Fake skin-like side blobs (model arms) that should be removed
        rgb[22:46, 8:19] = [214, 174, 142]
        alpha[22:46, 8:19] = 255
        rgb[24:48, 81:93] = [218, 176, 146]
        alpha[24:48, 81:93] = 255

        cleaned = _suppress_human_parts_from_garment(rgb, alpha, GarmentCategory.TOPS)
        assert np.count_nonzero(cleaned[22:46, 8:19] > 20) < 20
        assert np.count_nonzero(cleaned[24:48, 81:93] > 20) < 20
        # Garment core should remain mostly intact
        assert np.count_nonzero(cleaned[45:100, 30:70] > 20) > 0.9 * (55 * 40)


class TestBodyAnchorPipeline:
    """Structural pipeline primitives: pose map, anchors, scaling, depth warp."""

    def test_pose_map_and_anchor_metrics(self):
        from services.tryon.pose import PoseMap
        from services.tryon.anchoring import compute_body_anchors

        pm = PoseMap(
            left_shoulder=(40.0, 40.0, 0.9),
            right_shoulder=(100.0, 42.0, 0.9),
            neck=(70.0, 41.0, 0.9),
            left_hip=(48.0, 110.0, 0.9),
            right_hip=(96.0, 108.0, 0.9),
            confidence=0.9,
            image_width=160,
            image_height=160,
        )
        anchors = compute_body_anchors(pm)
        assert anchors.torso_width > 50.0
        assert anchors.torso_height > 50.0
        assert 65.0 <= anchors.neck_anchor[0] <= 75.0

    def test_intelligent_scale_uses_torso_width(self):
        import numpy as np
        from services.tryon.warp import compute_intelligent_scale

        g = np.zeros((80, 60, 4), dtype=np.uint8)
        g[:, :, :3] = 180
        g[8:72, 10:50, 3] = 255
        scaled, sf = compute_intelligent_scale(g, torso_width=96.0)
        assert sf > 1.0
        assert scaled.shape[1] >= 90

    def test_depth_estimation_and_mesh_warp_runs(self):
        import numpy as np
        from services.tryon.anchoring import BodyAnchors
        from services.tryon.warp import apply_pose_aware_mesh_warp, estimate_depth_match

        anchors = BodyAnchors(
            neck_anchor=(64.0, 30.0),
            torso_width=54.0,
            torso_height=90.0,
            shoulder_angle_rad=0.05,
            shoulder_mid=(64.0, 30.0),
            hip_mid=(64.0, 115.0),
        )
        d = estimate_depth_match(anchors, image_height=256)
        assert 0.03 <= d.perspective_strength <= 0.18
        src = np.zeros((120, 90, 4), dtype=np.uint8)
        src[:, :, :3] = [100, 150, 200]
        src[:, :, 3] = 255
        quad = np.array([[38, 30], [90, 30], [100, 140], [32, 140]], dtype=np.float32)
        warped = apply_pose_aware_mesh_warp(src, quad, (160, 220), depth=d)
        assert warped.shape == (220, 160, 4)
        assert int((warped[:, :, 3] > 10).sum()) > 1000


class TestModuleImports:
    """Verify all new modules import without errors."""

    def test_mcp_init(self):
        from services.mcp import ModelControlPipeline, TryOnOrchestrator, ModelRouter, TryOnCache, GPUScheduler
        assert all([ModelControlPipeline, TryOnOrchestrator, ModelRouter, TryOnCache, GPUScheduler])

    def test_live_preview(self):
        from services.live_preview import LivePreviewManager
        assert LivePreviewManager is not None

    def test_tryon_security(self):
        from middleware.tryon_security import validate_upload_image, generate_signed_url
        assert callable(validate_upload_image)
        assert callable(generate_signed_url)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
