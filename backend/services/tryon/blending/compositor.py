"""
CONFIT Backend — Image Blending Module
======================================
Photorealistic blending of garment onto person image.

Features:
- Multi-band blending for seamless integration
- Lighting/color matching
- Shadow generation
- Edge feathering and refinement
- Skin tone preservation
"""

import logging
import asyncio
import numpy as np
from typing import TYPE_CHECKING, Optional, Dict, List, Tuple, Any

if TYPE_CHECKING:
    from services.tryon.physics.material_engine import MaterialProperties
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import cv2

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

from services.tryon.vision.pose import PoseResult, BodyRegion
from services.tryon.warping.garment import ProcessedGarment, GarmentCategory
from services.tryon.segmentation.body import SegmentationPack
from services.tryon.blending.region_compositor import blend_fullframe_region_safe_sync

logger = logging.getLogger(__name__)

# Thread pool for blending operations
_executor = ThreadPoolExecutor(max_workers=4)

_HAND_PRESERVE_NAMES = (
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
)


def composite_tryon_professional(
    user_image_rgb: np.ndarray,
    warped_garment_rgba: np.ndarray,
    clothing_mask_u8: np.ndarray,
    pose: PoseResult,
) -> np.ndarray:
    """
    Erase original clothing under ``clothing_mask`` (inpaint), overlay warped garment,
    then restore face/head band and hands from the original photo.
    All images use RGB (uint8) except alpha in ``warped_garment_rgba``.
    """
    result = user_image_rgb.copy().astype(np.float32)
    h, w = result.shape[:2]

    cm = clothing_mask_u8
    if cm.shape[:2] != (h, w):
        cm = cv2.resize(cm, (w, h), interpolation=cv2.INTER_LINEAR)
    gwar = warped_garment_rgba
    if gwar.shape[:2] != (h, w):
        gwar = cv2.resize(gwar, (w, h), interpolation=cv2.INTER_LINEAR)

    clothing_mask_norm = cm.astype(np.float32) / 255.0
    inpaint_mask = ((cm > 128).astype(np.uint8) * 255)
    bgr = cv2.cvtColor(user_image_rgb, cv2.COLOR_RGB2BGR)
    base_bgr = cv2.inpaint(bgr, inpaint_mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    base_rgb = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

    for c in range(3):
        result[:, :, c] = result[:, :, c] * (1.0 - clothing_mask_norm) + base_rgb[:, :, c] * clothing_mask_norm

    if gwar.shape[2] == 4:
        garment_alpha_channel = gwar[:, :, 3].astype(np.float32) / 255.0
        garment_rgb = gwar[:, :, :3].astype(np.float32)
    else:
        garment_gray = cv2.cvtColor(gwar[:, :, :3], cv2.COLOR_RGB2GRAY)
        garment_alpha_channel = (garment_gray > 10).astype(np.float32)
        garment_rgb = gwar[:, :, :3].astype(np.float32)

    garment_alpha_channel = cv2.GaussianBlur(garment_alpha_channel, (5, 5), 2)
    ga = np.clip(garment_alpha_channel[:, :, np.newaxis], 0.0, 1.0)
    result = garment_rgb * ga + result * (1.0 - ga)

    preservation_mask = np.zeros((h, w), dtype=np.float32)
    if pose.success and pose.landmarks:
        ls = pose.landmarks.get("left_shoulder")
        rs = pose.landmarks.get("right_shoulder")
        if ls and rs:
            head_bottom = int(max(0, min(float(ls[1]), float(rs[1]))))
            preservation_mask[:head_bottom, :] = 1.0
        for name in _HAND_PRESERVE_NAMES:
            lm = pose.landmarks.get(name)
            if lm and float(lm[2]) > 0.3:
                cx, cy = int(lm[0]), int(lm[1])
                cv2.circle(preservation_mask, (cx, cy), 40, 1.0, -1)

    preservation_mask = cv2.GaussianBlur(preservation_mask, (31, 31), 15)
    pm = preservation_mask[:, :, np.newaxis]
    orig = user_image_rgb.astype(np.float32)
    result = orig * pm + result * (1.0 - pm)

    return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class BlendResult:
    """Result of image blending operation."""
    success: bool
    image: Optional["Image.Image"] = None
    mask: Optional[np.ndarray] = None
    blend_quality_score: float = 0.0
    lighting_match_score: float = 0.0
    edge_quality_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class LightingInfo:
    """Extracted lighting information from an image."""
    brightness: float = 0.5
    contrast: float = 0.5
    color_temperature: float = 0.5  # 0 = cool, 1 = warm
    dominant_light_direction: str = "front"  # front, left, right, top
    ambient_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)


