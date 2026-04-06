"""
CONFIT Backend — AR Virtual Try-On Service
==========================================
Real-time AR try-on processing for WebAR.

Features:
- Real-time pose detection using MediaPipe
- Body segmentation for garment overlay
- Privacy-first processing (no permanent storage)
- Mobile-optimized performance

Technology:
- TensorFlow/ MediaPipe for pose detection
- OpenCV for image processing
- WebSocket for real-time streaming
"""

import io
import logging
import base64
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ARProcessingMode(Enum):
    """AR processing modes."""
    REALTIME = "realtime"  # Optimized for speed
    QUALITY = "quality"    # Optimized for quality
    BALANCED = "balanced"  # Balance between speed and quality


@dataclass
class ARPoseResult:
    """Result of AR pose detection."""
    keypoints: List[Dict[str, float]]
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    timestamp: float
    is_valid: bool
    rotation_angle: float = 0.0
    body_segment: Optional[np.ndarray] = None


@dataclass
class ARGarmentOverlay:
    """Garment overlay result."""
    overlay_image: bytes
    mask: np.ndarray
    position: Tuple[int, int]
    scale: float
    rotation: float
    blend_mode: str
    opacity: float


@dataclass
class ARSessionState:
    """State of an AR try-on session."""
    session_id: str
    user_id: Optional[str]
    garment_id: str
    garment_image: Optional[bytes] = None
    garment_mask: Optional[np.ndarray] = None
    garment_category: str = "tops"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    frames_processed: int = 0
    last_pose: Optional[ARPoseResult] = None
    is_active: bool = True
    # Privacy tracking
    images_stored: int = 0
    images_deleted: int = 0


