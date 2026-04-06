#!/usr/bin/env python
"""
CONFIT Backend - API Smoke Tests
================================
Lightweight integration checks for core HTTP flows against the FastAPI app.

These tests assume:
- PostgreSQL is running and reachable via DATABASE_URL
- Alembic/metadata have been applied (tables exist)

Usage:
    python test_api_smoke.py
"""

import os
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


def _load_env() -> None:
    """Load backend environment for tests."""
    # Prefer explicit env file if present
    for name in (".env", ".env.postgres"):
        env_path = ROOT_DIR / name
        if env_path.exists():
            load_dotenv(env_path)
            break


def test_health(client) -> None:
    """Verify /api/health endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"/api/health failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data.get("status") == "ok"


def test_products_featured(client) -> None:
    """Verify /api/products/featured returns a list."""
    resp = client.get("/api/products/featured")
    assert resp.status_code == 200, f"/api/products/featured failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert isinstance(data, list)


def test_auth_register_and_login(client) -> None:
    """
    Basic auth flow:
    - Register a user with a random email
    - Login with the same credentials
    """
    email = f"smoke-{uuid4().hex[:12]}@confit.local"
    password = "Conf1tSmokeTest!2026"

    # Register
    register_payload = {
        "name": "Smoke Test User",
        "email": email,
        "password": password,
    }
    r1 = client.post("/api/auth/register", json=register_payload)
    assert r1.status_code in (200, 201, 400), f"Unexpected register status: {r1.status_code} {r1.text}"
    # If user already exists (unlikely for random email), continue to login anyway

    # Login
    login_payload = {"email": email, "password": password}
    r2 = client.post("/api/auth/login", json=login_payload)
    assert r2.status_code == 200, f"Login failed: {r2.status_code} {r2.text}"
    data = r2.json()
    assert "token" in data or "access_token" in data, f"Missing token in login response: {data}"


def main() -> int:
    """Run smoke tests using FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from main import app

    _load_env()

    client = TestClient(app)

    print("=" * 60)
    print("CONFIT Backend - API Smoke Tests")
    print("=" * 60)

    tests = [
        ("Health check", test_health),
        ("Featured products", test_products_featured),
        ("Auth register/login", test_auth_register_and_login),
    ]

    for name, fn in tests:
        print(f"[+] {name} ...", end=" ", flush=True)
        fn(client)
        print("OK")

    print("\nAll API smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

