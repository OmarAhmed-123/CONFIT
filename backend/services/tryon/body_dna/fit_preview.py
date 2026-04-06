"""
Pre-render fit prediction + skeleton for smart preview (no garment pixels required).
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Optional


def predict_fit_preview(
    profile: Dict[str, Any],
    garment_category: str = "tops",
    fit_type: str = "regular",
) -> Dict[str, Any]:
    """
    Heuristic fit scores from Body DNA measurements + category.
    Returns instant skeleton overlay description (normalized) for UI.
    """
    m = profile.get("measurements") or {}
    shoulder_w = float(m.get("shoulder_width_norm", 0.22))
    torso = float(m.get("torso_length_norm", 0.28))
    hip_r = float(m.get("hip_ratio", 1.0))
    arm = float(m.get("arm_length_norm", 0.35))

    cat = (garment_category or "tops").lower()
    fit = (fit_type or "regular").lower()

    # Base score from proportions vs category expectations
    base = 0.72
    if cat in ("tops", "outerwear"):
        balance = 1.0 - min(0.4, abs(shoulder_w - 0.2) * 2.0)
        score = base + 0.15 * balance
    elif cat in ("bottoms",):
        balance = 1.0 - min(0.35, abs(hip_r - 1.15) * 0.8)
        score = base + 0.12 * balance
    elif cat in ("dresses", "full_body"):
        balance = 1.0 - min(0.5, abs(torso / (arm + 1e-6) - 0.85) * 0.5)
        score = base + 0.1 * balance
    else:
        score = base

    if fit == "tight":
        score += 0.03
    elif fit == "loose":
        score -= 0.02

    score = max(0.35, min(0.98, score))

    # Skeleton for instant UI overlay (normalized)
    ln = profile.get("landmarks_norm") or {}
    joints = []
    for name, pt in ln.items():
        joints.append(
            {
                "name": name,
                "x_norm": float(pt.get("x", 0)),
                "y_norm": float(pt.get("y", 0)),
            }
        )

    # Simple edges for stick figure
    edges = [
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("right_shoulder", "right_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_elbow", "right_wrist"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"),
        ("right_hip", "right_knee"),
        ("left_knee", "left_ankle"),
        ("right_knee", "right_ankle"),
    ]
    present = set(ln.keys())
    lines = [{"a": a, "b": b} for a, b in edges if a in present and b in present]

    return {
        "fit_score": round(score, 3),
        "garment_category": cat,
        "fit_type": fit,
        "notes": "Heuristic preview from Body DNA; final fit may vary after render.",
        "skeleton": {"joints": joints, "edges": lines},
    }


def fit_preview_to_json(preview: Dict[str, Any]) -> str:
    return json.dumps(preview)
