#!/usr/bin/env python
"""Test all backend imports."""
import sys
import os

# Ensure we're in the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing backend imports...")
print("=" * 50)

errors = []

# Test services
try:
    from services.profile_service import ProfileService, get_profile_service
    print("services.profile_service: OK")
except Exception as e:
    print(f"services.profile_service: FAIL - {e}")
    errors.append(("services.profile_service", str(e)))

try:
    from services.confidence_service import ConfidenceService, get_confidence_service
    print("services.confidence_service: OK")
except Exception as e:
    print(f"services.confidence_service: FAIL - {e}")
    errors.append(("services.confidence_service", str(e)))

# Test routers
routers = [
    'routers.virtual_tryon',
    'routers.virtual_stylist', 
    'routers.rotation',
    'routers.auth',
    'routers.products',
    'routers.orders',
    'routers.newsletter',
    'routers.wardrobe',
    'routers.brands',
    'routers.stores',
    'routers.promo_codes',
    'routers.visual_search',
    'routers.wishlist',
    'routers.outfits',
    'routers.payments',
    'routers.analytics',
    'routers.digital_twin',
    'routers.social',
    'routers.resale',
    'routers.omni',
    'routers.challenges',
    'routers.chatbot',
    'routers.profile',
    'routers.onboarding',
    'routers.signals',
    'routers.privacy',
    'routers.identity_intelligence',
]

for r in routers:
    try:
        __import__(r)
        print(f"{r}: OK")
    except Exception as e:
        print(f"{r}: FAIL - {e}")
        errors.append((r, str(e)))

# Test main app
try:
    from main import app
    print("main app: OK")
except Exception as e:
    print(f"main app: FAIL - {e}")
    errors.append(("main", str(e)))

print("=" * 50)
if errors:
    print(f"\n{len(errors)} ERRORS FOUND:")
    for r, e in errors:
        print(f"  - {r}: {e}")
    sys.exit(1)
else:
    print("\nAll imports successful!")
    sys.exit(0)
