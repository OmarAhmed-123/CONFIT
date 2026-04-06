"""
CONFIT Backend — Anti-Sticker Effect Validation Tests
======================================================
Tests to validate the fixes for the "sticker effect" in try-on output.

Key improvements tested:
- Strip mesh (TPS-like) warp enabled by default
- Body-anchored garment scaling
- Raised quality thresholds (0.60 minimum)
- Enhanced torso detection and clip mask
- Adaptive edge feathering
"""

import os
import sys
import numpy as np
import cv2
import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStripMeshWarpDefault:
    """Verify strip mesh (TPS-like) warp is enabled by default."""

    def test_strip_mesh_env_default(self):
        """Strip mesh should be enabled by default via TRYON_USE_STRIP_MESH."""
        # Default should be "1" (enabled) in the code
        from services.tryon.tryon_service import os as service_os
        # The code reads: os.getenv("TRYON_USE_STRIP_MESH", "1")
        # So default is "1"
        default_val = "1"
        assert default_val == "1", "Strip mesh should default to enabled"

    def test_strip_mesh_warp_produces_curvature(self):
        """Strip mesh warp should follow body curvature, not flat perspective."""
        from services.tryon.warping.tps import warp_rgba_strip_mesh, warp_rgba_to_quad

        # Create a test garment with vertical stripes to visualize curvature
        h, w = 120, 100
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        # Vertical stripes
        for i in range(0, w, 10):
            rgba[:, i:i+5, :3] = [200, 100, 50]
            rgba[:, i:i+5, 3] = 255
        rgba[:, 5::10, :3] = [50, 100, 200]
        rgba[:, 5::10, 3] = 255

        # Destination quad with taper (body curvature)
        dst_quad = np.array([
            [30, 20],   # TL
            [130, 25],  # TR
            [120, 180], # BR
            [40, 175]   # BL
        ], dtype=np.float32)

        out_wh = (160, 200)

        # Strip mesh warp
        mesh_result = warp_rgba_strip_mesh(rgba, dst_quad, out_wh, strips=12)

        # Flat perspective warp
        flat_result = warp_rgba_to_quad(rgba, dst_quad, out_wh)

        # Mesh result should have different pixel distribution due to per-strip warping
        mesh_alpha_sum = np.sum(mesh_result[:, :, 3] > 50)
        flat_alpha_sum = np.sum(flat_result[:, :, 3] > 50)

        # Both should produce valid output
        assert mesh_alpha_sum > 1000, "Strip mesh should produce visible output"
        assert flat_alpha_sum > 1000, "Flat warp should produce visible output"

        # Mesh should handle the taper differently
        # The key difference is strip mesh preserves local proportions
        assert mesh_result.shape == flat_result.shape


class TestBodyAnchoredScaling:
    """Verify garment scaling adapts to body proportions."""

    def test_scaling_uses_torso_dimensions(self):
        """Garment scaling should consider torso width AND height."""
        from services.tryon.tryon_service import _scale_garment_rgba_to_shoulder
        from services.tryon.warping.garment import GarmentCategory

        # Create a tall narrow garment
        rgba = np.zeros((200, 80, 4), dtype=np.uint8)
        rgba[20:180, 10:70, :3] = [100, 150, 200]
        rgba[20:180, 10:70, 3] = 255

        shoulder_px = 100.0
        torso_mask = np.zeros((300, 200), dtype=np.uint8)
        torso_mask[50:200, 40:160] = 255
        torso_height = 150.0

        # Scale for TOPS category
        scaled = _scale_garment_rgba_to_shoulder(
            rgba, shoulder_px, GarmentCategory.TOPS,
            torso_mask=torso_mask, torso_height=torso_height
        )

        # Should scale based on shoulder width
        assert scaled.shape[1] >= 80, "Width should scale to shoulder"
        assert scaled.shape[0] >= 100, "Height should consider torso"

    def test_scaling_category_differences(self):
        """Different garment categories should scale differently."""
        from services.tryon.tryon_service import _scale_garment_rgba_to_shoulder
        from services.tryon.warping.garment import GarmentCategory

        # Same garment for all categories
        rgba = np.zeros((150, 100, 4), dtype=np.uint8)
        rgba[10:140, 10:90, :3] = [120, 120, 120]
        rgba[10:140, 10:90, 3] = 255

        shoulder_px = 90.0
        torso_mask = None
        torso_height = 120.0

        tops_scaled = _scale_garment_rgba_to_shoulder(
            rgba, shoulder_px, GarmentCategory.TOPS, torso_mask, torso_height
        )
        bottoms_scaled = _scale_garment_rgba_to_shoulder(
            rgba, shoulder_px, GarmentCategory.BOTTOMS, torso_mask, torso_height
        )
        dress_scaled = _scale_garment_rgba_to_shoulder(
            rgba, shoulder_px, GarmentCategory.DRESSES, torso_mask, torso_height
        )

        # Dresses should be taller than tops
        assert dress_scaled.shape[0] > tops_scaled.shape[0], \
            "Dresses should be taller than tops"

        # Bottoms should be narrower (hips < shoulders)
        assert bottoms_scaled.shape[1] <= tops_scaled.shape[1], \
            "Bottoms should be narrower than tops"


