"""
CONFIT Security — API Router
==============================
FastAPI router providing security scanning endpoints.

Routes:
    POST   /api/security/scan               — Start a new scan
    GET    /api/security/status/{scan_id}    — Get scan status
    GET    /api/security/report/{scan_id}    — Get scan report
    GET    /api/security/scans               — List all scans
    GET    /api/security/targets/discover    — Auto-discover targets
    GET    /api/security/health              — PentAGI health check
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.slowapi_limiter import limiter
from schemas.security_schemas import (
    DiscoveryResponse,
    HealthResponse,
    ScanListItem,
    ScanReportResponse,
    ScanRequest,
    ScanStartResponse,
    ScanStatus,
    ScanStatusResponse,
    SecurityFinding as SecurityFindingSchema,
    FindingSummary,
)
from database.security_db_models import SecurityFinding as SecurityFindingRow
from database.security_db_models import SecurityReport as SecurityReportRow
from database.security_db_models import SecurityScan as SecurityScanRow
from database.session import get_db
from services.security.discovery import TargetDiscovery
from services.security.pentagi_client import PentAGIClient, PentAGIError

logger = logging.getLogger("confit.security.router")

router = APIRouter(
    prefix="/api/security",
    tags=["Security"],
    responses={
        503: {"description": "PentAGI service unavailable"},
        500: {"description": "Internal security service error"},
    },
)

# ── Singletons ────────────────────────────────────────────────────────────────

_pentagi_client: Optional[PentAGIClient] = None
_discovery: Optional[TargetDiscovery] = None

def _get_client() -> PentAGIClient:
    global _pentagi_client
    if _pentagi_client is None:
        _pentagi_client = PentAGIClient()
    return _pentagi_client


def _get_discovery() -> TargetDiscovery:
    global _discovery
    if _discovery is None:
        _discovery = TargetDiscovery(
            api_base_url=os.getenv("SECURITY_INTERNAL_API_BASE_URL", "http://localhost:8000"),
            web_base_url=os.getenv("SECURITY_INTERNAL_WEB_BASE_URL", "https://nginx"),
        )
    return _discovery


# ── Security helpers ───────────────────────────────────────────────────────

SECURITY_SCAN_RATE_LIMIT = os.getenv("SECURITY_SCAN_RATE_LIMIT", "3/minute")
SECURITY_STATUS_RATE_LIMIT = os.getenv("SECURITY_STATUS_RATE_LIMIT", "10/minute")
SECURITY_REPORT_RATE_LIMIT = os.getenv("SECURITY_REPORT_RATE_LIMIT", "10/minute")

SECURITY_ALLOWED_TARGET_HOSTS = set(
    h.strip()
    for h in os.getenv(
        "SECURITY_ALLOWED_TARGET_HOSTS",
        "api,nginx,localhost,127.0.0.1",
    ).split(",")
    if h.strip()
)

SECURITY_INTERNAL_API_BASE_URL = os.getenv("SECURITY_INTERNAL_API_BASE_URL", "http://api:8000").rstrip("/")
SECURITY_INTERNAL_WEB_BASE_URL = os.getenv("SECURITY_INTERNAL_WEB_BASE_URL", "https://nginx").rstrip("/")


def _truncate(s: Optional[str], max_len: int) -> Optional[str]:
    if not s:
        return s
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]
    return s[: max_len - 3] + "..."


def _map_pentagi_status(pentagi_status: str) -> ScanStatus:
    # PentAGI tends to return: active/running/completed/done/failed/error.
    s = (pentagi_status or "").lower().strip()
    status_map = {
        "active": ScanStatus.RUNNING,
        "running": ScanStatus.RUNNING,
        "completed": ScanStatus.COMPLETED,
        "done": ScanStatus.COMPLETED,
        "failed": ScanStatus.FAILED,
        "error": ScanStatus.FAILED,
        "pending": ScanStatus.PENDING,
    }
    return status_map.get(s, ScanStatus.PENDING)


def _is_allowed_target(target: str) -> bool:
    t = (target or "").strip()
    if not t:
        return False
    if t.lower() == "auto":
        return True

    parsed = urlparse(t if "://" in t else f"http://{t}")
    if not parsed.hostname:
        return False

    return parsed.hostname in SECURITY_ALLOWED_TARGET_HOSTS


async def _build_auto_discovery_description(
    scan_type: str,
    user_description: Optional[str],
) -> Tuple[str, str]:
    """
    Returns (target_for_pentagi, combined_description).
    target_for_pentagi drives what PentAGI crawls; description provides route/service context.
    """
    discovery = _get_discovery()
    discovered = await discovery.get_scan_targets()

    api_routes = discovered.get("api_routes", [])[:50]
    web_routes = discovered.get("web_routes", [])[:80]
    services = discovered.get("services", [])[:10]
    summary = discovered.get("summary", {})

    context = {
        "summary": summary,
        "api_base": SECURITY_INTERNAL_API_BASE_URL,
        "web_base": SECURITY_INTERNAL_WEB_BASE_URL,
        "api_routes": api_routes,
        "web_routes": web_routes,
        "services": services,
        "auth_routes_hint": [
            r.get("path")
            for r in web_routes
            if isinstance(r.get("path"), str)
            and any(k in r["path"].lower() for k in ("login", "register", "auth"))
        ],
    }

    auto_description = json.dumps(context, ensure_ascii=False)
    combined = "\n\nAUTO-DISCOVERY CONTEXT (internal):\n" + auto_description
    if user_description:
        combined = (user_description or "") + combined

    combined = _truncate(combined, 1800) or ""

    st = (scan_type or "").lower()
    if st in ("api", "auth"):
        target_for_pentagi = SECURITY_INTERNAL_API_BASE_URL
    else:
        target_for_pentagi = SECURITY_INTERNAL_WEB_BASE_URL

    return target_for_pentagi, combined


def _resolve_manual_target_for_pentagi(scan_type: str, user_target: str) -> str:
    """
    Map common external-ish targets to internal docker-network targets.
    Keeps user_target intact in DB/UI, but ensures PentAGI only hits internal hosts.
    """
    t = (user_target or "").strip()
    st = (scan_type or "").lower()

    if "://" not in t:
        t = f"http://{t}"

    parsed = urlparse(t)
    host = (parsed.hostname or "").strip().lower()

    # Map localhost → docker service
    if host in ("localhost", "127.0.0.1"):
        if st in ("api", "auth"):
            return SECURITY_INTERNAL_API_BASE_URL
        return SECURITY_INTERNAL_WEB_BASE_URL

    # If the user already provided docker service hosts, keep as-is.
    if host in SECURITY_ALLOWED_TARGET_HOSTS:
        # Ensure explicit scheme (PentAGI expects URLs/hosts)
        scheme = parsed.scheme or ("https" if st not in ("api", "auth") else "http")
        port = f":{parsed.port}" if parsed.port else ""
        return f"{scheme}://{host}{port}"

    # Fallback (should be rejected earlier by allowlisting)
    return user_target


async def _fetch_and_persist_report(
    scan_row: SecurityScanRow,
    client: PentAGIClient,
    db: Session,
) -> SecurityReportRow:
    """
    Fetch PentAGI report for a scan flow and persist it into:
    - security_reports
    - security_findings
    - security_scans (status/findings_count/raw_ai_output)
    """
    if not scan_row.pentagi_flow_id:
        raise HTTPException(status_code=409, detail="PentAGI flow not available for scan")

    report_data = await client.get_scan_report(scan_row.pentagi_flow_id)

    pentagi_status = report_data.get("status", "completed")
    mapped_status = _map_pentagi_status(pentagi_status)

    findings = report_data.get("findings", []) or []
    raw_ai_output = report_data.get("raw_ai_output", "") or ""
    summary_data = report_data.get("summary", {}) or {}

    # Idempotent refresh
    existing_report = db.query(SecurityReportRow).filter(SecurityReportRow.scan_id == scan_row.id).first()
    if existing_report:
        db.query(SecurityFindingRow).filter(SecurityFindingRow.scan_id == scan_row.id).delete()
        db.delete(existing_report)
        db.commit()

    for f in findings:
        # PentAGI client produces ISO strings; convert for DB DateTime fields.
        ts_raw = f.get("timestamp")
        ts = None
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                ts = None

        db.add(
            SecurityFindingRow(
                scan_id=scan_row.id,
                severity=f.get("severity", "info"),
                vulnerability=f.get("vulnerability", "Unknown"),
                description=f.get("description", "") or "",
                remediation=f.get("remediation", "") or "",
                raw_ai_output=f.get("description", "") or None,
                timestamp=ts,
                status="open",
            )
        )

    report_row = SecurityReportRow(
        scan_id=scan_row.id,
        status=mapped_status.value,
        total=int(summary_data.get("total", len(findings)) or 0),
        critical=int(summary_data.get("critical", 0) or 0),
        high=int(summary_data.get("high", 0) or 0),
        medium=int(summary_data.get("medium", 0) or 0),
        low=int(summary_data.get("low", 0) or 0),
        info=int(summary_data.get("info", 0) or 0),
        raw_ai_output=raw_ai_output,
    )
    db.add(report_row)

    scan_row.status = mapped_status.value
    scan_row.findings_count = len(findings)
    scan_row.raw_ai_output = raw_ai_output
    scan_row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report_row)
    return report_row


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=ScanStartResponse,
    summary="Start a security scan",
    description="Initiates an AI-powered penetration test via PentAGI",
)
@limiter.limit(SECURITY_SCAN_RATE_LIMIT)
async def start_scan(
    request: Request,
    scan_request: ScanRequest,
    db: Session = Depends(get_db),
) -> ScanStartResponse:
    """Start a new security scan against the specified target."""
    if not _is_allowed_target(scan_request.target):
        raise HTTPException(status_code=400, detail="Target is not allowed")

    client = _get_client()
    scan_id = str(uuid.uuid4())
    requested_ip = (request.client.host if request.client else None)  # audit trail

    # Create scan row first so UI has an ID immediately (fail-safe)
    scan_row = SecurityScanRow(
        id=scan_id,
        pentagi_flow_id=None,
        target=scan_request.target,
        scan_type=scan_request.scan_type.value,
        status=ScanStatus.PENDING.value,
        description=scan_request.description,
        findings_count=0,
        tasks_count=0,
        requested_ip=requested_ip,
        requested_by=None,
    )
    db.add(scan_row)
    db.commit()
    db.refresh(scan_row)

    try:
        if scan_request.target.lower().strip() == "auto":
            target_for_pentagi, combined_description = await _build_auto_discovery_description(
                scan_type=scan_request.scan_type.value,
                user_description=scan_request.description,
            )
        else:
            target_for_pentagi = _resolve_manual_target_for_pentagi(scan_request.scan_type.value, scan_request.target)
            combined_description = scan_request.description

        flow = await client.start_scan(
            target=target_for_pentagi,
            scan_type=scan_request.scan_type.value,
            description=combined_description,
        )
        flow_id = flow.get("id")

        scan_row.pentagi_flow_id = flow_id
        scan_row.status = ScanStatus.RUNNING.value
        scan_row.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Scan started: scan_id=%s flow_id=%s ui_target=%s pentagi_target=%s",
            scan_id,
            flow_id,
            scan_request.target,
            target_for_pentagi,
        )

        return ScanStartResponse(
            scan_id=scan_id,
            pentagi_flow_id=flow_id,
            status=ScanStatus.RUNNING,
            target=scan_request.target,
            scan_type=scan_request.scan_type,
            message="Scan initiated successfully. Use /status/{scan_id} to monitor progress.",
            created_at=scan_row.created_at,
        )

    except PentAGIError as exc:
        logger.error("Scan start failed: %s", exc, exc_info=True)
        scan_row.status = ScanStatus.FAILED.value
        scan_row.error = str(exc)
        scan_row.updated_at = datetime.now(timezone.utc)
        db.commit()

        raise HTTPException(status_code=503, detail=f"PentAGI scan failed to start: {exc}")
    except Exception as exc:
        logger.error("Unexpected error starting scan: %s", exc, exc_info=True)
        scan_row.status = ScanStatus.FAILED.value
        scan_row.error = "Unexpected internal error starting scan"
        scan_row.updated_at = datetime.now(timezone.utc)
        db.commit()

        raise HTTPException(status_code=500, detail="Internal error starting security scan")


@router.get(
    "/status/{scan_id}",
    response_model=ScanStatusResponse,
    summary="Get scan status",
)
@limiter.limit(SECURITY_STATUS_RATE_LIMIT)
async def get_scan_status(
    request: Request,
    scan_id: str,
    db: Session = Depends(get_db),
) -> ScanStatusResponse:
    """Get the current status of a security scan."""
    scan_row = db.query(SecurityScanRow).filter(SecurityScanRow.id == scan_id).first()
    if not scan_row:
        raise HTTPException(status_code=404, detail="Scan not found")

    client = _get_client()
    flow_id = scan_row.pentagi_flow_id
    tasks: List[Dict[str, Any]] = []
    tasks_count = scan_row.tasks_count or 0

    # Refresh status if we have a flow_id and the scan isn't terminal.
    try:
        if flow_id and scan_row.status not in (ScanStatus.COMPLETED.value, ScanStatus.FAILED.value, ScanStatus.CANCELLED.value):
            status_data = await client.get_scan_status(flow_id)
            pentagi_status = status_data.get("status", "unknown")
            mapped = _map_pentagi_status(pentagi_status)
            scan_row.status = mapped.value
            scan_row.tasks_count = status_data.get("tasks_count", 0) or 0
            db.commit()

            tasks = status_data.get("tasks", []) or []

            # If completed and no report exists yet, persist it now (autonomous).
            if mapped == ScanStatus.COMPLETED:
                report_row = db.query(SecurityReportRow).filter(SecurityReportRow.scan_id == scan_row.id).first()
                if not report_row:
                    await _fetch_and_persist_report(scan_row=scan_row, client=client, db=db)
    except PentAGIError as exc:
        logger.warning("Could not fetch status for %s: %s", scan_id, exc)
    except Exception as exc:
        logger.error("Unexpected status refresh error: %s", exc, exc_info=True)

    status_enum = scan_row.status if scan_row.status in {s.value for s in ScanStatus} else ScanStatus.PENDING.value

    return ScanStatusResponse(
        scan_id=scan_row.id,
        pentagi_flow_id=scan_row.pentagi_flow_id,
        status=ScanStatus(status_enum),
        target=scan_row.target,
        scan_type=scan_row.scan_type,
        tasks_count=tasks_count,
        tasks=tasks,
        created_at=scan_row.created_at,
        updated_at=scan_row.updated_at,
    )


@router.get(
    "/report/{scan_id}",
    response_model=ScanReportResponse,
    summary="Get scan report",
)
@limiter.limit(SECURITY_REPORT_RATE_LIMIT)
async def get_scan_report(
    request: Request,
    scan_id: str,
    db: Session = Depends(get_db),
) -> ScanReportResponse:
    """Get the full security report for a scan."""
    scan_row = db.query(SecurityScanRow).filter(SecurityScanRow.id == scan_id).first()
    if not scan_row:
        raise HTTPException(status_code=404, detail="Scan not found")

    client = _get_client()
    if not scan_row.pentagi_flow_id:
        raise HTTPException(status_code=409, detail="Scan flow not started")

    report_row = db.query(SecurityReportRow).filter(SecurityReportRow.scan_id == scan_row.id).first()
    if not report_row:
        # Fetch + persist report on demand.
        await _fetch_and_persist_report(scan_row=scan_row, client=client, db=db)
        report_row = db.query(SecurityReportRow).filter(SecurityReportRow.scan_id == scan_row.id).first()

    findings_rows = (
        db.query(SecurityFindingRow)
        .filter(SecurityFindingRow.scan_id == scan_row.id)
        .order_by(SecurityFindingRow.timestamp.asc())
        .all()
    )

    findings: List[SecurityFindingSchema] = [
        SecurityFindingSchema(
            severity=f.severity,
            vulnerability=f.vulnerability,
            description=f.description or "",
            remediation=f.remediation or "",
            timestamp=f.timestamp,
        )
        for f in findings_rows
    ]

    summary = FindingSummary(
        total=report_row.total,
        critical=report_row.critical,
        high=report_row.high,
        medium=report_row.medium,
        low=report_row.low,
        info=report_row.info,
    )

    status_enum = report_row.status if report_row.status in {s.value for s in ScanStatus} else ScanStatus.PENDING.value

    return ScanReportResponse(
        scan_id=scan_row.id,
        pentagi_flow_id=scan_row.pentagi_flow_id,
        status=ScanStatus(status_enum),
        target=scan_row.target,
        scan_type=scan_row.scan_type,
        findings=findings,
        summary=summary,
        raw_ai_output=report_row.raw_ai_output or "",
        created_at=scan_row.created_at,
        updated_at=scan_row.updated_at,
    )


@router.get(
    "/scans",
    response_model=List[ScanListItem],
    summary="List all scans",
)
async def list_scans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[ScanListItem]:
    """List all security scans with optional status filtering."""
    query = db.query(SecurityScanRow)

    if status:
        query = query.filter(SecurityScanRow.status == status)

    scan_rows = (
        query.order_by(SecurityScanRow.created_at.desc())
        .limit(limit)
        .all()
    )

    valid_status = {s.value for s in ScanStatus}
    return [
        ScanListItem(
            scan_id=s.id,
            pentagi_flow_id=s.pentagi_flow_id,
            status=ScanStatus(s.status) if s.status in valid_status else ScanStatus.PENDING,
            target=s.target,
            scan_type=s.scan_type,
            findings_count=s.findings_count or 0,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in scan_rows
    ]


@router.get(
    "/targets/discover",
    response_model=DiscoveryResponse,
    summary="Discover scan targets",
    description="Auto-discover API endpoints and services for scanning",
)
@limiter.limit(SECURITY_STATUS_RATE_LIMIT)
async def discover_targets(request: Request) -> DiscoveryResponse:
    """Discover available scan targets from the CONFIT API."""
    discovery = _get_discovery()

    try:
        targets = await discovery.get_scan_targets()
        return DiscoveryResponse(**targets)
    except Exception as exc:
        logger.error("Target discovery failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Target discovery failed: {exc}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="PentAGI health check",
)
async def pentagi_health() -> HealthResponse:
    """Check PentAGI connectivity and health."""
    client = _get_client()
    is_healthy = await client.health_check()

    return HealthResponse(
        pentagi_reachable=is_healthy,
        pentagi_url=client._base_url,
        message=(
            "PentAGI is reachable and operational"
            if is_healthy
            else "PentAGI is not reachable. Ensure it is running and PENTAGI_URL is correct."
        ),
    )
