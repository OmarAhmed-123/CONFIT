import sys
sys.path.insert(0, r'e:\CONFIT\backend')

try:
    from database.config import settings
    print(f"Config OK, is_sqlite: {settings.is_sqlite}")
except Exception as e:
    print(f"Config FAIL: {e}")

try:
    from database.base import Base
    print(f"Base OK")
except Exception as e:
    print(f"Base FAIL: {e}")

try:
    import database.models
    print(f"database.models OK")
except Exception as e:
    print(f"database.models FAIL: {e}")

try:
    from database.session import engine
    print(f"Engine OK: {engine.url}")
except Exception as e:
    print(f"Engine FAIL: {e}")

try:
    from database.base import Base
    print(f"Tables count: {len(Base.metadata.tables.keys())}")
    print(f"Tables: {list(Base.metadata.tables.keys())[:20]}")
except Exception as e:
    print(f"Metadata FAIL: {e}")
