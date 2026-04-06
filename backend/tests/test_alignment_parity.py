"""
Preview vs final render alignment identity and diagnostics parity (no duplicate orientation stacks).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_preview_and_final_share_alignment_pipeline_version():
    from services.tryon.alignment_config import (
        ALIGNMENT_PIPELINE_VERSION,
        final_render_classical_options,
        preview_classical_options,
    )

    pv = preview_classical_options()["alignment_pipeline_version"]
    fv = final_render_classical_options()["alignment_pipeline_version"]
    assert pv == fv == ALIGNMENT_PIPELINE_VERSION


def test_alignment_diagnostics_payload_json_serializable():
    from services.tryon.stable_alignment import (
        OrientationInfo,
        build_alignment_diagnostics_payload,
    )

    lm = {
        "left_shoulder": (600.0, 200.0, 0.9),
        "right_shoulder": (400.0, 205.0, 0.88),
    }
    oi = OrientationInfo(
        forward_direction="front",
        shoulder_angle_rad=0.01,
        shoulder_width_px=200.0,
        neck_midpoint=(500.0, 180.0),
        hip_center=(500.0, 400.0),
        confidence=0.85,
        needs_flip_h=False,
        needs_flip_v=False,
        flip_reason="",
    )
    d = build_alignment_diagnostics_payload(
        pose_landmarks=lm,
        pose_confidence=0.92,
        orientation=oi,
        garment_corrections_applied=["rotation_-2.0deg"],
        pipeline_version="test",
        alignment_code_id="abc",
        preview_mode=False,
        stable_alignment_enabled=True,
        normalization_ran=True,
        category="tops",
    )
    json.dumps(d)
    assert d["alignment_pipeline_version"] == "test"
    assert d["max_rotation_cap_deg"] == 30.0


def test_rotation_correction_never_exceeds_cap_in_diagnostics():
    from services.tryon.stable_alignment import compute_garment_corrections

    lm = {
        "left_shoulder": (0.2, 0.2, 0.95),
        "right_shoulder": (0.9, 0.95, 0.95),
    }
    r = compute_garment_corrections(lm, 0.95)
    assert abs(float(r["rotation"])) <= 30.0


def test_mediapipe_force_cpu_skips_gpu_delegate():
    import services.tryon.vision.mediapipe_tasks_models as m

    old = os.environ.get("TRYON_FORCE_CPU")
    try:
        os.environ["TRYON_FORCE_CPU"] = "1"
        opts = m.get_gpu_delegate_options()
        assert opts == {}
    finally:
        if old is None:
            os.environ.pop("TRYON_FORCE_CPU", None)
        else:
            os.environ["TRYON_FORCE_CPU"] = old
