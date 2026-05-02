#!/usr/bin/env python3
"""Test Prometheus metrics import without duplication errors."""

import sys

def test_import():
    """Test that metrics can be imported without duplicate registration errors."""
    try:
        # First import
        from core.observability.prometheus_metrics import confit_orders_total
        print(f"First import OK: {confit_orders_total}")
        
        # Second import (simulates reload)
        from core.observability.prometheus_metrics import confit_orders_total as orders2
        print(f"Second import OK: {orders2}")
        
        # Import from metrics.py
        from core.observability.metrics import ORDERS_CREATED
        print(f"metrics.py import OK: {ORDERS_CREATED}")
        
        # Import monitoring middleware
        from core.middleware.monitoring import REQUEST_COUNT
        print(f"monitoring.py import OK: {REQUEST_COUNT}")
        
        print("\n✅ All metrics imported successfully!")
        return 0
    except ValueError as e:
        print(f"\n❌ Duplicate metric error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_import())
