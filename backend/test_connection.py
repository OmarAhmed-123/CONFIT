#!/usr/bin/env python
"""Quick test script to verify database connection and model registration."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUTPUT = []

def log(msg):
    OUTPUT.append(msg)
    print(msg)

def test_imports():
    """Test that all model imports work correctly."""
    log("Testing imports...")
    
    try:
        from database.base import Base
        log("  OK database.base")
    except Exception as e:
        log(f"  FAIL database.base: {e}")
        return False
    
    try:
        from database.config import settings
        log(f"  OK database.config (is_sqlite={settings.is_sqlite})")
    except Exception as e:
        log(f"  FAIL database.config: {e}")
        return False
    
    try:
        import database.models
        log("  OK database.models")
    except Exception as e:
        log(f"  FAIL database.models: {e}")
        return False
    
    try:
        import models.production_models
        log("  OK models.production_models")
    except Exception as e:
        log(f"  FAIL models.production_models: {e}")
        return False
    
    return True


def test_engine():
    """Test engine creation."""
    log("Testing engine creation...")
    
    try:
        from database.session import engine, async_engine
        log(f"  OK Sync engine: {engine.url}")
        log(f"  OK Async engine: {async_engine.url}")
        return True
    except Exception as e:
        log(f"  FAIL Engine creation: {e}")
        import traceback
        log(traceback.format_exc())
        return False


def test_metadata():
    """Test that models are registered with Base.metadata."""
    log("Testing metadata registration...")
    
    try:
        from database.base import Base
        tables = list(Base.metadata.tables.keys())
        log(f"  OK Tables registered: {len(tables)}")
        log(f"  Sample: {tables[:15]}")
        return True
    except Exception as e:
        log(f"  FAIL Metadata: {e}")
        return False


def main():
    log("=" * 60)
    log("CONFIT Database Connection Test")
    log("=" * 60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Engine", test_engine()))
    results.append(("Metadata", test_metadata()))
    
    log("")
    log("=" * 60)
    all_passed = all(r[1] for r in results)
    log(f"Overall: {'PASS' if all_passed else 'FAIL'}")
    
    # Write to file
    with open("test_results.txt", "w") as f:
        f.write("\n".join(OUTPUT))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
