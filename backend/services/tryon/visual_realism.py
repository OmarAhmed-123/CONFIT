"""
CONFIT Backend — Visual Realism Engine
======================================
Advanced visual realism analysis for virtual try-on.

Provides:
- Body pose alignment scoring
- Garment deformation physics simulation
- Lighting adaptation analysis
- Depth consistency checking
- Fit confidence score calculation
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class AlignmentQuality(Enum):
    """Quality levels for pose alignment."""
    EXCELLENT = "excellent"  # > 0.9
    GOOD = "good"           # 0.75 - 0.9
    ACCEPTABLE = "acceptable"  # 0.6 - 0.75
    POOR = "poor"           # < 0.6


@dataclass
class PoseAlignmentScore:
    """Detailed pose alignment analysis."""
    overall_score: float
    quality_level: AlignmentQuality
    
    # Component scores
    frontal_alignment: float      # How frontal the pose is
    shoulder_alignment: float     # Shoulder levelness
    hip_alignment: float          # Hip levelness
    arm_visibility: float         # Arms visible and apart
    body_centering: float         # Body centered in frame
    distance_score: float         # Optimal distance from camera
    
    # Feedback
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class GarmentDeformationResult:
    """Result of garment deformation physics simulation."""
    success: bool
    warped_garment: Optional[bytes] = None
    
    # Deformation metrics
    stretch_ratio: float = 1.0        # How much garment stretched
    compression_ratio: float = 1.0    # How much garment compressed
    fold_count: int = 0               # Estimated fold lines
    tension_score: float = 0.0        # Fabric tension (0-1)
    
    # Physics simulation data
    control_points: List[Tuple[float, float]] = field(default_factory=list)
    deformation_map: Optional[np.ndarray] = None


@dataclass
class LightingAnalysis:
    """Lighting adaptation analysis result."""
    overall_score: float
    
    # Component scores
    direction_consistency: float     # Light direction matches scene
    intensity_match: float           # Intensity matches environment
    color_temperature: float         # Color temperature harmony
    shadow_presence: float           # Realistic shadows present
    highlight_quality: float         # Natural highlights
    
    # Estimated lighting
    light_direction: Tuple[float, float] = (0.0, -1.0)  # (x, y) unit vector
    estimated_temperature: int = 5500  # Kelvin
    
    issues: List[str] = field(default_factory=list)


@dataclass
class DepthConsistencyResult:
    """Depth consistency analysis for try-on result."""
    overall_score: float
    
    # Component scores
    occlusion_accuracy: float        # Garment occludes body correctly
    depth_ordering: float           # Correct depth layering
    silhouette_depth: float         # Silhouette depth consistency
    edge_depth_gradient: float      # Natural depth transitions
    
    # Depth map data
    depth_variance: float = 0.0
    edge_artifacts: int = 0


@dataclass
class FitConfidenceScore:
    """Comprehensive fit confidence calculation."""
    overall_confidence: float        # 0-1 score
    
    # Component scores
    size_match_score: float          # How well size matches body
    proportion_score: float          # Proportions look natural
    style_fit_score: float           # Style matches garment type
    comfort_indicator: float         # Appears comfortable
    
    # Fit classification
    fit_category: str = "regular"    # tight, regular, loose, oversized
    size_recommendation: str = ""    # Recommended size adjustment
    
    # Warnings
    fit_issues: List[str] = field(default_factory=list)
    adjustment_suggestions: List[str] = field(default_factory=list)


class VisualRealismEngine:
    """
    Advanced visual realism analysis for virtual try-on.
    
    Coordinates multiple analysis modules to ensure realistic results:
    - Pose alignment scoring
    - Garment deformation physics
    - Lighting adaptation
    - Depth consistency
    - Fit confidence calculation
    
    Usage:
        engine = VisualRealismEngine()
        
        # Analyze pose alignment
        alignment = engine.analyze_pose_alignment(keypoints, image_shape)
        
        # Calculate fit confidence
        fit_score = engine.calculate_fit_confidence(
            body_measurements, garment_metadata, alignment
        )
    """
    
    def __init__(self):
        # Alignment thresholds
        self.alignment_thresholds = {
            'excellent': 0.90,
            'good': 0.75,
            'acceptable': 0.60,
        }
        
        # Physics simulation parameters
        self.fabric_properties = {
            'cotton': {'stretch': 0.05, 'drape': 0.3, 'weight': 0.7},
            'silk': {'stretch': 0.02, 'drape': 0.8, 'weight': 0.3},
            'denim': {'stretch': 0.03, 'drape': 0.2, 'weight': 0.9},
            'wool': {'stretch': 0.04, 'drape': 0.4, 'weight': 0.6},
            'polyester': {'stretch': 0.08, 'drape': 0.5, 'weight': 0.5},
        }
    
    # ==========================================
    # Pose Alignment Analysis
    # ==========================================
    
    def analyze_pose_alignment(
        self,
        keypoints: List[Dict],
        image_shape: Tuple[int, int]
    ) -> PoseAlignmentScore:
        """
        Analyze how well the pose is aligned for try-on.
        
        Args:
            keypoints: MediaPipe format keypoints (33 points)
            image_shape: (height, width) of image
            
        Returns:
            PoseAlignmentScore with detailed analysis
        """
        h, w = image_shape
        issues = []
        suggestions = []
        
        # 1. Frontal alignment (nose visibility and position)
        frontal_score = self._calculate_frontal_alignment(keypoints)
        if frontal_score < 0.7:
            issues.append("Not facing camera directly")
            suggestions.append("Face the camera straight on for best results")
        
        # 2. Shoulder alignment (should be level)
        shoulder_score = self._calculate_shoulder_alignment(keypoints)
        if shoulder_score < 0.7:
            issues.append("Shoulders not level")
            suggestions.append("Relax your shoulders to be level")
        
        # 3. Hip alignment
        hip_score = self._calculate_hip_alignment(keypoints)
        if hip_score < 0.7:
            issues.append("Hips not level")
            suggestions.append("Stand with weight evenly distributed")
        
        # 4. Arm visibility and positioning
        arm_score = self._calculate_arm_visibility(keypoints)
        if arm_score < 0.6:
            issues.append("Arms not optimally positioned")
            suggestions.append("Keep arms slightly away from body")
        
        # 5. Body centering in frame
        centering_score = self._calculate_body_centering(keypoints, w)
        if centering_score < 0.7:
            issues.append("Body not centered in frame")
            suggestions.append("Position yourself in the center of the frame")
        
        # 6. Distance from camera
        distance_score = self._calculate_distance_score(keypoints, w, h)
        if distance_score < 0.6:
            if distance_score < 0.3:
                issues.append("Too far from camera")
                suggestions.append("Move closer to the camera")
            else:
                issues.append("Too close to camera")
                suggestions.append("Move back slightly for better framing")
        
        # Calculate overall score (weighted average)
        weights = {
            'frontal': 0.25,
            'shoulder': 0.15,
            'hip': 0.10,
            'arm': 0.15,
            'centering': 0.15,
            'distance': 0.20,
        }
        
        overall_score = (
            frontal_score * weights['frontal'] +
            shoulder_score * weights['shoulder'] +
            hip_score * weights['hip'] +
            arm_score * weights['arm'] +
            centering_score * weights['centering'] +
            distance_score * weights['distance']
        )
        
        # Determine quality level
        if overall_score >= self.alignment_thresholds['excellent']:
            quality_level = AlignmentQuality.EXCELLENT
        elif overall_score >= self.alignment_thresholds['good']:
            quality_level = AlignmentQuality.GOOD
        elif overall_score >= self.alignment_thresholds['acceptable']:
            quality_level = AlignmentQuality.ACCEPTABLE
        else:
            quality_level = AlignmentQuality.POOR
        
        return PoseAlignmentScore(
            overall_score=overall_score,
            quality_level=quality_level,
            frontal_alignment=frontal_score,
            shoulder_alignment=shoulder_score,
            hip_alignment=hip_score,
            arm_visibility=arm_score,
            body_centering=centering_score,
            distance_score=distance_score,
            issues=issues,
            suggestions=suggestions,
        )
    
    def _calculate_frontal_alignment(self, keypoints: List[Dict]) -> float:
        """Calculate how frontal the pose is."""
        if len(keypoints) < 13:
            return 0.5
        
        # Check nose visibility (should be high for frontal)
        nose = keypoints[0]
        nose_visibility = nose.get('visibility', 0)
        
        # Check ear symmetry (both ears visible = frontal)
        left_ear = keypoints[7] if len(keypoints) > 7 else {}
        right_ear = keypoints[8] if len(keypoints) > 8 else {}
        
        left_ear_vis = left_ear.get('visibility', 0)
        right_ear_vis = right_ear.get('visibility', 0)
        
        # Both ears visible with similar visibility indicates frontal
        ear_symmetry = 1.0 - abs(left_ear_vis - right_ear_vis)
        ear_visibility = (left_ear_vis + right_ear_vis) / 2
        
        # Shoulder width ratio (frontal = wider shoulders)
        left_shoulder = keypoints[11]
        right_shoulder = keypoints[12]
        
        shoulder_width = abs(left_shoulder.get('x', 0) - right_shoulder.get('x', 0))
        
        # Normal shoulder width for frontal pose is 0.15-0.35 of image width
        shoulder_score = 1.0 - min(abs(shoulder_width - 0.25) / 0.15, 1.0)
        
        return (
            nose_visibility * 0.3 +
            ear_symmetry * 0.2 +
            ear_visibility * 0.2 +
            shoulder_score * 0.3
        )
    
    def _calculate_shoulder_alignment(self, keypoints: List[Dict]) -> float:
        """Calculate shoulder levelness."""
        if len(keypoints) < 13:
            return 0.5
        
        left_shoulder = keypoints[11]
        right_shoulder = keypoints[12]
        
        if left_shoulder.get('visibility', 0) < 0.3 or right_shoulder.get('visibility', 0) < 0.3:
            return 0.5
        
        # Calculate Y difference (should be minimal for level shoulders)
        y_diff = abs(left_shoulder.get('y', 0) - right_shoulder.get('y', 0))
        
        # Level shoulders have Y diff < 0.05
        # Tilted shoulders have Y diff > 0.15
        score = max(0, 1.0 - y_diff / 0.15)
        
        return score
    
    def _calculate_hip_alignment(self, keypoints: List[Dict]) -> float:
        """Calculate hip levelness."""
        if len(keypoints) < 25:
            return 0.5
        
        left_hip = keypoints[23]
        right_hip = keypoints[24]
        
        if left_hip.get('visibility', 0) < 0.3 or right_hip.get('visibility', 0) < 0.3:
            return 0.5
        
        y_diff = abs(left_hip.get('y', 0) - right_hip.get('y', 0))
        score = max(0, 1.0 - y_diff / 0.15)
        
        return score
    
    def _calculate_arm_visibility(self, keypoints: List[Dict]) -> float:
        """Calculate arm visibility and positioning."""
        if len(keypoints) < 17:
            return 0.5
        
        # Check wrist visibility
        left_wrist = keypoints[15]
        right_wrist = keypoints[16]
        
        left_vis = left_wrist.get('visibility', 0)
        right_vis = right_wrist.get('visibility', 0)
        
        # Check arm separation from body
        left_hip = keypoints[23] if len(keypoints) > 23 else {}
        right_hip = keypoints[24] if len(keypoints) > 24 else {}
        
        # Arms should be slightly away from body
        left_separation = abs(left_wrist.get('x', 0) - left_hip.get('x', 0.5))
        right_separation = abs(right_wrist.get('x', 0) - right_hip.get('x', 0.5))
        
        # Optimal separation is 0.05-0.15 of image width
        left_sep_score = 1.0 - min(abs(left_separation - 0.1) / 0.1, 1.0)
        right_sep_score = 1.0 - min(abs(right_separation - 0.1) / 0.1, 1.0)
        
        visibility_score = (left_vis + right_vis) / 2
        separation_score = (left_sep_score + right_sep_score) / 2
        
        return visibility_score * 0.5 + separation_score * 0.5
    
    def _calculate_body_centering(self, keypoints: List[Dict], width: int) -> float:
        """Calculate how well body is centered in frame."""
        if len(keypoints) < 25:
            return 0.5
        
        # Use hip center as body center reference
        left_hip = keypoints[23]
        right_hip = keypoints[24]
        
        center_x = (left_hip.get('x', 0.5) + right_hip.get('x', 0.5)) / 2
        
        # Perfect center is 0.5
        deviation = abs(center_x - 0.5)
        
        # Centered body has deviation < 0.1
        score = max(0, 1.0 - deviation / 0.25)
        
        return score
    
    def _calculate_distance_score(self, keypoints: List[Dict], w: int, h: int) -> float:
        """Calculate optimal distance from camera."""
        if len(keypoints) < 29:
            return 0.5
        
        # Use body height ratio in frame
        nose = keypoints[0]
        left_ankle = keypoints[27]
        right_ankle = keypoints[28]
        
        nose_y = nose.get('y', 0)
        left_ankle_y = left_ankle.get('y', 0) if left_ankle.get('visibility', 0) > 0.3 else 1.0
        right_ankle_y = right_ankle.get('y', 0) if right_ankle.get('visibility', 0) > 0.3 else 1.0
        
        bottom_y = max(left_ankle_y, right_ankle_y)
        body_height = bottom_y - nose_y
        
        # Optimal body height is 0.7-0.9 of frame height
        if body_height < 0.5:
            # Too far
            score = body_height / 0.7
        elif body_height > 0.95:
            # Too close
            score = max(0, 1.0 - (body_height - 0.9) / 0.1)
        else:
            # Good distance
            score = 1.0 - min(abs(body_height - 0.8) / 0.15, 0.2)
        
        return score
    
    # ==========================================
    # Garment Deformation Physics
    # ==========================================
    
    def simulate_garment_deformation(
        self,
        garment_image: bytes,
        body_measurements: Dict,
        pose_keypoints: Dict,
        fabric_type: str = "cotton",
        garment_category: str = "tops"
    ) -> GarmentDeformationResult:
        """
        Simulate physics-based garment deformation.
        
        Applies realistic fabric physics including:
        - Stretch and compression
        - Drape and fold simulation
        - Tension distribution
        
        Args:
            garment_image: Raw garment image bytes
            body_measurements: Body dimensions from analyzer
            pose_keypoints: Body pose landmarks
            fabric_type: Type of fabric (cotton, silk, denim, etc.)
            garment_category: Category (tops, pants, dresses)
            
        Returns:
            GarmentDeformationResult with warped garment and physics data
        """
        try:
            # Load garment
            garment = Image.open(io.BytesIO(garment_image)).convert('RGBA')
            garment_array = np.array(garment)
            
            # Get fabric properties
            fabric_props = self.fabric_properties.get(fabric_type, self.fabric_properties['cotton'])
            
            # Generate control points for deformation
            control_points = self._generate_deformation_control_points(
                pose_keypoints, body_measurements, garment_category
            )
            
            # Calculate deformation map
            deformation_map = self._calculate_deformation_map(
                garment_array.shape[:2],
                control_points,
                fabric_props
            )
            
            # Apply deformation
            warped = self._apply_deformation(garment_array, deformation_map)
            
            # Calculate physics metrics
            stretch_ratio = self._calculate_stretch_ratio(deformation_map)
            compression_ratio = self._calculate_compression_ratio(deformation_map)
            fold_count = self._estimate_folds(deformation_map, fabric_props['drape'])
            tension_score = self._calculate_tension(deformation_map)
            
            # Convert to bytes
            warped_pil = Image.fromarray(warped)
            buffer = io.BytesIO()
            warped_pil.save(buffer, format='PNG')
            
            return GarmentDeformationResult(
                success=True,
                warped_garment=buffer.getvalue(),
                stretch_ratio=stretch_ratio,
                compression_ratio=compression_ratio,
                fold_count=fold_count,
                tension_score=tension_score,
                control_points=control_points,
                deformation_map=deformation_map,
            )
            
        except Exception as e:
            logger.error(f"Garment deformation failed: {e}")
            return GarmentDeformationResult(success=False)
    
    def _generate_deformation_control_points(
        self,
        pose_keypoints: Dict,
        body_measurements: Dict,
        garment_category: str
    ) -> List[Tuple[float, float]]:
        """Generate control points for TPS deformation."""
        keypoints = pose_keypoints.get('keypoints', [])
        
        if garment_category == 'tops':
            # Shoulder points, chest, waist
            points = []
            if len(keypoints) > 12:
                points.append((keypoints[11]['x'], keypoints[11]['y']))  # Left shoulder
                points.append((keypoints[12]['x'], keypoints[12]['y']))  # Right shoulder
            if len(keypoints) > 24:
                points.append((keypoints[23]['x'], keypoints[23]['y']))  # Left hip
                points.append((keypoints[24]['x'], keypoints[24]['y']))  # Right hip
            return points
            
        elif garment_category == 'pants':
            # Hip points, knees, ankles
            points = []
            if len(keypoints) > 28:
                points.append((keypoints[23]['x'], keypoints[23]['y']))  # Left hip
                points.append((keypoints[24]['x'], keypoints[24]['y']))  # Right hip
                points.append((keypoints[25]['x'], keypoints[25]['y']))  # Left knee
                points.append((keypoints[26]['x'], keypoints[26]['y']))  # Right knee
                points.append((keypoints[27]['x'], keypoints[27]['y']))  # Left ankle
                points.append((keypoints[28]['x'], keypoints[28]['y']))  # Right ankle
            return points
            
        else:  # dresses
            # Combine top and bottom
            return self._generate_deformation_control_points(
                pose_keypoints, body_measurements, 'tops'
            ) + self._generate_deformation_control_points(
                pose_keypoints, body_measurements, 'pants'
            )
    
    def _calculate_deformation_map(
        self,
        shape: Tuple[int, int],
        control_points: List[Tuple[float, float]],
        fabric_props: Dict
    ) -> np.ndarray:
        """Calculate deformation field based on control points and fabric physics."""
        h, w = shape
        
        # Create deformation map (2D vector field)
        deformation = np.zeros((h, w, 2), dtype=np.float32)
        
        if len(control_points) < 4:
            return deformation
        
        # Simple interpolation between control points
        # In production, would use proper TPS or mesh-based deformation
        
        # Calculate average displacement
        center_x = np.mean([p[0] for p in control_points])
        center_y = np.mean([p[1] for p in control_points])
        
        # Create radial deformation based on fabric drape
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        # Distance from center
        dx = x_coords / w - center_x
        dy = y_coords / h - center_y
        dist = np.sqrt(dx**2 + dy**2)
        
        # Apply drape effect (more deformation at edges)
        drape_factor = fabric_props['drape'] * dist
        
        # Stretch effect
        stretch_factor = fabric_props['stretch']
        
        deformation[:, :, 0] = dx * drape_factor * stretch_factor * w
        deformation[:, :, 1] = dy * drape_factor * h
        
        return deformation
    
    def _apply_deformation(
        self,
        image: np.ndarray,
        deformation_map: np.ndarray
    ) -> np.ndarray:
        """Apply deformation map to image using remapping."""
        import cv2
        
        h, w = image.shape[:2]
        
        # Create source coordinates
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        # Apply deformation
        map_x = (x_coords + deformation_map[:, :, 0]).astype(np.float32)
        map_y = (y_coords + deformation_map[:, :, 1]).astype(np.float32)
        
        # Clamp to valid range
        map_x = np.clip(map_x, 0, w - 1)
        map_y = np.clip(map_y, 0, h - 1)
        
        # Remap image
        warped = cv2.remap(
            image,
            map_x,
            map_y,
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )
        
        return warped
    
    def _calculate_stretch_ratio(self, deformation_map: np.ndarray) -> float:
        """Calculate average stretch ratio from deformation."""
        # Magnitude of deformation vectors
        magnitude = np.sqrt(
            deformation_map[:, :, 0]**2 + deformation_map[:, :, 1]**2
        )
        
        # Average stretch (normalized)
        avg_magnitude = np.mean(magnitude)
        
        # Convert to ratio (1.0 = no stretch)
        return 1.0 + avg_magnitude / 100
    
    def _calculate_compression_ratio(self, deformation_map: np.ndarray) -> float:
        """Calculate compression ratio from deformation."""
        # Areas with negative deformation indicate compression
        compression = np.sum(deformation_map[:, :, 0] < 0) / deformation_map.size
        
        return 1.0 - compression * 0.1
    
    def _estimate_folds(self, deformation_map: np.ndarray, drape: float) -> int:
        """Estimate number of fabric folds based on deformation variance."""
        # High variance in deformation indicates folds
        variance = np.var(deformation_map)
        
        # Estimate fold count based on variance and drape
        fold_estimate = int(variance * drape * 100)
        
        return min(fold_estimate, 10)  # Cap at 10
    
    def _calculate_tension(self, deformation_map: np.ndarray) -> float:
        """Calculate fabric tension score (0-1)."""
        # High deformation gradient indicates tension
        grad_x = np.gradient(deformation_map[:, :, 0])
        grad_y = np.gradient(deformation_map[:, :, 1])
        
        tension = np.mean(np.abs(grad_x)) + np.mean(np.abs(grad_y))
        
        return min(tension / 10, 1.0)
    
    # ==========================================
    # Lighting Adaptation Analysis
    # ==========================================
    
    def analyze_lighting_adaptation(
        self,
        result_image: bytes,
        original_image: bytes,
        pose_keypoints: Optional[Dict] = None
    ) -> LightingAnalysis:
        """
        Analyze lighting adaptation in try-on result.
        
        Checks:
        - Light direction consistency
        - Intensity matching
        - Color temperature harmony
        - Shadow presence
        - Highlight quality
        
        Args:
            result_image: Generated try-on result
            original_image: Original user photo
            pose_keypoints: Body landmarks for shadow estimation
            
        Returns:
            LightingAnalysis with detailed scores
        """
        import cv2
        
        # Load images
        result = np.array(Image.open(io.BytesIO(result_image)).convert('RGB'))
        original = np.array(Image.open(io.BytesIO(original_image)).convert('RGB'))
        
        issues = []
        
        # 1. Light direction consistency
        direction_score, light_direction = self._analyze_light_direction(result, original)
        if direction_score < 0.6:
            issues.append("Light direction mismatch detected")
        
        # 2. Intensity matching
        intensity_score = self._analyze_intensity_match(result, original)
        if intensity_score < 0.6:
            issues.append("Lighting intensity mismatch")
        
        # 3. Color temperature
        temp_score, estimated_temp = self._analyze_color_temperature(result, original)
        if temp_score < 0.6:
            issues.append("Color temperature inconsistency")
        
        # 4. Shadow presence
        shadow_score = self._analyze_shadow_presence(result, pose_keypoints)
        if shadow_score < 0.5:
            issues.append("Missing realistic shadows")
        
        # 5. Highlight quality
        highlight_score = self._analyze_highlights(result, original)
        if highlight_score < 0.6:
            issues.append("Unnatural highlights")
        
        # Calculate overall score
        overall_score = (
            direction_score * 0.25 +
            intensity_score * 0.20 +
            temp_score * 0.20 +
            shadow_score * 0.20 +
            highlight_score * 0.15
        )
        
        return LightingAnalysis(
            overall_score=overall_score,
            direction_consistency=direction_score,
            intensity_match=intensity_score,
            color_temperature=temp_score,
            shadow_presence=shadow_score,
            highlight_quality=highlight_score,
            light_direction=light_direction,
            estimated_temperature=estimated_temp,
            issues=issues,
        )
    
    def _analyze_light_direction(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> Tuple[float, Tuple[float, float]]:
        """Estimate light direction and check consistency."""
        import cv2
        
        # Convert to grayscale
        result_gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        original_gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
        
        # Calculate gradient (indicates light direction)
        result_grad_x = cv2.Sobel(result_gray, cv2.CV_64F, 1, 0)
        result_grad_y = cv2.Sobel(result_gray, cv2.CV_64F, 0, 1)
        
        original_grad_x = cv2.Sobel(original_gray, cv2.CV_64F, 1, 0)
        original_grad_y = cv2.Sobel(original_gray, cv2.CV_64F, 0, 1)
        
        # Average gradient direction
        result_dir_x = np.mean(result_grad_x)
        result_dir_y = np.mean(result_grad_y)
        
        original_dir_x = np.mean(original_grad_x)
        original_dir_y = np.mean(original_grad_y)
        
        # Normalize to unit vectors
        result_mag = np.sqrt(result_dir_x**2 + result_dir_y**2) + 1e-6
        original_mag = np.sqrt(original_dir_x**2 + original_dir_y**2) + 1e-6
        
        result_dir = (result_dir_x / result_mag, result_dir_y / result_mag)
        original_dir = (original_dir_x / original_mag, original_dir_y / original_mag)
        
        # Calculate direction similarity (dot product)
        dot = result_dir[0] * original_dir[0] + result_dir[1] * original_dir[1]
        score = (dot + 1) / 2  # Map from [-1, 1] to [0, 1]
        
        return score, result_dir
    
    def _analyze_intensity_match(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> float:
        """Check if lighting intensity matches between images."""
        # Calculate mean brightness
        result_brightness = np.mean(result)
        original_brightness = np.mean(original)
        
        # Calculate ratio
        ratio = result_brightness / (original_brightness + 1e-6)
        
        # Score based on how close to 1.0
        score = 1.0 - min(abs(1.0 - ratio), 1.0)
        
        return score
    
    def _analyze_color_temperature(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> Tuple[float, int]:
        """Estimate color temperature and check consistency."""
        # Simple temperature estimation based on R/B ratio
        result_rb = np.mean(result[:, :, 0]) / (np.mean(result[:, :, 2]) + 1e-6)
        original_rb = np.mean(original[:, :, 0]) / (np.mean(original[:, :, 2]) + 1e-6)
        
        # Map to approximate Kelvin (simplified)
        # Higher R/B = warmer (lower K), Lower R/B = cooler (higher K)
        estimated_temp = int(6500 - (result_rb - 1) * 2000)
        estimated_temp = max(3000, min(8000, estimated_temp))
        
        # Score based on ratio similarity
        ratio_diff = abs(result_rb - original_rb)
        score = max(0, 1.0 - ratio_diff / 0.5)
        
        return score, estimated_temp
    
    def _analyze_shadow_presence(
        self,
        result: np.ndarray,
        pose_keypoints: Optional[Dict]
    ) -> float:
        """Check for realistic shadow presence."""
        import cv2
        
        # Look for darker regions (potential shadows)
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        
        # Calculate local variance in brightness
        # Shadows create variance in lighting
        local_mean = cv2.blur(gray, (50, 50))
        variance = np.mean((gray.astype(float) - local_mean.astype(float))**2)
        
        # Some variance indicates shadows
        # Too much variance = harsh shadows, too little = flat
        optimal_variance = 500
        score = 1.0 - min(abs(variance - optimal_variance) / optimal_variance, 1.0)
        
        return score
    
    def _analyze_highlights(
        self,
        result: np.ndarray,
        original: np.ndarray
    ) -> float:
        """Analyze highlight quality."""
        # Check for specular highlights
        result_max = np.max(result, axis=2)
        original_max = np.max(original, axis=2)
        
        # Count bright pixels (potential highlights)
        result_highlights = np.sum(result_max > 240) / result_max.size
        original_highlights = np.sum(original_max > 240) / original_max.size
        
        # Similarity in highlight distribution
        diff = abs(result_highlights - original_highlights)
        score = 1.0 - min(diff * 10, 1.0)
        
        return score
    
    # ==========================================
    # Depth Consistency Analysis
    # ==========================================
    
    def analyze_depth_consistency(
        self,
        result_image: bytes,
        segmentation_masks: Dict,
        pose_keypoints: Dict
    ) -> DepthConsistencyResult:
        """
        Analyze depth consistency in try-on result.
        
        Checks:
        - Occlusion accuracy (garment occludes body correctly)
        - Depth ordering (correct layering)
        - Silhouette depth consistency
        - Edge depth gradients
        
        Args:
            result_image: Generated try-on result
            segmentation_masks: Person and region masks
            pose_keypoints: Body landmarks
            
        Returns:
            DepthConsistencyResult with scores
        """
        import cv2
        
        # Load image
        result = np.array(Image.open(io.BytesIO(result_image)).convert('RGB'))
        h, w = result.shape[:2]
        
        # 1. Occlusion accuracy
        occlusion_score = self._check_occlusion_accuracy(result, segmentation_masks)
        
        # 2. Depth ordering
        ordering_score = self._check_depth_ordering(result, segmentation_masks, pose_keypoints)
        
        # 3. Silhouette depth
        silhouette_score = self._check_silhouette_depth(result, segmentation_masks)
        
        # 4. Edge depth gradient
        edge_score, edge_artifacts = self._check_edge_depth_gradients(result, segmentation_masks)
        
        # Calculate depth variance
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        depth_variance = np.var(gray)
        
        # Overall score
        overall_score = (
            occlusion_score * 0.30 +
            ordering_score * 0.25 +
            silhouette_score * 0.25 +
            edge_score * 0.20
        )
        
        return DepthConsistencyResult(
            overall_score=overall_score,
            occlusion_accuracy=occlusion_score,
            depth_ordering=ordering_score,
            silhouette_depth=silhouette_score,
            edge_depth_gradient=edge_score,
            depth_variance=float(depth_variance),
            edge_artifacts=edge_artifacts,
        )
    
    def _check_occlusion_accuracy(
        self,
        result: np.ndarray,
        segmentation_masks: Dict
    ) -> float:
        """Check if garment correctly occludes body parts."""
        person_mask = segmentation_masks.get('person')
        
        if person_mask is None:
            return 0.7  # Default score
        
        # Check for visible seams at boundaries
        # Good occlusion = smooth transitions
        import cv2
        
        edges = cv2.Canny(person_mask.astype(np.uint8) * 255, 50, 150)
        
        # Check color variance at edges
        result_float = result.astype(float)
        edge_pixels = np.where(edges > 0)
        
        if len(edge_pixels[0]) < 10:
            return 0.7
        
        # Calculate color variance at edges
        edge_colors = result_float[edge_pixels[0], edge_pixels[1]]
        variance = np.var(edge_colors, axis=0)
        avg_variance = np.mean(variance)
        
        # Low variance at edges = good occlusion
        score = 1.0 - min(avg_variance / 5000, 1.0)
        
        return score
    
    def _check_depth_ordering(
        self,
        result: np.ndarray,
        segmentation_masks: Dict,
        pose_keypoints: Dict
    ) -> float:
        """Verify correct depth layering."""
        # Simplified check: garment should be in front of body
        # In production, would use depth estimation model
        
        # Check if garment region has higher contrast (indicates foreground)
        upper_mask = segmentation_masks.get('upper_body')
        
        if upper_mask is None:
            return 0.7
        
        import cv2
        
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        
        # Calculate contrast in garment region vs non-garment
        garment_region = gray[upper_mask > 0]
        non_garment_region = gray[upper_mask == 0]
        
        if len(garment_region) < 10 or len(non_garment_region) < 10:
            return 0.7
        
        garment_contrast = np.std(garment_region)
        non_garment_contrast = np.std(non_garment_region)
        
        # Garment should have slightly higher contrast (foreground)
        ratio = garment_contrast / (non_garment_contrast + 1e-6)
        
        # Good ratio is 0.8-1.2
        score = 1.0 - min(abs(ratio - 1.0) / 0.5, 1.0)
        
        return score
    
    def _check_silhouette_depth(
        self,
        result: np.ndarray,
        segmentation_masks: Dict
    ) -> float:
        """Check silhouette depth consistency."""
        person_mask = segmentation_masks.get('person')
        
        if person_mask is None:
            return 0.7
        
        import cv2
        
        # Check for depth consistency along silhouette
        edges = cv2.Canny(person_mask.astype(np.uint8) * 255, 50, 150)
        
        # Dilate edges to get surrounding region
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Check brightness gradient from edge
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        
        # Sample along edges
        edge_pixels = np.where(edges > 0)
        
        if len(edge_pixels[0]) < 10:
            return 0.7
        
        # Check for smooth depth transition
        gradients = []
        for i in range(0, len(edge_pixels[0]), max(1, len(edge_pixels[0]) // 100)):
            y, x = edge_pixels[0][i], edge_pixels[1][i]
            
            # Sample perpendicular to edge
            if y > 5 and y < gray.shape[0] - 5:
                gradient = abs(int(gray[y-5, x]) - int(gray[y+5, x]))
                gradients.append(gradient)
        
        if not gradients:
            return 0.7
        
        avg_gradient = np.mean(gradients)
        
        # Moderate gradients indicate good depth consistency
        score = 1.0 - min(avg_gradient / 100, 1.0)
        
        return score
    
    def _check_edge_depth_gradients(
        self,
        result: np.ndarray,
        segmentation_masks: Dict
    ) -> Tuple[float, int]:
        """Check for unnatural depth gradients at edges."""
        import cv2
        
        person_mask = segmentation_masks.get('person')
        
        if person_mask is None:
            return 0.7, 0
        
        # Find edges
        edges = cv2.Canny(person_mask.astype(np.uint8) * 255, 50, 150)
        
        # Check for sharp color transitions at edges
        result_float = result.astype(float)
        
        # Calculate gradient magnitude at edges
        grad_x = cv2.Sobel(cv2.cvtColor(result, cv2.COLOR_RGB2GRAY), cv2.CV_64F, 1, 0)
        grad_y = cv2.Sobel(cv2.cvtColor(result, cv2.COLOR_RGB2GRAY), cv2.CV_64F, 0, 1)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        
        # Check gradients at edges
        edge_gradients = grad_mag[edges > 0]
        
        if len(edge_gradients) < 10:
            return 0.7, 0
        
        # Count high gradient artifacts
        artifact_threshold = 100
        artifacts = int(np.sum(edge_gradients > artifact_threshold))
        
        # Score based on artifact count
        artifact_ratio = artifacts / len(edge_gradients)
        score = 1.0 - min(artifact_ratio * 5, 1.0)
        
        return score, artifacts
    
    # ==========================================
    # Fit Confidence Calculation
    # ==========================================
    
    def calculate_fit_confidence(
        self,
        body_measurements: Dict,
        garment_metadata: Dict,
        pose_alignment: PoseAlignmentScore,
        garment_category: str = "tops"
    ) -> FitConfidenceScore:
        """
        Calculate comprehensive fit confidence score.
        
        Considers:
        - Size matching
        - Proportion accuracy
        - Style fit
        - Comfort indicators
        
        Args:
            body_measurements: Body dimensions from analyzer
            garment_metadata: Garment size, style, fit type info
            pose_alignment: Pose alignment analysis
            garment_category: Category (tops, pants, dresses)
            
        Returns:
            FitConfidenceScore with detailed analysis
        """
        fit_issues = []
        suggestions = []
        
        # 1. Size match score
        size_score = self._calculate_size_match(body_measurements, garment_metadata)
        if size_score < 0.6:
            fit_issues.append("Size may not match body proportions")
            suggestions.append("Consider trying a different size")
        
        # 2. Proportion score
        proportion_score = self._calculate_proportion_match(
            body_measurements, garment_metadata, garment_category
        )
        if proportion_score < 0.6:
            fit_issues.append("Proportions may not align well")
        
        # 3. Style fit score
        style_score = self._calculate_style_fit(garment_metadata, pose_alignment)
        
        # 4. Comfort indicator
        comfort_score = self._calculate_comfort_indicator(
            body_measurements, garment_metadata
        )
        if comfort_score < 0.6:
            fit_issues.append("Fit may feel uncomfortable")
            suggestions.append("Consider a more relaxed fit")
        
        # Calculate overall confidence
        overall = (
            size_score * 0.35 +
            proportion_score * 0.25 +
            style_score * 0.20 +
            comfort_score * 0.20
        )
        
        # Determine fit category
        fit_category = self._determine_fit_category(garment_metadata)
        
        # Generate size recommendation
        size_rec = self._generate_size_recommendation(
            body_measurements, garment_metadata, size_score
        )
        
        return FitConfidenceScore(
            overall_confidence=overall,
            size_match_score=size_score,
            proportion_score=proportion_score,
            style_fit_score=style_score,
            comfort_indicator=comfort_score,
            fit_category=fit_category,
            size_recommendation=size_rec,
            fit_issues=fit_issues,
            adjustment_suggestions=suggestions,
        )
    
    def _calculate_size_match(
        self,
        body_measurements: Dict,
        garment_metadata: Dict
    ) -> float:
        """Calculate how well garment size matches body."""
        # Get body measurements
        shoulder_width = body_measurements.get('shoulder_width', 0)
        hip_width = body_measurements.get('hip_width', 0)
        
        # Get garment size info
        garment_size = garment_metadata.get('size', 'M')
        size_chart = garment_metadata.get('size_chart', {})
        
        if not size_chart:
            return 0.7  # Default if no chart
        
        # Get expected measurements for garment size
        expected = size_chart.get(garment_size, {})
        
        if not expected:
            return 0.7
        
        # Compare shoulder width
        expected_shoulder = expected.get('shoulder', 0.16)
        shoulder_ratio = shoulder_width / (expected_shoulder + 1e-6)
        
        # Good match is 0.9-1.1 ratio
        shoulder_score = 1.0 - min(abs(shoulder_ratio - 1.0) / 0.3, 1.0)
        
        # Compare hip width
        expected_hip = expected.get('hip', 0.14)
        hip_ratio = hip_width / (expected_hip + 1e-6)
        hip_score = 1.0 - min(abs(hip_ratio - 1.0) / 0.3, 1.0)
        
        return (shoulder_score + hip_score) / 2
    
    def _calculate_proportion_match(
        self,
        body_measurements: Dict,
        garment_metadata: Dict,
        category: str
    ) -> float:
        """Calculate proportion match score."""
        # Get body proportions
        shoulder_to_hip = body_measurements.get('shoulder_to_hip_ratio', 1.0)
        torso_to_leg = body_measurements.get('torso_to_leg_ratio', 1.0)
        
        # Get garment expected proportions
        garment_fit = garment_metadata.get('fit_type', 'regular')
        
        # Different fits have different expected proportions
        if garment_fit == 'tight':
            # Tight fit should match body proportions closely
            proportion_score = 1.0 - min(abs(shoulder_to_hip - 1.3) / 0.5, 1.0)
        elif garment_fit == 'loose':
            # Loose fit can accommodate more variation
            proportion_score = 0.9  # Generally good
        else:
            # Regular fit
            proportion_score = 1.0 - min(abs(shoulder_to_hip - 1.2) / 0.4, 1.0)
        
        return proportion_score
    
    def _calculate_style_fit(
        self,
        garment_metadata: Dict,
        pose_alignment: PoseAlignmentScore
    ) -> float:
        """Calculate style fit score."""
        # Style fit depends on how well pose supports the garment style
        
        garment_style = garment_metadata.get('style', 'casual')
        
        # Formal garments need better pose alignment
        if garment_style == 'formal':
            # Need excellent alignment for formal wear
            return pose_alignment.overall_score * 1.1  # Weight alignment more
        elif garment_style == 'athletic':
            # Athletic wear is more forgiving
            return 0.9
        else:
            # Casual wear
            return pose_alignment.overall_score
    
    def _calculate_comfort_indicator(
        self,
        body_measurements: Dict,
        garment_metadata: Dict
    ) -> float:
        """Calculate comfort indicator."""
        # Check if garment allows natural movement
        
        garment_fit = garment_metadata.get('fit_type', 'regular')
        fabric = garment_metadata.get('fabric', 'cotton')
        
        # Tight fit with non-stretchy fabric = less comfortable
        if garment_fit == 'tight':
            fabric_props = self.fabric_properties.get(fabric, {})
            stretch = fabric_props.get('stretch', 0.05)
            
            # Low stretch tight fit = lower comfort
            return 0.6 + stretch * 3
        
        # Loose fit = generally comfortable
        elif garment_fit == 'loose':
            return 0.9
        
        # Regular fit
        else:
            return 0.85
    
    def _determine_fit_category(self, garment_metadata: Dict) -> str:
        """Determine the fit category of the garment."""
        return garment_metadata.get('fit_type', 'regular')
    
    def _generate_size_recommendation(
        self,
        body_measurements: Dict,
        garment_metadata: Dict,
        size_score: float
    ) -> str:
        """Generate size recommendation based on fit analysis."""
        if size_score >= 0.8:
            return "Size looks good"
        elif size_score >= 0.6:
            return "Consider trying one size up or down"
        else:
            # Determine direction
            shoulder_width = body_measurements.get('shoulder_width', 0)
            garment_size = garment_metadata.get('size', 'M')
            
            if shoulder_width > 0.18:  # Wide shoulders
                return f"Consider sizing up from {garment_size}"
            else:
                return f"Consider sizing down from {garment_size}"
