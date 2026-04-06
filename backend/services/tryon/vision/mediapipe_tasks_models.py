"""
Download and cache MediaPipe Tasks model files (pose landmarker, image segmenter).

Uses the same Python environment as the API server; first run may download ~6–30 MB.
Override URLs or cache dir via env — see .env.example.
"""

from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# After first GPU delegate failure (e.g. Windows wheels with GPU disabled in build flags),
# skip GPU for the remainder of the process to avoid repeated noisy init attempts.
_mediapipe_gpu_delegate_unavailable: bool = False


def set_mediapipe_gpu_delegate_unavailable(reason: str = "") -> None:
    """Call when MediaPipe Tasks GPU init fails; subsequent get_gpu_delegate_options() returns CPU-only."""
    global _mediapipe_gpu_delegate_unavailable
    if not _mediapipe_gpu_delegate_unavailable:
        logger.info(
            "MediaPipe GPU delegate disabled for this process (%s); using CPU only.",
            reason or "init failure",
        )
    _mediapipe_gpu_delegate_unavailable = True


def is_mediapipe_gpu_delegate_disabled() -> bool:
    return _mediapipe_gpu_delegate_unavailable


# Official Google Storage bundles (verified 2025)
DEFAULT_POSE_LANDMARKER_LITE_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
DEFAULT_SELFIE_MULTICLASS_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"
)


def _cache_dir() -> Path:
    env = os.getenv("MEDIAPIPE_MODEL_CACHE_DIR", "").strip()
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".cache" / "confit_mediapipe"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download(url: str, dest: Path, timeout_sec: int = 120) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        logger.info("Downloading MediaPipe model: %s -> %s", url, dest)
        urllib.request.urlretrieve(url, tmp)  # noqa: S310 — trusted Google URLs only
        tmp.replace(dest)
        return True
    except Exception as e:
        logger.warning("Model download failed (%s): %s", url, e)
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


def ensure_file(url: str, filename: str) -> Optional[str]:
    """Return absolute path to cached model, or None if download failed."""
    if not url:
        return None
    dest = _cache_dir() / filename
    if dest.is_file() and dest.stat().st_size > 1024:
        return str(dest.resolve())
    if _download(url, dest):
        return str(dest.resolve()) if dest.is_file() else None
    return None


def ensure_pose_landmarker_path() -> Optional[str]:
    url = os.getenv("TRYON_POSE_LANDMARKER_MODEL_URL", "").strip() or DEFAULT_POSE_LANDMARKER_LITE_URL
    return ensure_file(url, "pose_landmarker_lite.task")


def get_gpu_delegate_options() -> dict:
    """
    Configure GPU delegate for MediaPipe Tasks on supported hardware.
    Returns delegate options dict for BaseOptions.delegate.
    
    Set MEDIAPIPE_USE_GPU=0 or TRYON_FORCE_CPU=1 to force CPU mode.
    After a GPU init failure in this process, GPU is skipped automatically.
    
    Note: Returns the actual Delegate enum from mediapipe.tasks.python, not a string.
    This fixes the 'str' object has no attribute 'value' error.
    """
    if os.getenv("TRYON_FORCE_CPU", "").strip().lower() in ("1", "true", "yes"):
        return {}
    if _mediapipe_gpu_delegate_unavailable:
        return {}
    use_gpu = os.getenv("MEDIAPIPE_USE_GPU", "1").strip().lower() in ("1", "true", "yes", "auto")
    if not use_gpu:
        return {}
    
    try:
        from mediapipe.tasks.python import BaseOptions
        # Get the Delegate enum from BaseOptions
        # In MediaPipe Tasks, delegate is an enum: CPU, GPU, CORE_ML (on macOS)
        Delegate = BaseOptions.Delegate if hasattr(BaseOptions, 'Delegate') else None
        
        if Delegate is None:
            # Fallback for older MediaPipe versions
            logger.debug("MediaPipe BaseOptions.Delegate not available, using CPU")
            return {}
        
        # Check for CUDA/GPU availability
        try:
            import torch
            has_cuda = torch.cuda.is_available()
        except ImportError:
            has_cuda = False
        
        # Return the actual enum value, not a string
        # This is the fix for 'str' object has no attribute 'value'
        return {"delegate": Delegate.GPU}
        
    except ImportError:
        logger.debug("MediaPipe tasks not available for GPU delegate")
        return {}
    except Exception as e:
        logger.warning("GPU delegate setup failed: %s, using CPU", e)
        return {}


def ensure_selfie_segmenter_path() -> Optional[str]:
    url = os.getenv("TRYON_SELFIE_SEGMENTER_MODEL_URL", "").strip() or DEFAULT_SELFIE_MULTICLASS_URL
    return ensure_file(url, "selfie_multiclass_256x256.tflite")


# Full model URLs for higher accuracy (model_complexity=2 equivalent)
DEFAULT_POSE_LANDMARKER_FULL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
DEFAULT_POSE_LANDMARKER_HEAVY_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
)


def ensure_pose_landmarker_full_path() -> Optional[str]:
    """Download full model for model_complexity=2 equivalent (higher accuracy)."""
    url = os.getenv("TRYON_POSE_LANDMARKER_FULL_MODEL_URL", "").strip() or DEFAULT_POSE_LANDMARKER_FULL_URL
    return ensure_file(url, "pose_landmarker_full.task")


def ensure_pose_landmarker_heavy_path() -> Optional[str]:
    """Download heavy model for maximum accuracy (slower)."""
    url = os.getenv("TRYON_POSE_LANDMARKER_HEAVY_MODEL_URL", "").strip() or DEFAULT_POSE_LANDMARKER_HEAVY_URL
    return ensure_file(url, "pose_landmarker_heavy.task")
