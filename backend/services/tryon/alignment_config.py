"""
Shared classical try-on alignment identity.

Preview (`/api/tryon/preview/live`), final render (remote mock or local), and
`TryOnService.process_classical` must report the same ``alignment_pipeline_version``
so operators can verify parity. Orientation normalization uses
``services.tryon.stable_alignment`` for all paths that call ``process_classical``.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict

# Bump when stable_alignment / shoulder-angle logic changes materially.
ALIGNMENT_PIPELINE_VERSION = "2.2.0-affine-inpaint-15deg"

# Short fingerprint for diagnostics (deterministic string hash).
ALIGNMENT_CODE_ID = hashlib.sha256(
    b"CONFIT:tryon:alignment:v2.2:affine_inpaint+15deg_clamp+back_flip_only+sorted_shoulder"
).hexdigest()[:16]


def alignment_identity() -> Dict[str, str]:
    return {
        "alignment_pipeline_version": ALIGNMENT_PIPELINE_VERSION,
        "alignment_code_id": ALIGNMENT_CODE_ID,
    }


def merge_alignment_identity(options: Dict[str, Any] | None) -> Dict[str, Any]:
    """Merge alignment version fields into classical try-on options."""
    out = dict(options or {})
    ident = alignment_identity()
    for k, v in ident.items():
        out.setdefault(k, v)
    return out


def preview_classical_options() -> Dict[str, Any]:
    """Options shared by every preview attempt (identity + CPU-friendly preview)."""
    return merge_alignment_identity(
        {
            "preview_mode": True,
            "disable_input_preprocess": True,
        }
    )


def final_render_classical_options() -> Dict[str, Any]:
    """
    Default options for mock remote / high-quality final classical render.

    Keeps the same alignment stack as preview; differs only in quality/fabric
    knobs that do not change orientation normalization.
    """
    return merge_alignment_identity(
        {
            "fit_type": "regular",
            "quality_threshold": 0.62,
            "min_output_quality": 0.52,
            "allow_low_quality_output": True,
            "fabric_physics_enabled": True,
            "fabric_low_power": False,
            "fabric_intelligence": True,
            "return_validation_details": False,
            "preview_mode": False,
        }
    )