class ImageBlender:
    """
    Blends garment images onto person images with photorealistic results.
    Uses multi-band blending, lighting matching, and edge refinement.
    """

    def __init__(self):
        self._initialized = PIL_AVAILABLE
        if self._initialized:
            logger.info("ImageBlender initialized")
        else:
            logger.warning("ImageBlender: PIL not available")

    def _extract_lighting_sync(self, image: "Image.Image") -> LightingInfo:
        """
        Extract lighting information from image (synchronous).
        
        Args:
            image: PIL Image
            
        Returns:
            LightingInfo with extracted lighting parameters
        """
        if not PIL_AVAILABLE:
            return LightingInfo()

        img_array = np.array(image.convert("RGB"))
        h, w = img_array.shape[:2]

        # Calculate brightness (average luminance)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        brightness = np.mean(gray) / 255.0

        # Calculate contrast (standard deviation)
        contrast = np.std(gray) / 128.0

        # Estimate color temperature (ratio of warm to cool colors)
        r_mean = np.mean(img_array[:, :, 0])
        b_mean = np.mean(img_array[:, :, 2])
        color_temp = (r_mean - b_mean) / (r_mean + b_mean + 1e-6) * 0.5 + 0.5

        # Estimate light direction from shadow analysis
        # Simplified: look at brightness gradient
        left_brightness = np.mean(gray[:, :w//3])
        right_brightness = np.mean(gray[:, 2*w//3:])
        top_brightness = np.mean(gray[:h//3, :])
        bottom_brightness = np.mean(gray[2*h//3:, :])

        if left_brightness > right_brightness + 10:
            direction = "left"
        elif right_brightness > left_brightness + 10:
            direction = "right"
        elif top_brightness > bottom_brightness + 10:
            direction = "top"
        else:
            direction = "front"

        # Calculate ambient color (median color)
        median_color = np.median(img_array.reshape(-1, 3), axis=0)
        ambient = tuple(c / 255.0 for c in median_color)

        return LightingInfo(
            brightness=brightness,
            contrast=min(1.0, contrast),
            color_temperature=color_temp,
            dominant_light_direction=direction,
            ambient_color=ambient
        )

    def _match_garment_lab_luma_sync(
        self,
        person_array: np.ndarray,
        garment_rgb: np.ndarray,
        alpha: np.ndarray,
    ) -> np.ndarray:
        """Full LAB statistics transfer: match garment L/a/b channels to person lighting.

        Uses mean+std transfer (Reinhard-style) with conservative blending
        so the garment adapts to the person's lighting environment without
        losing its original color identity.
        """
        a = np.clip(alpha.astype(np.float32) / 255.0, 0.0, 1.0)
        if float(np.max(a)) < 0.02:
            return garment_rgb
        lab_p = cv2.cvtColor(person_array, cv2.COLOR_RGB2LAB)
        lab_g = cv2.cvtColor(garment_rgb, cv2.COLOR_RGB2LAB)
        lp = lab_p.astype(np.float32)
        lg = lab_g.astype(np.float32)
        m = a > 0.08
        if not np.any(m):
            return garment_rgb

        # Blend ratio: how aggressively to match person lighting (0.4 = moderate)
        blend_strength = 0.4

        for ch in range(3):  # L, a, b channels
            person_ch = lp[:, :, ch]
            garment_ch = lg[:, :, ch]
            p_mean = float(np.sum(person_ch * a) / (np.sum(a) + 1e-6))
            p_std = float(np.sqrt(np.sum(((person_ch - p_mean) ** 2) * a) / (np.sum(a) + 1e-6))) + 1e-6
            g_mean = float(np.sum(garment_ch * a) / (np.sum(a) + 1e-6))
            g_std = float(np.sqrt(np.sum(((garment_ch - g_mean) ** 2) * a) / (np.sum(a) + 1e-6))) + 1e-6

            # Reinhard-style statistics transfer with conservative blending
            if ch == 0:  # L channel: stronger transfer for brightness matching
                transferred = ((garment_ch - g_mean) * (p_std / g_std)) + p_mean
                lg[:, :, ch] = np.clip(
                    garment_ch * (1.0 - blend_strength) + transferred * blend_strength * a,
                    0.0, 255.0,
                )
            else:  # a/b channels: subtle color temperature matching
                ch_strength = blend_strength * 0.3  # much subtler for chrominance
                transferred = ((garment_ch - g_mean) * (p_std / g_std)) + p_mean
                lg[:, :, ch] = np.clip(
                    garment_ch * (1.0 - ch_strength * a) + transferred * ch_strength * a,
                    0.0, 255.0,
                )

        out = cv2.cvtColor(lg.astype(np.uint8), cv2.COLOR_LAB2RGB)
        return out

    def _match_lighting_sync(
        self,
        garment_array: np.ndarray,
        person_lighting: LightingInfo,
        region_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Match garment lighting to person image lighting (synchronous).
        
        Args:
            garment_array: RGBA garment image as numpy array
            person_lighting: Lighting info from person image
            region_mask: Optional mask for the garment region
            
        Returns:
            Lighting-adjusted garment array
        """
        result = garment_array.copy()

        # Adjust brightness
        current_brightness = np.mean(result[:, :, :3][result[:, :, 3] > 128])
        target_brightness = person_lighting.brightness * 255
        brightness_factor = target_brightness / (current_brightness + 1e-6)
        brightness_factor = np.clip(brightness_factor, 0.5, 2.0)

        result[:, :, :3] = np.clip(
            result[:, :, :3] * brightness_factor, 0, 255
        ).astype(np.uint8)

        # Adjust color temperature
        if person_lighting.color_temperature > 0.55:
            # Warm: add slight orange tint
            result[:, :, 0] = np.clip(result[:, :, 0] * 1.05, 0, 255).astype(np.uint8)
            result[:, :, 1] = np.clip(result[:, :, 1] * 1.02, 0, 255).astype(np.uint8)
        elif person_lighting.color_temperature < 0.45:
            # Cool: add slight blue tint
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.05, 0, 255).astype(np.uint8)

        # Adjust contrast
        if person_lighting.contrast > 0.6:
            # Increase contrast
            mean = np.mean(result[:, :, :3][result[:, :, 3] > 128])
            contrast_factor = 1.0 + (person_lighting.contrast - 0.5) * 0.3
            result[:, :, :3] = np.clip(
                mean + (result[:, :, :3] - mean) * contrast_factor, 0, 255
            ).astype(np.uint8)

        return result

    def _generate_shadow_sync(
        self,
        garment_array: np.ndarray,
        person_array: np.ndarray,
        position: Tuple[int, int],
        light_direction: str
    ) -> np.ndarray:
        """
        Generate realistic shadow for garment (synchronous).
        
        Args:
            garment_array: RGBA garment image
            person_array: RGB person image
            position: Garment position (x, y)
            light_direction: Direction of light source
            
        Returns:
            Shadow layer as numpy array
        """
        h, w = person_array.shape[:2]
        shadow = np.zeros((h, w, 4), dtype=np.uint8)

        # Get garment alpha channel
        alpha = garment_array[:, :, 3]

        # Create shadow offset based on light direction
        offset_x, offset_y = 5, 8  # Default down-right
        if light_direction == "left":
            offset_x, offset_y = 8, 6
        elif light_direction == "right":
            offset_x, offset_y = -8, 6
        elif light_direction == "top":
            offset_x, offset_y = 0, 10

        # Create shadow mask
        garment_mask = (alpha > 128).astype(np.uint8) * 255
        shadow_mask = cv2.GaussianBlur(garment_mask, (21, 21), 0)

        # Dilate shadow slightly
        kernel = np.ones((5, 5), np.uint8)
        shadow_mask = cv2.dilate(shadow_mask, kernel, iterations=1)
        shadow_mask = cv2.GaussianBlur(shadow_mask, (15, 15), 0)

        # Place shadow on canvas
        x, y = position
        g_h, g_w = garment_array.shape[:2]

        # Calculate shadow position
        shadow_x = x + offset_x
        shadow_y = y + offset_y

        # Ensure shadow is within bounds
        src_y_start = max(0, -shadow_y)
        src_y_end = min(g_h, h - shadow_y)
        src_x_start = max(0, -shadow_x)
        src_x_end = min(g_w, w - shadow_x)

        dst_y_start = max(0, shadow_y)
        dst_y_end = min(h, shadow_y + g_h)
        dst_x_start = max(0, shadow_x)
        dst_x_end = min(w, shadow_x + g_w)

        if dst_y_end > dst_y_start and dst_x_end > dst_x_start:
            shadow_region = shadow_mask[src_y_start:src_y_end, src_x_start:src_x_end]
            shadow[dst_y_start:dst_y_end, dst_x_start:dst_x_end, 3] = shadow_region

        # Set shadow color (dark gray with transparency)
        shadow[:, :, :3] = [25, 25, 30]
        shadow[:, :, 3] = (shadow[:, :, 3] * 0.45).astype(np.uint8)

        return shadow

    def _multiband_blend_sync(
        self,
        person_array: np.ndarray,
        garment_array: np.ndarray,
        position: Tuple[int, int],
        feather_radius: int = 15
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Multi-band blending for seamless integration (synchronous).
        
        Args:
            person_array: RGB person image
            garment_array: RGBA garment image
            position: Garment position (x, y)
            feather_radius: Edge feathering radius
            
        Returns:
            Tuple of (blended image, blend mask)
        """
        h, w = person_array.shape[:2]
        result = person_array.copy()
        blend_mask = np.zeros((h, w), dtype=np.uint8)

        x, y = position
        g_h, g_w = garment_array.shape[:2]

        # Calculate overlap region
        src_y_start = max(0, -y)
        src_y_end = min(g_h, h - y)
        src_x_start = max(0, -x)
        src_x_end = min(g_w, w - x)

        dst_y_start = max(0, y)
        dst_y_end = min(h, y + g_h)
        dst_x_start = max(0, x)
        dst_x_end = min(w, x + g_w)

        if dst_y_end <= dst_y_start or dst_x_end <= dst_x_start:
            return result, blend_mask

        # Extract garment region
        garment_region = garment_array[src_y_start:src_y_end, src_x_start:src_x_end]
        alpha = garment_region[:, :, 3:4] / 255.0

        # Create feathered alpha for smooth edges
        alpha_blurred = cv2.GaussianBlur(
            garment_region[:, :, 3], (feather_radius * 2 + 1, feather_radius * 2 + 1), 0
        )
        alpha_blurred = alpha_blurred / 255.0
        alpha_blurred = alpha_blurred[:, :, np.newaxis]

        # Extract person region
        person_region = result[dst_y_start:dst_y_end, dst_x_start:dst_x_end]

        # Multi-band blending approach
        # 1. Create Laplacian pyramids
        levels = 4

        # Convert to float
        garment_float = garment_region[:, :, :3].astype(np.float32)
        person_float = person_region.astype(np.float32)

        # Simple multi-band approximation using weighted blending
        # Weight by alpha and distance from edge
        weight = alpha_blurred

        # Additional edge weight for smoother transition
        dist_from_edge = cv2.distanceTransform(
            (alpha_blurred[:, :, 0] * 255).astype(np.uint8),
            cv2.DIST_L2, 5
        )
        edge_weight = np.clip(dist_from_edge / feather_radius, 0, 1)
        edge_weight = edge_weight[:, :, np.newaxis]

        # Combine weights
        final_weight = weight * edge_weight + weight * (1 - edge_weight) * 0.8

        # Blend
        blended = (garment_float * final_weight + person_float * (1 - final_weight))
        blended = np.clip(blended, 0, 255).astype(np.uint8)

        # Apply to result
        result[dst_y_start:dst_y_end, dst_x_start:dst_x_end] = blended
        blend_mask[dst_y_start:dst_y_end, dst_x_start:dst_x_end] = (
            alpha_blurred[:, :, 0] * 255
        ).astype(np.uint8)

        return result, blend_mask

    def _refine_edges_sync(
        self,
        blended_array: np.ndarray,
        mask: np.ndarray,
        person_array: np.ndarray
    ) -> np.ndarray:
        """
        Refine edges for natural appearance (synchronous).
        
        Args:
            blended_array: Blended image
            mask: Blend mask
            person_array: Original person image
            
        Returns:
            Edge-refined image
        """
        result = blended_array.copy()

        # Find edge region
        edges = cv2.Canny(mask, 50, 150)
        edge_region = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)

        # Apply slight blur to edge region for smoother transition
        blurred = cv2.GaussianBlur(result, (5, 5), 0)

        # Blend original and blurred at edges
        edge_weight = edge_region[:, :, np.newaxis] / 255.0 * 0.3
        result = (result * (1 - edge_weight) + blurred * edge_weight).astype(np.uint8)

        # Color matching at edges
        # Sample colors from both sides of the edge and blend
        edge_coords = np.where(edge_region > 0)
        if len(edge_coords[0]) > 0:
            # Average color on garment side
            garment_colors = person_array[mask > 128]
            if len(garment_colors) > 0:
                avg_garment = np.mean(garment_colors, axis=0)

                # Adjust edge pixels slightly toward average
                for i in range(len(edge_coords[0])):
                    y, x = edge_coords[0][i], edge_coords[1][i]
                    result[y, x] = (result[y, x] * 0.9 + avg_garment * 0.1).astype(np.uint8)

        return result

    async def blend(
        self,
        person_image: "Image.Image",
        garment: ProcessedGarment,
        pose: PoseResult,
        target_region: Optional[BodyRegion] = None
    ) -> BlendResult:
        """
        Blend garment onto person image with photorealistic results.
        
        Args:
            person_image: PIL Image of person
            garment: ProcessedGarment from GarmentProcessor
            pose: PoseResult from PoseDetector
            target_region: Optional specific region to place garment
            
        Returns:
            BlendResult with final blended image
        """
        if not self._initialized:
            return BlendResult(
                success=False,
                error_message="PIL not available"
            )

        if not garment.success or garment.image is None:
            return BlendResult(
                success=False,
                error_message="Garment processing was not successful"
            )

        if not pose.success:
            return BlendResult(
                success=False,
                error_message="Pose detection was not successful"
            )

        loop = asyncio.get_event_loop()

        try:
            # Convert person image to RGB numpy array
            if person_image.mode != "RGB":
                person_image = person_image.convert("RGB")
            person_array = np.array(person_image)
            h, w = person_array.shape[:2]

            # Extract lighting from person image
            person_lighting = await loop.run_in_executor(
                _executor, self._extract_lighting_sync, person_image
            )

            # Determine target region based on garment category
            if target_region is None:
                target_region = self._get_target_region(garment.category, pose)

            if target_region is None:
                return BlendResult(
                    success=False,
                    error_message="Could not determine target region for garment"
                )

            # Convert garment to numpy array
            garment_array = np.array(garment.image)

            # Match lighting
            garment_array = await loop.run_in_executor(
                _executor,
                self._match_lighting_sync,
                garment_array,
                person_lighting
            )

            # Calculate position
            position = self._calculate_position(
                target_region, garment_array.shape[:2], w, h
            )

            # Generate shadow
            shadow = await loop.run_in_executor(
                _executor,
                self._generate_shadow_sync,
                garment_array,
                person_array,
                position,
                person_lighting.dominant_light_direction
            )

            # Apply shadow first
            shadow_alpha = shadow[:, :, 3:4] / 255.0
            person_with_shadow = (
                person_array * (1 - shadow_alpha) +
                shadow[:, :, :3] * shadow_alpha
            ).astype(np.uint8)

            # Multi-band blend garment onto person
            blended, blend_mask = await loop.run_in_executor(
                _executor,
                self._multiband_blend_sync,
                person_with_shadow,
                garment_array,
                position
            )

            # Refine edges
            final_result = await loop.run_in_executor(
                _executor,
                self._refine_edges_sync,
                blended,
                blend_mask,
                person_array
            )

            # Calculate quality scores
            lighting_score = self._calculate_lighting_match_score(
                final_result, person_array, blend_mask
            )
            edge_score = self._calculate_edge_quality_score(blend_mask)
            overall_score = (lighting_score + edge_score) / 2

            # Generate warnings
            warnings = []
            if overall_score < 0.7:
                warnings.append("Blend quality may be suboptimal")
            if edge_score < 0.6:
                warnings.append("Edge blending may be visible")

            return BlendResult(
                success=True,
                image=Image.fromarray(final_result, "RGB"),
                mask=blend_mask,
                blend_quality_score=overall_score,
                lighting_match_score=lighting_score,
                edge_quality_score=edge_score,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Blending failed: {e}")
            return BlendResult(
                success=False,
                error_message=str(e)
            )

    async def blend_fullframe(
        self,
        person_image: "Image.Image",
        garment_rgba: np.ndarray,
        pose: PoseResult,
        segmentation: SegmentationPack,
        feather_px: Optional[int] = None,
        material: Optional["MaterialProperties"] = None,
    ) -> BlendResult:
        """
        Blend a garment already warped to full canvas (HxWx4) onto the person.

        Uses region-based compositing: garment alpha is clipped to torso/clip masks, never applied
        on face/hair, local feather only (no full-frame alpha melt), shadow suppressed on protected
        zones, arms and face restored from the original photo.
        """
        if not self._initialized:
            return BlendResult(success=False, error_message="PIL not available")
        loop = asyncio.get_event_loop()

        def _region_sync() -> BlendResult:
            return blend_fullframe_region_safe_sync(
                self,
                person_image,
                garment_rgba,
                pose,
                segmentation,
                feather_px=feather_px,
                material=material,
            )

        return await loop.run_in_executor(_executor, _region_sync)

    async def refine_blend_once(
        self,
        person_image: "Image.Image",
        blended: "Image.Image",
        mask: Optional[np.ndarray],
        protected_mask: Optional[np.ndarray] = None,
    ) -> Optional["Image.Image"]:
        """Single self-heal pass on garment boundary only; never touches face/hair if protected_mask is set."""

        if not self._initialized or not PIL_AVAILABLE:
            return None
        loop = asyncio.get_event_loop()

        def _sync() -> "Image.Image":
            b = np.array(blended.convert("RGB")).astype(np.float32)
            p = np.array(person_image.convert("RGB")).astype(np.float32)
            h, w = b.shape[:2]
            if mask is None or mask.shape[:2] != (h, w):
                return blended
            # OpenCV Canny expects CV_8U input.
            # `mask` might be float depending on upstream ops, so clamp+cast.
            m_u8 = np.clip(mask, 0, 255).astype(np.uint8)
            edge = cv2.Canny(m_u8, 35, 90)
            ring = cv2.dilate(edge, np.ones((9, 9), np.uint8), iterations=2)
            ring = (ring > 0).astype(np.float32)[:, :, np.newaxis]
            if protected_mask is not None and protected_mask.shape[:2] == (h, w):
                prot = (protected_mask > 80).astype(np.float32)[:, :, np.newaxis]
                ring = ring * (1.0 - prot)
            smooth = cv2.bilateralFilter(b.astype(np.uint8), 11, 45, 45).astype(np.float32)
            # Match local luminance noise from person around garment boundary
            pn = p + np.random.randn(h, w, 3).astype(np.float32) * 1.2
            mixed = b * (1.0 - ring * 0.45) + smooth * (ring * 0.25) + pn * (ring * 0.2)
            return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8), "RGB")

        return await loop.run_in_executor(_executor, _sync)

    def _get_target_region(
        self,
        category: GarmentCategory,
        pose: PoseResult
    ) -> Optional[BodyRegion]:
        """Get target body region based on garment category."""
        if category == GarmentCategory.TOPS:
            return pose.upper_body_region or pose.torso_region
        elif category == GarmentCategory.BOTTOMS:
            return pose.lower_body_region
        elif category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY):
            return pose.full_body_region or pose.upper_body_region
        elif category == GarmentCategory.OUTERWEAR:
            return pose.upper_body_region or pose.torso_region
        else:
            return pose.torso_region

    def _calculate_position(
        self,
        region: BodyRegion,
        garment_size: Tuple[int, int],
        canvas_width: int,
        canvas_height: int
    ) -> Tuple[int, int]:
        """Calculate garment position based on body region."""
        g_w, g_h = garment_size

        # Center garment in region
        x = region.x + (region.width - g_w) // 2
        y = region.y + max(0, (region.height - g_h) // 4)  # Slight offset upward

        # Ensure within bounds
        x = max(0, min(x, canvas_width - g_w))
        y = max(0, min(y, canvas_height - g_h))

        return (x, y)

    def _calculate_lighting_match_score(
        self,
        blended: np.ndarray,
        original: np.ndarray,
        mask: np.ndarray
    ) -> float:
        """Calculate how well lighting matches between blended region and original."""
        # Compare luminance in blend region vs surrounding area
        blend_region = blended[mask > 128]
        if len(blend_region) == 0:
            return 1.0

        # Get surrounding area
        dilated = cv2.dilate(mask, np.ones((30, 30), np.uint8))
        surrounding_mask = dilated - mask
        surrounding_region = original[surrounding_mask > 128]

        if len(surrounding_region) == 0:
            return 1.0

        # Compare brightness
        blend_brightness = np.mean(blend_region)
        surrounding_brightness = np.mean(surrounding_region)

        brightness_diff = abs(blend_brightness - surrounding_brightness) / 255.0

        # Score: lower difference = higher score
        score = 1.0 - min(1.0, brightness_diff * 2)

        return score

    def _calculate_edge_quality_score(self, mask: np.ndarray) -> float:
        """Calculate edge smoothness score."""
        # Find edges
        edges = cv2.Canny(mask, 50, 150)

        # Calculate edge gradient smoothness
        grad_x = cv2.Sobel(mask, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(mask, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Smooth edges should have gradual gradients
        edge_pixels = gradient_magnitude[edges > 0]
        if len(edge_pixels) == 0:
            return 1.0

        # Lower variance in edge gradients = smoother
        gradient_variance = np.var(edge_pixels)
        score = 1.0 / (1.0 + gradient_variance / 1000)

        return min(1.0, score)

    def health_check(self) -> Dict[str, Any]:
        """Return health status."""
        return {
            "status": "ok" if self._initialized else "degraded",
            "service": "image-blender",
            "pil_available": PIL_AVAILABLE,
            "opencv_available": True
        }
