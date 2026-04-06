"""
CONFIT Backend - Database Infrastructure
========================================
SQLAlchemy async database configuration and session management.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# BASE MODEL
# ─────────────────────────────────────────────────────────────────────────────

Base = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE URL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def get_database_url(async_driver: bool = True) -> str:
    """Get database URL with appropriate driver."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
    
    # Convert postgres:// to postgresql+asyncpg://
    if db_url.startswith("postgresql://") and async_driver:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://") and async_driver:
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    # Convert sqlite:// to sqlite+aiosqlite:// for async support
    elif db_url.startswith("sqlite://") and async_driver:
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    
    return db_url


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC ENGINE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def create_async_engine_configured() -> AsyncEngine:
    """Create configured async engine."""
    db_url = get_database_url(async_driver=True)
    
    # Configuration based on database type
    if db_url.startswith("postgresql"):
        engine_kwargs = {
            "echo": settings.DEBUG,
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }
    else:
        # SQLite configuration
        engine_kwargs = {
            "echo": settings.DEBUG,
            "connect_args": {"check_same_thread": False},
        }
    
    return create_async_engine(db_url, **engine_kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# SYNC ENGINE (for Alembic migrations)
# ─────────────────────────────────────────────────────────────────────────────

def create_sync_engine_configured():
    """Create configured sync engine for migrations."""
    db_url = get_database_url(async_driver=False)
    
    if db_url.startswith("postgresql"):
        return create_engine(
            db_url,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=5,
        )
    else:
        return create_engine(
            db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
        )


# ─────────────────────────────────────────────────────────────────────────────
# ENGINES
# ─────────────────────────────────────────────────────────────────────────────

# Async engine for application
engine: AsyncEngine = create_async_engine_configured()

# Session factories
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync session for migrations
sync_engine = create_sync_engine_configured()
sync_session_factory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session (FastAPI dependency)."""
    async with async_session_factory() as session:
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
    """Context manager for async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get sync database session (for migrations and scripts)."""
    return sync_session_factory()


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all database tables (use with caution!)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def is_postgresql() -> bool:
    """Check if using PostgreSQL."""
    return get_database_url().startswith("postgresql")


def is_sqlite() -> bool:
    """Check if using SQLite."""
    return get_database_url().startswith("sqlite")
