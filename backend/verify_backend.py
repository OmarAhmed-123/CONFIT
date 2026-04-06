#!/usr/bin/env python
"""Verify backend can start without errors."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("CONFIT Backend Verification")
print("=" * 60)

# Test 1: Database config
print("\n[1] Testing database config...")
try:
    from database.config import settings
    print(f"    OK - is_sqlite: {settings.is_sqlite}")
    print(f"    OK - database_url: {settings.database_url[:50]}...")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 2: Base import
print("\n[2] Testing Base import...")
try:
    from database.base import Base
    print("    OK - Base imported")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 3: Database models
print("\n[3] Testing database.models...")
try:
    import database.models
    print("    OK - database.models imported")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 4: Production models
print("\n[4] Testing models.production_models...")
try:
    import models.production_models
    print("    OK - production_models imported")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 5: Session creation
print("\n[5] Testing session creation...")
try:
    from database.session import engine, async_engine, SessionLocal
    print(f"    OK - Sync engine: {engine.url}")
    print(f"    OK - Async engine: {async_engine.url}")
except Exception as e:
    print(f"    FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Table count
print("\n[6] Testing metadata registration...")
try:
    from database.base import Base
    tables = list(Base.metadata.tables.keys())
    print(f"    OK - {len(tables)} tables registered")
    print(f"    Sample: {tables[:10]}")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 7: Auth service
print("\n[7] Testing auth service...")
try:
    from services.auth_service import AuthService
    print("    OK - AuthService imported")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# Test 8: Main app import
print("\n[8] Testing main app import...")
try:
    import main
    print("    OK - main.py imported")
except Exception as e:
    print(f"    FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED - Backend is ready")
print("=" * 60)
