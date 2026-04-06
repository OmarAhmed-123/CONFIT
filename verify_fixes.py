#!/usr/bin/env python3
"""
Verification script for CONFIT production fixes.
Run this after restarting the backend server.
"""

import urllib.request
import urllib.error
import json
import sys

def test_endpoint(name, url, expected_check):
    """Test an endpoint and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            headers = dict(response.headers)
            
            print(f"Status: {response.status} OK")
            print(f"\nResponse:")
            print(json.dumps(data, indent=2)[:500])
            
            if expected_check(data):
                print(f"\n✅ PASS: {name}")
                return True
            else:
                print(f"\n❌ FAIL: {name} - Unexpected response")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"Status: {e.code}")
        print(f"Error: {e.read().decode()}")
        print(f"\n❌ FAIL: {name} - HTTP Error {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}")
        print(f"\n❌ FAIL: {name} - Server not running?")
        return False
    except Exception as e:
        print(f"Error: {e}")
        print(f"\n❌ FAIL: {name} - Unexpected error")
        return False


def check_security_headers(url):
    """Check security headers on response."""
    print(f"\n{'='*60}")
    print(f"Testing: Security Headers")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as response:
            headers = dict(response.headers)
            
            required_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'Strict-Transport-Security',
                'Content-Security-Policy',
            ]
            
            all_present = True
            for header in required_headers:
                present = header in headers
                status = "✅" if present else "❌"
                print(f"{status} {header}: {headers.get(header, 'NOT SET')}")
                if not present:
                    all_present = False
            
            if all_present:
                print(f"\n✅ PASS: Security Headers")
                return True
            else:
                print(f"\n❌ FAIL: Some security headers missing")
                return False
                
    except urllib.error.HTTPError as e:
        # 405 is expected for HEAD on some endpoints, try GET
        if e.code == 405:
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as response:
                    headers = dict(response.headers)
                    required_headers = ['X-Content-Type-Options', 'X-Frame-Options']
                    all_present = all(h in headers for h in required_headers)
                    print(f"Headers found: {list(headers.keys())}")
                    return all_present
            except Exception as e2:
                print(f"Error: {e2}")
                return False
        print(f"Error: {e.code}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    print("=" * 60)
    print("  CONFIT Production Fixes Verification")
    print("=" * 60)
    
    results = []
    
    # Test 1: Synthetic product ID
    results.append(test_endpoint(
        "Products - Synthetic ID (prod-132)",
        "http://localhost:8001/api/products/prod-132",
        lambda d: d.get('id') == 'prod-132' and d.get('name') is not None
    ))
    
    # Test 2: Payment config
    results.append(test_endpoint(
        "Payments Config",
        "http://localhost:8001/api/payments/config",
        lambda d: 'stripe_enabled' in d and 'paymob_enabled' in d and 'paypal_enabled' in d
    ))
    
    # Test 3: Security headers
    results.append(check_security_headers("http://localhost:8001/api/products"))
    
    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Fixes verified!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Check server restart")
        return 1


if __name__ == "__main__":
    sys.exit(main())
