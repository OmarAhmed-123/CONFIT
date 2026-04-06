"""
CONFIT Backend — Inference Services
===================================
Service layer for virtual try-on inference.

Mode Selection:
- INFERENCE_MODE=mock → MockInferenceService (development)
- INFERENCE_MODE=gpu → GPUInferenceService (production)

The service is selected automatically based on environment.
"""

import os
from typing import Optional

from services.inference.base import (
    InferenceServiceBase,
    InferenceMode,
    InferenceResult,
    PoseDetectionResult,
    SegmentationResult,
    InferenceServiceFactory,
    get_inference_service,
)

__all__ = [
    'InferenceServiceBase',
    'InferenceMode',
    'InferenceResult',
    'PoseDetectionResult',
    'SegmentationResult',
    'InferenceServiceFactory',
    'get_inference_service',
    'get_service',
]


def get_service() -> InferenceServiceBase:
    """
    Get the configured inference service.
    
    Returns:
        InferenceServiceBase instance (mock or GPU based on env)
    """
    return get_inference_service()


# Convenience exports
from services.inference.mock_service import MockInferenceService
from services.inference.gpu_service import GPUInferenceService
