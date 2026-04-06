"""
CONFIT Backend - Test Configuration
====================================
Patches heavy DB/engine imports so tests can run without a live database.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Pre-import patching: prevent DB engine creation at module load time
# ---------------------------------------------------------------------------

# Mock infrastructure.database so create_async_engine is never called
_mock_db = MagicMock()
_mock_db.engine = MagicMock()
_mock_db.get_async_session = MagicMock()
_mock_db.AsyncEngine = MagicMock()
sys.modules.setdefault("infrastructure.database", _mock_db)

# Mock database.models so ORM models don't require real tables
_mock_models = MagicMock()
sys.modules.setdefault("database.models", _mock_models)
sys.modules.setdefault("database.donation_models", MagicMock())
sys.modules.setdefault("database.session", MagicMock())

# Mock api.deps so get_db doesn't try to create sessions
_mock_deps = MagicMock()
_mock_deps.get_db = MagicMock()
sys.modules.setdefault("api.deps", _mock_deps)

# Mock services that may need DB
sys.modules.setdefault("services.auth_service", MagicMock())
sys.modules.setdefault("services.donation_service", MagicMock())
