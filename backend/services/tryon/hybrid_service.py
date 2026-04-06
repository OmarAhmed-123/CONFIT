"""
Hybrid Try-On Service
=====================
Combines classical CV pipeline with neural models for best quality.

Strategy:
1. Try neural model (IDM-VTON) if available and GPU present
2. Fall back to classical CV pipeline if neural fails or unavailable
3. Optionally blend both approaches for enhanced results
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PIL import Image
import numpy as np

from services.tryon.tryon_service import ClassicalTryOnService, ClassicalTryOnResult
from services.tryon.neural import NeuralTryOnResult, NeuralModelType
from services.tryon.neural.manager import get_neural_manager, NeuralModelManager

logger = logging.getLogger(__name__)


@dataclass
class HybridTryOnResult:
    """Result from hybrid try-on (neural + classical)."""
    success: bool
    result_image: Optional[str] = None  # Base64 encoded
    quality_score: float = 0.0
    method_used: str = ""  # "neural", "classical", or "hybrid"
    neural_result: Optional[NeuralTryOnResult] = None
    classical_result: Optional[ClassicalTryOnResult] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class HybridTryOnService:
    """
    Unified try-on service that selects best available method.
    
    Priority:
    1. Neural (IDM-VTON) - highest quality, requires GPU
    2. Classical CV - always available, good quality with anti-sticker fixes
    3. Hybrid blend - combines both for enhanced output (optional)
    """
    
    def __init__(self, prefer_neural: bool = True, auto_load_neural: bool = False):
        """
        Initialize hybrid service.
        
        Args:
            prefer_neural: Prefer neural model when available
            auto_load_neural: Automatically load neural model on init
        """
        self._classical = ClassicalTryOnService()
        self._neural_manager: Optional[NeuralModelManager] = None
        self._prefer_neural = prefer_neural
        
        # Configuration from environment
        self._neural_enabled = os.getenv("TRYON_NEURAL_ENABLED", "1").lower() in ("1", "true", "yes")
        self._neural_fallback = os.getenv("TRYON_NEURAL_FALLBACK", "1").lower() in ("1", "true", "yes")
        self._hybrid_blend = os.getenv("TRYON_HYBRID_BLEND", "0").lower() in ("1", "true", "yes")
        
        if auto_load_neural and self._neural_enabled:
            self._init_neural_manager()
    
    def _init_neural_manager(self) -> None:
        """Initialize neural model manager."""
        if self._neural_manager is None:
            self._neural_manager = get_neural_manager()
    
    def _should_use_neural(self, opts: Dict[str, Any]) -> bool:
        """Determine if neural model should be used."""
        if not self._neural_enabled:
            return False
        
        if opts.get("force_classical"):
            return False
        
        if opts.get("force_neural"):
            return True
        
        if not self._prefer_neural:
            return False
        
        # Check if neural models are available
        self._init_neural_manager()
        return self._neural_manager.is_neural_available()
    
    async def try_on(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        options: Optional[Dict[str, Any]] = None,
    ) -> HybridTryOnResult:
        """
        Run hybrid try-on with automatic method selection.
        
        Args:
            user_image_base64: Base64 encoded person image
            garment_image_url: URL to garment image
            garment_name: Name of garment for category detection
            options: Additional options
            
        Returns:
            HybridTryOnResult with best available output
        """
        opts = options or {}
        t0 = time.time()
        warnings: List[str] = []
        
        use_neural = self._should_use_neural(opts)
        
        # Try neural first if enabled
        neural_result: Optional[NeuralTryOnResult] = None
        if use_neural:
            logger.info("hybrid tryon: attempting neural model")
            neural_result = await self._try_neural(
                user_image_base64, garment_image_url, garment_name, opts
            )
            
            if neural_result and neural_result.success:
                logger.info(f"hybrid tryon: neural succeeded (quality={neural_result.quality_score:.2f})")
                
                # If hybrid blend enabled, also run classical and blend
                if self._hybrid_blend:
                    classical_result = await self._classical.try_on(
                        user_image_base64, garment_image_url, garment_name, opts
                    )
                    if classical_result.success:
                        blended = self._blend_results(neural_result, classical_result)
                        return HybridTryOnResult(
                            success=True,
                            result_image=blended,
                            quality_score=max(neural_result.quality_score, classical_result.quality_score),
                            method_used="hybrid",
                            neural_result=neural_result,
                            classical_result=classical_result,
                            warnings=warnings,
                            processing_time_ms=(time.time() - t0) * 1000,
                        )
                
                # Return neural result directly
                return HybridTryOnResult(
                    success=True,
                    result_image=self._pil_to_base64(neural_result.image),
                    quality_score=neural_result.quality_score,
                    method_used="neural",
                    neural_result=neural_result,
                    warnings=warnings,
                    processing_time_ms=(time.time() - t0) * 1000,
                )
            else:
                neural_error = neural_result.error_message if neural_result else "Unknown error"
                warnings.append(f"Neural model failed: {neural_error}")
                logger.warning(f"hybrid tryon: neural failed, falling back to classical")
        
        # Fall back to classical
        logger.info("hybrid tryon: running classical pipeline")
        classical_result = await self._classical.try_on(
            user_image_base64, garment_image_url, garment_name, opts
        )
        
        if classical_result.success:
            method = "classical" if not use_neural else "classical_fallback"
            return HybridTryOnResult(
                success=True,
                result_image=classical_result.result_image,
                quality_score=classical_result.quality_score,
                method_used=method,
                classical_result=classical_result,
                warnings=warnings + (classical_result.warnings or []),
                processing_time_ms=(time.time() - t0) * 1000,
            )
        
        # Both failed
        error_msg = classical_result.error_message or "Unknown error"
        return HybridTryOnResult(
            success=False,
            error_message=error_msg,
            neural_result=neural_result,
            classical_result=classical_result,
            warnings=warnings,
            processing_time_ms=(time.time() - t0) * 1000,
        )
    
    async def _try_neural(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        opts: Dict[str, Any],
    ) -> Optional[NeuralTryOnResult]:
        """Attempt neural try-on inference."""
        try:
            from utils.image_utils import base64_to_pil, download_image_to_temp
            
            # Load images
            person_pil = base64_to_pil(user_image_base64)
            if person_pil is None:
                return NeuralTryOnResult(
                    success=False,
                    error_message="Invalid person image",
                )
            
            garment_path = await download_image_to_temp(garment_image_url, suffix=".png")
            garment_pil = Image.open(garment_path).convert("RGBA")
            
            # Get category
            from services.tryon.warping.garment import GarmentProcessor
            processor = GarmentProcessor()
            category_str = opts.get("garment_category", processor.detect_category(garment_name).value)
            
            # Run neural inference
            self._init_neural_manager()
            result = self._neural_manager.infer(
                person_image=person_pil.convert("RGB"),
                garment_image=garment_pil,
                category=category_str,
                num_inference_steps=opts.get("neural_inference_steps", 30),
                guidance_scale=opts.get("neural_guidance_scale", 7.5),
                seed=opts.get("neural_seed"),
            )
            
            # Cleanup
            try:
                os.unlink(garment_path)
            except OSError:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Neural try-on failed: {e}")
            return NeuralTryOnResult(
                success=False,
                error_message=str(e),
            )
    
    def _blend_results(
        self,
        neural: NeuralTryOnResult,
        classical: ClassicalTryOnResult,
    ) -> str:
        """Blend neural and classical results for hybrid output."""
        # For now, return neural result as it's typically higher quality
        # Future: implement smart blending based on quality scores per region
        return self._pil_to_base64(neural.image)
    
    def _pil_to_base64(self, image: Optional[Image.Image], format: str = "JPEG", quality: int = 92) -> str:
        """Convert PIL image to base64 string."""
        if image is None:
            return ""
        
        import io
        import base64
        
        buf = io.BytesIO()
        image.save(buf, format=format, quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    
    def health(self) -> Dict[str, Any]:
        """Get health status of all components."""
        health = {
            "classical": self._classical.health(),
            "neural": {
                "enabled": self._neural_enabled,
                "prefer_neural": self._prefer_neural,
                "fallback_enabled": self._neural_fallback,
            },
        }
        
        if self._neural_manager:
            health["neural"]["status"] = self._neural_manager.get_status()
        
        return health


# Convenience function for direct usage
async def hybrid_try_on(
    user_image_base64: str,
    garment_image_url: str,
    garment_name: str = "garment",
    options: Optional[Dict[str, Any]] = None,
) -> HybridTryOnResult:
    """
    Convenience function for hybrid try-on.
    
    Uses singleton service instance.
    """
    service = HybridTryOnService()
    return await service.try_on(user_image_base64, garment_image_url, garment_name, options)
