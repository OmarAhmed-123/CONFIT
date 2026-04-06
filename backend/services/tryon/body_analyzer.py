"""
CONFIT Backend — Body Analyzer
==============================
Extracts body measurements from pose keypoints.

Provides:
- Body proportion analysis
- Size estimation
- Pose angle calculation
- Fit recommendations
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BodyMeasurements:
    """Estimated body measurements."""
    # Dimensions (in pixels, normalized to image)
    shoulder_width: float
    torso_length: float
    hip_width: float
    arm_length: float
    leg_length: float
    total_height: float
    
    # Proportions (ratios)
    shoulder_to_hip_ratio: float
    torso_to_leg_ratio: float
    
    # Pose information
    pose_angle: float  # degrees from frontal
    is_frontal: bool
    is_full_body: bool
    
    # Fit recommendations
    suggested_size: str
    fit_adjustments: List[str]


class BodyAnalyzer:
    """
    Analyzes body pose to extract measurements and proportions.
    
    Used for:
    - Garment scaling
    - Fit type adjustment
    - Size recommendation
    
    Usage:
        analyzer = BodyAnalyzer()
        measurements = analyzer.analyze(keypoints, image_shape)
    """
    
    # Standard body proportion ratios (for validation)
    PROPORTION_RANGES = {
        'shoulder_to_hip_ratio': (1.0, 1.8),  # Shoulders wider than hips
        'torso_to_leg_ratio': (0.8, 1.2),     # Roughly equal
        'arm_to_torso_ratio': (0.7, 1.0),     # Arms ~80% of torso
    }
    
    def __init__(self):
        # Size charts (simplified)
        self.size_chart = {
            'XS': {'shoulder': 0.12, 'hip': 0.10},
            'S': {'shoulder': 0.14, 'hip': 0.12},
            'M': {'shoulder': 0.16, 'hip': 0.14},
            'L': {'shoulder': 0.18, 'hip': 0.16},
            'XL': {'shoulder': 0.20, 'hip': 0.18},
        }
    
    def analyze(
        self,
        keypoints: List[Dict],
        image_shape: Tuple[int, int]
    ) -> Dict[str, Any]:
        """
        Analyze body from pose keypoints.
        
        Args:
            keypoints: List of 33 keypoint dicts (MediaPipe format)
            image_shape: (height, width) of image
            
        Returns:
            Dict with measurements and analysis
        """
        h, w = image_shape
        
        # Extract key landmark positions
        landmarks = self._extract_landmarks(keypoints, w, h)
        
        # Calculate measurements
        shoulder_width = self._calculate_shoulder_width(landmarks)
        torso_length = self._calculate_torso_length(landmarks)
        hip_width = self._calculate_hip_width(landmarks)
        arm_length = self._calculate_arm_length(landmarks)
        leg_length = self._calculate_leg_length(landmarks)
        total_height = self._calculate_total_height(landmarks)
        
        # Calculate proportions
        shoulder_to_hip = shoulder_width / max(hip_width, 1e-6)
        torso_to_leg = torso_length / max(leg_length, 1e-6)
        
        # Pose analysis
        pose_angle = self._estimate_pose_angle(landmarks)
        is_frontal = abs(pose_angle) < 25
        is_full_body = self._check_full_body(landmarks)
        
        # Size recommendation
        suggested_size = self._suggest_size(shoulder_width, hip_width, w)
        
        # Fit adjustments
        fit_adjustments = self._get_fit_adjustments(
            shoulder_to_hip, 
            torso_to_leg,
            pose_angle
        )
        
        return {
            'shoulder_width': shoulder_width,
            'torso_length': torso_length,
            'hip_width': hip_width,
            'arm_length': arm_length,
            'leg_length': leg_length,
            'total_height': total_height,
            'shoulder_to_hip_ratio': shoulder_to_hip,
            'torso_to_leg_ratio': torso_to_leg,
            'pose_angle': pose_angle,
            'is_frontal': is_frontal,
            'is_full_body': is_full_body,
            'suggested_size': suggested_size,
            'fit_adjustments': fit_adjustments,
            'landmarks': landmarks,
        }
    
    def _extract_landmarks(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> Dict[str, Dict[str, float]]:
        """Extract key landmarks in pixel coordinates."""
        if not keypoints:
            return {}
        
        # MediaPipe landmark indices
        indices = {
            'nose': 0,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_ankle': 27,
            'right_ankle': 28,
        }
        
        landmarks = {}
        for name, idx in indices.items():
            if idx < len(keypoints):
                kp = keypoints[idx]
                landmarks[name] = {
                    'x': kp['x'] * width,
                    'y': kp['y'] * height,
                    'visibility': kp.get('visibility', 0),
                }
        
        return landmarks
    
    def _calculate_shoulder_width(self, landmarks: Dict) -> float:
        """Calculate shoulder width in pixels."""
        left = landmarks.get('left_shoulder', {})
        right = landmarks.get('right_shoulder', {})
        
        if left.get('visibility', 0) < 0.3 or right.get('visibility', 0) < 0.3:
            return 0.0
        
        return abs(left['x'] - right['x'])
    
    def _calculate_torso_length(self, landmarks: Dict) -> float:
        """Calculate torso length (shoulder to hip)."""
        left_shoulder = landmarks.get('left_shoulder', {})
        right_shoulder = landmarks.get('right_shoulder', {})
        left_hip = landmarks.get('left_hip', {})
        right_hip = landmarks.get('right_hip', {})
        
        # Use average of left and right sides
        shoulder_y = (left_shoulder.get('y', 0) + right_shoulder.get('y', 0)) / 2
        hip_y = (left_hip.get('y', 0) + right_hip.get('y', 0)) / 2
        
        return abs(hip_y - shoulder_y)
    
    def _calculate_hip_width(self, landmarks: Dict) -> float:
        """Calculate hip width in pixels."""
        left = landmarks.get('left_hip', {})
        right = landmarks.get('right_hip', {})
        
        if left.get('visibility', 0) < 0.3 or right.get('visibility', 0) < 0.3:
            return 0.0
        
        return abs(left['x'] - right['x'])
    
    def _calculate_arm_length(self, landmarks: Dict) -> float:
        """Calculate arm length (shoulder to wrist)."""
        lengths = []
        
        for side in ['left', 'right']:
            shoulder = landmarks.get(f'{side}_shoulder', {})
            elbow = landmarks.get(f'{side}_elbow', {})
            wrist = landmarks.get(f'{side}_wrist', {})
            
            if shoulder.get('visibility', 0) > 0.3 and wrist.get('visibility', 0) > 0.3:
                # Calculate total arm length
                upper_arm = np.sqrt(
                    (elbow['x'] - shoulder['x'])**2 + 
                    (elbow['y'] - shoulder['y'])**2
                ) if elbow.get('visibility', 0) > 0.3 else 0
                
                forearm = np.sqrt(
                    (wrist['x'] - elbow['x'])**2 + 
                    (wrist['y'] - elbow['y'])**2
                ) if elbow.get('visibility', 0) > 0.3 else 0
                
                lengths.append(upper_arm + forearm)
        
        return max(lengths) if lengths else 0.0
    
    def _calculate_leg_length(self, landmarks: Dict) -> float:
        """Calculate leg length (hip to ankle)."""
        lengths = []
        
        for side in ['left', 'right']:
            hip = landmarks.get(f'{side}_hip', {})
            knee = landmarks.get(f'{side}_knee', {})
            ankle = landmarks.get(f'{side}_ankle', {})
            
            if hip.get('visibility', 0) > 0.3 and ankle.get('visibility', 0) > 0.3:
                # Calculate total leg length
                upper_leg = np.sqrt(
                    (knee['x'] - hip['x'])**2 + 
                    (knee['y'] - hip['y'])**2
                ) if knee.get('visibility', 0) > 0.3 else 0
                
                lower_leg = np.sqrt(
                    (ankle['x'] - knee['x'])**2 + 
                    (ankle['y'] - knee['y'])**2
                ) if knee.get('visibility', 0) > 0.3 else 0
                
                lengths.append(upper_leg + lower_leg)
        
        return max(lengths) if lengths else 0.0
    
    def _calculate_total_height(self, landmarks: Dict) -> float:
        """Calculate total body height in pixels."""
        nose = landmarks.get('nose', {})
        left_ankle = landmarks.get('left_ankle', {})
        right_ankle = landmarks.get('right_ankle', {})
        
        # Use nose as top
        top_y = nose.get('y', 0)
        
        # Use lowest ankle as bottom
        left_y = left_ankle.get('y', 0) if left_ankle.get('visibility', 0) > 0.3 else 0
        right_y = right_ankle.get('y', 0) if right_ankle.get('visibility', 0) > 0.3 else 0
        bottom_y = max(left_y, right_y)
        
        return abs(bottom_y - top_y) if bottom_y > 0 else 0.0
    
    def _estimate_pose_angle(self, landmarks: Dict) -> float:
        """
        Estimate body rotation angle.
        
        Returns angle in degrees:
        - 0 = frontal
        - Positive = rotated right
        - Negative = rotated left
        """
        left_shoulder = landmarks.get('left_shoulder', {})
        right_shoulder = landmarks.get('right_shoulder', {})
        
        if left_shoulder.get('visibility', 0) < 0.3 or right_shoulder.get('visibility', 0) < 0.3:
            return 0.0
        
        # Calculate shoulder line angle
        dx = right_shoulder['x'] - left_shoulder['x']
        dy = right_shoulder['y'] - left_shoulder['y']
        
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Normalize to -90 to 90 range
        # Frontal pose should have horizontal shoulders (angle ~0)
        return angle
    
    def _check_full_body(self, landmarks: Dict) -> bool:
        """Check if full body is visible in frame."""
        required = ['left_ankle', 'right_ankle', 'nose']
        
        for name in required:
            lm = landmarks.get(name, {})
            if lm.get('visibility', 0) < 0.3:
                return False
        
        return True
    
    def _suggest_size(
        self,
        shoulder_width: float,
        hip_width: float,
        image_width: int
    ) -> str:
        """Suggest clothing size based on measurements."""
        # Normalize to image width
        shoulder_norm = shoulder_width / image_width
        hip_norm = hip_width / image_width
        
        # Match against size chart
        best_size = 'M'
        best_diff = float('inf')
        
        for size, dims in self.size_chart.items():
            diff = abs(shoulder_norm - dims['shoulder']) + abs(hip_norm - dims['hip'])
            if diff < best_diff:
                best_diff = diff
                best_size = size
        
        return best_size
    
    def _get_fit_adjustments(
        self,
        shoulder_to_hip: float,
        torso_to_leg: float,
        pose_angle: float
    ) -> List[str]:
        """Generate fit adjustment recommendations."""
        adjustments = []
        
        # Body type adjustments
        if shoulder_to_hip > 1.5:
            adjustments.append("Broad shoulders - consider relaxed fit for tops")
        elif shoulder_to_hip < 1.1:
            adjustments.append("Narrow shoulders - fitted tops recommended")
        
        # Proportion adjustments
        if torso_to_leg > 1.2:
            adjustments.append("Long torso - size up for dresses")
        elif torso_to_leg < 0.8:
            adjustments.append("Short torso - consider cropped styles")
        
        # Pose adjustments
        if abs(pose_angle) > 30:
            adjustments.append("Non-frontal pose - garment may not align perfectly")
        
        return adjustments
    
    def get_body_region_bbox(
        self,
        landmarks: Dict,
        region: str,
        padding: float = 0.1
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get bounding box for a body region.
        
        Args:
            landmarks: Extracted landmarks
            region: 'torso', 'upper_body', 'lower_body', 'face'
            padding: Padding as fraction
            
        Returns:
            (x_min, y_min, x_max, y_max) or None
        """
        region_landmarks = {
            'torso': ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip'],
            'upper_body': ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow', 
                          'left_wrist', 'right_wrist', 'left_hip', 'right_hip'],
            'lower_body': ['left_hip', 'right_hip', 'left_knee', 'right_knee',
                          'left_ankle', 'right_ankle'],
            'face': ['nose'],
        }
        
        if region not in region_landmarks:
            return None
        
        points = []
        for name in region_landmarks[region]:
            lm = landmarks.get(name, {})
            if lm.get('visibility', 0) > 0.3:
                points.append((lm['x'], lm['y']))
        
        if not points:
            return None
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        # Add padding
        pad_x = (x_max - x_min) * padding
        pad_y = (y_max - y_min) * padding
        
        return (
            int(max(0, x_min - pad_x)),
            int(max(0, y_min - pad_y)),
            int(x_max + pad_x),
            int(y_max + pad_y)
        )
