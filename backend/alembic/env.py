"""
CONFIT Backend - Alembic Environment Configuration
===================================================
Supports both online (database) and offline (SQL script) migrations.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.orm import sessionmaker

from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models to register them with Base.metadata
from database.base import Base
from database.config import settings, get_database_url

# Import all models so they are registered
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

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url() -> str:
    """
    Get database URL from environment or config.
    Priority: DATABASE_URL env var > alembic.ini
    """
    return get_database_url(async_driver=False)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare types for better migration detection
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare types for better migration detection
        compare_type=True,
        compare_server_default=True,
        # For PostgreSQL
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Uses async engine for PostgreSQL, sync for SQLite.
    """
    if settings.is_postgresql:
        asyncio.run(run_async_migrations())
    else:
        # SQLite - use sync engine
        from sqlalchemy import create_engine
        
        url = get_url()
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
            connect_args={"check_same_thread": False} if settings.is_sqlite else {},
        )
        
        with connectable.connect() as connection:
            do_run_migrations(connection)
        
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
