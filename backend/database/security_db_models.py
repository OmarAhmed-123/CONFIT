"""
CONFIT Security — SQLAlchemy ORM Models
========================================
Database models for persisting security scan results.
Uses the existing CONFIT database Base — tables auto-created via init_db().
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

# Import the shared Base from whichever database module is active
try:
    from database.base import Base
except ImportError:
    try:
        from infrastructure.database import Base
    except ImportError:
        from sqlalchemy.orm import declarative_base
        Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class SecurityScan(Base):
    """Persisted security scan metadata."""

    __tablename__ = "security_scans"

    id = Column(String(36), primary_key=True, default=_uuid)
    pentagi_flow_id = Column(String(64), nullable=True, index=True)
    target = Column(String(500), nullable=False)
    scan_type = Column(
        String(20),
        nullable=False,
        default="full",
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    description = Column(Text, nullable=True)
    findings_count = Column(Integer, default=0)
    tasks_count = Column(Integer, default=0)
    raw_ai_output = Column(Text, nullable=True)
    requested_ip = Column(String(64), nullable=True)
    requested_by = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # Relationships
    findings = relationship(
        "SecurityFinding",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    report = relationship(
        "SecurityReport",
        back_populates="scan",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_security_scans_created", "created_at"),
        Index("ix_security_scans_target", "target"),
    )

    def __repr__(self) -> str:
        return f"<SecurityScan(id={self.id}, target={self.target}, status={self.status})>"


class SecurityFinding(Base):
    """Individual vulnerability finding from a scan."""

    __tablename__ = "security_findings"

    id = Column(String(36), primary_key=True, default=_uuid)
    scan_id = Column(
        String(36),
        ForeignKey("security_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity = Column(
        String(20),
        nullable=False,
        default="info",
        index=True,
    )
    vulnerability = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    raw_output = Column(Text, nullable=True)
    raw_ai_output = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    scan = relationship("SecurityScan", back_populates="findings")

    def __repr__(self) -> str:
        return (
            f"<SecurityFinding(id={self.id}, severity={self.severity}, "
            f"vuln={self.vulnerability[:50]})>"
        )


class SecurityReport(Base):
    """Persisted report (summary + raw AI output) for a scan."""

    __tablename__ = "security_reports"

    id = Column(String(36), primary_key=True, default=_uuid)
    scan_id = Column(
        String(36),
        ForeignKey("security_scans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="completed", index=True)

    # Summary statistics
    total = Column(Integer, default=0, nullable=False)
    critical = Column(Integer, default=0, nullable=False)
    high = Column(Integer, default=0, nullable=False)
    medium = Column(Integer, default=0, nullable=False)
    low = Column(Integer, default=0, nullable=False)
    info = Column(Integer, default=0, nullable=False)

    raw_ai_output = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    scan = relationship("SecurityScan", back_populates="report")
