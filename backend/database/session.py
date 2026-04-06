"""
CONFIT Backend — Database Session
===================================
Session factory and FastAPI dependency. Use get_db() in route
dependencies and pass the session to services; never store
sessions in globals.

Supports both SQLite (development) and PostgreSQL (production).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.config import settings

# Import models so they are registered with Base.metadata before create_all
# Core database models (database/models.py) - CANONICAL SOURCE for all tables
import database.models  # noqa: F401

# Additional feature models from models/ directory
# NOTE: Only import models that define UNIQUE tables not already in database/models.py
# profile_models contains unique tables: user_confidence_profiles, user_behavior_signals, etc.
import models.profile_models  # noqa: F401
import models.chat_models  # noqa: F401
import models.challenge_models  # noqa: F401
import models.influencer_models  # noqa: F401
import models.style_dna_models  # noqa: F401
import models.wardrobe_analytics_models  # noqa: F401
import models.closet_planner_models  # noqa: F401
import models.sustainability_models  # noqa: F401
import models.production_models  # noqa: F401

# Security scan persistence models (security_scans/security_findings/security_reports)
import database.security_db_models  # noqa: F401
import database.growth_models  # noqa: F401

# Donation system models (donations, donor_credits, donor_redemptions)
import database.donation_models  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# SYNC ENGINE (for Alembic migrations and sync operations)
# ─────────────────────────────────────────────────────────────────────────────

# Build engine kwargs based on database type
_engine_kwargs = {"echo": False}

if settings.is_sqlite:
    # SQLite: Use StaticPool with check_same_thread=False
    # StaticPool maintains a single connection (suitable for dev/test)
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL: Use connection pooling
    _engine_kwargs.update(settings.pool_settings)

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC ENGINE (for FastAPI async routes)
# ─────────────────────────────────────────────────────────────────────────────

# Build async engine kwargs based on database type
_async_engine_kwargs = {"echo": False}

if settings.is_sqlite:
    # SQLite: Use StaticPool with check_same_thread=False
    _async_engine_kwargs["connect_args"] = {"check_same_thread": False}
    _async_engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL: Use connection pooling
    _async_engine_kwargs.update(settings.pool_settings)

async_engine: AsyncEngine = create_async_engine(
    settings.async_database_url, **_async_engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a sync DB session and closes it after the request.
    Use for simple operations or when async is not needed.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an async DB session.
    Use for async routes and operations.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async database session.
    Use for background tasks and scripts.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables synchronously.
    Called on app startup when using SQLite or for tests.
    For PostgreSQL, prefer using Alembic migrations.
    """
    # For SQLite, ensure tables are created with correct schema
    # by dropping and recreating tables that have schema mismatches
    if settings.is_sqlite:
        _fix_sqlite_schema()
    Base.metadata.create_all(bind=engine)


def _fix_sqlite_schema() -> None:
    """Fix SQLite schema mismatches by recreating problematic tables."""
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Tables that need to be recreated due to schema issues
    tables_to_fix = ['social_posts', 'social_votes']
    
    for table_name in tables_to_fix:
        if table_name in existing_tables:
            # Check if table has correct columns
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            
            # social_posts needs user_id column
            if table_name == 'social_posts' and 'user_id' not in columns:
                with engine.connect() as conn:
                    conn.execute(text(f'DROP TABLE IF EXISTS {table_name}'))
                    conn.commit()
            
            # social_votes needs correct schema
            elif table_name == 'social_votes':
                expected_cols = {'id', 'post_id', 'voter_user_id', 'value', 'created_at'}
                if not expected_cols.issubset(set(columns)):
                    with engine.connect() as conn:
                        conn.execute(text(f'DROP TABLE IF EXISTS {table_name}'))
                        conn.commit()

    if "users" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("users")}
        user_column_defs = {
            "phone": "VARCHAR(64)",
            "address": "TEXT",
            "avatar_url": "VARCHAR(1024)",
            "date_of_birth": "DATETIME",
            "style_preference": "VARCHAR(255)",
            "body_profile": "TEXT",
            "budget_range": "TEXT",
            "preferred_brands": "TEXT",
            "occasion_preferences": "TEXT",
            "marketing_consent": "BOOLEAN",
            "data_sharing_consent": "BOOLEAN",
        }
        with engine.connect() as conn:
            schema_changed = False
            for column_name, column_type in user_column_defs.items():
                if column_name not in cols:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
                    schema_changed = True
            if schema_changed:
                conn.commit()

    # Lightweight forward-compatible migrations for SQLite dev:
    # add missing columns that are required for production-grade flows.
    if "orders" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("orders")}
        with engine.connect() as conn:
            if "delivery_method" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN delivery_method VARCHAR(32)"))
            if "pickup_store_id" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN pickup_store_id VARCHAR(36)"))
            if "pickup_time" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN pickup_time VARCHAR(64)"))
            if "payment_status" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN payment_status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
            conn.commit()

    if "notifications" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("notifications")}
        with engine.connect() as conn:
            if "store_id" not in cols:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN store_id VARCHAR(36)"))
            if "delivery_status" not in cols:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN delivery_status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
            if "delivery_attempts" not in cols:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN delivery_attempts INTEGER NOT NULL DEFAULT 0"))
            if "last_emitted_at" not in cols:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN last_emitted_at DATETIME"))
            if "ack_received_at" not in cols:
                conn.execute(text("ALTER TABLE notifications ADD COLUMN ack_received_at DATETIME"))
            conn.commit()


async def init_db_async() -> None:
    """
    Create all tables asynchronously.
    For PostgreSQL, prefer using Alembic migrations.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close all database connections."""
    await async_engine.dispose()
    engine.dispose()
