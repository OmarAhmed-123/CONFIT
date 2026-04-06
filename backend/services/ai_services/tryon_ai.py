"""
CONFIT AI Services - Virtual Try-On
===================================
AI-powered virtual try-on service.

Features:
- Garment segmentation
- Body landmark detection
- Pose estimation
- Garment overlay and blending
- Realistic rendering
"""

import asyncio
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib

import numpy as np
from PIL import Image

from .base import (
    AIServiceBase,
    InferenceResult,
    ModelConfig,
    DeviceType,
    gpu_context,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

class BodyPart(Enum):
    """Body parts for landmark detection."""
    HEAD = "head"
    NECK = "neck"
    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    LEFT_ELBOW = "left_elbow"
    RIGHT_ELBOW = "right_elbow"
    LEFT_WRIST = "left_wrist"
    RIGHT_WRIST = "right_wrist"
    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"
    LEFT_KNEE = "left_knee"
    RIGHT_KNEE = "right_knee"
    LEFT_ANKLE = "left_ankle"
    RIGHT_ANKLE = "right_ankle"
    CHEST = "chest"
    WAIST = "waist"
    TORSO = "torso"


class GarmentType(Enum):
    """Types of garments for try-on."""
    TOP = "top"
    DRESS = "dress"
    PANTS = "pants"
    SKIRT = "skirt"
    JACKET = "jacket"
    COAT = "coat"
    SHORTS = "shorts"
    FULL_BODY = "full_body"


class BlendMode(Enum):
    """Blending modes for garment overlay."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"


@dataclass
class BodyLandmark:
    """Single body landmark point."""
    part: BodyPart
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1
    confidence: float = 1.0
    visibility: float = 1.0  # 0 = occluded, 1 = visible


@dataclass
class PoseEstimation:
    """Full pose estimation result."""
    landmarks: List[BodyLandmark]
    bounding_box: Tuple[float, float, float, float]  # x, y, w, h normalized
    rotation_angle: float = 0.0  # Body rotation in degrees
    confidence: float = 0.0
    
    def get_landmark(self, part: BodyPart) -> Optional[BodyLandmark]:
        """Get specific landmark by body part."""
        for lm in self.landmarks:
            if lm.part == part:
                return lm
        return None
    
    def get_torso_region(self) -> Tuple[float, float, float, float]:
        """Get torso bounding region."""
        shoulders = [
            self.get_landmark(BodyPart.LEFT_SHOULDER),
            self.get_landmark(BodyPart.RIGHT_SHOULDER),
        ]
        hips = [
            self.get_landmark(BodyPart.LEFT_HIP),
            self.get_landmark(BodyPart.RIGHT_HIP),
        ]
        
        if all(shoulders) and all(hips):
            x_min = min(s.x for s in shoulders if s) - 0.05
            x_max = max(s.x for s in shoulders if s) + 0.05
            y_min = min(s.y for s in shoulders if s) - 0.05
            y_max = max(h.y for h in hips if h) + 0.05
            return (x_min, y_min, x_max - x_min, y_max - y_min)
        
        return (0.25, 0.1, 0.5, 0.4)  # Default torso region


@dataclass
class SegmentationMask:
    """Segmentation mask for garment or body."""
    mask: np.ndarray  # Binary mask (H, W)
    class_label: str
    confidence: float = 1.0
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    
    def get_overlay_region(self) -> Tuple[int, int, int, int]:
        """Get bounding box of non-zero region."""
        rows = np.any(self.mask, axis=1)
        cols = np.any(self.mask, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return (0, 0, 0, 0)
        
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        return (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))


@dataclass
class GarmentSegment:
    """Segmented garment from image."""
    garment_type: GarmentType
    mask: SegmentationMask
    source_image: Optional[np.ndarray] = None
    extracted_image: Optional[np.ndarray] = None
    color_histogram: Optional[np.ndarray] = None
    texture_features: Optional[np.ndarray] = None


@dataclass
class TryOnResult:
    """Virtual try-on result."""
    output_image: np.ndarray
    output_mask: Optional[np.ndarray] = None
    pose: Optional[PoseEstimation] = None
    garment_mask: Optional[SegmentationMask] = None
    blend_score: float = 0.0
    realism_score: float = 0.0
    processing_time_ms: float = 0.0
    model_version: str = "tryon_v1"


@dataclass
class TryOnRequest:
    """Request for virtual try-on."""
    person_image_bytes: bytes
    garment_image_bytes: bytes
    garment_type: Optional[GarmentType] = None
    blend_mode: BlendMode = BlendMode.NORMAL
    preserve_person_features: bool = True
    adjust_lighting: bool = True
    refine_edges: bool = True
    output_size: Tuple[int, int] = (512, 512)


# ─────────────────────────────────────────────────────────────────────────────
# Try-On AI Service
# ─────────────────────────────────────────────────────────────────────────────

class TryOnAIService(AIServiceBase):
    """
    Virtual try-on AI service.
    
    Pipeline:
    1. Detect body pose and landmarks
    2. Segment garment from product image
    3. Warp garment to match body pose
    4. Blend garment onto person image
    5. Refine edges and adjust lighting
    
    Usage:
        service = TryOnAIService()
        
        result = await service.infer(TryOnRequest(
            person_image_bytes=person_image,
            garment_image_bytes=garment_image,
            garment_type=GarmentType.TOP,
        ))
    """
    
    # Body part connections for visualization
    SKELETON_CONNECTIONS = [
        (BodyPart.LEFT_SHOULDER, BodyPart.RIGHT_SHOULDER),
        (BodyPart.LEFT_SHOULDER, BodyPart.LEFT_ELBOW),
        (BodyPart.LEFT_ELBOW, BodyPart.LEFT_WRIST),
        (BodyPart.RIGHT_SHOULDER, BodyPart.RIGHT_ELBOW),
        (BodyPart.RIGHT_ELBOW, BodyPart.RIGHT_WRIST),
        (BodyPart.LEFT_SHOULDER, BodyPart.LEFT_HIP),
        (BodyPart.RIGHT_SHOULDER, BodyPart.RIGHT_HIP),
        (BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP),
        (BodyPart.LEFT_HIP, BodyPart.LEFT_KNEE),
        (BodyPart.LEFT_KNEE, BodyPart.LEFT_ANKLE),
        (BodyPart.RIGHT_HIP, BodyPart.RIGHT_KNEE),
        (BodyPart.RIGHT_KNEE, BodyPart.RIGHT_ANKLE),
    ]
    
    def __init__(self, config: Optional[ModelConfig] = None):
        config = config or ModelConfig(
            name="tryon_ai",
            device=DeviceType.CUDA,
            batch_size=4,
            precision="float16",
        )
        super().__init__(config)
        
        self._pose_model = None
        self._segmentation_model = None
        self._warping_model = None
        self._device = None
    
    @property
    def model_name(self) -> str:
        return "tryon_ai_v1"
    
    async def load_model(self) -> None:
        """Load models for try-on pipeline."""
        try:
            import torch
            
            # Set device
            self._device = self._get_device()
            
            # Load MediaPipe for pose estimation
            try:
                import mediapipe as mp
                self._mp_pose = mp.solutions.pose.Pose(
                    static_image_mode=True,
                    model_complexity=2,
                    enable_segmentation=True,
                )
                logger.info("Loaded MediaPipe pose model")
            except ImportError:
                logger.warning("MediaPipe not available, using fallback pose detection")
                self._mp_pose = None
            
            # Load segmentation model
            try:
                from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
                
                seg_model_name = "mattmdjaga/segformer_b2_clothes"
                self._seg_processor = AutoImageProcessor.from_pretrained(seg_model_name)
                self._segmentation_model = AutoModelForSemanticSegmentation.from_pretrained(seg_model_name)
                
                if self._device != "cpu":
                    self._segmentation_model = self._segmentation_model.to(self._device)
                
                self._segmentation_model.eval()
                logger.info(f"Loaded segmentation model on {self._device}")
            except ImportError:
                logger.warning("Segmentation model not available")
                self._segmentation_model = None
            
            self._model = "loaded"
            
        except ImportError as e:
            logger.warning(f"Try-on dependencies not available: {e}")
            self._model = "fallback"
    
    async def _infer(self, input_data: TryOnRequest) -> TryOnResult:
        """
        Process virtual try-on request.
        
        Args:
            input_data: TryOnRequest with person and garment images
            
        Returns:
            TryOnResult with output image
        """
        start_time = datetime.now(timezone.utc)
        
        # Load images
        person_image = self._load_image(input_data.person_image_bytes)
        garment_image = self._load_image(input_data.garment_image_bytes)
        
        # Resize to output size
        person_image = np.array(
            Image.fromarray(person_image).resize(
                input_data.output_size, Image.Resampling.LANCZOS
            )
        )
        garment_image = np.array(
            Image.fromarray(garment_image).resize(
                input_data.output_size, Image.Resampling.LANCZOS
            )
        )
        
        # Step 1: Detect pose
        pose = await self._detect_pose(person_image)
        
        # Step 2: Segment garment
        garment_segment = await self._segment_garment(
            garment_image, input_data.garment_type
        )
        
        # Step 3: Warp garment to body
        warped_garment = await self._warp_garment(
            garment_segment, pose, person_image.shape
        )
        
        # Step 4: Blend onto person
        output_image, output_mask = await self._blend_garment(
            person_image, warped_garment, pose,
            blend_mode=input_data.blend_mode,
            adjust_lighting=input_data.adjust_lighting,
            refine_edges=input_data.refine_edges,
        )
        
        # Compute quality scores
        blend_score = self._compute_blend_score(output_image, person_image)
        realism_score = self._compute_realism_score(output_image, output_mask)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return TryOnResult(
            output_image=output_image,
            output_mask=output_mask,
            pose=pose,
            garment_mask=garment_segment.mask,
            blend_score=blend_score,
            realism_score=realism_score,
            processing_time_ms=processing_time,
        )
    
    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        """Load image from bytes."""
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return np.array(image)
    
    async def _detect_pose(
        self,
        image: np.ndarray
    ) -> PoseEstimation:
        """
        Detect body pose and landmarks.
        
        Uses MediaPipe or fallback detection.
        """
        if self._mp_pose is not None:
            return await self._mediapipe_pose(image)
        else:
            return await self._fallback_pose_detection(image)
    
    async def _mediapipe_pose(
        self,
        image: np.ndarray
    ) -> PoseEstimation:
        """MediaPipe-based pose detection."""
        h, w = image.shape[:2]
        
        # Run MediaPipe
        results = self._mp_pose.process(image)
        
        if not results.pose_landmarks:
            return await self._fallback_pose_detection(image)
        
        # Extract landmarks
        landmarks = []
        landmark_map = {
            0: BodyPart.HEAD,
            11: BodyPart.LEFT_SHOULDER,
            12: BodyPart.RIGHT_SHOULDER,
            13: BodyPart.LEFT_ELBOW,
            14: BodyPart.RIGHT_ELBOW,
            15: BodyPart.LEFT_WRIST,
            16: BodyPart.RIGHT_WRIST,
            23: BodyPart.LEFT_HIP,
            24: BodyPart.RIGHT_HIP,
            25: BodyPart.LEFT_KNEE,
            26: BodyPart.RIGHT_KNEE,
            27: BodyPart.LEFT_ANKLE,
            28: BodyPart.RIGHT_ANKLE,
        }
        
        for idx, part in landmark_map.items():
            lm = results.pose_landmarks.landmark[idx]
            landmarks.append(BodyLandmark(
                part=part,
                x=lm.x,
                y=lm.y,
                confidence=lm.visibility,
                visibility=lm.visibility,
            ))
        
        # Compute bounding box
        x_coords = [lm.x for lm in landmarks]
        y_coords = [lm.y for lm in landmarks]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Add padding
        padding = 0.1
        x_min = max(0, x_min - padding)
        x_max = min(1, x_max + padding)
        y_min = max(0, y_min - padding)
        y_max = min(1, y_max + padding)
        
        # Compute rotation
        left_shoulder = next((lm for lm in landmarks if lm.part == BodyPart.LEFT_SHOULDER), None)
        right_shoulder = next((lm for lm in landmarks if lm.part == BodyPart.RIGHT_SHOULDER), None)
        
        rotation = 0.0
        if left_shoulder and right_shoulder:
            dx = right_shoulder.x - left_shoulder.x
            dy = right_shoulder.y - left_shoulder.y
            rotation = np.degrees(np.arctan2(dy, dx))
        
        return PoseEstimation(
            landmarks=landmarks,
            bounding_box=(x_min, y_min, x_max - x_min, y_max - y_min),
            rotation_angle=rotation,
            confidence=0.9,
        )
    
    async def _fallback_pose_detection(
        self,
        image: np.ndarray
    ) -> PoseEstimation:
        """Fallback pose detection using heuristics."""
        h, w = image.shape[:2]
        
        # Simple heuristic: assume centered person
        landmarks = [
            BodyLandmark(BodyPart.HEAD, 0.5, 0.1, 0.8),
            BodyLandmark(BodyPart.NECK, 0.5, 0.15, 0.8),
            BodyLandmark(BodyPart.LEFT_SHOULDER, 0.35, 0.18, 0.7),
            BodyLandmark(BodyPart.RIGHT_SHOULDER, 0.65, 0.18, 0.7),
            BodyLandmark(BodyPart.LEFT_ELBOW, 0.25, 0.35, 0.6),
            BodyLandmark(BodyPart.RIGHT_ELBOW, 0.75, 0.35, 0.6),
            BodyLandmark(BodyPart.LEFT_WRIST, 0.2, 0.5, 0.5),
            BodyLandmark(BodyPart.RIGHT_WRIST, 0.8, 0.5, 0.5),
            BodyLandmark(BodyPart.LEFT_HIP, 0.4, 0.5, 0.7),
            BodyLandmark(BodyPart.RIGHT_HIP, 0.6, 0.5, 0.7),
            BodyLandmark(BodyPart.LEFT_KNEE, 0.42, 0.7, 0.6),
            BodyLandmark(BodyPart.RIGHT_KNEE, 0.58, 0.7, 0.6),
            BodyLandmark(BodyPart.LEFT_ANKLE, 0.45, 0.95, 0.5),
            BodyLandmark(BodyPart.RIGHT_ANKLE, 0.55, 0.95, 0.5),
        ]
        
        return PoseEstimation(
            landmarks=landmarks,
            bounding_box=(0.2, 0.05, 0.6, 0.9),
            rotation_angle=0.0,
            confidence=0.5,
        )
    
    async def _segment_garment(
        self,
        garment_image: np.ndarray,
        garment_type: Optional[GarmentType] = None
    ) -> GarmentSegment:
        """
        Segment garment from product image.
        
        Uses semantic segmentation or fallback.
        """
        if self._segmentation_model is not None:
            return await self._ml_segmentation(garment_image, garment_type)
        else:
            return await self._fallback_segmentation(garment_image, garment_type)
    
    async def _ml_segmentation(
        self,
        image: np.ndarray,
        garment_type: Optional[GarmentType]
    ) -> GarmentSegment:
        """ML-based garment segmentation."""
        try:
            import torch
            
            # Preprocess
            pil_image = Image.fromarray(image)
            inputs = self._seg_processor(images=pil_image, return_tensors="pt")
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Segment
            with torch.no_grad():
                outputs = self._segmentation_model(**inputs)
                logits = outputs.logits
            
            # Get mask
            logits = logits.cpu().numpy()
            mask = np.argmax(logits[0], axis=0)
            
            # Resize to original size
            mask = np.array(
                Image.fromarray(mask.astype(np.uint8)).resize(
                    (image.shape[1], image.shape[0]),
                    Image.Resampling.NEAREST
                )
            )
            
            # Map to garment class (simplified)
            # In production, would use proper class mapping
            garment_mask = (mask > 0).astype(np.uint8) * 255
            
            detected_type = garment_type or GarmentType.TOP
            
            return GarmentSegment(
                garment_type=detected_type,
                mask=SegmentationMask(
                    mask=garment_mask,
                    class_label=detected_type.value,
                    confidence=0.85,
                ),
                source_image=image,
                extracted_image=image * (garment_mask[:, :, np.newaxis] // 255),
            )
            
        except Exception as e:
            logger.error(f"ML segmentation error: {e}")
            return await self._fallback_segmentation(image, garment_type)
    
    async def _fallback_segmentation(
        self,
        image: np.ndarray,
        garment_type: Optional[GarmentType]
    ) -> GarmentSegment:
        """Fallback segmentation using background removal."""
        try:
            import cv2
            
            # Convert to different color spaces
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Background removal using GrabCut-like approach
            # Assume center is foreground
            h, w = image.shape[:2]
            
            # Create initial mask
            mask = np.zeros((h, w), np.uint8)
            
            # Assume center region is garment
            center_y, center_x = h // 2, w // 2
            radius = min(h, w) // 3
            
            y, x = np.ogrid[:h, :w]
            center_mask = ((x - center_x) ** 2 + (y - center_y) ** 2) < radius ** 2
            mask[center_mask] = 255
            
            # Refine using edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Dilate mask slightly
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=2)
            
            # Apply edge constraint
            mask[edges > 0] = 0
            
            # Clean up
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            detected_type = garment_type or GarmentType.TOP
            
            return GarmentSegment(
                garment_type=detected_type,
                mask=SegmentationMask(
                    mask=mask,
                    class_label=detected_type.value,
                    confidence=0.6,
                ),
                source_image=image,
                extracted_image=image * (mask[:, :, np.newaxis] // 255),
            )
            
        except Exception as e:
            logger.error(f"Fallback segmentation error: {e}")
            # Return full image as mask
            h, w = image.shape[:2]
            return GarmentSegment(
                garment_type=garment_type or GarmentType.TOP,
                mask=SegmentationMask(
                    mask=np.ones((h, w), dtype=np.uint8) * 255,
                    class_label="full",
                    confidence=0.3,
                ),
                source_image=image,
            )
    
    async def _warp_garment(
        self,
        garment: GarmentSegment,
        pose: PoseEstimation,
        target_shape: Tuple[int, int, int]
    ) -> np.ndarray:
        """
        Warp garment to match body pose.
        
        Uses thin-plate spline or affine transformation.
        """
        if garment.extracted_image is None:
            return np.zeros(target_shape, dtype=np.uint8)
        
        try:
            import cv2
            
            h, w = target_shape[:2]
            garment_h, garment_w = garment.source_image.shape[:2]
            
            # Get torso region
            torso = pose.get_torso_region()
            torso_x, torso_y, torso_w, torso_h = torso
            
            # Convert to pixel coordinates
            target_x = int(torso_x * w)
            target_y = int(torso_y * h)
            target_w = int(torso_w * w)
            target_h = int(torso_h * h)
            
            # Compute scale and position
            scale_x = target_w / garment_w
            scale_y = target_h / garment_h
            scale = min(scale_x, scale_y) * 1.1  # Slightly larger
            
            # Compute rotation
            angle = pose.rotation_angle
            
            # Build transformation matrix
            center = (garment_w // 2, garment_h // 2)
            M = cv2.getRotationMatrix2D(center, angle, scale)
            
            # Add translation
            M[0, 2] += target_x - garment_w * scale / 2
            M[1, 2] += target_y - garment_h * scale / 2
            
            # Warp garment
            warped = cv2.warpAffine(
                garment.extracted_image,
                M,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            
            # Warp mask
            warped_mask = cv2.warpAffine(
                garment.mask.mask,
                M,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0
            )
            
            # Store warped mask
            garment.mask.mask = warped_mask
            
            return warped
            
        except Exception as e:
            logger.error(f"Garment warping error: {e}")
            # Return simple resize
            return np.array(
                Image.fromarray(garment.extracted_image).resize(
                    (target_shape[1], target_shape[0]),
                    Image.Resampling.LANCZOS
                )
            )
    
    async def _blend_garment(
        self,
        person_image: np.ndarray,
        warped_garment: np.ndarray,
        pose: PoseEstimation,
        blend_mode: BlendMode,
        adjust_lighting: bool,
        refine_edges: bool
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Blend garment onto person image.
        
        Handles lighting adjustment and edge refinement.
        """
        try:
            import cv2
            
            h, w = person_image.shape[:2]
            
            # Create mask from warped garment
            gray_garment = cv2.cvtColor(warped_garment, cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(gray_garment, 10, 255, cv2.THRESH_BINARY)
            
            # Refine edges
            if refine_edges:
                mask = self._refine_mask(mask)
            
            # Adjust lighting if requested
            if adjust_lighting:
                warped_garment = self._adjust_lighting(
                    warped_garment, person_image, mask
                )
            
            # Apply blend mode
            blended = self._apply_blend_mode(
                person_image, warped_garment, mask, blend_mode
            )
            
            # Final alpha blending
            mask_float = mask.astype(np.float32) / 255.0
            mask_3ch = np.stack([mask_float] * 3, axis=-1)
            
            output = (
                person_image * (1 - mask_3ch) +
                blended * mask_3ch
            ).astype(np.uint8)
            
            return output, mask
            
        except Exception as e:
            logger.error(f"Blending error: {e}")
            return person_image, np.zeros(person_image.shape[:2], dtype=np.uint8)
    
    def _refine_mask(self, mask: np.ndarray) -> np.ndarray:
        """Refine mask edges for smoother blending."""
        try:
            import cv2
            
            # Feather edges
            mask = cv2.GaussianBlur(mask, (15, 15), 0)
            
            # Morphological cleanup
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Threshold back to binary
            _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            
            return mask
            
        except Exception:
            return mask
    
    def _adjust_lighting(
        self,
        garment: np.ndarray,
        person: np.ndarray,
        mask: np.ndarray
    ) -> np.ndarray:
        """Adjust garment lighting to match person."""
        try:
            import cv2
            
            # Compute average brightness in person's skin region
            # (simplified - would use skin detection in production)
            person_gray = cv2.cvtColor(person, cv2.COLOR_RGB2GRAY)
            garment_gray = cv2.cvtColor(garment, cv2.COLOR_RGB2GRAY)
            
            # Get average brightness
            person_brightness = np.mean(person_gray)
            garment_brightness = np.mean(garment_gray[mask > 0])
            
            if garment_brightness < 1:
                return garment
            
            # Compute adjustment factor
            factor = person_brightness / garment_brightness
            factor = np.clip(factor, 0.5, 1.5)
            
            # Apply adjustment
            adjusted = (garment.astype(np.float32) * factor).clip(0, 255).astype(np.uint8)
            
            return adjusted
            
        except Exception:
            return garment
    
    def _apply_blend_mode(
        self,
        base: np.ndarray,
        overlay: np.ndarray,
        mask: np.ndarray,
        mode: BlendMode
    ) -> np.ndarray:
        """Apply specified blend mode."""
        if mode == BlendMode.NORMAL:
            return overlay
        
        # Convert to float
        base_f = base.astype(np.float32) / 255.0
        overlay_f = overlay.astype(np.float32) / 255.0
        mask_f = mask.astype(np.float32) / 255.0
        
        if mode == BlendMode.MULTIPLY:
            result = base_f * overlay_f
        elif mode == BlendMode.OVERLAY:
            result = np.where(
                base_f < 0.5,
                2 * base_f * overlay_f,
                1 - 2 * (1 - base_f) * (1 - overlay_f)
            )
        elif mode == BlendMode.SOFT_LIGHT:
            result = self._soft_light_blend(base_f, overlay_f)
        elif mode == BlendMode.HARD_LIGHT:
            result = np.where(
                overlay_f < 0.5,
                2 * base_f * overlay_f,
                1 - 2 * (1 - base_f) * (1 - overlay_f)
            )
        else:
            result = overlay_f
        
        # Apply mask
        mask_3ch = np.stack([mask_f] * 3, axis=-1)
        result = base_f * (1 - mask_3ch) + result * mask_3ch
        
        return (result * 255).astype(np.uint8)
    
    def _soft_light_blend(
        self,
        base: np.ndarray,
        overlay: np.ndarray
    ) -> np.ndarray:
        """Soft light blend mode."""
        return (
            (1 - 2 * overlay) * base ** 2 +
            2 * overlay * base
        )
    
    def _compute_blend_score(
        self,
        output: np.ndarray,
        original: np.ndarray
    ) -> float:
        """Compute blend quality score."""
        try:
            import cv2
            
            # Structural similarity
            output_gray = cv2.cvtColor(output, cv2.COLOR_RGB2GRAY)
            original_gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
            
            # Compute difference
            diff = np.abs(output_gray.astype(float) - original_gray.astype(float))
            
            # Score based on smoothness of transition
            edges = cv2.Canny(output_gray, 50, 150)
            edge_diff = diff[edges > 0]
            
            if len(edge_diff) > 0:
                smoothness = 1 - np.mean(edge_diff) / 255
                return float(np.clip(smoothness, 0, 1))
            
            return 0.8
            
        except Exception:
            return 0.7
    
    def _compute_realism_score(
        self,
        output: np.ndarray,
        mask: np.ndarray
    ) -> float:
        """Compute realism score of try-on result."""
        try:
            import cv2
            
            # Check for artifacts at boundaries
            edges = cv2.Canny(mask, 50, 150)
            
            # Check color consistency
            output_hsv = cv2.cvtColor(output, cv2.COLOR_RGB2HSV)
            
            # Variance in saturation and value at edges
            edge_pixels = output_hsv[edges > 0]
            
            if len(edge_pixels) > 10:
                s_var = np.var(edge_pixels[:, 1])
                v_var = np.var(edge_pixels[:, 2])
                
                # Lower variance = more realistic
                score = 1 - (s_var + v_var) / (255 ** 2 * 2)
                return float(np.clip(score, 0, 1))
            
            return 0.75
            
        except Exception:
            return 0.7


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

async def try_on_garment(
    person_image: bytes,
    garment_image: bytes,
    garment_type: Optional[GarmentType] = None
) -> TryOnResult:
    """
    Convenience function for virtual try-on.
    
    Args:
        person_image: Person image bytes
        garment_image: Garment image bytes
        garment_type: Optional garment type hint
        
    Returns:
        TryOnResult with output image
    """
    service = TryOnAIService()
    request = TryOnRequest(
        person_image_bytes=person_image,
        garment_image_bytes=garment_image,
        garment_type=garment_type,
    )
    result = await service.infer(request)
    return result


def output_to_bytes(result: TryOnResult, format: str = "PNG") -> bytes:
    """
    Convert TryOnResult output to image bytes.
    
    Args:
        result: TryOnResult from try-on
        format: Output format (PNG, JPEG)
        
    Returns:
        Image bytes
    """
    image = Image.fromarray(result.output_image)
    
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    
    return buffer.getvalue()
