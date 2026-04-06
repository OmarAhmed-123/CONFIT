"""
Multi-Channel Alert System
==========================
Dispatches alerts through Slack, Email, and In-app notifications.
Uses edge-triggered logic to avoid alert spam.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import smtplib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

from services.debug.health_store import (
    get_health_store,
    AlertEntry,
    HealthHistoryStore,
)
from services.debug.health_check import HealthCheckResult

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ALERT MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AlertPayload:
    """Payload for alert dispatch."""
    provider: str
    check_name: str
    status: str
    message: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    debug_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# SLACK ALERTS
# ─────────────────────────────────────────────────────────────────────────────

def format_slack_message(payload: AlertPayload) -> Dict[str, Any]:
    """Format alert as Slack message payload."""
    # Color based on status
    color = "danger" if payload.status == "fail" else "warning"
    
    # Build attachment
    attachment = {
        "color": color,
        "title": f"⚠️ {payload.provider.upper()} Health Alert",
        "fields": [
            {
                "title": "Provider",
                "value": payload.provider.upper(),
                "short": True,
            },
            {
                "title": "Check",
                "value": payload.check_name,
                "short": True,
            },
            {
                "title": "Status",
                "value": payload.status.upper(),
                "short": True,
            },
            {
                "title": "Time",
                "value": payload.timestamp,
                "short": True,
            },
            {
                "title": "Message",
                "value": payload.message,
                "short": False,
            },
        ],
        "footer": "CONFIT Payment Health Monitor",
        "footer_icon": "https://confit.app/favicon.ico",
    }
    
    if payload.debug_url:
        attachment["actions"] = [
            {
                "type": "button",
                "text": "View Dashboard",
                "url": payload.debug_url,
            }
        ]
    
    return {
        "attachments": [attachment],
        "text": f"⚠️ {payload.provider.upper()} Health Alert: {payload.check_name}",
    }


async def send_slack_alert(payload: AlertPayload) -> bool:
    """Send alert to Slack via webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not configured - skipping Slack alert")
        return False
    
    try:
        message = format_slack_message(payload)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
            )
            
            if r.status_code == 200:
                logger.info(f"Slack alert sent for {payload.provider}/{payload.check_name}")
                return True
            else:
                logger.warning(f"Slack alert failed: HTTP {r.status_code}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL ALERTS
# ─────────────────────────────────────────────────────────────────────────────

def format_email_html(payload: AlertPayload) -> str:
    """Format alert as HTML email."""
    status_color = "#dc2626" if payload.status == "fail" else "#f59e0b"
    status_bg = "#fef2f2" if payload.status == "fail" else "#fffbeb"
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {status_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; }}
        .alert-box {{ background: {status_bg}; border-left: 4px solid {status_color}; padding: 16px; margin: 16px 0; }}
        .field {{ margin: 8px 0; }}
        .label {{ font-weight: 600; color: #374151; }}
        .value {{ color: #6b7280; }}
        .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; 
                   text-decoration: none; border-radius: 6px; margin-top: 16px; }}
        .footer {{ color: #9ca3af; font-size: 12px; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>⚠️ {payload.provider.upper()} Health Alert</h2>
            <p style="margin: 0; opacity: 0.9;">Payment Infrastructure Monitoring</p>
        </div>
        <div class="content">
            <div class="alert-box">
                <div class="field">
                    <span class="label">Provider:</span>
                    <span class="value">{payload.provider.upper()}</span>
                </div>
                <div class="field">
                    <span class="label">Check:</span>
                    <span class="value">{payload.check_name}</span>
                </div>
                <div class="field">
                    <span class="label">Status:</span>
                    <span class="value" style="color: {status_color}; font-weight: 600;">
                        {payload.status.upper()}
                    </span>
                </div>
                <div class="field">
                    <span class="label">Time:</span>
                    <span class="value">{payload.timestamp}</span>
                </div>
                <div class="field">
                    <span class="label">Message:</span>
                    <span class="value">{payload.message}</span>
                </div>
            </div>
            
            {"<a href='" + payload.debug_url + "' class='button'>View Debug Dashboard</a>" if payload.debug_url else ""}
            
            <div class="footer">
                <p>CONFIT Payment Health Monitor</p>
                <p>This is an automated alert from the CONFIT health monitoring system.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""


def format_email_plain(payload: AlertPayload) -> str:
    """Format alert as plain text email."""
    debug_section = f"\n\nView Dashboard: {payload.debug_url}" if payload.debug_url else ""
    
    return f"""
CONFIT Payment Health Alert
===========================

Provider: {payload.provider.upper()}
Check: {payload.check_name}
Status: {payload.status.upper()}
Time: {payload.timestamp}

Message:
{payload.message}
{debug_section}

--
CONFIT Payment Health Monitor
This is an automated alert from the CONFIT health monitoring system.
"""


async def send_email_alert(payload: AlertPayload) -> bool:
    """Send alert via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    alert_email_to = os.getenv("ALERT_EMAIL_TO", "").strip()
    
    if not all([smtp_host, smtp_user, smtp_password, alert_email_to]):
        logger.debug("SMTP not fully configured - skipping email alert")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[CONFIT] {payload.provider.upper()} Health Alert: {payload.check_name}"
        msg["From"] = smtp_user
        msg["To"] = alert_email_to
        
        # Attach both plain and HTML versions
        plain_part = MIMEText(format_email_plain(payload), "plain")
        html_part = MIMEText(format_email_html(payload), "html")
        msg.attach(plain_part)
        msg.attach(html_part)
        
        # Send
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [alert_email_to], msg.as_string())
        
        logger.info(f"Email alert sent for {payload.provider}/{payload.check_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# IN-APP ALERTS
# ─────────────────────────────────────────────────────────────────────────────

def create_in_app_alert(
    payload: AlertPayload,
    store: Optional[HealthHistoryStore] = None,
) -> AlertEntry:
    """Create an in-app alert entry."""
    store = store or get_health_store()
    
    alert = AlertEntry(
        id=f"alert-{payload.provider}-{payload.check_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        provider=payload.provider,
        check_name=payload.check_name,
        status=payload.status,
        message=payload.message,
        timestamp=payload.timestamp,
        acknowledged=False,
        details=payload.details,
    )
    
    store.add_alert(alert)
    logger.info(f"In-app alert created: {alert.id}")
    return alert


# ─────────────────────────────────────────────────────────────────────────────
# ALERT ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

async def dispatch_alert(
    result: HealthCheckResult,
    store: Optional[HealthHistoryStore] = None,
) -> Dict[str, bool]:
    """
    Dispatch alerts through all channels for a health check result.
    Uses edge-triggered logic - only alerts on state change.
    
    Returns dict of channel -> success status.
    """
    store = store or get_health_store()
    
    # Check if we should alert (edge-triggered)
    if not store.should_alert(result.provider, result.check_name, result.status):
        logger.debug(
            f"Skipping alert for {result.provider}/{result.check_name} - "
            f"no state change (status: {result.status})"
        )
        return {}
    
    # Update state
    previous_status = store.update_check_status(
        result.provider,
        result.check_name,
        result.status,
    )
    
    # Build payload
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    payload = AlertPayload(
        provider=result.provider,
        check_name=result.check_name,
        status=result.status,
        message=result.message,
        timestamp=result.timestamp,
        details=result.details,
        debug_url=f"{frontend_url}/debug/payments",
    )
    
    results: Dict[str, bool] = {}
    
    # Dispatch to all channels
    try:
        # Slack
        results["slack"] = await send_slack_alert(payload)
        
        # Email
        results["email"] = await send_email_alert(payload)
        
        # In-app (always succeeds)
        create_in_app_alert(payload, store)
        results["in_app"] = True
        
        # Mark as alerted
        store.mark_alerted(result.provider, result.check_name)
        
        logger.info(
            f"Alert dispatched for {result.provider}/{result.check_name}: "
            f"status={result.status}, previous={previous_status}, channels={results}"
        )
    except Exception as e:
        logger.error(f"Error dispatching alerts: {e}")
    
    return results


async def process_health_check_results(
    results: List[HealthCheckResult],
    store: Optional[HealthHistoryStore] = None,
) -> Dict[str, Dict[str, bool]]:
    """
    Process a list of health check results and dispatch alerts as needed.
    Returns dict of check_name -> channel results.
    """
    store = store or get_health_store()
    alert_results: Dict[str, Dict[str, bool]] = {}
    
    for result in results:
        if result.status in ("fail", "warn"):
            alert_results[result.check_name] = await dispatch_alert(result, store)
    
    return alert_results
