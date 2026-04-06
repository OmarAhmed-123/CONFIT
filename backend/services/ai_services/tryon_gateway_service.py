"""
CONFIT Backend — Try-On Gateway Service
========================================
High-quality virtual try-on via a cloud multimodal image model.

Providers (configure one):
- **Gemini** (recommended): set `GEMINI_API_KEY` from https://aistudio.google.com/apikey — free tier.
- **Lovable gateway** (legacy): set `LOVABLE_API_KEY` and optional `AI_GATEWAY_URL`.

Selection: `TRYON_GATEWAY_PROVIDER=auto|gemini|lovable` (default `auto` prefers Gemini when the key exists).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

AI_GATEWAY_URL = os.getenv(
    "AI_GATEWAY_URL",
    "https://ai.gateway.lovable.dev/v1/chat/completions",
)
GEMINI_API_BASE = os.getenv(
    "GEMINI_API_BASE",
    "https://generativelanguage.googleapis.com/v1beta",
).rstrip("/")
DEFAULT_GEMINI_TRYON_MODEL = os.getenv(
    "GEMINI_TRYON_MODEL",
    "gemini-2.5-flash-image",
)
FALLBACK_GEMINI_MODELS = tuple(
    m.strip()
    for m in os.getenv(
        "GEMINI_TRYON_MODEL_FALLBACKS",
        "gemini-3.1-flash-image-preview,gemini-3-pro-image-preview",
    ).split(",")
    if m.strip()
)


@dataclass
class GatewayTryOnResult:
    success: bool
    result_image: Optional[str] = None  # data URI or HTTPS URL
    quality_score: float = 0.0
    pose_detected: bool = False
    garment_category: str = "tops"
    warnings: list[str] | None = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result_image": self.result_image,
            "quality_score": self.quality_score,
            "pose_detected": self.pose_detected,
            "garment_category": self.garment_category,
            "warnings": self.warnings or [],
            "error": self.error,
        }


def _split_data_uri(data_uri_or_b64: str) -> Tuple[str, str]:
    """Return (mime_type, raw_base64) from a data URI or raw base64 string."""
    s = (data_uri_or_b64 or "").strip()
    m = re.match(r"^data:([^;]+);base64,(.+)$", s, re.DOTALL)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "image/jpeg", s


def _guess_mime_from_bytes(data: bytes) -> str:
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 2 and data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


class TryOnGatewayService:
    """
    Virtual try-on backed by Gemini (Google AI Studio) or the Lovable OpenAI-compatible gateway.
    """

    def __init__(self) -> None:
        self._gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self._lovable_key = (os.getenv("LOVABLE_API_KEY") or "").strip()
        self._provider_pref = (os.getenv("TRYON_GATEWAY_PROVIDER") or "auto").strip().lower()

    def _effective_provider(self) -> str:
        if self._provider_pref == "gemini":
            return "gemini" if self._gemini_key else "none"
        if self._provider_pref == "lovable":
            return "lovable" if self._lovable_key else "none"
        # auto
        if self._gemini_key:
            return "gemini"
        if self._lovable_key:
            return "lovable"
        return "none"

    async def process_tryon(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: Optional[str] = None,
        skin_undertone: str = "natural",
        strict_single_image: bool = True,
    ) -> Dict[str, Any]:
        if not user_image_base64 or len(user_image_base64) < 100:
            return GatewayTryOnResult(
                success=False,
                error="Invalid user image (too small or empty)",
            ).to_dict()

        if not garment_image_url.startswith(("http://", "https://")):
            return GatewayTryOnResult(
                success=False,
                error="Invalid garment image URL",
            ).to_dict()

        category = (garment_category or "clothing").lower()
        prompt = self._build_prompt(
            garment_name=garment_name or "the garment",
            garment_category=category,
            skin_undertone=skin_undertone or "natural",
            strict_single_image=strict_single_image,
        )

        provider = self._effective_provider()
        if provider == "none":
            return GatewayTryOnResult(
                success=False,
                error="No cloud try-on API configured — set GEMINI_API_KEY (recommended) or LOVABLE_API_KEY",
                warnings=["Gateway backend disabled due to missing API keys"],
            ).to_dict()

        if provider == "gemini":
            return await self._process_gemini(
                prompt=prompt,
                user_image_base64=user_image_base64,
                garment_image_url=garment_image_url,
                garment_category=category,
            )
        return await self._process_lovable(
            prompt=prompt,
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_category=category,
        )

    async def _fetch_garment_inline(self, garment_url: str) -> Tuple[str, str]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(garment_url)
            resp.raise_for_status()
            raw = resp.content
        mime = _guess_mime_from_bytes(raw)
        return mime, base64.standard_b64encode(raw).decode("ascii")

    def _parse_gemini_image_part(self, data: Dict[str, Any]) -> Optional[str]:
        candidates = data.get("candidates") or []
        for cand in candidates:
            content = cand.get("content") or {}
            for part in content.get("parts") or []:
                inline = part.get("inline_data") or part.get("inlineData")
                if not inline:
                    continue
                mime = (
                    inline.get("mime_type")
                    or inline.get("mimeType")
                    or "image/png"
                )
                b64 = inline.get("data")
                if b64:
                    return f"data:{mime};base64,{b64}"
        return None

    def _gemini_error_message(self, data: Dict[str, Any]) -> str:
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("status") or data)
        return str(err or data)

    async def _process_gemini(
        self,
        prompt: str,
        user_image_base64: str,
        garment_image_url: str,
        garment_category: str,
    ) -> Dict[str, Any]:
        user_mime, user_b64 = _split_data_uri(user_image_base64)
        try:
            garment_mime, garment_b64 = await self._fetch_garment_inline(garment_image_url)
        except httpx.HTTPStatusError as exc:
            logger.error("Garment download failed: %s", exc)
            return GatewayTryOnResult(
                success=False,
                error=f"Could not download garment image ({exc.response.status_code})",
            ).to_dict()
        except httpx.RequestError as exc:
            logger.error("Garment download error: %s", exc)
            return GatewayTryOnResult(
                success=False,
                error=f"Could not download garment image: {exc}",
            ).to_dict()

        multimodal_intro = (
            "Image 1 (first picture): the person to dress. "
            "Image 2 (second picture): the garment product reference. "
        )
        full_prompt = multimodal_intro + prompt

        models_to_try = (DEFAULT_GEMINI_TRYON_MODEL,) + tuple(
            m for m in FALLBACK_GEMINI_MODELS if m != DEFAULT_GEMINI_TRYON_MODEL
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": full_prompt},
                        {"inline_data": {"mime_type": user_mime, "data": user_b64}},
                        {"inline_data": {"mime_type": garment_mime, "data": garment_b64}},
                    ],
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }

        last_err = "Gemini request failed"
        async with httpx.AsyncClient(timeout=120.0) as client:
            for model in models_to_try:
                url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
                try:
                    response = await client.post(
                        url,
                        headers={
                            "x-goog-api-key": self._gemini_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                except httpx.RequestError as exc:
                    last_err = f"Gemini request failed: {exc}"
                    logger.warning("Gemini model %s: %s", model, exc)
                    continue

                if response.status_code == 404:
                    logger.info("Gemini model not available: %s — trying fallback", model)
                    try:
                        data = response.json()
                        last_err = self._gemini_error_message(data)
                    except Exception:
                        last_err = response.text or "model not found"
                    continue

                if response.status_code == 429:
                    return GatewayTryOnResult(
                        success=False,
                        error="High demand — please try again in a moment.",
                        warnings=["RATE_LIMITED"],
                    ).to_dict()

                if not response.is_success:
                    try:
                        data = response.json()
                        last_err = self._gemini_error_message(data)
                    except Exception:
                        last_err = response.text or str(response.status_code)
                    logger.error("Gemini error [%s]: %s", response.status_code, last_err)
                    return GatewayTryOnResult(
                        success=False,
                        error=f"AI processing failed: {last_err}",
                    ).to_dict()

                data = response.json()
                image_uri = self._parse_gemini_image_part(data)
                if image_uri:
                    warnings: list[str] = []
                    if self._looks_like_collage(image_uri):
                        warnings.append("gateway_output_suspicious_layout")
                    return GatewayTryOnResult(
                        success=True,
                        result_image=image_uri,
                        quality_score=0.88,
                        pose_detected=True,
                        garment_category=garment_category,
                        warnings=warnings,
                    ).to_dict()

                last_err = self._gemini_error_message(data)
                logger.error("No image in Gemini response: %s", last_err)

        return GatewayTryOnResult(
            success=False,
            error=f"Failed to generate try-on image — {last_err}",
        ).to_dict()

    async def _process_lovable(
        self,
        prompt: str,
        user_image_base64: str,
        garment_image_url: str,
        garment_category: str,
    ) -> Dict[str, Any]:
        if not self._lovable_key:
            return GatewayTryOnResult(
                success=False,
                error="LOVABLE_API_KEY is not configured",
                warnings=["Lovable gateway selected but key missing"],
            ).to_dict()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    AI_GATEWAY_URL,
                    headers={
                        "Authorization": f"Bearer {self._lovable_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "google/gemini-3-pro-image-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": user_image_base64}},
                                    {"type": "image_url", "image_url": {"url": garment_image_url}},
                                ],
                            }
                        ],
                        "modalities": ["image", "text"],
                    },
                )
        except httpx.RequestError as exc:
            logger.error("AI gateway request failed: %s", exc)
            return GatewayTryOnResult(
                success=False,
                error=f"AI gateway request failed: {exc}",
            ).to_dict()

        if response.status_code == 429:
            return GatewayTryOnResult(
                success=False,
                error="High demand — please try again in a moment.",
                warnings=["RATE_LIMITED"],
            ).to_dict()
        if response.status_code == 402:
            return GatewayTryOnResult(
                success=False,
                error="Usage limit reached. Please try again later.",
                warnings=["CREDITS_EXHAUSTED"],
            ).to_dict()

        if not response.is_success:
            logger.error("AI gateway error [%s]: %s", response.status_code, response.text)
            return GatewayTryOnResult(
                success=False,
                error=f"AI processing failed: {response.status_code}",
            ).to_dict()

        data = response.json()
        logger.info("Lovable gateway response received successfully")

        generated_image_url: Optional[str] = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("images", [{}])[0]
            .get("image_url", {})
            .get("url")
        )
        if not generated_image_url:
            logger.error("No image returned by AI: %s", data)
            return GatewayTryOnResult(
                success=False,
                error="Failed to generate try-on image — no image in response",
            ).to_dict()

        warnings: list[str] = []
        if self._looks_like_collage(generated_image_url):
            warnings.append("gateway_output_suspicious_layout")

        return GatewayTryOnResult(
            success=True,
            result_image=generated_image_url,
            quality_score=0.9,
            pose_detected=True,
            garment_category=garment_category,
            warnings=warnings,
            error=None,
        ).to_dict()

    def _build_prompt(
        self,
        garment_name: str,
        garment_category: str,
        skin_undertone: str,
        strict_single_image: bool,
    ) -> str:
        category_rules: Dict[str, str] = {
            "tops": """- The top must sit naturally on the shoulders, following the collarbone line
