"""
CONFIT Backend — Rotation Service
===================================
Generates perspective-transformed frames from a single source
image so the frontend can display a 360-degree rotation viewer.

Each frame applies incremental horizontal shear, subtle scaling,
and brightness adjustments to simulate viewing the subject from
a different angle.
"""

import io
import logging
import math
from typing import List

from utils.image_utils import (
    base64_to_pil,
    pil_to_base64,
)

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class RotationService:
    """Create rotation-frame sequences from a single photograph."""

    async def generate_frames(
        self,
        source_image_base64: str,
        frame_count: int = 36,
    ) -> List[str]:
        """
        Generate *frame_count* perspective-transformed copies of the
        source image, spaced evenly across 360 degrees.

        Returns a list of base64-encoded JPEG data-URIs.
        """
        if not PIL_AVAILABLE:
            logger.warning("Pillow is not installed; returning source image as single frame.")
            return [source_image_base64]

        source = base64_to_pil(source_image_base64)
        if source is None:
            raise ValueError("Failed to decode the source image from base64.")

        if source.mode != "RGB":
            source = source.convert("RGB")

        width, height = source.size
        frames: List[str] = []
        angle_step = 360.0 / frame_count

        for index in range(frame_count):
            angle_deg = index * angle_step
            angle_rad = math.radians(angle_deg)

            frame = self._create_perspective_frame(
                source, width, height, angle_rad,
            )
            frames.append(pil_to_base64(frame, format="JPEG", quality=85))

        logger.info("Generated %d rotation frames.", len(frames))
        return frames

    @staticmethod
    def _create_perspective_frame(
        source: "Image.Image",
        width: int,
        height: int,
        angle_rad: float,
    ) -> "Image.Image":
        """
        Apply an affine perspective simulation for a given rotation angle.

        The technique uses horizontal shear combined with non-uniform
        horizontal scaling to mimic the foreshortening that occurs when
        viewing a flat image from different horizontal angles.
        """
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Horizontal scale factor: narrows the image as it turns sideways
        h_scale = max(abs(cos_a), 0.25)

        # Horizontal shear coefficient (subtle)
        shear = sin_a * 0.08

        # Affine transform coefficients for PIL.Image.transform:
        #   (a, b, c, d, e, f)  maps output (x, y) → input (x', y'):
        #   x' = a*x + b*y + c
        #   y' = d*x + e*y + f
        scaled_width = int(width * h_scale)
        x_offset = (width - scaled_width) / 2.0

        coeffs = (
            1.0 / h_scale,    # a – horizontal stretch
            shear,             # b – horizontal shear
            -x_offset / h_scale,  # c – x offset
            0.0,               # d
            1.0,               # e
            0.0,               # f
        )

        frame = source.transform(
            (width, height),
            Image.AFFINE,
            coeffs,
            resample=Image.BICUBIC,
            fillcolor=(245, 245, 245),
        )

        # Subtle brightness variation to simulate ambient light change
        brightness_factor = 0.92 + 0.08 * abs(cos_a)
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(brightness_factor)

        return frame
