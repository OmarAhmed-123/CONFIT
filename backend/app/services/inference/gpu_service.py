"""
CONFIT Backend — GPU Inference Service
=====================================
Production GPU inference service (INACTIVE in development).

IMPORTANT: This file is NOT imported or executed when INFERENCE_MODE=mock.
It will only be activated when:
1. INFERENCE_MODE=gpu
2. CUDA is available
3. Model weights exist
"""

import logging
import os
from typing import Dict, Any, Optional

from services.inference.base import (
    InferenceServiceBase,
    InferenceMode,
    InferenceResult,
    PoseDetectionResult,
    SegmentationResult,
)

logger = logging.getLogger(__name__)


class GPUInferenceService(InferenceServiceBase):
    """
    GPU-accelerated inference service.
    
    This service requires:
    - NVIDIA GPU with CUDA support
    - PyTorch with CUDA
    - Model weights downloaded
    
    If requirements are not met, the service will mark itself
    as unavailable and the system will fall back to mock.
    
    Usage:
        service = GPUInferenceService()
        if service.is_available:
            result = await service.process_tryon(...)
        else:
            # Fall back to mock
    """
    
    def __init__(self):
        self._mode = InferenceMode.GPU
        self._available = False
        self._init_error: Optional[str] = None
        
        # Lazy-loaded components
        self._orchestrator = None
        self._pose_detector = None
        self._segmenter = None
        self._tryon_engine = None
        
        # Check availability
        self._check_availability()
    
    @property
    def mode(self) -> InferenceMode:
        return self._mode
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def _check_availability(self):
        """Check if GPU inference is available."""
        checks = []
        
        # Check CUDA
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            checks.append(('CUDA', cuda_available))
            
            if cuda_available:
                logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            else:
                self._init_error = "CUDA not available"
                logger.warning("CUDA not available - GPU service disabled")
                return
                
        except ImportError:
            self._init_error = "PyTorch not installed"
            logger.warning("PyTorch not installed - GPU service disabled")
            return
        
        # Check model weights
        weights_path = os.getenv('MODEL_WEIGHTS_PATH', '/app/weights')
        weights_exist = os.path.exists(weights_path)
        checks.append(('Model Weights', weights_exist))
        
        if not weights_exist:
            logger.warning(f"Model weights not found at {weights_path}")
            # Don't disable completely - might be first run
        
        # All critical checks passed
        self._available = cuda_available
        
        if self._available:
            logger.info("GPU Inference Service initialized successfully")
        else:
            logger.warning(f"GPU Inference Service unavailable: {self._init_error}")
    
    def _ensure_available(self):
        """Raise error if service is not available."""
        if not self._available:
            raise RuntimeError(
                f"GPU Inference Service is not available: {self._init_error}. "
                "Please check CUDA installation and model weights."
            )
    
    def _lazy_load_orchestrator(self):
        """Lazy load the try-on orchestrator."""
        if self._orchestrator is None:
            try:
                # Import from gpu_production directory
                import sys
                gpu_prod_path = os.path.join(
                    os.path.dirname(__file__), 
                    '..', '..', '..', 'gpu_production'
                )
                sys.path.insert(0, gpu_prod_path)
                
                from services.tryon.orchestrator import TryOnOrchestrator
                self._orchestrator = TryOnOrchestrator()
                logger.info("Try-on orchestrator loaded")
                
            except ImportError as e:
                logger.error(f"Failed to load orchestrator: {e}")
                raise RuntimeError(f"Failed to load GPU inference components: {e}")
    
    async def process_tryon(
        self,
        user_image: str,
        garment_image: str,
        garment_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """
        Process virtual try-on using GPU models.
        
        Args:
            user_image: Base64 encoded user photo
            garment_image: Base64 encoded garment image
            garment_id: Unique garment identifier
            options: Optional processing options
            
        Returns:
            InferenceResult with try-on output
        """
        self._ensure_available()
        
        logger.info(f"[GPU] Processing try-on for garment: {garment_id}")
        
        try:
            self._lazy_load_orchestrator()
            
            # Prepare request
            from models.tryon_models import TryOnRequest
            
            request = TryOnRequest(
                userImageBase64=user_image,
                garmentId=garment_id,
                garmentImageBase64=garment_image,
                options=options or {},
            )
            
            # Process
            result = await self._orchestrator.process(request)
            
            return InferenceResult(
                success=result.success,
                result_image=result.resultImage,
                processing_time_ms=result.processingTimeMs,
                quality_score=result.qualityScore,
                pose_detected=result.poseDetected,
                garment_category=result.garmentCategory,
                error=result.error,
                metadata={
                    'mode': 'gpu',
                    'model': getattr(self._orchestrator, 'model_name', 'unknown'),
                }
            )
            
        except Exception as e:
            logger.error(f"[GPU] Try-on failed: {e}", exc_info=True)
            return InferenceResult(
                success=False,
                error=str(e),
            )
    
    async def detect_pose(self, image: str) -> PoseDetectionResult:
        """Detect pose using GPU-accelerated model."""
        self._ensure_available()
        
        try:
            if self._pose_detector is None:
                from gpu_production.services.tryon.pose_detector import PoseDetector
                self._pose_detector = PoseDetector()
            
            result = await self._pose_detector.detect(image)
            
            return PoseDetectionResult(
                success=result.get('keypoints') is not None,
                keypoints=result.get('keypoints'),
                score=result.get('score', 0),
                is_valid=result.get('is_valid', False),
                feedback=result.get('feedback'),
            )
            
        except Exception as e:
            logger.error(f"[GPU] Pose detection failed: {e}")
            return PoseDetectionResult(
                success=False,
                error=str(e),
            )
    
    async def segment_image(
        self,
        image: str,
        pose_keypoints: Optional[Dict] = None
    ) -> SegmentationResult:
        """Segment image using GPU-accelerated model."""
        self._ensure_available()
        
        try:
            if self._segmenter is None:
                from gpu_production.services.tryon.segmenter import BodySegmenter
                self._segmenter = BodySegmenter()
            
            result = await self._segmenter.segment(image, pose_keypoints)
            
            return SegmentationResult(
                success=True,
                person_mask=result.get('person'),
                face_mask=result.get('face'),
                upper_body_mask=result.get('upper_body'),
                lower_body_mask=result.get('lower_body'),
            )
            
        except Exception as e:
            logger.error(f"[GPU] Segmentation failed: {e}")
            return SegmentationResult(
                success=False,
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check GPU service health."""
        import torch
        
        health = {
            'status': 'healthy' if self._available else 'unavailable',
            'mode': 'gpu',
            'available': self._available,
            'gpu_required': True,
            'init_error': self._init_error,
        }
        
        if self._available and torch.cuda.is_available():
            health['gpu'] = {
                'device_name': torch.cuda.get_device_name(0),
                'device_count': torch.cuda.device_count(),
                'memory_allocated_gb': torch.cuda.memory_allocated(0) / 1024**3,
                'memory_total_gb': torch.cuda.get_device_properties(0).total_memory / 1024**3,
            }
        
        return health


# ========================================
# Fallback Wrapper
# ========================================

class GPUInferenceServiceWithFallback:
    """
    GPU service with automatic fallback to mock.
    
    This wrapper ensures the system never fails due to
    GPU unavailability.
    """
    
    def __init__(self):
        self._gpu_service = GPUInferenceService()
        self._mock_service = None
    
    @property
    def mode(self) -> InferenceMode:
        if self._gpu_service.is_available:
            return InferenceMode.GPU
        return InferenceMode.MOCK
    
    @property
    def is_available(self) -> bool:
        return True  # Always available (with fallback)
    
    def _get_service(self) -> InferenceServiceBase:
        """Get appropriate service based on availability."""
        if self._gpu_service.is_available:
            return self._gpu_service
        
        # Lazy load mock service
        if self._mock_service is None:
            from services.inference.mock_service import MockInferenceService
            self._mock_service = MockInferenceService()
            logger.warning("GPU unavailable, using mock service as fallback")
        
        return self._mock_service
    
    async def process_tryon(
        self,
        user_image: str,
        garment_image: str,
        garment_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """Process with automatic fallback."""
        service = self._get_service()
        result = await service.process_tryon(user_image, garment_image, garment_id, options)
        
        # Mark if fallback was used
        if service.mode == InferenceMode.MOCK and self._gpu_service._init_error:
            result.metadata = result.metadata or {}
            result.metadata['fallback_reason'] = self._gpu_service._init_error
        
        return result
    
    async def detect_pose(self, image: str) -> PoseDetectionResult:
        return await self._get_service().detect_pose(image)
    
    async def segment_image(
        self,
        image: str,
        pose_keypoints: Optional[Dict] = None
    ) -> SegmentationResult:
        return await self._get_service().segment_image(image, pose_keypoints)
    
    async def health_check(self) -> Dict[str, Any]:
        gpu_health = await self._gpu_service.health_check()
        gpu_health['fallback_active'] = not self._gpu_service.is_available
        return gpu_health
