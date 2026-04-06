"""
CONFIT Backend — Body Segmenter
===============================
Image segmentation for virtual try-on.

Segments:
- Person mask (full body)
- Face region
- Upper/lower body separation
- Existing clothing regions
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class SegmentationClass(Enum):
    """Segmentation class labels."""
    BACKGROUND = 0
    HEAD = 1
    TORSO = 2
    UPPER_CLOTHES = 3
    LOWER_CLOTHES = 4
    ARMS = 5
    LEGS = 6
    SHOES = 7
    FACE = 11
    HAIR = 12
    HAT = 13
    SUNGLASSES = 14


@dataclass
class SegmentationResult:
    """Result of segmentation process."""
    person_mask: np.ndarray
    face_mask: Optional[np.ndarray] = None
    upper_body_mask: Optional[np.ndarray] = None
    lower_body_mask: Optional[np.ndarray] = None
    clothes_mask: Optional[np.ndarray] = None
    parsing_map: Optional[np.ndarray] = None
    success: bool = True
    error: Optional[str] = None


class BodySegmenter:
    """
    Image segmentation for virtual try-on.
    
    Uses SAM (Segment Anything Model) or Self-Correction-Human-Parsing
    for high-quality segmentation.
    
    Usage:
        segmenter = BodySegmenter()
        result = await segmenter.segment(image_bytes, pose_keypoints)
        person_mask = result['person']
    """
    
    def __init__(
        self,
        model_type: str = "sam",
        device: str = "auto"
    ):
        """
        Initialize segmenter.
        
        Args:
            model_type: "sam" or "schp" (Self-Correction-Human-Parsing)
            device: "auto", "cuda", or "cpu"
        """
        self.model_type = model_type
        self.device = self._get_device(device)
        
        self._sam = None
        self._schp = None
        self._initialized = False
    
    def _get_device(self, device: str) -> str:
        """Determine compute device."""
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def _initialize(self):
        """Lazy initialization of segmentation model."""
        if self._initialized:
            return
        
        if self.model_type == "sam":
            self._init_sam()
        else:
            self._init_schp()
        
        self._initialized = True
    
    def _init_sam(self):
        """Initialize Segment Anything Model."""
        try:
            from segment_anything import sam_model_registry, SamPredictor
            
            # Use ViT-H for best quality, ViT-B for speed
            model_variant = "vit_h" if self.device == "cuda" else "vit_b"
            
            checkpoint_path = f"models/sam_{model_variant}.pth"
            
            sam = sam_model_registry[model_variant](checkpoint=checkpoint_path)
            sam.to(device=self.device)
            
            self._sam = SamPredictor(sam)
            logger.info(f"SAM initialized on {self.device}")
            
        except ImportError:
            logger.warning("segment_anything not available")
        except Exception as e:
            logger.warning(f"Failed to initialize SAM: {e}")
    
    def _init_schp(self):
        """Initialize Self-Correction-Human-Parsing model."""
        try:
            # SCHP provides parsing maps with semantic labels
            import torch
            from models.schp import SCHPModel
            
            self._schp = SCHPModel(
                checkpoint="models/schp.pth",
                device=self.device
            )
            logger.info(f"SCHP initialized on {self.device}")
            
        except ImportError:
            logger.warning("SCHP not available")
    
    async def segment(
        self,
        image_bytes: bytes,
        pose_keypoints: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Segment image into person and clothing regions.

        Accepts either ``{'keypoints': [...]}`` or a legacy dict mapping
        landmark index -> {x,y,visibility} (normalized 0-1).
        
        Args:
            image_bytes: Raw image bytes
            pose_keypoints: Optional pose landmarks for guided segmentation
            
        Returns:
            Dict with masks:
            - person: Full person mask
            - face: Face region mask
            - upper_body: Upper body region
            - lower_body: Lower body region
            - clothes: Current clothing region
            - parsing_map: Semantic parsing map (if available)
        """
        self._initialize()

        if pose_keypoints and "keypoints" not in pose_keypoints:
            # Legacy: dict[int, dict] from vision pose_result_to_legacy_keypoints_dict
            kp_list = []
            for i in range(33):
                d = pose_keypoints.get(i) if isinstance(pose_keypoints, dict) else None
                if isinstance(d, dict):
                    kp_list.append(d)
                else:
                    kp_list.append({"x": 0, "y": 0, "z": 0, "visibility": 0})
            pose_keypoints = {"keypoints": kp_list}
        
        # Load image
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image_array = np.array(image)
        h, w = image_array.shape[:2]
        
        # Try SAM first (best quality)
        if self._sam is not None:
            return await self._segment_with_sam(image_array, pose_keypoints)
        
        # Fallback to SCHP
        if self._schp is not None:
            return await self._segment_with_schp(image_array)
        
        # Final fallback: simple pose-based segmentation
        return await self._segment_with_pose(image_array, pose_keypoints)
    
    async def _segment_with_sam(
        self,
        image: np.ndarray,
        pose_keypoints: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Segment using SAM with pose-guided prompts.
        
        SAM uses point prompts for targeted segmentation.
        """
        self._sam.set_image(image)
        
        h, w = image.shape[:2]
        
        # Generate point prompts from pose keypoints
        if pose_keypoints and 'keypoints' in pose_keypoints:
            keypoints = pose_keypoints['keypoints']
            
            # Foreground points (body center)
            foreground_points = self._get_foreground_points(keypoints, w, h)
            
            # Segment person
            masks, scores, _ = self._sam.predict(
                point_coords=np.array(foreground_points),
                point_labels=np.ones(len(foreground_points)),
                multimask_output=True
            )
            
            # Select best mask
            best_idx = np.argmax(scores)
            person_mask = masks[best_idx]
            
        else:
            # No pose available, use automatic mask generation
            from segment_anything import SamAutomaticMaskGenerator
            
            mask_generator = SamAutomaticMaskGenerator(self._sam.model)
            masks = mask_generator.generate(image)
            
            # Find largest mask (likely person)
            if masks:
                largest_mask = max(masks, key=lambda m: m['area'])
                person_mask = largest_mask['segmentation']
            else:
                person_mask = np.ones((h, w), dtype=bool)
        
        # Generate sub-masks from person mask
        result = self._generate_sub_masks(image, person_mask, pose_keypoints)
        
        return result
    
    def _get_foreground_points(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> List[Tuple[int, int]]:
        """Generate foreground points from keypoints."""
        points = []
        
        # Key body points for SAM prompting
        key_indices = [
            (0, "nose"),      # Face center
            (11, "left_shoulder"),
            (12, "right_shoulder"),
            (23, "left_hip"),
            (24, "right_hip"),
        ]
        
        for idx, name in key_indices:
            if idx < len(keypoints):
                kp = keypoints[idx]
                if kp.get('visibility', 0) > 0.5:
                    x = int(kp['x'] * width)
                    y = int(kp['y'] * height)
                    points.append((x, y))
        
        # Add torso center point
        if len(keypoints) > 24:
            left_shoulder = keypoints[11]
            right_hip = keypoints[24]
            
            center_x = (left_shoulder['x'] + right_hip['x']) / 2 * width
            center_y = (left_shoulder['y'] + right_hip['y']) / 2 * height
            points.append((int(center_x), int(center_y)))
        
        return points
    
    async def _segment_with_schp(
        self,
        image: np.ndarray
    ) -> Dict[str, Any]:
        """
        Segment using Self-Correction-Human-Parsing.
        
        SCHP provides semantic parsing maps with clothing labels.
        """
        parsing_map = self._schp.inference(image)
        
        # Extract masks from parsing map
        person_mask = parsing_map > 0
        
        # Face mask (label 11)
        face_mask = parsing_map == 11
        
        # Upper clothes (label 3)
        upper_clothes_mask = parsing_map == 3
        
        # Lower clothes (label 4)
        lower_clothes_mask = parsing_map == 4
        
        # Torso region
        torso_mask = np.isin(parsing_map, [2, 3, 5])
        
        # Legs region
        legs_mask = np.isin(parsing_map, [6, 4])
        
        return {
            'person': person_mask.astype(np.uint8),
            'face': face_mask.astype(np.uint8),
            'upper_body': torso_mask.astype(np.uint8),
            'lower_body': legs_mask.astype(np.uint8),
            'clothes': (upper_clothes_mask | lower_clothes_mask).astype(np.uint8),
            'parsing_map': parsing_map,
        }
    
    async def _segment_with_pose(
        self,
        image: np.ndarray,
        pose_keypoints: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Fallback segmentation using pose keypoints.
        
        Creates approximate masks from body landmarks.
        """
        h, w = image.shape[:2]
        
        if not pose_keypoints or 'keypoints' not in pose_keypoints:
            # No pose available, return full image mask
            return {
                'person': np.ones((h, w), dtype=np.uint8),
                'face': np.zeros((h, w), dtype=np.uint8),
                'upper_body': np.ones((h, w), dtype=np.uint8),
                'lower_body': np.ones((h, w), dtype=np.uint8),
                'clothes': np.ones((h, w), dtype=np.uint8),
            }
        
        keypoints = pose_keypoints['keypoints']
        
        # Create person mask from convex hull of keypoints
        person_mask = self._create_person_mask_from_keypoints(keypoints, w, h)
        
        # Create sub-masks
        face_mask = self._create_face_mask(keypoints, w, h)
        upper_body_mask = self._create_upper_body_mask(keypoints, w, h)
        lower_body_mask = self._create_lower_body_mask(keypoints, w, h)
        
        return {
            'person': person_mask.astype(np.uint8),
            'face': face_mask.astype(np.uint8),
            'upper_body': upper_body_mask.astype(np.uint8),
            'lower_body': lower_body_mask.astype(np.uint8),
            'clothes': (upper_body_mask | lower_body_mask).astype(np.uint8),
        }
    
    def _create_person_mask_from_keypoints(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> np.ndarray:
        """Create person mask from convex hull of visible keypoints."""
        import cv2
        
        # Collect visible keypoint coordinates
        points = []
        for kp in keypoints:
            if kp.get('visibility', 0) > 0.3:
                x = int(kp['x'] * width)
                y = int(kp['y'] * height)
                points.append([x, y])
        
        if len(points) < 3:
            return np.ones((height, width), dtype=np.uint8)
        
        points = np.array(points)
        
        # Compute convex hull
        hull = cv2.convexHull(points)
        
        # Create mask
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(mask, hull, 1)
        
        # Dilate slightly for safety margin
        kernel = np.ones((20, 20), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask
    
    def _create_face_mask(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> np.ndarray:
        """Create face mask from facial landmarks."""
        import cv2
        
        # Face landmarks: nose, eyes, ears, mouth
        face_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        points = []
        for idx in face_indices:
            if idx < len(keypoints):
                kp = keypoints[idx]
                if kp.get('visibility', 0) > 0.3:
                    x = int(kp['x'] * width)
                    y = int(kp['y'] * height)
                    points.append([x, y])
        
        if len(points) < 3:
            return np.zeros((height, width), dtype=np.uint8)
        
        points = np.array(points)
        
        # Create ellipse around face points
        center = np.mean(points, axis=0)
        distances = np.linalg.norm(points - center, axis=1)
        radius = np.max(distances) * 1.5
        
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, (int(center[0]), int(center[1])), int(radius), 1, -1)
        
        return mask
    
    def _create_upper_body_mask(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> np.ndarray:
        """Create upper body mask (torso + arms)."""
        import cv2
        
        # Upper body landmarks
        upper_indices = [11, 12, 13, 14, 15, 16, 23, 24]  # shoulders, elbows, wrists, hips
        
        points = []
        for idx in upper_indices:
            if idx < len(keypoints):
                kp = keypoints[idx]
                if kp.get('visibility', 0) > 0.3:
                    x = int(kp['x'] * width)
                    y = int(kp['y'] * height)
                    points.append([x, y])
        
        if len(points) < 3:
            return np.zeros((height, width), dtype=np.uint8)
        
        points = np.array(points)
        
        # Create polygon mask
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [points], 1)
        
        # Dilate for coverage
        kernel = np.ones((30, 30), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask
    
    def _create_lower_body_mask(
        self,
        keypoints: List[Dict],
        width: int,
        height: int
    ) -> np.ndarray:
        """Create lower body mask (hips + legs)."""
        import cv2
        
        # Lower body landmarks
        lower_indices = [23, 24, 25, 26, 27, 28]  # hips, knees, ankles
        
        points = []
        for idx in lower_indices:
            if idx < len(keypoints):
                kp = keypoints[idx]
                if kp.get('visibility', 0) > 0.3:
                    x = int(kp['x'] * width)
                    y = int(kp['y'] * height)
                    points.append([x, y])
        
        if len(points) < 3:
            return np.zeros((height, width), dtype=np.uint8)
        
        points = np.array(points)
        
        # Create polygon mask
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [points], 1)
        
        # Extend to bottom of image
        y_min = np.min(points[:, 1])
        mask[int(y_min):, :] = 1
        
        return mask
    
    def _generate_sub_masks(
        self,
        image: np.ndarray,
        person_mask: np.ndarray,
        pose_keypoints: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate sub-masks from person mask."""
        h, w = image.shape[:2]
        
        if pose_keypoints and 'keypoints' in pose_keypoints:
            keypoints = pose_keypoints['keypoints']
            
            face_mask = self._create_face_mask(keypoints, w, h)
            upper_body_mask = self._create_upper_body_mask(keypoints, w, h)
            lower_body_mask = self._create_lower_body_mask(keypoints, w, h)
            
            # Clip to person mask
            face_mask = face_mask & person_mask
            upper_body_mask = upper_body_mask & person_mask
            lower_body_mask = lower_body_mask & person_mask
        else:
            # Simple split
            face_mask = np.zeros_like(person_mask)
            upper_body_mask = person_mask.copy()
            upper_body_mask[h//2:, :] = 0
            lower_body_mask = person_mask.copy()
            lower_body_mask[:h//2, :] = 0
        
        return {
            'person': person_mask.astype(np.uint8),
            'face': face_mask.astype(np.uint8),
            'upper_body': upper_body_mask.astype(np.uint8),
            'lower_body': lower_body_mask.astype(np.uint8),
            'clothes': ((upper_body_mask | lower_body_mask) & ~face_mask).astype(np.uint8),
        }
    
    def refine_mask_edges(
        self,
        mask: np.ndarray,
        blur_radius: int = 5
    ) -> np.ndarray:
        """
        Refine mask edges with Gaussian blur.
        
        Creates smoother transitions for compositing.
        """
        from services.tryon.cv_compat import refine_mask_float01

        refined = refine_mask_float01(mask, blur_radius)
        
        return refined
    
    def close(self):
        """Release resources."""
        self._sam = None
        self._schp = None
        self._initialized = False
