"""
CONFIT Backend - Security Audit Logging
========================================
Logs every sensitive action to the security_audit_log table.
Events: auth (login, logout, password_change, 2fa_enable),
        payment (refund_initiated, manual_adjust),
        admin (user_deleted, role_changed, coupon_created_manually).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audit event types
# ---------------------------------------------------------------------------

class AuditEventType:
    # Auth events
    LOGIN = "auth:login"
    LOGIN_FAILED = "auth:login_failed"
    REGISTER = "auth:register"
    REGISTER_FAILED = "auth:register_failed"
    LOGOUT = "auth:logout"
    PASSWORD_CHANGE = "auth:password_change"
    PASSWORD_RESET_REQUEST = "auth:password_reset_request"
    PASSWORD_RESET_CONFIRM = "auth:password_reset_confirm"
    MFA_ENABLE = "auth:2fa_enable"
    MFA_DISABLE = "auth:2fa_disable"
    MFA_VERIFY = "auth:2fa_verify"
    BRUTE_FORCE_LOCKOUT = "auth:brute_force_lockout"

    # Payment events
    REFUND_INITIATED = "payment:refund_initiated"
    MANUAL_ADJUST = "payment:manual_adjust"

    # Admin events
    USER_DELETED = "admin:user_deleted"
    ROLE_CHANGED = "admin:role_changed"
    COUPON_CREATED_MANUALLY = "admin:coupon_created_manually"
    USER_CREATED = "admin:user_created"
    USER_SUSPENDED = "admin:user_suspended"

    # Security events
    CSRF_REJECTION = "security:csrf_rejection"
    RATE_LIMIT_EXCEEDED = "security:rate_limit_exceeded"
    WEBHOOK_SIGNATURE_INVALID = "security:webhook_signature_invalid"
    SSRF_BLOCKED = "security:ssrf_blocked"


class AuditOutcome:
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


# ---------------------------------------------------------------------------
# Audit log record
# ---------------------------------------------------------------------------

class AuditLogEntry:
    """In-memory representation of an audit log entry."""

    def __init__(
        self,
        event_type: str,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        outcome: str = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        target_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.actor_id = actor_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.outcome = outcome
        self.details = details or {}
        self.target_id = target_id
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "outcome": self.outcome,
            "details": json.dumps(self.details) if isinstance(self.details, dict) else self.details,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Audit logger service
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    Security audit logger that writes to both the database and structured logs.

    Usage:
        await audit_logger.log(
            event_type=AuditEventType.LOGIN,
            actor_id=user_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
    """

    def __init__(self):
        self._db_writer = None

    def set_db_writer(self, writer):
        """Set a callable that persists entries to the database."""
        self._db_writer = writer

    async def log(
        self,
        event_type: str,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        outcome: str = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        target_id: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Record a security audit event.

        Writes to:
        1. Structured log (always)
        2. Database (if db_writer is configured)
        """
        entry = AuditLogEntry(
            event_type=event_type,
            actor_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            outcome=outcome,
            details=details,
            target_id=target_id,
        )

        # Structured log
        logger.info(
            "security_audit event=%s actor=%s ip=%s outcome=%s target=%s details=%s",
            entry.event_type,
            entry.actor_id,
            entry.ip_address,
            entry.outcome,
            entry.target_id,
            json.dumps(entry.details) if entry.details else "",
        )

        # Database persistence
        if self._db_writer:
            try:
                await self._db_writer(entry)
            except Exception as e:
                logger.error("Failed to write audit log to database: %s", e)

        return entry


# Global instance
audit_logger = AuditLogger()


# ---------------------------------------------------------------------------
# Convenience: extract audit context from a FastAPI Request
# ---------------------------------------------------------------------------

def audit_context_from_request(request) -> Dict[str, Optional[str]]:
    """Extract actor_id, IP, and user_agent from a FastAPI Request object."""
    actor_id = None
    # Try to get user_id from request state (set by auth middleware)
    if hasattr(request, "state") and hasattr(request.state, "user_id"):
        actor_id = str(request.state.user_id)

    ip_address = None
    if hasattr(request, "client") and request.client:
        ip_address = request.client.host
    # Check X-Forwarded-For for reverse proxy
    if hasattr(request, "headers"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()

    user_agent = None
    if hasattr(request, "headers"):
        user_agent = request.headers.get("user-agent")

    return {
        "actor_id": actor_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }


__all__ = [
    "AuditEventType",
    "AuditOutcome",
    "AuditLogEntry",
    "AuditLogger",
    "audit_logger",
    "audit_context_from_request",
]
