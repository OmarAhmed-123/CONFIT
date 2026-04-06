#!/usr/bin/env python3
"""Quick test for CONFIT fixes - run this after starting the backend."""

import urllib.request
import json

def test():
    print("Testing Products API (prod-132)...")
    try:
        url = "http://localhost:8001/api/products/prod-132"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            print(f"✅ SUCCESS: {data.get('name', 'No name')} - ${data.get('price', 0)}")
            return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    test()
