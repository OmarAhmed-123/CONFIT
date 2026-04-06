"""
CONFIT Backend — Quality Validation Module
=========================================
Validates virtual try-on results for realism and quality.

Features:
- Anomaly detection (unnatural edges, color mismatches)
- Body proportion validation
- Garment fit verification
- Artifact detection
- Realism scoring
"""

import logging
import asyncio
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import cv2

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

logger = logging.getLogger(__name__)

# Thread pool for validation operations
_executor = ThreadPoolExecutor(max_workers=2)


@dataclass
class ValidationResult:
    """Result of quality validation."""
    is_valid: bool
    overall_score: float  # 0.0 to 1.0
    realism_score: float
    edge_quality_score: float
    color_consistency_score: float
    proportion_score: float
    artifact_score: float  # Lower is better
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class QualityValidator:
    """
    Validates virtual try-on results for photorealism and quality.
    Detects common AI-generated image artifacts and inconsistencies.
    """

    def __init__(self, quality_threshold: float = 0.7):
        """
        Initialize validator.
        
        Args:
            quality_threshold: Minimum acceptable quality score (0.0 to 1.0)
        """
        self._initialized = PIL_AVAILABLE
        self._quality_threshold = quality_threshold
        if self._initialized:
            logger.info(f"QualityValidator initialized (threshold={quality_threshold})")
        else:
            logger.warning("QualityValidator: PIL not available")

    def _check_edge_artifacts_sync(
        self,
        result_array: np.ndarray,
        mask: np.ndarray
    ) -> Tuple[float, List[str]]:
        """
        Check for edge artifacts in the blended region (synchronous).
        
        Args:
            result_array: Result image as numpy array
            mask: Blend mask
            
        Returns:
            Tuple of (score, list of issues found)
        """
        issues = []
        score = 1.0

        # Find edges of the blend region
        edges = cv2.Canny(mask, 50, 150)
        edge_pixels = np.where(edges > 0)

        if len(edge_pixels[0]) == 0:
            return score, issues

        # Check for hard edges (sharp color transitions)
        result_gray = cv2.cvtColor(result_array, cv2.COLOR_RGB2GRAY)
        grad_x = cv2.Sobel(result_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(result_gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Sample gradients at edge pixels
        edge_gradients = gradient_magnitude[edge_pixels]
        mean_edge_gradient = np.mean(edge_gradients)

        # High gradients at edges indicate hard edges (bad)
        if mean_edge_gradient > 50:
            issues.append("Hard edges detected at garment boundary")
            score -= min(0.3, mean_edge_gradient / 200)

        # Check for color discontinuity at edges
        result_array_float = result_array.astype(np.float32)

        # Sample colors on both sides of the edge
        for i in range(0, len(edge_pixels[0]), max(1, len(edge_pixels[0]) // 20)):
            y, x = edge_pixels[0][i], edge_pixels[1][i]

            # Get colors from inside and outside the blend region
            inside_color = None
            outside_color = None

            # Check neighboring pixels
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]:
                    if mask[ny, nx] > 128 and inside_color is None:
                        inside_color = result_array_float[ny, nx]
                    elif mask[ny, nx] <= 128 and outside_color is None:
                        outside_color = result_array_float[ny, nx]

            if inside_color is not None and outside_color is not None:
                color_diff = np.sqrt(np.sum((inside_color - outside_color) ** 2))
                if color_diff > 100:  # Significant color difference
                    score -= 0.02
                    if "Color discontinuity at edges" not in issues:
                        issues.append("Color discontinuity at edges")

        return max(0.0, score), issues

    def _check_color_consistency_sync(
        self,
        result_array: np.ndarray,
        original_array: np.ndarray,
        mask: np.ndarray
    ) -> Tuple[float, List[str]]:
        """
        Check color consistency between blended and original regions (synchronous).
        
        Args:
            result_array: Result image
            original_array: Original person image
            mask: Blend mask
            
        Returns:
            Tuple of (score, list of issues)
        """
        issues = []
        score = 1.0

        # Get surrounding region (non-blended area near blend region)
        dilated = cv2.dilate(mask, np.ones((50, 50), np.uint8))
        surrounding_mask = dilated - mask

        if np.sum(surrounding_mask) == 0:
            return score, issues

        # Compare color statistics
        blend_region = result_array[mask > 128]
        surrounding_region = result_array[surrounding_mask > 128]

        if len(blend_region) == 0 or len(surrounding_region) == 0:
            return score, issues

        # Compare mean colors
        blend_mean = np.mean(blend_region, axis=0)
        surrounding_mean = np.mean(surrounding_region, axis=0)

        color_diff = np.sqrt(np.sum((blend_mean - surrounding_mean) ** 2))
        if color_diff > 40:
            issues.append(f"Color mismatch between garment and surrounding area (diff={color_diff:.1f})")
            score -= min(0.3, color_diff / 100)

        # Compare color temperature
        blend_warmth = np.mean(blend_region[:, 0]) - np.mean(blend_region[:, 2])
        surrounding_warmth = np.mean(surrounding_region[:, 0]) - np.mean(surrounding_region[:, 2])

        warmth_diff = abs(blend_warmth - surrounding_warmth)
        if warmth_diff > 15:
            issues.append("Color temperature mismatch detected")
            score -= min(0.2, warmth_diff / 50)

        # Check for unnatural color saturation
        blend_hsv = cv2.cvtColor(
            cv2.cvtColor(blend_region.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV),
            cv2.COLOR_HSV2RGB
        ).reshape(-1, 3)

        # High saturation variance can indicate unnatural colors
        saturation = blend_hsv[:, 1]
        if np.std(saturation) > 80:
            issues.append("Unnatural color saturation detected")
            score -= 0.1

        return max(0.0, score), issues

    def _check_proportions_sync(
        self,
        result_array: np.ndarray,
        mask: np.ndarray,
        expected_region: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[float, List[str]]:
        """
        Check if garment proportions look natural (synchronous).
        
        Args:
            result_array: Result image
            mask: Blend mask
            expected_region: Expected bounding box (x, y, w, h)
            
        Returns:
            Tuple of (score, list of issues)
        """
        issues = []
        score = 1.0

        # Find garment bounding box
        coords = cv2.findNonZero(mask)
        if coords is None:
            return 0.0, ["No garment region detected"]

        x, y, w, h = cv2.boundingRect(coords)

        # Check aspect ratio
        aspect_ratio = w / (h + 1e-6)
        if aspect_ratio > 2.0 or aspect_ratio < 0.3:
            issues.append(f"Unusual garment aspect ratio: {aspect_ratio:.2f}")
            score -= 0.15

        # Check if garment is too small or too large relative to image
        img_area = result_array.shape[0] * result_array.shape[1]
        garment_area = np.sum(mask > 128)
        coverage = garment_area / img_area

        if coverage < 0.05:
            issues.append("Garment appears too small in the image")
            score -= 0.2
        elif coverage > 0.7:
            issues.append("Garment appears too large relative to image")
            score -= 0.15

        # Check position (should not be at extreme edges)
        img_h, img_w = result_array.shape[:2]
        center_x = x + w / 2
        center_y = y + h / 2

        # Garment should be roughly centered horizontally
        horizontal_offset = abs(center_x - img_w / 2) / img_w
        if horizontal_offset > 0.3:
            issues.append("Garment is not well-centered horizontally")
            score -= 0.1

        # Garment should be in upper-middle portion vertically (for tops)
        if center_y > img_h * 0.7:
            issues.append("Garment position seems too low")
            score -= 0.1

        return max(0.0, score), issues

    def _detect_artifacts_sync(
        self,
        result_array: np.ndarray,
        mask: np.ndarray
    ) -> Tuple[float, List[str]]:
        """
        Detect common AI artifacts in the result (synchronous).
        
        Args:
            result_array: Result image
            mask: Blend mask
            
        Returns:
            Tuple of (artifact_score, list of detected artifacts)
        """
        artifacts = []
        score = 1.0  # Higher is better (no artifacts)

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(result_array, cv2.COLOR_RGB2GRAY)

        # 1. Check for blurring artifacts
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            artifacts.append("Image appears blurry")
            score -= 0.2
        elif laplacian_var < 200:
            artifacts.append("Image may have slight blurring")
            score -= 0.1

        # 2. Check for compression artifacts (blockiness)
        # Look for 8x8 block patterns
        block_size = 8
        block_vars = []
        for i in range(0, gray.shape[0] - block_size, block_size):
            for j in range(0, gray.shape[1] - block_size, block_size):
                block = gray[i:i+block_size, j:j+block_size]
                block_vars.append(np.var(block))

        if len(block_vars) > 0 and np.std(block_vars) > 500:
            artifacts.append("Possible compression artifacts detected")
            score -= 0.1

        # 3. Check for unnatural smoothness in blend region
        blend_gray = gray[mask > 128]
        if len(blend_gray) > 0:
            blend_smoothness = np.std(blend_gray)
            if blend_smoothness < 20:
                artifacts.append("Garment region appears unnaturally smooth")
                score -= 0.15

        # 4. Check for color banding
        result_hsv = cv2.cvtColor(result_array, cv2.COLOR_RGB2HSV)
        hue = result_hsv[:, :, 0][mask > 128]

        if len(hue) > 0:
            # Count unique hue values
            unique_hues = len(np.unique(hue))
            if unique_hues < 10:
                artifacts.append("Color banding detected")
                score -= 0.1

        # 5. Check for ghosting (double edges)
        edges = cv2.Canny(gray, 50, 150)
        dilated_edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
        edge_density = np.sum(dilated_edges > 0) / (gray.shape[0] * gray.shape[1])

        if edge_density > 0.15:
            artifacts.append("Possible ghosting or double edges detected")
            score -= 0.1

        return max(0.0, score), artifacts

    def _calculate_realism_score_sync(
        self,
        result_array: np.ndarray,
        original_array: np.ndarray,
        mask: np.ndarray
    ) -> float:
        """
        Calculate overall realism score (synchronous).
        
        Args:
            result_array: Result image
            original_array: Original person image
            mask: Blend mask
            
        Returns:
            Realism score (0.0 to 1.0)
        """
        score = 1.0

        # 1. Texture consistency
        result_gray = cv2.cvtColor(result_array, cv2.COLOR_RGB2GRAY)
        original_gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)

        # Compare texture in surrounding area vs blend area
        dilated = cv2.dilate(mask, np.ones((30, 30), np.uint8))
        surrounding_mask = dilated - mask

        if np.sum(surrounding_mask) > 0 and np.sum(mask > 128) > 0:
            # Calculate texture using Local Binary Patterns approximation
            def calc_texture_variance(gray_img, region_mask):
                region = gray_img[region_mask > 128]
                if len(region) == 0:
                    return 0
                # Use gradient-based texture measure
                grad_x = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(gray_img, cv2.CV_64F, 0, 1, ksize=3)
                gradient_mag = np.sqrt(grad_x**2 + grad_y**2)
                return np.mean(gradient_mag[region_mask > 128])

            blend_texture = calc_texture_variance(result_gray, mask)
            surrounding_texture = calc_texture_variance(result_gray, surrounding_mask)

            # Textures should be somewhat similar
            texture_diff = abs(blend_texture - surrounding_texture)
            if texture_diff > 20:
                score -= min(0.2, texture_diff / 100)

        # 2. Lighting consistency
        blend_region = result_array[mask > 128]
        surrounding_region = result_array[surrounding_mask > 128]

        if len(blend_region) > 0 and len(surrounding_region) > 0:
            # Compare brightness
            blend_brightness = np.mean(blend_region)
            surrounding_brightness = np.mean(surrounding_region)

            brightness_diff = abs(blend_brightness - surrounding_brightness) / 255
            if brightness_diff > 0.2:
                score -= min(0.15, brightness_diff)

        # 3. Edge smoothness
        edges = cv2.Canny(mask, 50, 150)
        edge_pixels = np.where(edges > 0)

        if len(edge_pixels[0]) > 0:
            # Check gradient smoothness at edges
            grad_x = cv2.Sobel(result_gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(result_gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_mag = np.sqrt(grad_x**2 + grad_y**2)

            edge_gradients = gradient_mag[edge_pixels]
            gradient_variance = np.var(edge_gradients)

            if gradient_variance > 500:
                score -= min(0.15, gradient_variance / 2000)

        return max(0.0, min(1.0, score))

    async def validate(
        self,
        result_image: "Image.Image",
        original_image: "Image.Image",
        blend_mask: np.ndarray
    ) -> ValidationResult:
        """
        Validate the virtual try-on result.
        
        Args:
            result_image: Final blended image
            original_image: Original person image
            blend_mask: Mask of the blended region
            
        Returns:
            ValidationResult with scores and issues
        """
        if not self._initialized:
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                realism_score=0.0,
                edge_quality_score=0.0,
                color_consistency_score=0.0,
                proportion_score=0.0,
                artifact_score=0.0,
                error_message="PIL not available"
            )

        loop = asyncio.get_event_loop()

        try:
            # Convert to numpy arrays
            if result_image.mode != "RGB":
                result_image = result_image.convert("RGB")
            if original_image.mode != "RGB":
                original_image = original_image.convert("RGB")

            result_array = np.array(result_image)
            original_array = np.array(original_image)

            # Run all checks in parallel
            edge_task = loop.run_in_executor(
                _executor, self._check_edge_artifacts_sync, result_array, blend_mask
            )
            color_task = loop.run_in_executor(
                _executor, self._check_color_consistency_sync, result_array, original_array, blend_mask
            )
            proportion_task = loop.run_in_executor(
                _executor, self._check_proportions_sync, result_array, blend_mask
            )
            artifact_task = loop.run_in_executor(
                _executor, self._detect_artifacts_sync, result_array, blend_mask
            )
            realism_task = loop.run_in_executor(
                _executor, self._calculate_realism_score_sync, result_array, original_array, blend_mask
            )

            # Wait for all checks
            (edge_score, edge_issues), \
            (color_score, color_issues), \
            (proportion_score, proportion_issues), \
            (artifact_score, artifact_issues), \
            realism_score = await asyncio.gather(
                edge_task, color_task, proportion_task, artifact_task, realism_task
            )

            # Combine all issues
            all_issues = edge_issues + color_issues + proportion_issues + artifact_issues

            # Calculate overall score
            overall_score = (
                edge_score * 0.25 +
                color_score * 0.25 +
                proportion_score * 0.20 +
                artifact_score * 0.15 +
                realism_score * 0.15
            )

            # Generate suggestions
            suggestions = []
            if edge_score < 0.7:
                suggestions.append("Consider increasing edge feathering for smoother transitions")
            if color_score < 0.7:
                suggestions.append("Adjust lighting/color matching for better integration")
            if proportion_score < 0.7:
                suggestions.append("Review garment positioning and sizing")
            if artifact_score < 0.7:
                suggestions.append("Check source image quality and consider re-processing")

            # Generate warnings for borderline cases
            warnings = []
            if 0.6 <= overall_score < self._quality_threshold:
                warnings.append("Result quality is below optimal threshold")
            if len(all_issues) > 3:
                warnings.append("Multiple quality issues detected")

            return ValidationResult(
                is_valid=overall_score >= self._quality_threshold,
                overall_score=overall_score,
                realism_score=realism_score,
                edge_quality_score=edge_score,
                color_consistency_score=color_score,
                proportion_score=proportion_score,
                artifact_score=artifact_score,
                issues=all_issues,
                warnings=warnings,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                realism_score=0.0,
                edge_quality_score=0.0,
                color_consistency_score=0.0,
                proportion_score=0.0,
                artifact_score=0.0,
                error_message=str(e)
            )

    def health_check(self) -> Dict[str, Any]:
        """Return health status."""
        return {
            "status": "ok" if self._initialized else "degraded",
            "service": "quality-validator",
            "pil_available": PIL_AVAILABLE,
            "opencv_available": True,
            "quality_threshold": self._quality_threshold
        }