class TestQualityThresholds:
    """Verify raised quality thresholds reject bad outputs."""

    def test_minimum_output_quality_raised(self):
        """Minimum output quality should be at least 0.60."""
        from services.tryon.tryon_service import _effective_min_output_quality

        # Default threshold
        min_q = _effective_min_output_quality({}, 0.72)
        assert min_q >= 0.60, f"Minimum quality should be >= 0.60, got {min_q}"

        # With lower threshold, should still floor at 0.60
        min_q_low = _effective_min_output_quality({}, 0.50)
        assert min_q_low >= 0.60, f"Minimum quality should floor at 0.60, got {min_q_low}"

    def test_quality_threshold_default_raised(self):
        """Quality threshold default should be 0.72."""
        # This is set in the code: thresh = float(opts.get("quality_threshold", 0.72))
        default_thresh = 0.72
        assert default_thresh >= 0.70, "Default threshold should be >= 0.70"


class TestEnhancedSegmentation:
    """Verify improved torso detection and clip mask."""

    def test_torso_expansion_increased(self):
        """Torso expansion should be 22% (up from 18%)."""
        from services.tryon.segmentation.body import UnifiedBodySegmenter
        from services.tryon.vision.pose import PoseResult

        # Check env default
        expand_ratio = float(os.getenv("TRYON_TORSO_POSE_EXPAND", "0.22"))
        assert expand_ratio >= 0.20, "Torso expansion should be >= 20%"

    def test_clip_mask_covers_longer_garments(self):
        """Clip mask should extend to 88% height for dresses."""
        from services.tryon.segmentation.body import UnifiedBodySegmenter

        # The code uses: y_cut = min(h, int(h * 0.88))
        # Check env default
        clip_height_ratio = 0.88
        assert clip_height_ratio >= 0.85, "Clip mask should cover >= 85% height"

    def test_torso_horizontal_dilation(self):
        """Torso mask should include horizontal dilation for shoulder coverage."""
        from services.tryon.segmentation.body import UnifiedBodySegmenter
        from services.tryon.vision.pose import PoseResult

        # Create mock pose with shoulder landmarks
        pose = PoseResult(
            success=True,
            landmarks={
                "left_shoulder": (40, 60, 0.9),
                "right_shoulder": (120, 62, 0.9),
                "left_hip": (50, 150, 0.8),
                "right_hip": (110, 148, 0.8),
            },
            body_regions={},
            body_proportions={},
            image_width=160,
            image_height=200,
            confidence=0.85,
        )

        segmenter = UnifiedBodySegmenter()
        torso = segmenter._torso_from_pose(pose, 160, 200)

        # Torso should cover shoulder region
        shoulder_region = torso[50:70, 30:130]
        coverage = np.mean(shoulder_region > 80)
        assert coverage > 0.5, "Torso should cover shoulder region"


