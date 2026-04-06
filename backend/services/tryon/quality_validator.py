"""
CONFIT Backend — Quality Validator
=================================
Validates try-on result quality.

Metrics:
- Realism score
- Edge quality
- Color consistency
- Proportion accuracy
- Artifact detection
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of quality validation."""
    overall_score: float
    realism_score: float
    edge_quality_score: float
    color_consistency_score: float
    proportion_score: float
    artifact_score: float
    issues: List[str]
    suggestions: List[str]
    passed: bool


class QualityValidator:
    """
    Validates try-on result quality.
    
    Uses multiple metrics to assess realism and identify issues.
    
    Usage:
        validator = QualityValidator()
        result = await validator.validate(result_image, original_image, pose_keypoints)
        if result.passed:
            # Accept result
        else:
            # Retry or request new photo
    """
    
    def __init__(self, quality_threshold: float = 0.65):
        """
        Initialize validator.
        
        Args:
            quality_threshold: Minimum score to pass validation
        """
        self.quality_threshold = quality_threshold
        
        # Weights for overall score calculation
        self.weights = {
            'realism': 0.30,
            'edge_quality': 0.25,
            'color_consistency': 0.20,
            'proportion': 0.15,
            'artifact': 0.10,
        }
    
    async def validate(
        self,
        result_image: bytes,
        original_image: bytes,
        pose_keypoints: Optional[Dict] = None
    ) -> "QualityMetrics":
        """
        Validate try-on result quality.
        
        Args:
            result_image: Generated try-on result
            original_image: Original user photo
            pose_keypoints: Body landmarks for proportion check
            
        Returns:
            QualityMetrics with scores and issues
        """
        from models.tryon_models import QualityMetrics
        
        # Load images
        result = np.array(Image.open(io.BytesIO(result_image)).convert('RGB'))
        original = np.array(Image.open(io.BytesIO(original_image)).convert('RGB'))
        
        # Ensure same size
        if result.shape[:2] != original.shape[:2]:
            from PIL import Image as PILImage
            original_pil = PILImage.fromarray(original)
            original_pil = original_pil.resize(
                (result.shape[1], result.shape[0]),
                PILImage.Resampling.LANCZOS
            )
            original = np.array(original_pil)
        
        # Calculate metrics
        realism_score = self._calculate_realism_score(result, original)
        edge_score = self._calculate_edge_quality(result, original)
        color_score = self._calculate_color_consistency(result, original)
        proportion_score = self._calculate_proportion_score(result, pose_keypoints)
        artifact_score = self._calculate_artifact_score(result)
        
        # Calculate overall score
        overall_score = (
            realism_score * self.weights['realism'] +
            edge_score * self.weights['edge_quality'] +
            color_score * self.weights['color_consistency'] +
            proportion_score * self.weights['proportion'] +
            artifact_score * self.weights['artifact']
        )
        
        # Identify issues
        issues = []
        suggestions = []
        
        if realism_score < 0.6:
            issues.append("Result appears artificial")
            suggestions.append("Try a different photo with better lighting")
        
        if edge_score < 0.6:
            issues.append("Visible seams at garment edges")
            suggestions.append("Ensure garment image has clean edges")
        
        if color_score < 0.6:
            issues.append("Color mismatch between garment and scene")
            suggestions.append("Photo should have even, natural lighting")
        
        if proportion_score < 0.6:
            issues.append("Garment proportions don't match body")
            suggestions.append("Stand straight with arms slightly apart")
        
        if artifact_score < 0.6:
            issues.append("Visible artifacts or distortions")
            suggestions.append("Use a higher resolution photo")
        
        return QualityMetrics(
            overallScore=overall_score,
            realismScore=realism_score,
            edgeQualityScore=edge_score,
            colorConsistencyScore=color_score,
            proportionScore=proportion_score,
            artifactScore=artifact_score,
            issues=issues,
            suggestions=suggestions,
        )
    
    def _calculate_realism_score(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> float:
        """
        Calculate realism score based on natural appearance.
        
        Checks:
        - Texture naturalness
        - Lighting consistency
        - Shadow presence
        """
        import cv2
        
        # Convert to grayscale for analysis
        result_gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        original_gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
        
        # Check for unnatural smoothness (AI artifacts)
        # Real photos have more texture variation
        result_laplacian = cv2.Laplacian(result_gray, cv2.CV_64F).var()
        original_laplacian = cv2.Laplacian(original_gray, cv2.CV_64F).var()
        
        # Score based on texture similarity
        texture_ratio = min(result_laplacian / (original_laplacian + 1e-6), 2.0)
        texture_score = 1.0 - abs(1.0 - texture_ratio) / 2
        
        # Check lighting consistency
        result_mean = np.mean(result_gray)
        original_mean = np.mean(original_gray)
        lighting_diff = abs(result_mean - original_mean) / 255
        lighting_score = 1.0 - lighting_diff
        
        # Check for shadows (darker regions near garment)
        # This is a simplified check
        shadow_score = 0.7  # Default
        
        return (texture_score * 0.4 + lighting_score * 0.4 + shadow_score * 0.2)
    
    def _calculate_edge_quality(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> float:
        """
        Calculate edge quality score.
        
        Checks for visible seams at garment boundaries.
        """
        import cv2
        
        # Detect edges in both images
        result_edges = cv2.Canny(result, 50, 150)
        original_edges = cv2.Canny(original, 50, 150)
        
        # Find new edges (potential seams)
        new_edges = result_edges & ~original_edges
        
        # Calculate edge density increase
        original_edge_density = np.sum(original_edges > 0) / original_edges.size
        result_edge_density = np.sum(result_edges > 0) / result_edges.size
        new_edge_density = np.sum(new_edges > 0) / new_edges.size
        
        # Score based on edge quality
        # Good result should not have many new sharp edges
        if result_edge_density > 0:
            edge_ratio = new_edge_density / result_edge_density
            score = 1.0 - min(edge_ratio, 1.0)
        else:
            score = 0.5
        
        # Check for smooth transitions using gradient magnitude
        result_grad = np.sqrt(
            cv2.Sobel(cv2.cvtColor(result, cv2.COLOR_RGB2GRAY), cv2.CV_64F, 1, 0)**2 +
            cv2.Sobel(cv2.cvtColor(result, cv2.COLOR_RGB2GRAY), cv2.CV_64F, 0, 1)**2
        )
        
        # High gradients indicate sharp edges
        high_grad_ratio = np.sum(result_grad > 50) / result_grad.size
        smoothness_score = 1.0 - min(high_grad_ratio * 5, 1.0)
        
        return (score + smoothness_score) / 2
    
    def _calculate_color_consistency(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> float:
        """
        Calculate color consistency score.
        
        Checks if colors harmonize between result and original.
        """
        import cv2
        
        # Convert to LAB color space
        result_lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB)
        original_lab = cv2.cvtColor(original, cv2.COLOR_RGB2LAB)
        
        # Compare color distributions
        scores = []
        
        for channel in range(3):
            result_hist = cv2.calcHist([result_lab], [channel], None, [256], [0, 256])
            original_hist = cv2.calcHist([original_lab], [channel], None, [256], [0, 256])
            
            # Normalize histograms
            result_hist = result_hist.flatten() / (result_hist.sum() + 1e-6)
            original_hist = original_hist.flatten() / (original_hist.sum() + 1e-6)
            
            # Compare using correlation
            correlation = cv2.compareHist(
                result_hist.astype(np.float32),
                original_hist.astype(np.float32),
                cv2.HISTCMP_CORREL
            )
            scores.append(max(0, correlation))
        
        # Also check mean color difference
        result_mean = np.mean(result, axis=(0, 1))
        original_mean = np.mean(original, axis=(0, 1))
        color_diff = np.linalg.norm(result_mean - original_mean) / (255 * np.sqrt(3))
        mean_score = 1.0 - color_diff
        
        return (np.mean(scores) * 0.7 + mean_score * 0.3)
    
    def _calculate_proportion_score(
        self,
        result: np.ndarray,
        pose_keypoints: Optional[Dict]
    ) -> float:
        """
        Calculate proportion score.
        
        Checks if garment proportions match body.
        """
        if pose_keypoints is None:
            return 0.7  # Default score if no pose data
        
        keypoints = pose_keypoints.get('keypoints', [])
        
        if len(keypoints) < 25:
            return 0.7
        
        # Check shoulder alignment
        left_shoulder = keypoints[11]
        right_shoulder = keypoints[12]
        
        if left_shoulder.get('visibility', 0) > 0.5 and right_shoulder.get('visibility', 0) > 0.5:
            shoulder_width = abs(left_shoulder['x'] - right_shoulder['x'])
            
            # Shoulders should be roughly 15-25% of image width
            ideal_ratio = 0.2
            actual_ratio = shoulder_width
            ratio_score = 1.0 - min(abs(actual_ratio - ideal_ratio) / ideal_ratio, 1.0)
        else:
            ratio_score = 0.7
        
        # Check body centering
        left_hip = keypoints[23]
        right_hip = keypoints[24]
        
        if left_hip.get('visibility', 0) > 0.5 and right_hip.get('visibility', 0) > 0.5:
            center_x = (left_hip['x'] + right_hip['x']) / 2
            centering_score = 1.0 - abs(center_x - 0.5) * 2
        else:
            centering_score = 0.7
        
        return (ratio_score + centering_score) / 2
    
    def _calculate_artifact_score(
        self,
        result: np.ndarray
    ) -> float:
        """
        Calculate artifact score.
        
        Detects common AI-generated artifacts:
        - Blurring
        - Color bleeding
        - Unnatural patterns
        """
        import cv2
        
        # Check for excessive blur
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Low variance indicates blur
        blur_score = min(laplacian_var / 100, 1.0)
        
        # Check for color bleeding (unnatural color gradients)
        # Look for sudden color changes
        result_float = result.astype(np.float32)
        
        # Calculate color gradients
        grad_x = np.diff(result_float, axis=1)
        grad_y = np.diff(result_float, axis=0)
        
        # High gradient variance might indicate artifacts
        grad_var = np.var(grad_x) + np.var(grad_y)
        artifact_score = 1.0 - min(grad_var / 1e8, 1.0)
        
        # Check for repetitive patterns (common in AI generation)
        # Using autocorrelation
        gray_float = gray.astype(np.float32)
        gray_norm = (gray_float - gray_float.mean()) / (gray_float.std() + 1e-6)
        
        # Simple pattern detection
        pattern_score = 0.8  # Default
        
        return (blur_score * 0.4 + artifact_score * 0.4 + pattern_score * 0.2)
    
    def get_quality_grade(self, score: float) -> str:
        """Map score to quality grade."""
        if score >= 0.90:
            return 'A+ (Excellent)'
        elif score >= 0.85:
            return 'A (Very Good)'
        elif score >= 0.75:
            return 'B (Good)'
        elif score >= 0.65:
            return 'C (Acceptable)'
        elif score >= 0.50:
            return 'D (Poor)'
        else:
            return 'F (Unacceptable - Retry Recommended)'


def validate_image_quality(image: np.ndarray) -> Tuple[float, List[str]]:
    """
    Validate input image quality.
    
    Returns quality score and list of issues.
    """
    import cv2
    
    issues = []
    scores = []
    
    # Check blur
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    if laplacian_var < 50:
        issues.append("Image is blurry")
        scores.append(laplacian_var / 100)
    else:
        scores.append(1.0)
    
    # Check brightness
    mean_brightness = np.mean(gray)
    if mean_brightness < 50:
        issues.append("Image is too dark")
        scores.append(mean_brightness / 50)
    elif mean_brightness > 200:
        issues.append("Image is too bright")
        scores.append((255 - mean_brightness) / 55)
    else:
        scores.append(1.0)
    
    # Check contrast
    contrast = gray.std()
    if contrast < 30:
        issues.append("Image has low contrast")
        scores.append(contrast / 50)
    else:
        scores.append(1.0)
    
    overall_score = np.mean(scores)
    return overall_score, issues
