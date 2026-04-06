"""
CONFIT Security — Pydantic Schemas
===================================
Request/response models for the security scanning API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Enums ─────────────────────────────────────────────────────────────────────


class ScanType(str, Enum):
    """Types of security scans available."""
    API = "api"
    WEB = "web"
    AUTH = "auth"
    FULL = "full"


class ScanStatus(str, Enum):
    """Possible scan states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ── Request Models ────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    """Request to start a security scan."""
    target: str = Field(
        ...,
        description="URL or host to scan (e.g., 'http://api:8000')",
        examples=["http://api:8000", "http://localhost:8000"],
    )
    scan_type: ScanType = Field(
        default=ScanType.FULL,
        description="Type of security scan to perform",
    )
    description: Optional[str] = Field(
        default=None,
        description="Additional context for the AI scanning agent",
        max_length=2000,
    )


# ── Response Models ───────────────────────────────────────────────────────────


class ScanStartResponse(BaseModel):
    """Response after starting a scan."""
    scan_id: str = Field(..., description="Unique scan identifier")
    pentagi_flow_id: Optional[str] = Field(
        None, description="PentAGI flow ID for tracking"
    )
    status: ScanStatus = Field(default=ScanStatus.PENDING)
    target: str
    scan_type: ScanType
    message: str = Field(default="Scan initiated successfully")
    created_at: datetime


class ScanStatusResponse(BaseModel):
    """Scan status response."""
    scan_id: str
    pentagi_flow_id: Optional[str] = None
    status: ScanStatus
    target: str
    scan_type: ScanType
    tasks_count: int = 0
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class SecurityFinding(BaseModel):
    """A single security vulnerability finding."""
    severity: Severity
    vulnerability: str = Field(..., max_length=500)
    description: str = Field(default="")
    remediation: str = Field(default="")
    timestamp: Optional[datetime] = None


class FindingSummary(BaseModel):
    """Summary statistics for findings."""
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class ScanReportResponse(BaseModel):
    """Full scan report with findings."""
    scan_id: str
    pentagi_flow_id: Optional[str] = None
    status: ScanStatus
    target: str
    scan_type: ScanType
    findings: List[SecurityFinding] = Field(default_factory=list)
    summary: FindingSummary = Field(default_factory=FindingSummary)
    raw_ai_output: str = Field(default="")
    created_at: datetime
    updated_at: Optional[datetime] = None


class ScanListItem(BaseModel):
    """Scan item for listing."""
    scan_id: str
    pentagi_flow_id: Optional[str] = None
    status: ScanStatus
    target: str
    scan_type: ScanType
    findings_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class DiscoveredRoute(BaseModel):
    """A discovered API route."""
    path: str
    method: str
    tags: List[str] = Field(default_factory=list)
    summary: str = ""
    url: str = ""


class DiscoverySummary(BaseModel):
    """Summary of discovered targets."""
    total_routes: int = 0
    total_web_routes: int = 0
    total_services: int = 0
    route_groups: Dict[str, int] = Field(default_factory=dict)
    methods: Dict[str, int] = Field(default_factory=dict)


class DiscoveryResponse(BaseModel):
    """Response from target discovery."""
    api_routes: List[DiscoveredRoute] = Field(default_factory=list)
    web_routes: List[DiscoveredRoute] = Field(default_factory=list)
    services: List[Dict[str, Any]] = Field(default_factory=list)
    summary: DiscoverySummary = Field(default_factory=DiscoverySummary)


class HealthResponse(BaseModel):
    """PentAGI health status."""
    pentagi_reachable: bool
    pentagi_url: str
    message: str
