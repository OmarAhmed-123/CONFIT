"""
CONFIT Backend — MCP Model Router
===================================
Selects the optimal try-on model based on request type,
hardware availability, and service health.

Implements the Strategy pattern — each model backend exposes a
common interface so the router can swap them transparently.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModelBackend(str, Enum):
    """Available model backends in priority order."""
    # Dedicated diffusion VTON API (https://docs.fashn.ai)
    FASHN = "fashn"
    # High-level diffusion / gateway-based virtual try-on (prompt + multi-modal model)
    GATEWAY = "gateway"
    # Full AI pipeline (pose + segmentation + blend)
    ADVANCED = "advanced"
    # External diffusion VTON (e.g. IDM-VTON via HuggingFace / Gradio)
    HUGGINGFACE = "huggingface"
    # Local compositing fallback
    LOCAL = "local"


class ModelRouter:
    """Selects best available model backend for a try-on request.

    Selection priority:
    1. FASHN diffusion try-on (if `FASHN_API_KEY` configured)
    2. HuggingFace IDM-VTON (via Gradio; works without `HF_TOKEN` if the Space is public)
    3. Advanced AI pipeline (pose + segmentation + blend)
    4. Local PIL compositing (fallback)

    Usage:
        router = ModelRouter()
        backend = router.select(category="tops", quality="high")
    """

    def __init__(self) -> None:
        self._availability: dict[str, bool] = {
            ModelBackend.FASHN: False,
            ModelBackend.GATEWAY: False,
            ModelBackend.ADVANCED: False,
            ModelBackend.HUGGINGFACE: False,
            ModelBackend.LOCAL: True,  # Always available
        }
        self._probe_backends()

    def _probe_backends(self) -> None:
        """Check which backends are actually importable / configured."""
        import os

        # Reset dynamic availability each probe; local stays always true.
        self._availability[ModelBackend.FASHN] = False
        self._availability[ModelBackend.GATEWAY] = False
        self._availability[ModelBackend.ADVANCED] = False
        self._availability[ModelBackend.HUGGINGFACE] = False
        self._availability[ModelBackend.LOCAL] = True

        # FASHN — diffusion try-on (not overlay)
        if os.getenv("FASHN_API_KEY"):
            try:
                from services.tryon.fashn_tryon_service import FashnTryOnService  # noqa: F401

                self._availability[ModelBackend.FASHN] = True
                logger.info("ModelRouter: FASHN backend available (FASHN_API_KEY set)")
            except ImportError:
                logger.info("ModelRouter: FASHN module import failed")

        # Cloud multimodal try-on (Gemini / Lovable)
        # Disabled by default to comply with "do not use Gemini/GPT for try-on".
        enable_gateway = os.getenv("TRYON_ENABLE_GEMINI_GATEWAY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        try:
            from services.ai_services.tryon_gateway_service import (  # type: ignore  # noqa: F401
                TryOnGatewayService,
            )

            if enable_gateway and (os.getenv("GEMINI_API_KEY") or os.getenv("LOVABLE_API_KEY")):
                self._availability[ModelBackend.GATEWAY] = True
                logger.info("ModelRouter: Gateway backend enabled (TRYON_ENABLE_GEMINI_GATEWAY=1)")
            elif enable_gateway:
                logger.info(
                    "ModelRouter: Gateway backend disabled (missing GEMINI_API_KEY / LOVABLE_API_KEY)"
                )
            else:
                logger.info(
                    "ModelRouter: Gateway backend disabled by default (set TRYON_ENABLE_GEMINI_GATEWAY=1 to enable)"
                )
        except ImportError:
            logger.info("ModelRouter: Gateway backend module not available")

        # Advanced service
        try:
            from services.advanced_tryon_service import AdvancedTryOnService
            self._availability[ModelBackend.ADVANCED] = True
            logger.info("ModelRouter: Advanced backend available")
        except ImportError:
            logger.info("ModelRouter: Advanced backend not available")

        # HuggingFace (IDM-VTON via Gradio)
        # Mark it available if the module is importable.
        # If the Space is gated, requests will fail and the pipeline will fallback.
        try:
            from services.tryon_service import VirtualTryOnService  # noqa: F401

            self._availability[ModelBackend.HUGGINGFACE] = True
            if os.getenv("HF_TOKEN"):
                logger.info("ModelRouter: HuggingFace backend available (HF_TOKEN configured)")
            else:
                logger.info(
                    "ModelRouter: HuggingFace backend available (no HF_TOKEN; using public access if available)"
                )
        except ImportError:
            logger.info("ModelRouter: HuggingFace backend not available (import failed)")

        # Local is always available
        logger.info("ModelRouter: Local backend available (fallback)")

    def select(
        self,
        category: str = "tops",
        quality: str = "auto",
        force_backend: Optional[str] = None,
    ) -> ModelBackend:
        """Select the best model backend.

        Args:
            category: Garment category (tops, bottoms, dresses, etc.)
            quality: "high" (prefer advanced), "fast" (prefer local), or "auto"
            force_backend: Force a specific backend (for testing)

        Returns:
            ModelBackend enum value
        """
        # Forced selection
        if force_backend:
            try:
                backend = ModelBackend(force_backend)
            except ValueError:
                logger.warning("Forced backend '%s' is not a valid backend, ignoring", force_backend)
            else:
                if self._availability.get(backend, False):
                    return backend
                logger.warning("Forced backend '%s' not available, falling back", force_backend)

        # Quality-based routing
        if quality == "fast":
            # Fast path explicitly prefers the lightweight local compositing backend
            return ModelBackend.LOCAL

        # Default priority chain for best quality:
        # 1) FASHN diffusion try-on (tryon-v1.6)
        # 2) HuggingFace IDM-VTON (via Gradio)
        # 3) Advanced in-house pipeline
        # 4) Gateway (Gemini / Lovable) [disabled by default]
        # 5) Local PIL fallback (never preferred for realism)
        if self._availability[ModelBackend.FASHN]:
            return ModelBackend.FASHN

        if self._availability[ModelBackend.HUGGINGFACE]:
            return ModelBackend.HUGGINGFACE

        if self._availability[ModelBackend.ADVANCED]:
            return ModelBackend.ADVANCED

        if self._availability[ModelBackend.GATEWAY]:
            return ModelBackend.GATEWAY

        return ModelBackend.LOCAL

    def is_available(self, backend: ModelBackend) -> bool:
        return self._availability.get(backend, False)

    def mark_unavailable(self, backend: ModelBackend) -> None:
        """Mark a backend as temporarily unavailable (e.g. after failure)."""
        self._availability[backend] = False
        logger.warning("ModelRouter: Marked %s as unavailable", backend.value)

    def mark_available(self, backend: ModelBackend) -> None:
        self._availability[backend] = True

    def refresh(self) -> None:
        """Re-probe backend availability (used after runtime config changes)."""
        self._probe_backends()

    def available_backends(self) -> list[str]:
        return [b for b, avail in self._availability.items() if avail]

    def stats(self) -> dict:
        return {
            "available_backends": self.available_backends(),
            "default_selection": self.select().value,
        }