class ARTryOnService:
    """
    Real-time AR Virtual Try-On Service.
    
    Provides WebAR-compatible try-on with:
    - Real-time pose detection
    - Dynamic garment overlay
    - Movement tracking
    - Privacy-first processing
    
    Usage:
        service = ARTryOnService()
        session = await service.create_session(garment_id, garment_image)
        
        # Process each frame
        result = await service.process_frame(
            session.session_id, 
            frame_base64
        )
        
        # Cleanup when done
        await service.end_session(session.session_id)
    """
    
    # Performance settings
    MAX_RESOLUTION = (640, 480)  # Mobile-optimized
    TARGET_FPS = 30
    POSE_SMOOTHING_FACTOR = 0.3
    
    # Garment categories
    UPPER_BODY = ["tops", "shirt", "blouse", "jacket", "sweater", "hoodie"]
    LOWER_BODY = ["pants", "jeans", "shorts", "skirt", "trousers"]
    FULL_BODY = ["dress", "jumpsuit", "romper"]
    
    def __init__(
        self,
        mode: ARProcessingMode = ARProcessingMode.BALANCED,
        use_gpu: bool = True
    ):
        """
        Initialize AR Try-On Service.
        
        Args:
            mode: Processing mode (realtime/quality/balanced)
            use_gpu: Whether to use GPU acceleration
        """
        self.mode = mode
        self.use_gpu = use_gpu
        
        # Lazy-loaded components
        self._pose_detector = None
        self._segmenter = None
        self._garment_processor = None
        
        # Active sessions
        self._sessions: Dict[str, ARSessionState] = {}
        
        # Performance metrics
        self._metrics = {
            "total_frames_processed": 0,
            "average_processing_time_ms": 0.0,
            "sessions_created": 0,
        }
        
        # Pose smoothing state
        self._pose_history: Dict[str, List[ARPoseResult]] = {}
        
        logger.info(f"AR Try-On Service initialized with mode={mode.value}")
    
    # ==========================================
    # Component Initialization
    # ==========================================
    
    @property
    def pose_detector(self):
        """Lazy load pose detector."""
        if self._pose_detector is None:
            from services.tryon.pose_detector import PoseDetector
            self._pose_detector = PoseDetector(
                model_complexity=1 if self.mode == ARProcessingMode.REALTIME else 2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        return self._pose_detector
    
    @property
    def segmenter(self):
        """Lazy load body segmenter."""
        if self._segmenter is None:
            from services.tryon.segmenter import BodySegmenter
            self._segmenter = BodySegmenter(model_type="sam")
        return self._segmenter
    
    # ==========================================
    # Session Management
    # ==========================================
    
    async def create_session(
        self,
        garment_id: str,
        garment_image: bytes,
        user_id: Optional[str] = None,
        garment_category: Optional[str] = None
    ) -> ARSessionState:
        """
        Create a new AR try-on session.
        
        Args:
            garment_id: Garment identifier
            garment_image: Garment image bytes
            user_id: Optional user ID
            garment_category: Optional category override
            
        Returns:
            ARSessionState with session details
        """
        import uuid
        
        session_id = f"ar_{uuid.uuid4().hex[:12]}"
        
        # Detect category if not provided
        if garment_category is None:
            garment_category = self._detect_garment_category(garment_id)
        
        # Process garment image for overlay
        processed_garment, garment_mask = await self._prepare_garment(
            garment_image, 
            garment_category
        )
        
        session = ARSessionState(
            session_id=session_id,
            user_id=user_id,
            garment_id=garment_id,
            garment_image=processed_garment,
            garment_mask=garment_mask,
            garment_category=garment_category
        )
        
        self._sessions[session_id] = session
        self._pose_history[session_id] = []
        
        self._metrics["sessions_created"] += 1
        
        logger.info(f"Created AR session {session_id} for garment {garment_id}")
        
        return session
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End an AR session and cleanup resources.
        
        Privacy: Ensures all temporary data is deleted.
        
        Args:
            session_id: Session to end
            
        Returns:
            Session summary with privacy report
        """
        session = self._sessions.get(session_id)
        
        if session is None:
            return {"success": False, "error": "Session not found"}
        
        # Mark session as inactive
        session.is_active = False
        
        # Clear pose history
        if session_id in self._pose_history:
            del self._pose_history[session_id]
        
        # Generate privacy report
        privacy_report = {
            "session_id": session_id,
            "frames_processed": session.frames_processed,
            "images_stored": session.images_stored,
            "images_deleted": session.images_deleted,
            "data_retention": "0 seconds (no permanent storage)",
            "gdpr_compliant": True
        }
        
        # Remove session
        del self._sessions[session_id]
        
        logger.info(f"Ended AR session {session_id}, processed {session.frames_processed} frames")
        
        return {
            "success": True,
            "privacy_report": privacy_report
        }
    
    # ==========================================
    # Frame Processing
    # ==========================================
    
    async def process_frame(
        self,
        session_id: str,
        frame_base64: str,
        return_overlay: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single video frame for AR try-on.
        
        Real-time processing pipeline:
        1. Decode frame
        2. Detect pose
        3. Smooth pose (temporal filtering)
        4. Generate garment overlay
        5. Composite result
        6. Return as base64
        
        Args:
            session_id: Active session ID
            frame_base64: Base64-encoded frame
            return_overlay: Whether to return composited image
            
        Returns:
            Dict with:
            - pose: Detected pose keypoints
            - overlay_image: Composited result (if return_overlay)
            - confidence: Detection confidence
            - processing_time_ms: Processing time
        """
        start_time = time.time()
        
        session = self._sessions.get(session_id)
        if session is None or not session.is_active:
            return {
                "success": False,
                "error": "Session not found or inactive"
            }
        
        try:
            # Decode frame
            frame_bytes = self._decode_base64(frame_base64)
            frame_image = Image.open(io.BytesIO(frame_bytes)).convert('RGB')
            
            # Resize for performance
            frame_array = self._resize_frame(np.array(frame_image))
            
            # Detect pose
            pose_result = await self._detect_pose(frame_array)
            
            # Apply temporal smoothing
            smoothed_pose = self._smooth_pose(session_id, pose_result)
            
            # Update session state
            session.last_pose = smoothed_pose
            session.frames_processed += 1
            
            result = {
                "success": True,
                "pose": {
                    "keypoints": smoothed_pose.keypoints,
                    "bounding_box": smoothed_pose.bounding_box,
                    "confidence": smoothed_pose.confidence,
                    "rotation_angle": smoothed_pose.rotation_angle,
                    "is_valid": smoothed_pose.is_valid
                },
                "frame_number": session.frames_processed
            }
            
            # Generate overlay if requested and pose is valid
            if return_overlay and smoothed_pose.is_valid:
                overlay = await self._generate_overlay(
                    frame_array,
                    smoothed_pose,
                    session
                )
                
                if overlay:
                    result["overlay_image"] = self._encode_overlay(overlay)
            
            # Track processing time
            processing_time = (time.time() - start_time) * 1000
            result["processing_time_ms"] = processing_time
            
            # Update metrics
            self._update_metrics(processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _detect_pose(self, frame: np.ndarray) -> ARPoseResult:
        """
        Detect pose in frame using MediaPipe.
        
        Args:
            frame: RGB frame array
            
        Returns:
            ARPoseResult with keypoints and metadata
        """
        h, w = frame.shape[:2]
        
        # Run pose detection
        pose_data = await self.pose_detector.detect(frame.tobytes())
        
        if not pose_data.get('keypoints'):
            return ARPoseResult(
                keypoints=[],
                bounding_box=(0, 0, w, h),
                confidence=0.0,
                timestamp=time.time(),
                is_valid=False
            )
        
        keypoints = pose_data['keypoints']
        
        # Calculate bounding box from keypoints
        bbox = self.pose_detector.get_body_bbox(keypoints, (h, w))
        
        # Estimate rotation angle
        rotation = self.pose_detector.estimate_pose_angle(keypoints)
        
        return ARPoseResult(
            keypoints=keypoints,
            bounding_box=bbox,
            confidence=pose_data.get('score', 0.0),
            timestamp=time.time(),
            is_valid=pose_data.get('is_valid', False),
            rotation_angle=rotation
        )
    
    def _smooth_pose(
        self,
        session_id: str,
        current_pose: ARPoseResult
    ) -> ARPoseResult:
        """
        Apply temporal smoothing to pose for stable tracking.
        
        Uses exponential moving average for smooth transitions.
        """
        history = self._pose_history.get(session_id, [])
        
        if not history or not current_pose.is_valid:
            history.append(current_pose)
            self._pose_history[session_id] = history[-5:]  # Keep last 5
            return current_pose
        
        # Get last valid pose
        last_pose = history[-1]
        
        if not last_pose.is_valid:
            history.append(current_pose)
            self._pose_history[session_id] = history[-5:]
            return current_pose
        
        # Smooth keypoints
        smoothed_keypoints = []
        for i, kp in enumerate(current_pose.keypoints):
            if i < len(last_pose.keypoints):
                last_kp = last_pose.keypoints[i]
                
                # Exponential moving average
                smoothed_x = (1 - self.POSE_SMOOTHING_FACTOR) * last_kp['x'] + \
                             self.POSE_SMOOTHING_FACTOR * kp['x']
                smoothed_y = (1 - self.POSE_SMOOTHING_FACTOR) * last_kp['y'] + \
                             self.POSE_SMOOTHING_FACTOR * kp['y']
                
                smoothed_keypoints.append({
                    'x': smoothed_x,
                    'y': smoothed_y,
                    'z': kp.get('z', 0),
                    'visibility': kp.get('visibility', 1.0),
                    'name': kp.get('name', f'keypoint_{i}')
                })
            else:
                smoothed_keypoints.append(kp)
        
        # Smooth rotation
        smoothed_rotation = (1 - self.POSE_SMOOTHING_FACTOR) * last_pose.rotation_angle + \
                           self.POSE_SMOOTHING_FACTOR * current_pose.rotation_angle
        
        smoothed = ARPoseResult(
            keypoints=smoothed_keypoints,
            bounding_box=current_pose.bounding_box,
            confidence=current_pose.confidence,
            timestamp=current_pose.timestamp,
            is_valid=current_pose.is_valid,
            rotation_angle=smoothed_rotation
        )
        
        history.append(smoothed)
        self._pose_history[session_id] = history[-5:]
        
        return smoothed
    
    async def _generate_overlay(
        self,
        frame: np.ndarray,
        pose: ARPoseResult,
        session: ARSessionState
    ) -> Optional[np.ndarray]:
        """
        Generate garment overlay on frame.
        
        Args:
            frame: Original frame
            pose: Detected pose
            session: Session with garment data
            
        Returns:
            Composited frame with garment overlay
        """
        if session.garment_image is None:
            return None
        
        try:
            import cv2
            
            h, w = frame.shape[:2]
            
            # Get key body points for positioning
            keypoints = pose.keypoints
            
            # Calculate garment position and size based on category
            if session.garment_category in self.UPPER_BODY:
                position, size = self._calculate_upper_body_placement(keypoints, w, h)
            elif session.garment_category in self.LOWER_BODY:
                position, size = self._calculate_lower_body_placement(keypoints, w, h)
            else:  # Full body
                position, size = self._calculate_full_body_placement(keypoints, w, h)
            
            # Load and transform garment
            garment_img = Image.open(io.BytesIO(session.garment_image))
            garment_array = np.array(garment_img.convert('RGBA'))
            
            # Resize garment
            garment_resized = cv2.resize(
                garment_array, 
                (size[0], size[1]),
                interpolation=cv2.INTER_LINEAR
            )
            
            # Apply rotation if needed
            if abs(pose.rotation_angle) > 5:
                garment_resized = self._rotate_garment(
                    garment_resized, 
                    pose.rotation_angle
                )
            
            # Create overlay
            overlay = frame.copy()
            overlay = cv2.cvtColor(overlay, cv2.COLOR_RGB2RGBA)
            
            # Blend garment onto frame
            x, y = position
            gx, gy = 0, 0
            gw, gh = garment_resized.shape[:2]
            
            # Ensure bounds
            if x < 0:
                gx = -x
                x = 0
            if y < 0:
                gy = -y
                y = 0
            
            end_x = min(x + gw - gx, w)
            end_y = min(y + gh - gy, h)
            
            # Alpha blending
            for c in range(3):  # RGB channels
                alpha = garment_resized[gy:gy+(end_y-y), gx:gx+(end_x-x), 3] / 255.0
                overlay[y:end_y, x:end_x, c] = (
                    overlay[y:end_y, x:end_x, c] * (1 - alpha) +
                    garment_resized[gy:gy+(end_y-y), gx:gx+(end_x-x), c] * alpha
                )
            
            # Convert back to RGB
            result = cv2.cvtColor(overlay, cv2.COLOR_RGBA2RGB)
            
            return result
            
        except Exception as e:
            logger.error(f"Overlay generation failed: {e}")
            return None
    
    def _calculate_upper_body_placement(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Calculate position and size for upper body garments."""
        # Use shoulders and hips for positioning
        left_shoulder = keypoints[11] if len(keypoints) > 11 else {'x': 0.3, 'y': 0.2}
        right_shoulder = keypoints[12] if len(keypoints) > 12 else {'x': 0.7, 'y': 0.2}
        left_hip = keypoints[23] if len(keypoints) > 23 else {'x': 0.35, 'y': 0.5}
        right_hip = keypoints[24] if len(keypoints) > 24 else {'x': 0.65, 'y': 0.5}
        
        # Calculate center position
        center_x = (left_shoulder['x'] + right_shoulder['x']) / 2 * width
        top_y = min(left_shoulder['y'], right_shoulder['y']) * height - height * 0.05
        bottom_y = max(left_hip['y'], right_hip['y']) * height + height * 0.05
        
        # Calculate size
        shoulder_width = abs(right_shoulder['x'] - left_shoulder['x']) * width
        torso_height = bottom_y - top_y
        
        garment_width = int(shoulder_width * 1.4)
        garment_height = int(torso_height * 1.2)
        
        position = (int(center_x - garment_width // 2), int(top_y))
        size = (garment_width, garment_height)
        
        return position, size
    
    def _calculate_lower_body_placement(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Calculate position and size for lower body garments."""
        left_hip = keypoints[23] if len(keypoints) > 23 else {'x': 0.35, 'y': 0.5}
        right_hip = keypoints[24] if len(keypoints) > 24 else {'x': 0.65, 'y': 0.5}
        left_knee = keypoints[25] if len(keypoints) > 25 else {'x': 0.35, 'y': 0.7}
        right_knee = keypoints[26] if len(keypoints) > 26 else {'x': 0.65, 'y': 0.7}
        
        # Calculate position
        center_x = (left_hip['x'] + right_hip['x']) / 2 * width
        top_y = min(left_hip['y'], right_hip['y']) * height - height * 0.02
        bottom_y = height * 0.95  # Extend to bottom of frame
        
        # Calculate size
        hip_width = abs(right_hip['x'] - left_hip['x']) * width
        garment_width = int(hip_width * 1.8)
        garment_height = int(bottom_y - top_y)
        
        position = (int(center_x - garment_width // 2), int(top_y))
        size = (garment_width, garment_height)
        
        return position, size
    
    def _calculate_full_body_placement(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Calculate position and size for full body garments."""
        # Use shoulders and ankles
        left_shoulder = keypoints[11] if len(keypoints) > 11 else {'x': 0.3, 'y': 0.2}
        right_shoulder = keypoints[12] if len(keypoints) > 12 else {'x': 0.7, 'y': 0.2}
        
        # Calculate position
        center_x = (left_shoulder['x'] + right_shoulder['x']) / 2 * width
        top_y = min(left_shoulder['y'], right_shoulder['y']) * height - height * 0.08
        bottom_y = height * 0.98
        
        # Calculate size
        shoulder_width = abs(right_shoulder['x'] - left_shoulder['x']) * width
        garment_width = int(shoulder_width * 1.6)
        garment_height = int(bottom_y - top_y)
        
        position = (int(center_x - garment_width // 2), int(top_y))
        size = (garment_width, garment_height)
        
        return position, size
    
    def _rotate_garment(
        self,
        garment: np.ndarray,
        angle: float
    ) -> np.ndarray:
        """Rotate garment image for pose alignment."""
        import cv2
        
        h, w = garment.shape[:2]
        center = (w // 2, h // 2)
        
        # Get rotation matrix
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Apply rotation with transparent border
        rotated = cv2.warpAffine(
            garment, matrix, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )
        
        return rotated
    
    # ==========================================
    # Garment Preparation
    # ==========================================
    
    async def _prepare_garment(
        self,
        garment_image: bytes,
        category: str
    ) -> Tuple[bytes, np.ndarray]:
        """
        Prepare garment image for overlay.
        
        Steps:
        1. Remove background
        2. Create alpha mask
        3. Optimize size
        """
        # Load image
        img = Image.open(io.BytesIO(garment_image)).convert('RGBA')
        
        # Resize if too large
        max_size = 512
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Simple background removal (in production, use AI segmentation)
        mask = self._create_garment_mask(np.array(img))
        
        # Apply mask to alpha channel
        img_array = np.array(img)
        img_array[:, :, 3] = mask * 255
        
        # Convert back to bytes
        result_img = Image.fromarray(img_array)
        output = io.BytesIO()
        result_img.save(output, format='PNG')
        
        return output.getvalue(), mask
    
    def _create_garment_mask(self, image: np.ndarray) -> np.ndarray:
        """Create mask for garment (simple threshold-based)."""
        import cv2
        
        # Convert to HSV for better color separation
        if image.shape[2] == 4:
            rgb = image[:, :, :3]
        else:
            rgb = image
        
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        
        # Simple background removal (white/light backgrounds)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        
        mask = cv2.inRange(hsv, lower_white, upper_white)
        mask = cv2.bitwise_not(mask)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Normalize to 0-1
        return (mask > 0).astype(np.float32)
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    def _decode_base64(self, data: str) -> bytes:
        """Decode base64 string to bytes."""
        # Remove data URI prefix if present
        if ',' in data:
            data = data.split(',')[1]
        return base64.b64decode(data)
    
    def _encode_overlay(self, overlay: np.ndarray) -> str:
        """Encode overlay image as base64."""
        img = Image.fromarray(overlay)
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        encoded = base64.b64encode(output.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded}"
    
    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to max resolution for performance."""
        h, w = frame.shape[:2]
        max_w, max_h = self.MAX_RESOLUTION
        
        if w > max_w or h > max_h:
            import cv2
            ratio = min(max_w / w, max_h / h)
            new_size = (int(w * ratio), int(h * ratio))
            return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
        
        return frame
    
    def _detect_garment_category(self, garment_id: str) -> str:
        """Detect garment category from ID."""
        garment_id_lower = garment_id.lower()
        
        if any(x in garment_id_lower for x in self.UPPER_BODY):
            return "tops"
        elif any(x in garment_id_lower for x in self.LOWER_BODY):
            return "pants"
        elif any(x in garment_id_lower for x in self.FULL_BODY):
            return "dress"
        
        return "tops"
    
    def _update_metrics(self, processing_time_ms: float):
        """Update performance metrics."""
        total = self._metrics["total_frames_processed"]
        avg = self._metrics["average_processing_time_ms"]
        
        # Running average
        self._metrics["average_processing_time_ms"] = (
            (avg * total + processing_time_ms) / (total + 1)
        )
        self._metrics["total_frames_processed"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        return {
            **self._metrics,
            "active_sessions": len(self._sessions),
            "mode": self.mode.value
        }
    
    async def capture_screenshot(
        self,
        session_id: str,
        frame_base64: str
    ) -> Dict[str, Any]:
        """
        Capture a screenshot from the AR session.
        
        Privacy: Screenshot is returned to client, not stored.
        
        Args:
            session_id: Active session ID
            frame_base64: Current frame
            
        Returns:
            Dict with screenshot data and metadata
        """
        session = self._sessions.get(session_id)
        if session is None:
            return {"success": False, "error": "Session not found"}
        
        # Process frame with quality mode
        result = await self.process_frame(
            session_id,
            frame_base64,
            return_overlay=True
        )
        
        if not result.get("success"):
            return result
        
        # Return screenshot without storing
        return {
            "success": True,
            "screenshot": result.get("overlay_image"),
            "garment_id": session.garment_id,
            "garment_category": session.garment_category,
            "pose_confidence": result.get("pose", {}).get("confidence", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "privacy_note": "Screenshot not stored on server"
        }


# ==========================================
# Singleton Instance
# ==========================================

_instance: Optional[ARTryOnService] = None


def get_ar_tryon_service() -> ARTryOnService:
    """Get singleton AR Try-On service instance."""
    global _instance
    if _instance is None:
        _instance = ARTryOnService()
    return _instance
