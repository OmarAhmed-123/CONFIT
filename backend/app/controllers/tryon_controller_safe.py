"""
CONFIT Backend — Safe Try-On Controller
=====================================
Controller with automatic fallback and error handling.

This controller wraps the inference service with safety features:
- Automatic mock fallback if GPU unavailable
- Graceful error handling
- Input validation
- Timeout protection
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from models.tryon_models import TryOnRequest, TryOnResponse, QualityMetrics
from services.inference import get_inference_service, InferenceMode

logger = logging.getLogger(__name__)


class SafeTryOnController:
    """
    Safe try-on controller with automatic fallback.
    
    This controller ensures the try-on feature never fails
    due to GPU unavailability or other infrastructure issues.
    
    Usage:
        controller = SafeTryOnController()
        response = await controller.process(request)
    """
    
    def __init__(self):
        self._service = None
        self._last_mode: Optional[InferenceMode] = None
    
    @property
    def service(self):
        """Lazy load inference service."""
        if self._service is None:
            self._service = get_inference_service()
            self._last_mode = self._service.mode
            logger.info(f"Inference service initialized: {self._last_mode.value}")
        return self._service
    
    async def process(self, request: TryOnRequest) -> TryOnResponse:
        """
        Process try-on request with safety features.
        
        Args:
            request: Validated try-on request
            
        Returns:
            TryOnResponse (always returns valid response, never raises)
        """
        try:
            # Validate input
            self._validate_request(request)
            
            # Get service (mock or GPU)
            service = self.service
            
            # Log mode change
            if self._last_mode != service.mode:
                logger.warning(f"Inference mode changed: {self._last_mode} → {service.mode}")
                self._last_mode = service.mode
            
            # Process with timeout
            result = await asyncio.wait_for(
                service.process_tryon(
                    user_image=request.userImageBase64,
                    garment_image=request.garmentImageBase64 or "",
                    garment_id=request.garmentId,
                    options=request.options.dict() if request.options else {}
                ),
                timeout=60.0  # 1 minute max
            )
            
            # Build response
            return self._build_response(request, result)
            
        except asyncio.TimeoutError:
            logger.error("Try-on processing timed out")
            return TryOnResponse(
                success=False,
                error="Processing timed out. Please try with a smaller image.",
                message="Timeout error",
            )
            
        except Exception as e:
            logger.error(f"Try-on processing failed: {e}", exc_info=True)
            
            # Attempt fallback
            return await self._fallback_process(request, str(e))
    
    async def _fallback_process(
        self,
        request: TryOnRequest,
        original_error: str
    ) -> TryOnResponse:
        """
        Fallback processing when primary fails.
        
        Attempts mock service if GPU failed.
        """
        try:
            # Check if we're already using mock
            if self.service.mode == InferenceMode.MOCK:
                # Already using mock, can't fallback further
                return TryOnResponse(
                    success=False,
                    error=original_error,
                    message="Processing failed. Please try again.",
                )
            
            logger.warning("Attempting fallback to mock service")
            
            # Force mock service
            from services.inference.mock_service import MockInferenceService
            mock_service = MockInferenceService()
            
            result = await mock_service.process_tryon(
                user_image=request.userImageBase64,
                garment_image=request.garmentImageBase64 or "",
                garment_id=request.garmentId,
                options=request.options.dict() if request.options else {}
            )
            
            response = self._build_response(request, result)
            response.warnings = response.warnings or []
            response.warnings.append(f"GPU inference unavailable, using mock mode: {original_error}")
            
            return response
            
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            return TryOnResponse(
                success=False,
                error=f"Primary: {original_error}, Fallback: {fallback_error}",
                message="Processing failed. Please try again later.",
            )
    
    def _validate_request(self, request: TryOnRequest):
        """Validate request parameters."""
        if not request.userImageBase64:
            raise ValueError("User image is required")
        
        if not request.garmentId:
            raise ValueError("Garment ID is required")
        
        # Validate image size (max 10MB)
        import base64
        try:
            image_bytes = base64.b64decode(request.userImageBase64.split(',')[-1])
            if len(image_bytes) > 10 * 1024 * 1024:
                raise ValueError("Image too large. Maximum 10MB.")
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}")
    
    def _build_response(
        self,
        request: TryOnRequest,
        result
    ) -> TryOnResponse:
        """Build response from inference result."""
        return TryOnResponse(
            success=result.success,
            resultImage=result.result_image,
            message="Virtual try-on completed successfully!" if result.success else "Processing failed",
            error=result.error,
            qualityScore=result.quality_score,
            poseDetected=result.pose_detected,
            garmentCategory=result.garment_category,
            processingTimeMs=result.processing_time_ms,
            qualityMetrics=QualityMetrics(
                overallScore=result.quality_score,
                realismScore=result.quality_score * 0.9,
                edgeQualityScore=result.quality_score * 0.85,
                colorConsistencyScore=result.quality_score * 0.9,
                proportionScore=result.quality_score * 0.95,
                artifactScore=result.quality_score * 0.9,
            ) if result.success else None,
            warnings=[],
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check controller and service health."""
        try:
            service_health = await self.service.health_check()
            
            return {
                'status': 'healthy',
                'controller': 'operational',
                'inference': service_health,
                'mode': self.service.mode.value,
            }
        except Exception as e:
            return {
                'status': 'degraded',
                'controller': 'error',
                'error': str(e),
            }


# Singleton instance
_controller: Optional[SafeTryOnController] = None


def get_tryon_controller() -> SafeTryOnController:
    """Get the try-on controller instance."""
    global _controller
    if _controller is None:
        _controller = SafeTryOnController()
    return _controller
