"""
CONFIT Backend — Database Configuration
=========================================
Centralised database URL and settings. Supports SQLite (development)
and PostgreSQL (production). Never commit real credentials; use env vars.
"""

import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse, quote_plus


def get_database_url(async_driver: bool = False) -> str:
    """
    Get database URL with appropriate driver.
    
    Args:
        async_driver: If True, returns URL with async driver (asyncpg/aiosqlite)
    
    Returns:
        Database connection URL
    """
    db_url = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
    
    if not async_driver:
        return db_url
    
    # Convert to async drivers
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("sqlite://"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    
    return db_url


def get_connect_args() -> Dict[str, Any]:
    """
    Get connection arguments based on database type.
    
    Returns:
        Dictionary of connection arguments
    """
    db_url = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
    
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    
    # PostgreSQL doesn't need special connect args
    return {}


def get_pool_settings() -> Dict[str, Any]:
    """
    Get connection pool settings for PostgreSQL.
    
    Returns:
        Dictionary of pool settings
    """
    db_url = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
    
    if db_url.startswith(("postgresql", "postgres")):
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "pool_pre_ping": True,  # Verify connections before use
        }
    
    # SQLite doesn't use connection pooling
    return {}


class Settings:
    """Database settings loaded from environment."""
    
    # Database URL (sync driver)
    database_url: str = get_database_url(async_driver=False)
    
    # Database URL (async driver)
    async_database_url: str = get_database_url(async_driver=True)
    
    # Connection arguments
    connect_args: Dict[str, Any] = get_connect_args()
    
    # Pool settings (PostgreSQL only)
    pool_settings: Dict[str, Any] = get_pool_settings()
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL."""
        return self.database_url.startswith(("postgresql", "postgres"))
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return self.database_url.startswith("sqlite")


settings = Settings()
