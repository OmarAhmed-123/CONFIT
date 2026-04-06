"""
CONFIT Backend — Sales Alerts Router
====================================
API endpoints for sales alerts, preferences, and history.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from core.slowapi_limiter import limiter
from database.session import get_db
from database.sales_alert_models import (
    SalesAlert,
    SalesAlertPreferences,
    SalesAlertLog,
    AlertType,
    AlertSeverity,
    AlertStatus,
    get_default_thresholds,
    get_default_frequency,
    get_default_type_preferences,
)
from services.sales_alert_service import SalesAlertService, get_sales_alert_service
from services.auth_service import AuthService
from utils.auth_deps import require_auth, get_auth_service
from schemas.sales_alert_schemas import (
    SalesAlertResponse,
    SalesAlertListResponse,
    SalesAlertPreferencesResponse,
    SalesAlertPreferencesUpdate,
    SalesAlertFilterRequest,
    SalesAlertSortRequest,
    PaginationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales-alerts", tags=["Sales Alerts"])


# ─── Alert List & History ──────────────────────────────────────────────────────

@router.get("", response_model=SalesAlertListResponse)
@limiter.limit("30/minute")
async def list_alerts(
    request: Request,
    type: Optional[List[AlertType]] = Query(None),
    severity: Optional[List[AlertSeverity]] = Query(None),
    status: Optional[List[AlertStatus]] = Query(None),
    read: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    List sales alerts with filtering, sorting, and pagination.
    """
    # Get user's store(s) - for now, assume single store
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    # Build query
    query = db.query(SalesAlert).filter(SalesAlert.store_id == store_id)

    # Apply filters
    if type:
        query = query.filter(SalesAlert.type.in_(type))
    if severity:
        query = query.filter(SalesAlert.severity.in_(severity))
    if status:
        query = query.filter(SalesAlert.status.in_(status))
    if read is not None:
        query = query.filter(SalesAlert.read == read)
    if date_from:
        query = query.filter(SalesAlert.created_at >= date_from)
    if date_to:
        query = query.filter(SalesAlert.created_at <= date_to)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SalesAlert.title.ilike(search_term),
                SalesAlert.rich_preview.ilike(search_term),
                SalesAlert.message.ilike(search_term),
            )
        )

    # Get total count
    total_count = query.count()

    # Apply sorting
    sort_column = getattr(SalesAlert, sort_by, SalesAlert.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * limit
    alerts = query.offset(offset).limit(limit).all()

    # Build response
    total_pages = max(1, (total_count + limit - 1) // limit)

    return SalesAlertListResponse(
        success=True,
        data=[SalesAlertResponse(**a.to_dict()) for a in alerts],
        pagination={
            "total_rows": total_count,
            "current_page": page,
            "page_size": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
        filters_applied={
            "type": [t.value for t in type] if type else None,
            "severity": [s.value for s in severity] if severity else None,
            "status": [s.value for s in status] if status else None,
            "read": read,
            "search": search,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        sort_applied={"field": sort_by, "direction": sort_order},
    )


@router.get("/unread-count")
@limiter.limit("60/minute")
async def get_unread_count(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get unread alert counts by severity."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    counts = (
        db.query(SalesAlert.severity, db.func.count(SalesAlert.id))
        .filter(SalesAlert.store_id == store_id, SalesAlert.read == False)
        .group_by(SalesAlert.severity)
        .all()
    )

    result = {"total": 0, "critical": 0, "warning": 0, "info": 0}
    for severity, count in counts:
        result[severity.value] = count
        result["total"] += count

    return result


@router.get("/summary")
@limiter.limit("30/minute")
async def get_alert_summary(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get alert summary statistics for the past N days."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    alerts = (
        db.query(SalesAlert)
        .filter(SalesAlert.store_id == store_id, SalesAlert.created_at >= since)
        .all()
    )

    summary = {
        "period_days": days,
        "total_alerts": len(alerts),
        "by_type": {},
        "by_severity": {"critical": 0, "warning": 0, "info": 0},
        "by_status": {},
        "read_rate": 0,
    }

    for alert in alerts:
        # By type
        type_key = alert.type.value
        summary["by_type"][type_key] = summary["by_type"].get(type_key, 0) + 1

        # By severity
        severity_key = alert.severity.value
        summary["by_severity"][severity_key] = summary["by_severity"].get(severity_key, 0) + 1

        # By status
        status_key = alert.status.value
        summary["by_status"][status_key] = summary["by_status"].get(status_key, 0) + 1

    # Read rate
    read_count = sum(1 for a in alerts if a.read)
    summary["read_rate"] = (read_count / len(alerts) * 100) if alerts else 0

    return summary


# ─── Alert Actions ─────────────────────────────────────────────────────────────

@router.get("/{alert_id}", response_model=SalesAlertResponse)
@limiter.limit("60/minute")
async def get_alert(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a single alert by ID."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return SalesAlertResponse(**alert.to_dict())


@router.post("/{alert_id}/read")
@limiter.limit("60/minute")
async def mark_alert_read(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark an alert as read."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not alert.read:
        alert.read = True
        _log_alert_event(db, alert, "read", user.id)
        db.commit()

    return {"success": True}


@router.post("/read-all")
@limiter.limit("30/minute")
async def mark_all_read(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark all alerts as read for the user's store."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    db.query(SalesAlert).filter(
        SalesAlert.store_id == store_id, SalesAlert.read == False
    ).update({"read": True})

    db.commit()
    return {"success": True}


@router.post("/{alert_id}/acknowledge")
@limiter.limit("60/minute")
async def acknowledge_alert(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.read = True

    _log_alert_event(db, alert, "acknowledged", user.id)
    db.commit()

    return {"success": True}


@router.post("/{alert_id}/resolve")
@limiter.limit("60/minute")
async def resolve_alert(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    alert.read = True

    _log_alert_event(db, alert, "resolved", user.id)
    db.commit()

    return {"success": True}


@router.post("/{alert_id}/dismiss")
@limiter.limit("60/minute")
async def dismiss_alert(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Dismiss an alert."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.DISMISSED
    alert.dismissed = True
    alert.read = True

    _log_alert_event(db, alert, "dismissed", user.id)
    db.commit()

    return {"success": True}


@router.delete("/{alert_id}")
@limiter.limit("60/minute")
async def delete_alert(
    request: Request,
    alert_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete an alert (soft delete via dismissed status)."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    alert = (
        db.query(SalesAlert)
        .filter(SalesAlert.id == alert_id, SalesAlert.store_id == store_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    _log_alert_event(db, alert, "deleted", user.id)
    db.delete(alert)
    db.commit()

    return {"success": True}


# ─── Preferences ───────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=SalesAlertPreferencesResponse)
@limiter.limit("30/minute")
async def get_preferences(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get alert preferences for the user's store."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    prefs = (
        db.query(SalesAlertPreferences)
        .filter(SalesAlertPreferences.store_id == store_id)
        .first()
    )

    if not prefs:
        # Create default preferences
        prefs = SalesAlertPreferences(
            store_id=store_id,
            thresholds=get_default_thresholds(),
            frequency=get_default_frequency(),
            type_preferences=get_default_type_preferences(),
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return SalesAlertPreferencesResponse(**prefs.to_dict())


@router.put("/preferences", response_model=SalesAlertPreferencesResponse)
@limiter.limit("30/minute")
async def update_preferences(
    request: Request,
    update: SalesAlertPreferencesUpdate,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update alert preferences for the user's store."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    prefs = (
        db.query(SalesAlertPreferences)
        .filter(SalesAlertPreferences.store_id == store_id)
        .first()
    )

    if not prefs:
        prefs = SalesAlertPreferences(
            store_id=store_id,
            thresholds=update.thresholds or get_default_thresholds(),
            frequency=update.frequency or get_default_frequency(),
            type_preferences=update.type_preferences or get_default_type_preferences(),
        )
        db.add(prefs)
    else:
        if update.thresholds:
            prefs.thresholds = {**prefs.thresholds, **update.thresholds}
        if update.frequency:
            prefs.frequency = {**prefs.frequency, **update.frequency}
        if update.type_preferences:
            prefs.type_preferences = {**prefs.type_preferences, **update.type_preferences}

    db.commit()
    db.refresh(prefs)

    return SalesAlertPreferencesResponse(**prefs.to_dict())


@router.post("/preferences/reset")
@limiter.limit("10/minute")
async def reset_preferences(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Reset alert preferences to defaults."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    prefs = (
        db.query(SalesAlertPreferences)
        .filter(SalesAlertPreferences.store_id == store_id)
        .first()
    )

    if prefs:
        prefs.thresholds = get_default_thresholds()
        prefs.frequency = get_default_frequency()
        prefs.type_preferences = get_default_type_preferences()
        db.commit()
        db.refresh(prefs)
        return SalesAlertPreferencesResponse(**prefs.to_dict())

    return {"success": True}


# ─── Export ────────────────────────────────────────────────────────────────────

@router.get("/export/csv")
@limiter.limit("10/minute")
async def export_alerts_csv(
    request: Request,
    type: Optional[List[AlertType]] = Query(None),
    severity: Optional[List[AlertSeverity]] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Export alerts to CSV format."""
    store_id = _get_user_store_id(user.id, db)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store associated with user")

    # Build query with filters
    query = db.query(SalesAlert).filter(SalesAlert.store_id == store_id)
    if type:
        query = query.filter(SalesAlert.type.in_(type))
    if severity:
        query = query.filter(SalesAlert.severity.in_(severity))
    if date_from:
        query = query.filter(SalesAlert.created_at >= date_from)
    if date_to:
        query = query.filter(SalesAlert.created_at <= date_to)

    alerts = query.order_by(desc(SalesAlert.created_at)).all()

    # Generate CSV
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Type", "Severity", "Status", "Title", "Rich Preview",
        "Store ID", "Created At", "Read", "Dismissed"
    ])

    # Rows
    for alert in alerts:
        writer.writerow([
            str(alert.id),
            alert.type.value,
            alert.severity.value,
            alert.status.value,
            alert.title,
            alert.rich_preview,
            str(alert.store_id),
            alert.created_at.isoformat() if alert.created_at else "",
            "Yes" if alert.read else "No",
            "Yes" if alert.dismissed else "No",
        ])

    from fastapi.responses import Response

    timestamp = datetime.now().strftime("%Y%m%d")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="confit-alerts-{timestamp}.csv"'
        }
    )


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _get_user_store_id(user_id: str, db: Session) -> Optional[str]:
    """Get the store ID for a user (brand manager)."""
    from database.models import UserRole, AppRole, Store, BrandManager

    # Check if admin
    role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    if role and role.role == AppRole.admin:
        # Admin can access all stores - return first for now
        store = db.query(Store).first()
        return str(store.id) if store else None

    # Get brand manager's store
    bm = db.query(BrandManager).filter(BrandManager.user_id == user_id).first()
    if bm:
        store = db.query(Store).filter(Store.brand_id == bm.brand_id).first()
        return str(store.id) if store else None

    return None


def _log_alert_event(db: Session, alert: SalesAlert, event_type: str, actor_id: str):
    """Log an alert event for audit trail."""
    log = SalesAlertLog(
        alert_id=alert.id,
        store_id=alert.store_id,
        event_type=event_type,
        previous_state={"status": alert.status.value} if alert.status else None,
        new_state={"status": event_type},
        actor_id=actor_id,
        actor_type="user",
    )
    db.add(log)
