"""
CONFIT Security — PentAGI Async Client
=======================================
Wraps PentAGI's GraphQL and REST APIs for programmatic scan management.

Usage:
    client = PentAGIClient()
    flow_id = await client.start_scan("http://api:8000", "api")
    status  = await client.get_scan_status(flow_id)
    report  = await client.get_scan_report(flow_id)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("confit.security.pentagi")


class PentAGIClient:
    """Async client for PentAGI AI penetration testing platform."""

    # GraphQL queries
    _GQL_CREATE_FLOW = """
    mutation CreateFlow($input: CreateFlowInput!) {
        createFlow(input: $input) {
            id
            title
            status
            createdAt
        }
    }
    """

    _GQL_GET_FLOW = """
    query GetFlow($id: ID!) {
        flow(id: $id) {
            id
            title
            status
            createdAt
            updatedAt
            tasks {
                id
                name
                status
                result
                subtasks {
                    id
                    name
                    status
                    agentType
                    actions {
                        id
                        type
                        status
                        result
                    }
                }
            }
        }
    }
    """

    _GQL_LIST_FLOWS = """
    query ListFlows {
        flows {
            id
            title
            status
            createdAt
            updatedAt
        }
    }
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        ssl_verify: Optional[bool] = None,
    ):
        self._base_url = (
            base_url or os.getenv("PENTAGI_URL", "https://pentagi:8443")
        ).rstrip("/")

        self._api_token = api_token or os.getenv("PENTAGI_API_TOKEN", "")

        _verify_env = os.getenv("PENTAGI_SSL_VERIFY", "true")
        self._ssl_verify_bool = (
            ssl_verify if ssl_verify is not None
            else _verify_env.lower() in ("true", "1", "yes")
        )
        ca_path = os.getenv("PENTAGI_CA_CERT_PATH") or os.getenv("PENTAGI_CA_BUNDLE_PATH")
        # httpx accepts `verify=True/False` or a path to a CA bundle file.
        self._http_verify = ca_path if (self._ssl_verify_bool and ca_path) else self._ssl_verify_bool

        self._graphql_url = f"{self._base_url}/api/v1/graphql"
        self._rest_url = f"{self._base_url}/api/v1"

        logger.info(
            "PentAGI client initialized — url=%s ssl_verify=%s token_set=%s",
            self._base_url,
            self._http_verify,
            bool(self._api_token),
        )

    # ── Internal Helpers ──────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        """Build request headers with Bearer auth."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        """Create a configured async HTTP client."""
        return httpx.AsyncClient(
            verify=self._http_verify,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers=self._headers(),
        )

    async def _graphql(
        self, query: str, variables: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against PentAGI."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with self._client() as client:
            resp = await client.post(self._graphql_url, json=payload)
            resp.raise_for_status()
            result = resp.json()

        if "errors" in result and result["errors"]:
            error_msgs = "; ".join(e.get("message", str(e)) for e in result["errors"])
            raise PentAGIError(f"GraphQL errors: {error_msgs}")

        return result.get("data", {})

    # ── Health Check ──────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check if PentAGI server is reachable."""
        try:
            async with self._client() as client:
                resp = await client.get(
                    f"{self._rest_url}/health",
                    timeout=httpx.Timeout(10.0),
                )
                return resp.status_code == 200
        except Exception as exc:
            logger.warning("PentAGI health check failed: %s", exc)
            return False

    # ── Scan Operations ───────────────────────────────────────────────────

    async def start_scan(
        self,
        target: str,
        scan_type: str = "full",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start a new penetration test scan.

        Args:
            target: URL or host to scan (e.g., "http://api:8000")
            scan_type: Type of scan — "api", "web", "auth", "full"
            description: Optional description of the scan task

        Returns:
            Dict with flow id, title, status, createdAt
        """
        if not self._api_token:
            raise PentAGIError(
                "PENTAGI_API_TOKEN not configured. "
                "Generate a token from PentAGI Settings > API Tokens."
            )

        prompt = self._build_scan_prompt(target, scan_type, description)

        variables = {
            "input": {
                "title": f"CONFIT Security Scan — {scan_type.upper()} — {target}",
                "description": prompt,
            }
        }

        try:
            data = await self._graphql(self._GQL_CREATE_FLOW, variables)
            flow = data.get("createFlow", {})
            logger.info(
                "Scan started: flow_id=%s target=%s type=%s",
                flow.get("id"),
                target,
                scan_type,
            )
            return flow
        except httpx.HTTPStatusError as exc:
            logger.error("Failed to start scan: HTTP %s", exc.response.status_code)
            raise PentAGIError(f"HTTP {exc.response.status_code}: {exc.response.text}")
        except Exception as exc:
            logger.error("Failed to start scan: %s", exc)
            raise PentAGIError(str(exc))

    async def get_scan_status(self, flow_id: str) -> Dict[str, Any]:
        """
        Get the status of a running scan.

        Returns:
            Dict with flow id, title, status, tasks summary
        """
        try:
            data = await self._graphql(self._GQL_GET_FLOW, {"id": flow_id})
            flow = data.get("flow", {})
            return {
                "id": flow.get("id"),
                "title": flow.get("title"),
                "status": flow.get("status", "unknown"),
                "created_at": flow.get("createdAt"),
                "updated_at": flow.get("updatedAt"),
                "tasks_count": len(flow.get("tasks", [])),
                "tasks": [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "status": t.get("status"),
                    }
                    for t in flow.get("tasks", [])
                ],
            }
        except Exception as exc:
            logger.error("Failed to get scan status for %s: %s", flow_id, exc)
            raise PentAGIError(str(exc))

    async def get_scan_report(self, flow_id: str) -> Dict[str, Any]:
        """
        Get full scan report with findings.

        Returns:
            Dict with flow details, tasks, subtasks, actions, and parsed findings
        """
        try:
            data = await self._graphql(self._GQL_GET_FLOW, {"id": flow_id})
            flow = data.get("flow", {})

            # Extract findings from task results
            findings = []
            raw_outputs = []

            for task in flow.get("tasks", []):
                if task.get("result"):
                    raw_outputs.append(task["result"])
                    parsed = self._parse_findings(task["result"])
                    findings.extend(parsed)

                for subtask in task.get("subtasks", []):
                    for action in subtask.get("actions", []):
                        if action.get("result"):
                            raw_outputs.append(action["result"])

            return {
                "id": flow.get("id"),
                "title": flow.get("title"),
                "status": flow.get("status"),
                "created_at": flow.get("createdAt"),
                "updated_at": flow.get("updatedAt"),
                "findings": findings,
                "raw_ai_output": "\n---\n".join(raw_outputs),
                "summary": {
                    "total": len(findings),
                    "critical": sum(1 for f in findings if f["severity"] == "critical"),
                    "high": sum(1 for f in findings if f["severity"] == "high"),
                    "medium": sum(1 for f in findings if f["severity"] == "medium"),
                    "low": sum(1 for f in findings if f["severity"] == "low"),
                    "info": sum(1 for f in findings if f["severity"] == "info"),
                },
            }
        except Exception as exc:
            logger.error("Failed to get report for %s: %s", flow_id, exc)
            raise PentAGIError(str(exc))

    async def list_scans(self) -> List[Dict[str, Any]]:
        """List all scan flows."""
        try:
            data = await self._graphql(self._GQL_LIST_FLOWS)
            return data.get("flows", [])
        except Exception as exc:
            logger.error("Failed to list scans: %s", exc)
            raise PentAGIError(str(exc))

    # ── Prompt Builder ────────────────────────────────────────────────────

    @staticmethod
    def _build_scan_prompt(
        target: str, scan_type: str, description: Optional[str] = None
    ) -> str:
        """Build an AI-optimized scan prompt for PentAGI agents."""
        base = f"Perform a {scan_type} penetration test on: {target}\n\n"

        scan_instructions = {
            "api": (
                "Focus on API security testing:\n"
                "1. Discover all API endpoints from the OpenAPI/Swagger schema\n"
                "2. Test for OWASP API Security Top 10 vulnerabilities\n"
                "3. Check authentication and authorization bypass\n"
                "4. Test for injection attacks (SQL, NoSQL, Command)\n"
                "5. Check rate limiting and input validation\n"
                "6. Test CORS configuration\n"
                "7. Check for sensitive data exposure in responses\n"
                "8. Generate remediation suggestions for each finding\n"
            ),
            "web": (
                "Focus on web application security testing:\n"
                "1. Crawl and map all frontend routes\n"
                "2. Test for XSS (reflected, stored, DOM-based)\n"
                "3. Check for CSRF vulnerabilities\n"
                "4. Test for insecure direct object references\n"
                "5. Check Content Security Policy headers\n"
                "6. Test for clickjacking\n"
                "7. Analyze JavaScript for sensitive data leaks\n"
                "8. Generate remediation suggestions\n"
            ),
            "auth": (
                "Focus on authentication and authorization testing:\n"
                "1. Test login/registration for brute force protection\n"
                "2. Check JWT token security (algorithm, expiry, signing)\n"
                "3. Test session management\n"
                "4. Check password policy enforcement\n"
                "5. Test OAuth flows if available\n"
                "6. Check for privilege escalation\n"
                "7. Test password reset flows\n"
                "8. Generate remediation suggestions\n"
            ),
            "full": (
                "Perform comprehensive penetration testing:\n"
                "1. Discover all API endpoints and web routes\n"
                "2. Test for OWASP Top 10 vulnerabilities\n"
                "3. Test authentication/authorization security\n"
                "4. Check for injection attacks (SQL, XSS, Command)\n"
                "5. Test network exposure and open ports\n"
                "6. Check SSL/TLS configuration\n"
                "7. Test for sensitive data exposure\n"
                "8. Check security headers\n"
                "9. Test rate limiting and DoS resilience\n"
                "10. Generate prioritized remediation plan\n"
            ),
        }

        prompt = base + scan_instructions.get(scan_type, scan_instructions["full"])

        if description:
            prompt += f"\nAdditional context: {description}\n"

        prompt += (
            "\nFormat findings as structured output with severity levels: "
            "CRITICAL, HIGH, MEDIUM, LOW, INFO.\n"
            "For each finding provide: vulnerability name, description, "
            "affected endpoint/component, proof of concept, and remediation steps.\n"
        )

        return prompt

    # ── Finding Parser ────────────────────────────────────────────────────

    @staticmethod
    def _parse_findings(raw_text: str) -> List[Dict[str, Any]]:
        """
        Parse AI-generated findings from raw text output.
        Returns structured findings with severity classification.
        """
        findings = []
        if not raw_text:
            return findings

        severity_keywords = {
            "critical": ["critical", "rce", "remote code execution", "sql injection"],
            "high": ["high", "authentication bypass", "privilege escalation", "xss"],
            "medium": ["medium", "csrf", "information disclosure", "cors"],
            "low": ["low", "missing header", "verbose error", "cookie"],
            "info": ["info", "informational", "note", "observation"],
        }

        # Split into sections by common separators
        sections = raw_text.split("\n\n")

        for section in sections:
            section_stripped = section.strip()
            if not section_stripped or len(section_stripped) < 20:
                continue

            # Detect severity
            lower = section_stripped.lower()
            detected_severity = "info"
            for sev, keywords in severity_keywords.items():
                if any(kw in lower for kw in keywords):
                    detected_severity = sev
                    break

            # Only include sections that look like findings
            finding_indicators = [
                "vulnerab", "finding", "issue", "risk", "exploit",
                "inject", "bypass", "expos", "leak", "attack",
                "missing", "insecure", "weak", "broken",
            ]
            if any(ind in lower for ind in finding_indicators):
                findings.append({
                    "severity": detected_severity,
                    "vulnerability": section_stripped.split("\n")[0][:200],
                    "description": section_stripped[:1000],
                    "remediation": "",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return findings


class PentAGIError(Exception):
    """Exception raised by PentAGI client operations."""
    pass
