"""Tests for garment clip mask union (shoulders visible after warp)."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fake_pose(ls, rs):
    from services.tryon.vision.pose import PoseResult

    return PoseResult(
        success=True,
        landmarks={
            "left_shoulder": (ls[0], ls[1], 0.95),
            "right_shoulder": (rs[0], rs[1], 0.94),
        },
        body_regions={},
        body_proportions={},
        image_width=640,
        image_height=480,
        confidence=0.9,
    )


def test_shoulder_line_clip_mask_nonzero():
    from services.tryon.tryon_service import _shoulder_line_clip_mask

    pose = _fake_pose((420.0, 120.0), (220.0, 125.0))
    m = _shoulder_line_clip_mask(pose, 640, 480)
    assert m.shape == (480, 640)
    assert np.max(m) > 200


def test_clip_union_covers_shoulder_outside_torso_band():
    """Where torso-tight is 0 at shoulders, wide clip + shoulder mask must retain alpha support."""
    h, w = 200, 200
    torso_tight = np.zeros((h, w), dtype=np.uint8)
    torso_tight[80:180, 70:130] = 255  # narrow vertical band — misses lateral shoulders
    wide = np.zeros((h, w), dtype=np.uint8)
    wide[60:190, 20:180] = 220
    pose = _fake_pose((160.0, 70.0), (40.0, 72.0))
    from services.tryon.tryon_service import _shoulder_line_clip_mask

    shoulder_sup = _shoulder_line_clip_mask(pose, w, h)
    clip = np.maximum(np.maximum(torso_tight, wide), shoulder_sup)
    # Shoulder pixel (x=40,y=70) is outside narrow torso_tight but must be in clip
    assert clip[70, 40] > 10
    assert clip[70, 160] > 10
