#!/usr/bin/env python
"""Quick test to verify model imports work without conflicts."""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

print("Testing model imports...")
try:
    from database import Base
    print(f"SUCCESS: Base.metadata has {len(Base.metadata.tables)} tables")
    
    # Check for duplicates
    table_names = list(Base.metadata.tables.keys())
    print(f"Sample tables: {table_names[:10]}")
    
    # Test main import
    from main import app
    print("SUCCESS: main.app imported")
    
    print("\nALL TESTS PASSED!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
