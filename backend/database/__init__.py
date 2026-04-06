"""
CONFIT Backend — Database Package
==================================
SQLAlchemy configuration, session management, and ORM models.
Use this package for all persistent storage; keep routers and
controllers independent of the database implementation.

Supports both SQLite (development) and PostgreSQL (production).
"""

from database.config import settings, get_database_url
from database.session import (
    SessionLocal,
    AsyncSessionLocal,
    get_db,
    get_async_session,
    get_db_session,
    init_db,
    init_db_async,
    close_db,
    engine,
    async_engine,
)
from database.base import Base
from database.donation_models import (
    Donation,
    DonorCredit,
    DonorRedemption,
    DonationConfig,
    DonationStatus,
    DonorCreditStatus,
)

__all__ = [
    "settings",
    "get_database_url",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_session",
    "get_db_session",
    "init_db",
    "init_db_async",
    "close_db",
    "Base",
    "engine",
    "async_engine",
    # Donation models
    "Donation",
    "DonorCredit",
    "DonorRedemption",
    "DonationConfig",
    "DonationStatus",
    "DonorCreditStatus",
]
