"""
CONFIT Backend — Virtual Try-On Service
=========================================
Integrates with IDM-VTON HuggingFace Space via Gradio Client
to perform photorealistic virtual garment try-on, with
edge-feathered compositing for seamless person-clothing merging.
"""

import os
import asyncio
import logging
import io
import tempfile
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

    class Image:  # noqa: E303
        pass

try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    Client = object
    handle_file = lambda x: x  # noqa: E731

from utils.image_utils import (
    base64_to_pil,
    download_image,
    GarmentImageDownloadError,
    pil_to_base64,
    download_image_to_temp,
    resize_image,
    cleanup_temp_file,
)

logger = logging.getLogger(__name__)
# Gradio/HF polling can emit noisy heartbeat 404 logs that are non-fatal.
# Keep application logs actionable.
logging.getLogger("httpx").setLevel(logging.WARNING)

# HuggingFace Space for IDM-VTON
TRYON_SPACE_ID = "yisol/IDM-VTON"

# Thread pool for blocking Gradio calls (predict is synchronous)
_executor = ThreadPoolExecutor(max_workers=2)

# Maximum retry attempts for transient Gradio failures
MAX_RETRIES = 2

# Garment categories for upper/lower body detection
UPPER_BODY_KEYWORDS = [
    "shirt", "t-shirt", "tshirt", "top", "blouse", "jacket", "coat",
    "sweater", "hoodie", "polo", "vest", "cardigan", "blazer",
    "pullover", "tank", "tee", "outerwear", "overcoat", "parka",
    "windbreaker", "bomber", "denim jacket", "leather jacket",
    "crop top", "tunic", "henley", "flannel",
]

LOWER_BODY_KEYWORDS = [
    "pants", "trousers", "jeans", "shorts", "skirt", "leggings",
    "chinos", "joggers", "sweatpants", "culottes", "cargo",
    "slacks", "khakis", "capri", "bermuda",
]

FULL_BODY_KEYWORDS = [
    "dress", "jumpsuit", "romper", "overall", "suit", "onesie",
    "gown", "bodysuit",
]

# Backup garment URLs used when a catalog URL returns HTTP 404.
# Can be overridden via env (comma-separated URLs).
_GARMENT_FALLBACK_URLS = {
    "upper_body": [
        "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=512&h=768&fit=crop&q=80",
        "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=512&h=768&fit=crop&q=80",
    ],
    "lower_body": [
        "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=512&h=768&fit=crop&q=80",
        "https://images.unsplash.com/photo-1542272604-787c3835535d?w=512&h=768&fit=crop&q=80",
    ],
    "dresses": [
        "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=512&h=768&fit=crop&q=80",
        "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=512&h=768&fit=crop&q=80",
    ],
}


def detect_garment_category(garment_name: str) -> str:
    """
    Detect whether the garment is upper body, lower body, or full body
    based on its name. Returns 'upper_body', 'lower_body', or 'dresses'.
    """
    name_lower = garment_name.lower()

    for keyword in FULL_BODY_KEYWORDS:
        if keyword in name_lower:
            return "dresses"

    for keyword in LOWER_BODY_KEYWORDS:
        if keyword in name_lower:
            return "lower_body"

    for keyword in UPPER_BODY_KEYWORDS:
        if keyword in name_lower:
            return "upper_body"

    return "upper_body"


