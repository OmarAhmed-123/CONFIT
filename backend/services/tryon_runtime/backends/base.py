from __future__ import annotations

from typing import Any, Dict, Tuple


class TryOnBackendBase:
    backend_name: str = "unknown"

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        raise NotImplementedError

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

