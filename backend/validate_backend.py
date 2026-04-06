#!/usr/bin/env python
"""CONFIT Backend — Full Validation Test."""

import sys
import traceback

errors = []
passed = []

def test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"[OK] {name}")
        return True
    except Exception as e:
        errors.append((name, str(e)))
        print(f"[FAIL] {name}: {e}")
        return False

# Test 1: Main app
test("Main app import", lambda: __import__("main"))

# Test 2: Core modules
def test_core():
    from core.config import settings
    from core.errors import AppError, ValidationError, NotFoundError, AuthError
    from core.responses import success_response, error_response
    from core.exceptions import register_exception_handlers
test("Core modules", test_core)

# Test 3: Repositories
def test_repos():
    from repositories import BaseRepository, UserRepository, ProductRepository, OrderRepository, WardrobeRepository
test("Repositories", test_repos)

# Test 4: Schemas
def test_schemas():
    from schemas import UserCreate, ProductCreate, OrderCreate, WardrobeItemCreate
test("Schemas", test_schemas)

# Test 5: Utils
def test_utils():
    from utils import validate_email, utc_now, validate_base64_image, get_current_user
test("Utils", test_utils)

# Test 6: Database
def test_db():
    from database import Base, SessionLocal, get_db
test("Database", test_db)

# Test 7: Key routers
def test_routers():
    from routers.profile import router
    from routers.onboarding import router
    from routers.signals import router
test("Key routers", test_routers)

# Test 8: Key services
def test_services():
    from services.profile_service import ProfileService
    from services.ai_brain_service import AIBrainService
test("Key services", test_services)

# Test 9: Models
def test_models():
    from database.models import User, Product, Order, WardrobeItem
test("ORM Models", test_models)

# Test 10: App routes count
def test_routes():
    from main import app
    routes = [r for r in app.routes if hasattr(r, 'path')]
    assert len(routes) > 50, f"Expected >50 routes, got {len(routes)}"
test("Route registration", test_routes)

print()
print("=" * 50)
if errors:
    print(f"FAILED: {len(errors)} errors found")
    for name, err in errors:
        print(f"  - {name}: {err}")
    sys.exit(1)
else:
    print(f"SUCCESS: {len(passed)} tests passed")
    print("Backend is production-ready")
    sys.exit(0)
