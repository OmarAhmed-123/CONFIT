"""
CONFIT Backend — AI Services Module
====================================
Advanced AI-powered services for virtual try-on,
including pose detection, garment processing, and photorealistic blending.
"""

from .pose_detector import PoseDetector, PoseResult
from .garment_processor import GarmentProcessor, GarmentCategory
from .image_blender import ImageBlender, BlendResult
from .quality_validator import QualityValidator, ValidationResult

__all__ = [
    "PoseDetector",
    "PoseResult",
    "GarmentProcessor",
    "GarmentCategory",
    "ImageBlender",
    "BlendResult",
    "QualityValidator",
    "ValidationResult",
]
