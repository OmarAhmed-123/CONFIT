"""
CONFIT Backend - SQLAlchemy Declarative Base
=============================================
Single base for all ORM models so Alembic can discover them.
"""

import os
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import JSON


class Base(DeclarativeBase):
    """Base class for all CONFIT database models."""
    pass

# JSONType for SQLite/PostgreSQL compatibility
# SQLite doesn't support JSONB, so we use JSON which works for both
JSONType = JSON

# Schema support - SQLite doesn't support schemas
_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
SCHEMA = "public" if _DB_URL.startswith("postgresql") else None

def get_table_args(schema: str = "public", **kwargs):
    """
    Get table args with conditional schema support.
    Use this instead of hardcoding {"schema": "public"}.
    
    In PostgreSQL: uses the specified schema
    In SQLite: omits schema entirely
    """
    if SCHEMA:
        kwargs["schema"] = schema
    kwargs.setdefault("extend_existing", True)
    return kwargs