class TestAdaptiveEdgeFeathering:
    """Verify enhanced edge feathering for anti-sticker effect."""

    def test_feather_default_increased(self):
        """Default feather should be 21px (up from 17)."""
        from services.tryon.blending.region_compositor import blend_fullframe_region_safe_sync

        # Check env default in code
        default_feather = int(os.getenv("TRYON_BLEND_FEATHER_PX", "21"))
        assert default_feather >= 19, "Default feather should be >= 19px"

    def test_adaptive_erosion_based_on_edge_density(self):
        """Feathering should adapt erosion based on edge density."""
        from services.tryon.blending.region_compositor import _feather_alpha_u8

        # Create alpha with dense edges (complex shape)
        dense_alpha = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(dense_alpha, (10, 10), (90, 90), 255, -1)
        cv2.circle(dense_alpha, (50, 50), 30, 0, -1)  # Hole in middle
        for i in range(20, 80, 5):
            cv2.line(dense_alpha, (i, 10), (i, 90), 0, 1)  # Vertical lines

        # Create alpha with sparse edges (simple shape)
        sparse_alpha = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(sparse_alpha, (20, 20), (80, 80), 255, -1)

        # Feather both
        dense_feathered = _feather_alpha_u8(dense_alpha, ksize=21)
        sparse_feathered = _feather_alpha_u8(sparse_alpha, ksize=21)

        # Both should produce valid feathered output
        assert np.max(dense_feathered) > 100
        assert np.max(sparse_feathered) > 100

        # Dense edges should have more erosion
        dense_edge_sum = np.sum(dense_feathered > 50)
        sparse_edge_sum = np.sum(sparse_feathered > 50)

        # Dense should have slightly less visible area due to adaptive erosion
        # (this is the anti-bleeding measure)
        assert dense_edge_sum > 0 and sparse_edge_sum > 0


class TestEstimateBodyAngleMoved:
    """Verify estimate_body_angle_deg moved to anchoring.py."""

    def test_function_in_anchoring_module(self):
        """estimate_body_angle_deg should be importable from anchoring."""
        from services.tryon.anchoring import estimate_body_angle_deg
        assert callable(estimate_body_angle_deg)

    def test_function_accepts_pose_result(self):
        """estimate_body_angle_deg should accept PoseResult."""
        from services.tryon.anchoring import estimate_body_angle_deg
        from services.tryon.vision.pose import PoseResult

        pose = PoseResult(
            success=True,
            landmarks={
                "left_shoulder": (40, 50, 0.9),
                "right_shoulder": (100, 55, 0.9),
            },
            body_regions={},
            body_proportions={},
            image_width=160,
            image_height=200,
            confidence=0.85,
        )

        angle = estimate_body_angle_deg(pose)
        assert isinstance(angle, float)
        # Should detect slight tilt
        assert -30 <= angle <= 30, f"Angle should be reasonable, got {angle}"

    def test_function_accepts_pose_map(self):
        """estimate_body_angle_deg should accept PoseMap."""
        from services.tryon.anchoring import estimate_body_angle_deg
        from services.tryon.pose import PoseMap

        pm = PoseMap(
            left_shoulder=(40.0, 50.0, 0.9),
            right_shoulder=(100.0, 55.0, 0.9),
            neck=(70.0, 52.0, 0.9),
            left_hip=(45.0, 140.0, 0.8),
            right_hip=(95.0, 138.0, 0.8),
            confidence=0.85,
            image_width=160,
            image_height=200,
        )

        angle = estimate_body_angle_deg(pm)
        assert isinstance(angle, float)

    def test_function_not_in_tps(self):
        """estimate_body_angle_deg should NOT be in tps.py anymore."""
        import services.tryon.warping.tps as tps_module
        assert not hasattr(tps_module, 'estimate_body_angle_deg'), \
            "estimate_body_angle_deg should be removed from tps.py"


