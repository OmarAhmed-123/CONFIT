"""
Unit tests for stable garment alignment (shoulder ordering, rotation clamp, confidence gate).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _lm(x: float, y: float, vis: float = 0.95) -> tuple:
    return (float(x), float(y), float(vis))


def test_front_facing_no_flip():
    """Front-facing person should not trigger horizontal flip; rotation near 0."""
    from services.tryon.stable_alignment import compute_garment_corrections

    landmarks = {
        "left_shoulder": _lm(0.6, 0.3),
        "right_shoulder": _lm(0.4, 0.3),
        "left_hip": _lm(0.55, 0.7),
        "right_hip": _lm(0.45, 0.7),
    }
    result = compute_garment_corrections(landmarks, pose_confidence=0.95)
    assert result["flip"] is False
    assert result.get("skipped") is not True
    assert abs(result["rotation"]) < 5.0


def test_slight_angled_pose_small_rotation():
    """Slight shoulder tilt yields a modest rotation (still within clamp)."""
    from services.tryon.stable_alignment import compute_garment_corrections

    landmarks = {
        "left_shoulder": _lm(0.65, 0.40),
        "right_shoulder": _lm(0.35, 0.32),
        "left_hip": _lm(0.55, 0.72),
        "right_hip": _lm(0.45, 0.72),
    }
    result = compute_garment_corrections(landmarks, pose_confidence=0.92)
    assert result["flip"] is False
    assert abs(result["rotation"]) <= 30.0
    assert abs(result["rotation"]) >= 3.0


def test_extreme_rotation_clamped():
    """Extreme detected angle should be clamped to ±30°."""
    from services.tryon.stable_alignment import compute_garment_corrections

    landmarks = {
        "left_shoulder": _lm(0.3, 0.3),
        "right_shoulder": _lm(0.7, 0.8),
        "left_hip": _lm(0.35, 0.85),
        "right_hip": _lm(0.65, 0.85),
    }
    result = compute_garment_corrections(landmarks, pose_confidence=0.9)
    assert abs(result["rotation"]) <= 30.0


def test_low_confidence_skips_corrections():
    """Low pose confidence should skip corrections."""
    from services.tryon.stable_alignment import compute_garment_corrections

    landmarks = {
        "left_shoulder": _lm(0.6, 0.3),
        "right_shoulder": _lm(0.4, 0.3),
    }
    result = compute_garment_corrections(landmarks, pose_confidence=0.5)
    assert result["skipped"] is True
    assert result["rotation"] == 0.0
    assert result["flip"] is False


def test_sorted_shoulder_angle_not_near_180_for_front_camera():
    """Image-ordered shoulder angle stays near 0° for typical front-facing layout."""
    from services.tryon.stable_alignment import shoulder_tilt_degrees_raw_sorted

    landmarks = {
        "left_shoulder": _lm(620, 180),
        "right_shoulder": _lm(380, 185),
    }
    deg = shoulder_tilt_degrees_raw_sorted(landmarks)
    assert abs(deg) < 20.0


def test_align_garment_to_body_runs():
    """Smoke test: affine align returns valid array."""
    from services.tryon.warping.garment import align_garment_to_body

    garment = np.zeros((200, 160, 4), dtype=np.uint8)
    garment[:, :, 3] = 255
    garment[:, :, 0] = 200
    lm = {
        "left_shoulder": _lm(300, 100),
        "right_shoulder": _lm(100, 105),
        "left_hip": _lm(280, 400),
        "right_hip": _lm(120, 400),
    }
    out = align_garment_to_body(garment, lm, (400, 500), category="tops")
    assert out.shape == (500, 400, 4)


@pytest.mark.parametrize("category", ["tops", "bottoms"])
def test_align_garment_to_body_categories(category: str):
    from services.tryon.warping.garment import align_garment_to_body

    garment = np.zeros((120, 100, 4), dtype=np.uint8)
    garment[:, :, 3] = 255
    lm = {
        "left_shoulder": _lm(80, 40),
        "right_shoulder": _lm(40, 42),
        "left_hip": _lm(75, 90),
        "right_hip": _lm(45, 90),
    }
    out = align_garment_to_body(garment, lm, (120, 140), category=category)
    assert out.shape[2] == 4
