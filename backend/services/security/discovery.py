"""
CONFIT Security — Auto-Discovery Service
==========================================
Discovers scan targets by reading the FastAPI OpenAPI schema
and extracting all registered routes with their methods and tags.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("confit.security.discovery")


class TargetDiscovery:
    """Auto-discovers API endpoints and services for security scanning."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        web_base_url: Optional[str] = None,
    ):
        self._api_base_url = api_base_url.rstrip("/")
        self._web_base_url = (web_base_url or os.getenv("SECURITY_INTERNAL_WEB_BASE_URL", "https://nginx")).rstrip(
            "/"
        )

    def _repo_root(self) -> Path:
        # discovery.py -> backend/services/security -> backend/services -> backend -> repo root
        return Path(__file__).resolve().parents[3]

    def _discover_react_routes_from_app_tsx(self) -> List[str]:
        """
        Extract route paths from `src/App.tsx` (React Router <Route path="..."> usage).
        """
        app_tsx = self._repo_root() / "src" / "App.tsx"
        if not app_tsx.exists():
            return []

        content = app_tsx.read_text(encoding="utf-8", errors="ignore")
        # Matches: <Route path="/security" element=... />
        paths = re.findall(r'path\s*=\s*"([^"]+)"', content)
        # React Router also includes "*" wildcard; keep but exclude non-path tokens.
        uniq = []
        seen = set()
        for p in paths:
            if p and p not in seen:
                seen.add(p)
                uniq.append(p)
        return uniq

    async def discover_api_routes(self) -> List[Dict[str, Any]]:
        """
        Fetch FastAPI OpenAPI schema and extract all routes.

        Returns:
            List of dicts with path, methods, tags, description
        """
        routes: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._api_base_url}/openapi.json")
                resp.raise_for_status()
                schema = resp.json()
        except Exception as exc:
            logger.error("Failed to fetch OpenAPI schema: %s", exc)
            return routes

        paths = schema.get("paths", {})
        for path, methods_spec in paths.items():
            for method, details in methods_spec.items():
                if method.lower() in ("get", "post", "put", "patch", "delete"):
                    routes.append({
                        "path": path,
                        "method": method.upper(),
                        "tags": details.get("tags", []),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "has_auth": any(
                            "security" in str(details).lower()
                            for _ in [1]
                        ),
                        "url": f"{self._api_base_url}{path}",
                    })

        logger.info("Discovered %d API routes from OpenAPI schema", len(routes))
        return routes

    async def discover_services(self) -> List[Dict[str, Any]]:
        """
        Discover known services in the Docker network.

        Returns:
            List of service targets with name, url, type
        """
        services = [
            {
                "name": "CONFIT API",
                "url": f"{self._api_base_url}",
                "type": "api",
                "description": "Main FastAPI backend server",
            },
            {
                "name": "CONFIT API Health",
                "url": f"{self._api_base_url}/api/health",
                "type": "health",
                "description": "Backend health check endpoint",
            },
            {
                "name": "CONFIT API Docs",
                "url": f"{self._api_base_url}/docs",
                "type": "docs",
                "description": "Swagger/OpenAPI documentation",
            },
            {
                "name": "CONFIT Web",
                "url": f"{self._web_base_url}",
                "type": "web",
                "description": "Frontend entry served behind nginx",
                "accessible": None,
                "status_code": None,
            },
        ]

        # Check only API endpoints (avoid TLS verification issues for web discovery).
        accessible: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for svc in services:
                if svc["type"] != "api" and svc["type"] != "health" and svc["type"] != "docs":
                    accessible.append(svc)
                    continue

                try:
                    resp = await client.get(svc["url"])
                    svc["accessible"] = resp.status_code < 500
                    svc["status_code"] = resp.status_code
                except Exception:
                    svc["accessible"] = False
                    svc["status_code"] = None
                accessible.append(svc)

        return accessible

    async def get_scan_targets(self) -> Dict[str, Any]:
        """
        Get all discovered scan targets in a scan-ready format.

        Returns:
            Dict with routes, services, and summary
        """
        routes = await self.discover_api_routes()
        web_routes = await self.discover_frontend_routes()
        services = await self.discover_services()

        # Group API routes by tag
        tags: Dict[str, int] = {}
        for route in routes:
            for tag in route.get("tags", ["untagged"]):
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "api_routes": routes,
            "web_routes": web_routes,
            "services": services,
            "summary": {
                "total_routes": len(routes),
                "total_web_routes": len(web_routes),
                "total_services": len(services),
                "route_groups": tags,
                "methods": {
                    m: sum(1 for r in routes if r["method"] == m)
                    for m in set(r["method"] for r in routes)
                },
            },
        }

    async def discover_frontend_routes(self) -> List[Dict[str, Any]]:
        """
        Discover frontend routes from React Router source code.
        """
        routes = self._discover_react_routes_from_app_tsx()
        discovered: List[Dict[str, Any]] = []
        for p in routes:
            if not p.startswith("/"):
                continue
            discovered.append(
                {
                    "path": p,
                    "method": "GET",
                    "tags": ["react-route"],
                    "summary": "React route",
                    "url": f"{self._web_base_url}{p}",
                }
            )
        return discovered
