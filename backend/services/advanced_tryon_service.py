"""
CONFIT Backend — Advanced Virtual Try-On Service
================================================
Orchestrates AI-powered virtual try-on with:
- Body pose detection
- Garment processing and warping
- Photorealistic blending
- Quality validation

This service provides professional-grade virtual try-on results
that look natural and realistic.
"""

import logging
import asyncio
import tempfile
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import httpx

try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageFilter = None

from utils.image_utils import (
    base64_to_pil,
    pil_to_base64,
    download_image_to_temp,
    resize_image,
    cleanup_temp_file,
)

from services.ai.quality_validator import QualityValidator, ValidationResult
from services.tryon.tryon_service import TryOnService

logger = logging.getLogger(__name__)

# Thread pool for image processing
_executor = ThreadPoolExecutor(max_workers=4)


@dataclass
class TryOnResult:
    """Complete result of virtual try-on processing."""
    success: bool
    result_image: Optional[str] = None  # Base64 data URI
    quality_score: float = 0.0
    pose_detected: bool = False
    garment_category: str = "tops"
    validation: Optional[ValidationResult] = None
    processing_time_ms: float = 0.0
    warnings: List[str] = None
    error_message: Optional[str] = None
    body_dna_pose_reused: bool = False
    fit_preview_json: Optional[str] = None
    body_profile_json: Optional[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class AdvancedTryOnService:
    """
    Advanced virtual try-on service using AI-powered processing.
    
    Pipeline:
    1. Load and preprocess images
    2. Detect body pose and regions
    3. Process garment (background removal, warping)
    4. Blend garment onto person with lighting matching
    5. Validate result quality
    6. Return with quality metrics
    """

    def __init__(self):
        self._tryon = TryOnService()
        self._quality_validator = QualityValidator(quality_threshold=0.65)
        self._initialized = PIL_AVAILABLE
        if self._initialized:
            logger.info("AdvancedTryOnService initialized (unified TryOnService pipeline)")
        else:
            logger.warning("AdvancedTryOnService: PIL not available")

    async def process_tryon(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        options: Optional[Dict[str, Any]] = None
    ) -> TryOnResult:
        """
        Process a virtual try-on request with full AI pipeline.
        
        Args:
            user_image_base64: Base64-encoded person image
            garment_image_url: URL of the garment image
            garment_name: Name of the garment for category detection
            options: Optional processing options
                - fit_type: "tight", "regular", or "loose"
                - quality_threshold: Override quality threshold
                - validate: Whether to run validation (default True)
                - return_validation_details: Include detailed validation info
                
        Returns:
            TryOnResult with final image and quality metrics
        """
        import time
        start_time = time.time()

        if not self._initialized:
            logger.warning("Advanced service not fully initialized, using fallback")
            return await self._fallback_process(
                user_image_base64, garment_image_url, garment_name, start_time
            )

        options = options or {}
        validate = options.get("validate", True)
        return_validation_details = options.get("return_validation_details", False)

        try:
            merged = dict(options)
            core = await self._tryon.process_classical(
                user_image_base64,
                garment_image_url,
                garment_name,
                merged,
            )

            if not core.success or not core.result_image:
                # Propagate intentional failures (e.g. quality gate) — do not mask with naive overlay.
                if core.error_message:
                    processing_time = (time.time() - start_time) * 1000
                    return TryOnResult(
                        success=False,
                        error_message=core.error_message,
                        processing_time_ms=processing_time,
                        warnings=list(core.warnings or []),
                    )
                return await self._fallback_process(
                    user_image_base64, garment_image_url, garment_name, start_time
                )

            person_img = base64_to_pil(user_image_base64)
            person_img_for_processing = (
                resize_image(person_img, max_width=1024, max_height=1024).convert("RGB")
                if person_img
                else None
            )
            result_img = base64_to_pil(core.result_image) if core.result_image else None

            validation_result = None
            quality_score = core.quality_score

            if (
                validate
                and result_img is not None
                and person_img_for_processing is not None
            ):
                # Approximate mask from difference for validator
                import numpy as np
                import cv2

                a = np.array(result_img.convert("RGB"), dtype=np.float32)
                b = np.array(person_img_for_processing, dtype=np.float32)
                diff = np.mean(np.abs(a - b), axis=2)
                mask = (diff > 12).astype(np.uint8) * 255
                mask = cv2.GaussianBlur(mask, (21, 21), 0)
                validation_result = await self._quality_validator.validate(
                    result_img,
                    person_img_for_processing,
                    mask,
                )
                quality_score = validation_result.overall_score

            warnings = list(core.warnings)
            if validation_result:
                warnings.extend(validation_result.warnings)

            processing_time = (time.time() - start_time) * 1000

            return TryOnResult(
                success=True,
                result_image=core.result_image,
                quality_score=quality_score,
                pose_detected=core.pose_detected,
                garment_category=core.garment_category,
                validation=validation_result if return_validation_details else None,
                processing_time_ms=processing_time,
                warnings=warnings,
                body_dna_pose_reused=getattr(core, "body_dna_pose_reused", False),
                fit_preview_json=getattr(core, "fit_preview_json", None),
                body_profile_json=getattr(core, "body_profile_json", None),
            )

        except Exception as e:
            logger.error(f"Advanced try-on failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            return TryOnResult(
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
            )

    async def _fallback_process(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        start_time: float
    ) -> TryOnResult:
        """
        Fallback processing when AI modules are not available.
        Uses basic image overlay with feathering.
        """
        try:
            # Load images
            person_img = base64_to_pil(user_image_base64)
            if person_img is None:
                raise ValueError("Failed to decode person image")

            garment_path = await download_image_to_temp(garment_image_url, suffix=".png")
            garment_img = Image.open(garment_path)

            # Simple overlay
            result = await self._simple_overlay(person_img, garment_img, garment_name)

            processing_time = (time.time() - start_time) * 1000
            result_base64 = pil_to_base64(result, format="JPEG", quality=92) if result else None

            return TryOnResult(
                success=True,
                result_image=result_base64,
                quality_score=0.5,  # Lower score for fallback
                pose_detected=False,
                garment_category="tops",
                processing_time_ms=processing_time,
                warnings=["Used fallback processing (AI modules unavailable)"]
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return TryOnResult(
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    async def _simple_overlay(
        self,
        person_img: "Image.Image",
        garment_img: "Image.Image",
        garment_name: str
    ) -> "Image.Image":
        """Simple overlay fallback when AI modules are unavailable."""
        import numpy as np

        # Ensure modes
        if person_img.mode != "RGBA":
            person_img = person_img.convert("RGBA")
        if garment_img.mode != "RGBA":
            garment_img = garment_img.convert("RGBA")

        pw, ph = person_img.size
        gw, gh = garment_img.size

        # Simple category-based placement
        category = self._detect_category_simple(garment_name)

        # Scale garment
        scale = min(pw * 0.6 / gw, ph * 0.45 / gh)
        scale = min(scale, 1.0)
        new_w = int(gw * scale)
        new_h = int(gh * scale)

        garment_resized = garment_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Position based on category
        x = (pw - new_w) // 2
        if category == "tops":
            y = int(ph * 0.15)
        elif category == "bottoms":
            y = int(ph * 0.45)
        elif category == "dresses":
            y = int(ph * 0.12)
        else:
            y = int(ph * 0.2)

        # Create result
        result = person_img.copy()

        # Apply with feathered edges
        alpha = garment_resized.split()[3]
        alpha_blurred = alpha.filter(ImageFilter.GaussianBlur(radius=10))
        garment_resized.putalpha(alpha_blurred)

        result.paste(garment_resized, (x, y), garment_resized)

        return result.convert("RGB")

    def _detect_category_simple(self, name: str) -> str:
        """Simple category detection."""
        name_lower = name.lower()

        if any(kw in name_lower for kw in ["dress", "gown", "jumpsuit", "romper"]):
            return "dresses"
        if any(kw in name_lower for kw in ["pants", "jeans", "shorts", "skirt", "trousers"]):
            return "bottoms"
        if any(kw in name_lower for kw in ["jacket", "coat", "blazer", "hoodie"]):
            return "outerwear"

        return "tops"

    def health_check(self) -> Dict[str, Any]:
        """Return comprehensive health status."""
        out = dict(self._tryon.health())
        out["quality_validator"] = self._quality_validator.health_check()
        out["service"] = "advanced-virtual-try-on"
        out["pil_available"] = PIL_AVAILABLE
        return out
