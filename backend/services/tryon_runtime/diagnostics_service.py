from __future__ import annotations

from typing import Any, Dict

from .capability_registry import CapabilityRegistry


class DiagnosticsService:
    """Runtime diagnostics for frontend and ops visibility."""

    def __init__(self) -> None:
        self._registry = CapabilityRegistry()

    def snapshot(self) -> Dict[str, Any]:
        caps = self._registry.snapshot().to_dict()
        return {"capabilities": caps, "health_summary": caps.get("details", {}).get("health", {})}