- Sleeve length must match the garment's design (short/long/3-quarter)
- The hem should fall at the correct waist/hip level based on the garment's cut
- Show natural fabric creases at the elbow bend and underarm""",
            "bottoms": """- Waistband sits at the natural waist or hip based on the pant rise
- Leg silhouette follows the garment's cut (slim/straight/wide/bootcut)
- Fabric drapes naturally around knees and ankles
- Hem break matches the trouser style""",
            "dresses": """- Neckline frames the décolletage correctly for the dress style
- Waist definition matches the dress silhouette (A-line/bodycon/shift)
- Skirt length and volume are accurate to the original garment
- Fabric flow follows gravity and body movement naturally""",
            "outerwear": """- Coat/jacket layers visibly over the existing outfit underneath
- Shoulder seams align with natural shoulder points
- Lapels, collar, and buttons are positioned anatomically correct
- The garment's structure (structured blazer vs soft cardigan) is maintained""",
            "shoes": """- Shoes fit naturally on the feet with correct perspective
- Shoe style and proportions match the original product exactly
- Shadows and ground contact look realistic""",
            "accessories": """- Accessory placement is anatomically correct (wrist for watch, neck for necklace)
- Scale matches the person's proportions
- Reflections and material finish are realistic""",
        }

        normalized_category = garment_category if garment_category in category_rules else "tops"
        fit_instructions = category_rules[normalized_category]

        single_image_rules = """
## ABSOLUTE OUTPUT FORMAT RULES
1. Generate **ONE** single-frame image only.
2. Do NOT create collages, split-screens, or before/after comparisons.
3. Do NOT place the garment or person image in separate panels.
4. The final image must look like a single photograph of the dressed person.
"""

        return f"""You are an elite fashion technology AI specializing in photorealistic virtual try-on. Your task is to dress the person in Image 1 with the exact garment shown in Image 2 ("{garment_name}").

## CRITICAL REQUIREMENTS — PRESERVATION
1. The person's face, hair, skin tone ({skin_undertone} undertone), body proportions, and pose must remain PIXEL-PERFECT identical
2. The original background, lighting direction, and ambient color temperature must be preserved exactly
3. Do NOT alter body shape, weight, height, or any physical features
4. Hands, fingers, and any visible skin must remain untouched

## GARMENT APPLICATION — {normalized_category.upper()}
{fit_instructions}

## PHOTOREALISM STANDARDS
- Match the garment's exact color, pattern, texture, and material finish from Image 2
- Shadows on the garment must follow the same light source as the original photo
- Fabric interaction with body (stretching over curves, compression at joints, gravity drape) must be physically accurate
- Seams, stitching details, logos, and hardware (zippers, buttons) must be visible and correctly placed
- Color accuracy: the garment color in the result must match Image 2 exactly — no color shifting

{single_image_rules if strict_single_image else ""}

## OUTPUT
Generate a single high-resolution photorealistic image. The result should be indistinguishable from a professional fashion photograph taken in a studio."""

    def _looks_like_collage(self, image_ref: str) -> bool:
        if not image_ref.startswith("data:image/"):
            return False

        try:
            header, b64 = image_ref.split(",", 1)
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw))
            w, h = img.size
            aspect = w / float(h or 1)
            return aspect > 1.8
        except Exception:
            return False