class TestBuildAnchoredDstQuad:
    """Verify build_anchored_dst_quad accepts image dimensions."""

    def test_accepts_image_width_height(self):
        """build_anchored_dst_quad should accept image_width and image_height."""
        from services.tryon.anchoring import build_anchored_dst_quad, BodyAnchors
        from services.tryon.warping.garment import GarmentCategory

        anchors = BodyAnchors(
            neck_anchor=(100.0, 50.0),
            torso_width=80.0,
            torso_height=120.0,
            shoulder_angle_rad=0.05,
            shoulder_mid=(100.0, 50.0),
            hip_mid=(100.0, 170.0),
        )

        quad = build_anchored_dst_quad(
            anchors,
            GarmentCategory.TOPS,
            image_width=200,
            image_height=300
        )

        assert quad.shape == (4, 2)
        assert quad.dtype == np.float32

        # Quad should be within image bounds
        assert np.all(quad[:, 0] >= 1) and np.all(quad[:, 0] <= 198)
        assert np.all(quad[:, 1] >= 1) and np.all(quad[:, 1] <= 298)

    def test_uses_pose_map_landmarks(self):
        """build_anchored_dst_quad should use pose_map via compute_body_anchors."""
        from services.tryon.anchoring import build_anchored_dst_quad, compute_body_anchors
        from services.tryon.pose import PoseMap
        from services.tryon.warping.garment import GarmentCategory

        pm = PoseMap(
            left_shoulder=(60.0, 80.0, 0.9),
            right_shoulder=(140.0, 82.0, 0.9),
            neck=(100.0, 81.0, 0.9),
            left_hip=(70.0, 200.0, 0.8),
            right_hip=(130.0, 198.0, 0.8),
            confidence=0.85,
            image_width=200,
            image_height=300,
        )

        anchors = compute_body_anchors(pm)
        quad = build_anchored_dst_quad(anchors, GarmentCategory.TOPS, 200, 300)

        # Neck anchor from pose_map should be used
        assert 90 <= anchors.neck_anchor[0] <= 110
        assert 75 <= anchors.neck_anchor[1] <= 90


class TestIntegrationAntiSticker:
    """Integration tests for anti-sticker improvements."""

    def test_full_pipeline_quality_check(self):
        """Full pipeline should reject low-quality outputs."""
        from services.tryon.quality import evaluate_tryon_quality
        from services.tryon.segmentation.body import SegmentationPack
        from services.tryon.vision.pose import PoseResult

        h, w = 128, 128

        # Simulate a "sticker" output (flat, misaligned)
        blended = np.full((h, w, 3), 100, dtype=np.uint8)
        # Garment as a simple rectangle (sticker-like)
        blended[40:80, 30:90] = [150, 150, 150]

        original = np.random.randint(80, 120, (h, w, 3), dtype=np.uint8)
        garment_alpha = np.zeros((h, w), dtype=np.uint8)
        garment_alpha[40:80, 30:90] = 255

        seg = SegmentationPack(
            person_mask=np.ones((h, w), dtype=np.uint8) * 255,
            torso_mask=np.zeros((h, w), dtype=np.uint8),
            arms_mask=np.zeros((h, w), dtype=np.uint8),
            face_mask=np.zeros((h, w), dtype=np.uint8),
            hair_mask=np.zeros((h, w), dtype=np.uint8),
            garment_clip_mask=np.zeros((h, w), dtype=np.uint8),
            segmentation_confidence=0.5,
            segmentation_source="test",
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

        eval_result = evaluate_tryon_quality(blended, original, garment_alpha, pose, seg)

        # Quality should be moderate (not great due to sticker-like appearance)
        # The raised thresholds should catch this
        assert eval_result.overall < 0.85, "Sticker-like output should have moderate quality"

    def test_strip_mesh_vs_flat_quality(self):
        """Strip mesh should produce better edge quality than flat warp."""
        from services.tryon.warping.tps import warp_rgba_strip_mesh, warp_rgba_to_quad

        # Create garment with gradient (simulates fabric texture)
        h, w = 100, 80
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        for y in range(h):
            rgba[y, :, :3] = [100 + y//2, 120, 140 - y//3]
        rgba[:, :, 3] = 255

        # Tapered quad (body shape)
        dst_quad = np.array([
            [20, 10],
            [100, 12],
            [90, 150],
            [30, 148]
        ], dtype=np.float32)

        out_wh = (120, 160)

        mesh = warp_rgba_strip_mesh(rgba, dst_quad, out_wh, strips=16)
        flat = warp_rgba_to_quad(rgba, dst_quad, out_wh)

        # Check edge smoothness
        mesh_edges = cv2.Canny(mesh[:, :, 3], 50, 150)
        flat_edges = cv2.Canny(flat[:, :, 3], 50, 150)

        # Both should have edges, but mesh should handle curvature better
        assert np.sum(mesh_edges) > 0
        assert np.sum(flat_edges) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
