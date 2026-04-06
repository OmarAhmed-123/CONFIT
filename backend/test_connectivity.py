#!/usr/bin/env python
"""Test backend connectivity."""
import httpx
import time

print("Testing backend connectivity...")
print("=" * 50)

for i in range(3):
    try:
        resp = httpx.get("http://127.0.0.1:8000/api/health", timeout=2.0)
        print(f"[OK] Health check: {resp.status_code} - {resp.json()}")
        break
    except Exception as e:
        print(f"[RETRY {i+1}] Backend not responding: {e}")
        time.sleep(1)
else:
    print("[FAIL] Backend not responding after 3 attempts")
    print("Start backend with: cd backend && python main.py")
    exit(1)

# Test a few more endpoints
endpoints = [
    "/",
    "/api/products",
    "/api/products/featured",
    "/api/brands",
]

for endpoint in endpoints:
    try:
        resp = httpx.get(f"http://127.0.0.1:8000{endpoint}", timeout=5.0)
        print(f"[OK] {endpoint}: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] {endpoint}: {e}")

print("=" * 50)
print("Backend connectivity test complete")
