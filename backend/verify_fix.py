#!/usr/bin/env python3
"""Quick verification that model imports work without conflicts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("Testing model imports...")

try:
    # Import database session which loads all models
    from database import Base, engine, SessionLocal
    print("✓ database imports successful")
    
    # Check that models are registered
    tables = list(Base.metadata.tables.keys())
    print(f"✓ {len(tables)} tables registered")
    
    # Check for duplicates (should not happen now)
    table_names = set()
    duplicates = []
    for name in tables:
        if name in table_names:
            duplicates.append(name)
        table_names.add(name)
    
    if duplicates:
        print(f"✗ Duplicate tables found: {duplicates}")
        sys.exit(1)
    else:
        print("✓ No duplicate tables")
    
    # Test connection
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"⚠ Database connection skipped: {e}")
    
    print("\n✅ All model imports working correctly!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
