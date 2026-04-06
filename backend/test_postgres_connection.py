#!/usr/bin/env python3
"""
CONFIT Backend - PostgreSQL Connection Test Script
===================================================
Tests database connectivity, table creation, and basic operations.

Usage:
    python test_postgres_connection.py
    python test_postgres_connection.py --env-file .env.postgres
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure stdout can handle Unicode on Windows terminals (e.g., checkmarks)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # Fallback to default encoding if reconfiguration is not supported
    pass

# Load environment variables
from dotenv import load_dotenv


def load_environment(env_file: Optional[str] = None) -> None:
    """Load environment variables from file."""
    if env_file:
        env_path = Path(__file__).parent / env_file
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✓ Loaded environment from: {env_file}")
        else:
            print(f"✗ Environment file not found: {env_file}")
            sys.exit(1)
    else:
        # Try to load .env, then .env.postgres
        for env_name in ['.env', '.env.postgres']:
            env_path = Path(__file__).parent / env_name
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✓ Loaded environment from: {env_name}")
                break


def test_sync_connection() -> bool:
    """Test synchronous database connection."""
    print("\n" + "=" * 60)
    print("Testing Synchronous Connection")
    print("=" * 60)
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import StaticPool
        from database.config import settings
        
        print(f"\nDatabase URL: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
        print(f"Database Type: {'PostgreSQL' if settings.is_postgresql else 'SQLite'}")
        
        # Create engine with proper pool settings
        engine_kwargs = {"echo": False}
        
        if settings.is_sqlite:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs.update(settings.pool_settings)
        
        engine = create_engine(settings.database_url, **engine_kwargs)
        
        # Test connection
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1"))
            print("✓ Basic query successful: SELECT 1")
            
            # Get database version
            if settings.is_postgresql:
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.scalar()
                print(f"✓ PostgreSQL Version: {version[:50]}...")
                
                # Check extensions
                ext_result = conn.execute(text(
                    "SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto', 'pg_trgm')"
                ))
                extensions = [row[0] for row in ext_result]
                if extensions:
                    print(f"✓ Extensions installed: {', '.join(extensions)}")
            else:
                print("✓ SQLite connection successful")
        
        engine.dispose()
        print("\n✓ Synchronous connection test PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Synchronous connection test FAILED: {e}")
        return False


async def test_async_connection() -> bool:
    """Test asynchronous database connection."""
    print("\n" + "=" * 60)
    print("Testing Asynchronous Connection")
    print("=" * 60)
    
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import StaticPool
        from database.config import settings
        
        print(f"\nAsync Database URL: {settings.async_database_url.split('@')[-1] if '@' in settings.async_database_url else settings.async_database_url}")
        
        # Create async engine with proper pool settings
        engine_kwargs = {"echo": False}
        
        if settings.is_sqlite:
            # SQLite async requires StaticPool for check_same_thread
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs.update(settings.pool_settings)
        
        engine = create_async_engine(settings.async_database_url, **engine_kwargs)
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Async basic query successful: SELECT 1")
            
            if settings.is_postgresql:
                version_result = await conn.execute(text("SELECT version()"))
                version = version_result.scalar()
                print(f"✓ Async PostgreSQL connection verified")
        
        await engine.dispose()
        print("\n✓ Asynchronous connection test PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Asynchronous connection test FAILED: {e}")
        return False


def test_table_creation() -> bool:
    """Test table creation using SQLAlchemy models."""
    print("\n" + "=" * 60)
    print("Testing Table Creation")
    print("=" * 60)
    
    try:
        from database import Base, engine
        from sqlalchemy import inspect
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        
        # Inspect tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables in database: {len(tables)} tables")
        
        if tables:
            print(f"  Tables: {', '.join(sorted(tables)[:10])}")
            if len(tables) > 10:
                print(f"  ... and {len(tables) - 10} more")
        
        print("\n✓ Table creation test PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Table creation test FAILED: {e}")
        return False


def test_session_operations() -> bool:
    """Test basic CRUD operations using session."""
    print("\n" + "=" * 60)
    print("Testing Session Operations")
    print("=" * 60)
    
    try:
        from sqlalchemy import text
        from database import SessionLocal
        
        session = SessionLocal()
        
        try:
            # Test insert
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            session.commit()
            print("✓ Test table created")
            
            # Test insert
            session.execute(text("INSERT INTO test_table (name) VALUES (:name)"), {"name": "test_user"})
            session.commit()
            print("✓ Test insert successful")
            
            # Test select
            result = session.execute(text("SELECT name FROM test_table WHERE name = :name"), {"name": "test_user"})
            row = result.fetchone()
            if row and row[0] == "test_user":
                print("✓ Test select successful")
            
            # Test update
            session.execute(text("UPDATE test_table SET name = :new_name WHERE name = :old_name"), 
                          {"new_name": "updated_user", "old_name": "test_user"})
            session.commit()
            print("✓ Test update successful")
            
            # Test delete
            session.execute(text("DELETE FROM test_table WHERE name = :name"), {"name": "updated_user"})
            session.commit()
            print("✓ Test delete successful")
            
            # Cleanup
            session.execute(text("DROP TABLE IF EXISTS test_table"))
            session.commit()
            print("✓ Test table cleaned up")
            
        finally:
            session.close()
        
        print("\n✓ Session operations test PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Session operations test FAILED: {e}")
        return False


def test_alembic_migrations() -> bool:
    """Test Alembic migration setup."""
    print("\n" + "=" * 60)
    print("Testing Alembic Migrations")
    print("=" * 60)
    
    try:
        from alembic.config import Config
        from alembic import command
        
        # Check alembic.ini
        alembic_ini = Path(__file__).parent / "alembic.ini"
        if not alembic_ini.exists():
            print("✗ alembic.ini not found")
            return False
        print("✓ alembic.ini found")
        
        # Check versions directory
        versions_dir = Path(__file__).parent / "alembic" / "versions"
        if not versions_dir.exists():
            print("✗ alembic/versions directory not found")
            return False
        print("✓ alembic/versions directory found")
        
        # List migrations
        migrations = list(versions_dir.glob("*.py"))
        migrations = [m for m in migrations if m.name != "__init__.py"]
        print(f"✓ Found {len(migrations)} migration file(s)")
        
        if migrations:
            for migration in migrations[:5]:
                print(f"  - {migration.name}")
        
        # Check current revision
        alembic_cfg = Config(str(alembic_ini))
        try:
            command.current(alembic_cfg)
            print("✓ Alembic current command executed")
        except Exception as e:
            print(f"  Note: Could not get current revision: {e}")
        
        print("\n✓ Alembic migrations test PASSED")
        return True
        
    except ImportError as e:
        print(f"\n✗ Alembic not installed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Alembic migrations test FAILED: {e}")
        return False


def test_docker_connection() -> bool:
    """Test if Docker PostgreSQL container is running."""
    print("\n" + "=" * 60)
    print("Testing Docker PostgreSQL Container")
    print("=" * 60)
    
    import subprocess
    
    try:
        # Check if Docker is available
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=confit-postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "confit-postgres" in result.stdout:
            print("✓ confit-postgres container is running")
            
            # Get container details
            result = subprocess.run(
                ["docker", "inspect", "confit-postgres", "--format", "{{.State.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            status = result.stdout.strip()
            print(f"✓ Container status: {status}")
            
            return True
        else:
            print("✗ confit-postgres container is not running")
            print("\n  To start the container, run:")
            print("  docker-compose -f docker-compose.postgres.yml up -d")
            return False
            
    except FileNotFoundError:
        print("✗ Docker is not installed or not in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("✗ Docker command timed out")
        return False
    except Exception as e:
        print(f"✗ Docker test failed: {e}")
        return False


def main() -> int:
    """Run all tests and return exit code."""
    parser = argparse.ArgumentParser(description="Test PostgreSQL connection for CONFIT")
    parser.add_argument("--env-file", help="Path to environment file", default=None)
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker container check")
    args = parser.parse_args()
    
    print("=" * 60)
    print("CONFIT PostgreSQL Connection Test")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Load environment
    load_environment(args.env_file)
    
    # Run tests
    results = []
    
    # Docker test (optional)
    if not args.skip_docker:
        results.append(("Docker Container", test_docker_connection()))
    
    # Database connection tests
    results.append(("Sync Connection", test_sync_connection()))
    results.append(("Async Connection", asyncio.run(test_async_connection())))
    results.append(("Table Creation", test_table_creation()))
    results.append(("Session Operations", test_session_operations()))
    results.append(("Alembic Migrations", test_alembic_migrations()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Database is ready for production.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
