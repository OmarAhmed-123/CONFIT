#!/usr/bin/env python
"""Quick validation check."""
import sys

errors = []
passed = []

# Test 1
try:
    from main import app
    passed.append("main.py")
except Exception as e:
    errors.append(f"main: {e}")

# Test 2
try:
    from core.config import settings
    passed.append("core.config")
except Exception as e:
    errors.append(f"core.config: {e}")

# Test 3
try:
    from core.errors import AppError, ValidationError
    passed.append("core.errors")
except Exception as e:
    errors.append(f"core.errors: {e}")

# Test 4
try:
    from repositories import UserRepository, ProductRepository
    passed.append("repositories")
except Exception as e:
    errors.append(f"repositories: {e}")

# Test 5
try:
    from schemas import UserCreate, ProductCreate
    passed.append("schemas")
except Exception as e:
    errors.append(f"schemas: {e}")

# Test 6
try:
    from utils import validate_email, utc_now
    passed.append("utils")
except Exception as e:
    errors.append(f"utils: {e}")

# Test 7
try:
    from database import Base, get_db
    passed.append("database")
except Exception as e:
    errors.append(f"database: {e}")

# Write results
with open("validation_result.txt", "w") as f:
    f.write(f"PASSED: {len(passed)}\n")
    for p in passed:
        f.write(f"  [OK] {p}\n")
    
    if errors:
        f.write(f"\nFAILED: {len(errors)}\n")
        for e in errors:
            f.write(f"  [FAIL] {e}\n")
    else:
        f.write("\nALL IMPORTS SUCCESSFUL\n")

sys.exit(0 if not errors else 1)
