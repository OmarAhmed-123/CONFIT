"""
CONFIT Backend - Seed Test Users
================================
Creates test users for E2E testing and development with proper role assignments.

Test Accounts (from docs/ACCESS_CONTROL_AND_E2E.md):
- Customer: customer.e2e@confit.com / ConfitTest123 (role: user)
- Store Owner: owner.e2e@confit.com / ConfitTest123 (role: brand_manager)
- Admin: admin.e2e@confit.com / ConfitTest123 (role: admin)

Usage:
    python -m scripts.seed_test_users
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.session import SessionLocal
from database.models import User, UserRole, AppRole, UserGamification
from services.auth_service import AuthService
from sqlalchemy.exc import IntegrityError


# Test user definitions
TEST_USERS = [
    {
        "email": "customer.e2e@confit.com",
        "password": "ConfitTest123",
        "name": "E2E Customer",
        "role": AppRole.user,
        "description": "Standard customer account for testing shopping flows",
    },
    {
        "email": "owner.e2e@confit.com",
        "password": "ConfitTest123",
        "name": "E2E Store Owner",
        "role": AppRole.brand_manager,
        "description": "Store owner account for testing store management",
    },
    {
        "email": "admin.e2e@confit.com",
        "password": "ConfitTest123",
        "name": "E2E Admin",
        "role": AppRole.admin,
        "description": "Admin account for testing admin features",
    },
    {
        "email": "stylist.e2e@confit.com",
        "password": "ConfitTest123",
        "name": "E2E Stylist",
        "role": AppRole.stylist,
        "description": "Stylist account for testing styling tools",
    },
    # Development convenience accounts
    {
        "email": "demo@confit.com",
        "password": "Demo123456",
        "name": "Demo User",
        "role": AppRole.brand_manager,
        "description": "Demo account for quick testing",
    },
    {
        "email": "admin@confit.com",
        "password": "Admin123456",
        "name": "Admin User",
        "role": AppRole.admin,
        "description": "Admin account for quick testing",
    },
]


def seed_test_users(db=None, force: bool = False) -> dict:
    """
    Seed test users with their roles.
    
    Args:
        db: Database session (optional, will create if not provided)
        force: If True, update existing users' passwords and roles
    
    Returns:
        Dict with seeded users and any errors
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    results = {"seeded": [], "updated": [], "skipped": [], "errors": []}
    auth_service = AuthService(db)
    
    for user_def in TEST_USERS:
        email = user_def["email"].lower().strip()
        existing = db.query(User).filter(User.email == email).first()
        
        try:
            if existing:
                if force:
                    # Update password and role
                    existing.password_hash = auth_service._hash_password(user_def["password"])
                    existing.name = user_def["name"]
                    db.commit()
                    
                    # Update role
                    existing_roles = db.query(UserRole).filter(UserRole.user_id == existing.id).all()
                    for r in existing_roles:
                        db.delete(r)
                    db.commit()
                    
                    new_role = UserRole(
                        user_id=existing.id,
                        role=user_def["role"]
                    )
                    db.add(new_role)
                    db.commit()
                    
                    results["updated"].append({
                        "email": email,
                        "role": user_def["role"].value,
                    })
                else:
                    results["skipped"].append({
                        "email": email,
                        "reason": "Already exists (use force=True to update)",
                    })
            else:
                # Create new user
                profile, error = auth_service.register(
                    name=user_def["name"],
                    email=email,
                    password=user_def["password"],
                )
                
                if error:
                    results["errors"].append({
                        "email": email,
                        "error": error,
                    })
                    continue
                
                # Update role (register creates default 'user' role)
                if user_def["role"] != AppRole.user:
                    existing_roles = db.query(UserRole).filter(UserRole.user_id == profile.id).all()
                    for r in existing_roles:
                        db.delete(r)
                    db.commit()
                    
                    new_role = UserRole(
                        user_id=profile.id,
                        role=user_def["role"]
                    )
                    db.add(new_role)
                    db.commit()
                
                results["seeded"].append({
                    "email": email,
                    "name": user_def["name"],
                    "role": user_def["role"].value,
                    "description": user_def["description"],
                })
                
        except IntegrityError as e:
            db.rollback()
            results["errors"].append({
                "email": email,
                "error": f"IntegrityError: {str(e)}",
            })
        except Exception as e:
            db.rollback()
            results["errors"].append({
                "email": email,
                "error": str(e),
            })
    
    if should_close:
        db.close()
    
    return results


def main():
    """Run seed script from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed test users for CONFIT")
    parser.add_argument("--force", "-f", action="store_true", help="Update existing users")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  CONFIT Test Users Seeder")
    print("=" * 60)
    
    results = seed_test_users(force=args.force)
    
    if not args.quiet:
        if results["seeded"]:
            print("\n[SEEDED]")
            for user in results["seeded"]:
                print(f"  + {user['email']} ({user['role']}) - {user['description']}")
        
        if results["updated"]:
            print("\n[UPDATED]")
            for user in results["updated"]:
                print(f"  ~ {user['email']} ({user['role']})")
        
        if results["skipped"]:
            print("\n[SKIPPED]")
            for user in results["skipped"]:
                print(f"  - {user['email']}: {user['reason']}")
        
        if results["errors"]:
            print("\n[ERRORS]")
            for user in results["errors"]:
                print(f"  ! {user['email']}: {user['error']}")
    
    # Summary
    total = len(results["seeded"]) + len(results["updated"]) + len(results["skipped"])
    print(f"\n[SUMMARY] {len(results['seeded'])} seeded, {len(results['updated'])} updated, {len(results['skipped'])} skipped, {len(results['errors'])} errors")
    
    if results["seeded"] or results["updated"]:
        print("\n[TEST ACCOUNTS]")
        print("-" * 60)
        for user_def in TEST_USERS:
            print(f"  {user_def['role'].value:15} | {user_def['email']:25} | {user_def['password']}")
        print("-" * 60)
    
    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
