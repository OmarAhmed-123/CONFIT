"""
CONFIT Backend — Inference Service Base Interface
=================================================
Abstract base class for inference services.

This interface ensures mock and GPU services have identical APIs.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class InferenceMode(Enum):
    """Available inference modes."""
    MOCK = "mock"
    GPU = "gpu"
    AUTO = "auto"  # Auto-detect based on availability


@dataclass
class InferenceResult:
    """Standard result from any inference service."""
    success: bool
    result_image: Optional[str] = None  # Base64 encoded
    processing_time_ms: float = 0.0
    quality_score: float = 0.0
    pose_detected: bool = False
    garment_category: str = "unknown"
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PoseDetectionResult:
    """Result from pose detection."""
    success: bool
    keypoints: Optional[Dict[str, Any]] = None
    score: float = 0.0
    is_valid: bool = False
    feedback: Optional[str] = None


@dataclass
class SegmentationResult:
    """Result from image segmentation."""
    success: bool
    person_mask: Optional[str] = None  # Base64 encoded
    face_mask: Optional[str] = None
    upper_body_mask: Optional[str] = None
    lower_body_mask: Optional[str] = None
    parsing_map: Optional[str] = None


class InferenceServiceBase(ABC):
    """
    Abstract base class for inference services.
    
    All inference services (mock, GPU, HuggingFace) must implement
    these methods with identical signatures.
    
    This ensures the controller can switch between services
    without code changes.
    """
    
    @property
    @abstractmethod
    def mode(self) -> InferenceMode:
        """Return the current inference mode."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""
        pass
    
    @abstractmethod
    async def process_tryon(
        self,
        user_image: str,
        garment_image: str,
        garment_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """
        Process virtual try-on request.
        
        Args:
            user_image: Base64 encoded user photo
            garment_image: Base64 encoded garment image
            garment_id: Unique garment identifier
            options: Optional processing options
            
        Returns:
            InferenceResult with try-on output
        """
        pass
    
    @abstractmethod
    async def detect_pose(
        self,
        image: str
    ) -> PoseDetectionResult:
        """
        Detect pose in image.
        
        Args:
            image: Base64 encoded image
            
        Returns:
            PoseDetectionResult with keypoints
        """
        pass
    
    @abstractmethod
    async def segment_image(
        self,
        image: str,
        pose_keypoints: Optional[Dict] = None
    ) -> SegmentationResult:
        """
        Segment image into regions.
        
        Args:
            image: Base64 encoded image
            pose_keypoints: Optional pose data for guided segmentation
            
        Returns:
            SegmentationResult with masks
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health.
        
        Returns:
            Dict with health status
        """
        pass


class InferenceServiceFactory:
    """
    Factory for creating inference services.
    
    Automatically selects the appropriate service based on
    environment configuration and availability.
    """
    
    _instances: Dict[InferenceMode, InferenceServiceBase] = {}
    
    @classmethod
    def get_service(
        cls,
        mode: Optional[InferenceMode] = None
    ) -> InferenceServiceBase:
        """
        Get inference service instance.
        
        Args:
            mode: Desired mode (MOCK, GPU, AUTO)
            
        Returns:
            InferenceServiceBase instance
        """
        import os
        
        # Determine mode
        if mode is None or mode == InferenceMode.AUTO:
            env_mode = os.getenv('INFERENCE_MODE', 'mock').lower()
            mode = InferenceMode(env_mode) if env_mode in ['mock', 'gpu'] else InferenceMode.MOCK
        
        # Check cache
        if mode in cls._instances:
            return cls._instances[mode]
        
        # Create instance
        if mode == InferenceMode.MOCK:
            from services.inference.mock_service import MockInferenceService
            service = MockInferenceService()
        elif mode == InferenceMode.GPU:
            from services.inference.gpu_service import GPUInferenceService
            service = GPUInferenceService()
        else:
            raise ValueError(f"Unknown inference mode: {mode}")
        
        # Cache and return
        cls._instances[mode] = service
        return service
    
    @classmethod
    def clear_cache(cls):
        """Clear cached service instances."""
        cls._instances.clear()


def get_inference_service() -> InferenceServiceBase:
    """
    Convenience function to get the configured inference service.
    
    Returns:
        InferenceServiceBase instance based on environment
    """
    return InferenceServiceFactory.get_service()