class VirtualTryOnService:
    """
    Service for performing virtual try-on using IDM-VTON,
    with edge-feathered compositing for seamless image merging.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self._hf_token = hf_token
        self._client: Optional[Client] = None
        logger.info("VirtualTryOnService initialized")

    def _get_client(self) -> Client:
        """
        Lazily initialize the Gradio client connection.
        """
        if self._client is None:
            logger.info("Connecting to HuggingFace Space: %s", TRYON_SPACE_ID)
            try:
                self._client = Client(
                    TRYON_SPACE_ID,
                    token=self._hf_token or None,
                )
                logger.info("Connected to IDM-VTON Space successfully")
            except Exception as exc:
                logger.error("Failed to connect to IDM-VTON Space: %s", exc)
                raise ConnectionError(
                    f"Cannot connect to IDM-VTON model: {exc}"
                ) from exc
        return self._client

    def _call_predict(self, person_path: str, garment_path: str, garment_name: str):
        """
        Synchronous Gradio predict call — runs in a thread pool.
        Returns the result tuple (output_path, masked_image_path).
        """
        category = detect_garment_category(garment_name)
        logger.info("Detected garment category: %s (from: %s)", category, garment_name)

        client = self._get_client()

        result = client.predict(
            dict(
                background=handle_file(person_path),
                layers=[],
                composite=None,
            ),
            handle_file(garment_path),
            garment_name,
            True,
            False,
            30,
            42,
            api_name="/tryon",
        )

        return result

    @staticmethod
    def composite_merge(
        person_img: "Image.Image",
        result_img: "Image.Image",
        feather_radius: int = 12,
    ) -> "Image.Image":
        """
        Merge the try-on result with the original person image using
        edge-feathered alpha blending and luminance/color matching in the
        transition zone so the garment does not look pasted or AI-generated.

        - Larger feather radius for softer, more natural boundaries.
        - Luminance matching in the blend region to reduce visible seams.
        - Final pass keeps garment colors intact in the core region.
        """
        if not PIL_AVAILABLE:
            return result_img

        import numpy as np

        # Ensure both images have the same dimensions
        if person_img.size != result_img.size:
            result_img = result_img.resize(person_img.size, Image.Resampling.LANCZOS)

        # Ensure RGB mode
        if person_img.mode != "RGB":
            person_img = person_img.convert("RGB")
        if result_img.mode != "RGB":
            result_img = result_img.convert("RGB")

        person_arr = np.array(person_img, dtype=np.float32)
        result_arr = np.array(result_img, dtype=np.float32)

        # Per-pixel difference magnitude to find garment region
        diff = np.sqrt(np.sum((result_arr - person_arr) ** 2, axis=2))
        threshold = 25.0
        mask_binary = (diff > threshold).astype(np.float32)

        # Softer mask: multi-pass blur for natural falloff (avoids hard edges)
        mask_pil = Image.fromarray((mask_binary * 255).astype(np.uint8), mode="L")
        for _ in range(2):
            mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        mask_arr = np.array(mask_pil, dtype=np.float32) / 255.0

        # Expand mask to 3 channels for per-pixel blending
        mask_3d = np.stack([mask_arr, mask_arr, mask_arr], axis=2)

        # Luminance matching in blend region: adjust result pixels toward
        # original luminance in the transition zone so the boundary is less visible
        def luminance(rgb: np.ndarray) -> np.ndarray:
            return 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        lum_p = luminance(person_arr)
        lum_r = luminance(result_arr)
        lum_p_3d = np.stack([lum_p, lum_p, lum_p], axis=2)
        lum_r_3d = np.stack([lum_r, lum_r, lum_r], axis=2)

        # Only in transition zone (0 < mask < 1): nudge result toward person luminance
        eps = 1e-6
        transition = mask_3d * (1.0 - mask_3d)
        scale = np.where(
            lum_r_3d > eps,
            np.clip(lum_p_3d / (lum_r_3d + eps), 0.7, 1.3),
            1.0,
        )
        result_toned = result_arr * (1.0 - 0.4 * transition) + (result_arr * scale) * (0.4 * transition)
        result_toned = np.clip(result_toned, 0, 255).astype(np.float32)

        # Alpha blend: result (toned) over person using feathered mask
        composite_arr = result_toned * mask_3d + person_arr * (1.0 - mask_3d)
        composite_arr = np.clip(composite_arr, 0, 255).astype(np.uint8)

        return Image.fromarray(composite_arr, mode="RGB")

    async def _prepare_garment_for_vton(
        self,
        garment_image_url: str,
        garment_name: str,
    ) -> Tuple[str, List[str]]:
        """
        Download and preprocess garment into a background-removed PNG (RGBA).

        Why: IDM-VTON quality drops significantly when the garment image has
        a hard background/hanger/studio artifacts, causing "sticker" composites.
        """
        use_processing = os.getenv("VTON_PROCESS_GARMENT", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        warnings: List[str] = []
        category = detect_garment_category(garment_name)
        if not use_processing:
            return await download_image_to_temp(garment_image_url, suffix=".png"), warnings

        # Download bytes in-memory with robust fallback for dead catalog URLs.
        candidates: List[str] = [garment_image_url]
        env_key = f"TRYON_FALLBACK_GARMENT_URLS_{category.upper()}"
        env_urls = [u.strip() for u in (os.getenv(env_key, "") or "").split(",") if u.strip()]
        candidates.extend(env_urls)
        candidates.extend(_GARMENT_FALLBACK_URLS.get(category, []))

        raw = None
        primary_error: Optional[str] = None
        for idx, candidate in enumerate(candidates):
            try:
                raw = await download_image(candidate)
                if idx > 0:
                    warnings.append("primary_garment_url_unreachable_using_fallback_image")
                break
            except GarmentImageDownloadError as e:
                if idx == 0:
                    primary_error = str(e)
                continue
        if raw is None:
            raise GarmentImageDownloadError(primary_error or "Could not fetch garment image from any fallback URL")

        garment_img = Image.open(io.BytesIO(raw))
        if garment_img.mode not in ("RGBA", "RGB"):
            garment_img = garment_img.convert("RGBA")
        garment_img = garment_img.convert("RGBA")

        from services.tryon.warping.garment import GarmentProcessor

        processed = await GarmentProcessor().process(garment_img, garment_name)
        if not processed.success or processed.image is None:
            # Fallback to raw garment bytes that were downloaded successfully.
            raw_img = Image.open(io.BytesIO(raw)).convert("RGBA")
            raw_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
            raw_img.save(raw_path, format="PNG")
            return raw_path, warnings

        garment_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
        processed.image.save(garment_path, format="PNG")
        return garment_path, warnings

    async def process_tryon_detailed(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
    ) -> dict:
        """
        IDM-VTON try-on with identity-preserving mask-based compositing.

        Args:
            user_image_base64: Base64-encoded person image
            garment_image_url: URL of the garment image
            garment_name: Name of the garment (used for category detection)

        Returns:
            Dict:
              - result_image: data URI
              - quality_score: float
              - warnings: list[str]
              - validation: structured validation details
        """
        if not PIL_AVAILABLE or not GRADIO_AVAILABLE:
            logger.warning("Dependencies missing — returning original image as fallback.")
            return {
                "result_image": user_image_base64,
                "quality_score": 0.0,
                "warnings": ["dependencies_missing"],
                "validation": None,
            }

        person_path = None
        garment_path = None

        try:
            # Step 1: Prepare the person image (keep original size for final output)
            logger.info("[Step 1/4] Preparing person image...")
            person_img = base64_to_pil(user_image_base64)
            if person_img is None:
                raise ValueError("Failed to decode person image from base64")

            original_size = person_img.size
            person_img_for_model = resize_image(person_img, max_width=1024, max_height=1024)
            if person_img_for_model.mode != "RGB":
                person_img_for_model = person_img_for_model.convert("RGB")

            person_path = tempfile.NamedTemporaryFile(
                delete=False, suffix=".jpg"
            ).name
            person_img_for_model.save(person_path, "JPEG", quality=92)

            # Step 2: Download and preprocess garment image for VTON
            logger.info("[Step 2/4] Preparing garment for VTON...")
            garment_path, garment_prep_warnings = await self._prepare_garment_for_vton(
                garment_image_url=garment_image_url,
                garment_name=garment_name,
            )

            # Step 3: Call IDM-VTON with retry logic
            logger.info("[Step 3/4] Calling IDM-VTON model (this may take 30–60 seconds)...")
            loop = asyncio.get_event_loop()
            last_error = None

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = await loop.run_in_executor(
                        _executor,
                        self._call_predict,
                        person_path,
                        garment_path,
                        garment_name,
                    )
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "IDM-VTON attempt %d/%d failed: %s",
                        attempt, MAX_RETRIES, exc,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 * attempt)

            if last_error is not None:
                raise last_error

            # Step 4: Process and composite-merge the result
            logger.info("[Step 4/4] Compositing and merging result...")
            if isinstance(result, (list, tuple)):
                result_path = result[0] if result else None
            else:
                result_path = result

            if result_path is None:
                raise RuntimeError("Model returned empty result")

            result_img = Image.open(result_path)
            result_img = resize_image(result_img, max_width=1024, max_height=1024)

            # Identity-preserving blend at model resolution.
            warnings: list[str] = []
            warnings.extend(garment_prep_warnings)
            validation_data = None
            merged = None

            try:
                from services.vton_identity_compositor import (
                    VTONBlendParams,
                    build_pose_and_segmentation,
                    blend_idm_vton_result_with_masks,
                )

                logger.info("Running pose + segmentation for identity preservation...")
                pose, seg = await build_pose_and_segmentation(person_img_for_model)

                base_protect_blur = int(os.getenv("VTON_PROTECT_BLUR_PX", "13"))
                base_protect_dilate = int(os.getenv("VTON_PROTECT_DILATE_PX", "12"))

                params1 = VTONBlendParams(
                    protect_blur_px=base_protect_blur,
                    protect_dilate_px=base_protect_dilate,
                )
                merged1, validation1 = await blend_idm_vton_result_with_masks(
                    person_img=person_img_for_model,
                    idm_vton_img=result_img,
                    pose=pose,
                    seg=seg,
                    params=params1,
                )

                merged = merged1
                validation_data = validation1

                if not validation1.ok:
                    warnings.append(
                        f"identity_validation_failed_attempt1_overall={validation1.overall_quality:.3f} "
                        f"faceDiff={validation1.face_mean_abs_diff:.2f} bgDiff={validation1.bg_mean_abs_diff:.2f}"
                    )
                    # Retry refinement once: stronger protection feathering.
                    params2 = VTONBlendParams(
                        protect_blur_px=min(25, base_protect_blur + 6),
                        protect_dilate_px=base_protect_dilate + 6,
                        min_overall_quality=float(
                            os.getenv("VTON_MIN_OVERALL_QUALITY_RETRY", str(params1.min_overall_quality))
                        ),
                    )
                    merged2, validation2 = await blend_idm_vton_result_with_masks(
                        person_img=person_img_for_model,
                        idm_vton_img=result_img,
                        pose=pose,
                        seg=seg,
                        params=params2,
                    )
                    merged = merged2
                    validation_data = validation2

                    if not validation2.ok:
                        warnings.append(
                            "identity_validation_failed_attempt2; returning best available composite"
                        )

            except Exception as exc:
                # Fallback: older diff-based compositing (kept for safety).
                logger.warning("Mask-based compositing failed; using diff-based fallback: %s", exc)
                merged = self.composite_merge(person_img_for_model, result_img, feather_radius=8)
                warnings.append("mask_compositing_fallback")

            # Upscale result back to original upload size for a sharp, natural-looking output
            if original_size != merged.size and original_size[0] > merged.size[0]:
                merged = merged.resize(original_size, Image.Resampling.LANCZOS)

            result_base64 = pil_to_base64(merged, format="JPEG", quality=92)

            quality_score = float(getattr(validation_data, "overall_quality", 0.6) or 0.6) if validation_data else 0.6
            return {
                "result_image": result_base64,
                "quality_score": quality_score,
                "warnings": warnings,
                "validation": (
                    {
                        "ok": getattr(validation_data, "ok", None),
                        "overall_quality": getattr(validation_data, "overall_quality", None),
                        "face_mean_abs_diff": getattr(validation_data, "face_mean_abs_diff", None),
                        "bg_mean_abs_diff": getattr(validation_data, "bg_mean_abs_diff", None),
                        "evaluator_notes": getattr(validation_data, "evaluator_notes", None),
                    }
                    if validation_data is not None
                    else None
                ),
            }

        # NOTE: keep exception handling identical to old code
        except Exception as exc:
            logger.error("Virtual try-on processing failed: %s", str(exc))
            if "connect" in str(exc).lower() or "timeout" in str(exc).lower():
                self._client = None
            raise

        finally:
            cleanup_temp_file(person_path)
            cleanup_temp_file(garment_path)

    async def process_tryon(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
    ) -> str:
        """Backward-compatible wrapper: returns only result image (data URI)."""
        out = await self.process_tryon_detailed(
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
        )
        return out["result_image"]

            # (cleanup moved into process_tryon_detailed)
