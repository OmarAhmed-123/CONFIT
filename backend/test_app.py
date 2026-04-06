#!/usr/bin/env python
"""Quick test to verify FastAPI app loads correctly."""

import sys
import traceback

try:
    from main import app
    print("SUCCESS: FastAPI app loaded")
    print(f"App title: {app.title}")
    print(f"Total routes: {len([r for r in app.routes])}")
    
    # Test key routers
    from routers.profile import router as profile_router
    from routers.onboarding import router as onboarding_router
    from routers.signals import router as signals_router
    print("SUCCESS: All key routers imported")
    
    # Test core modules
    from core.config import settings
    from core.errors import AppError, ValidationError, NotFoundError
    print("SUCCESS: Core modules imported")
    
    print("\n=== ALL TESTS PASSED ===")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
