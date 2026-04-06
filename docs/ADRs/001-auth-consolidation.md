# ADR-001: Auth Service Consolidation

## Status
Accepted

## Date
2026-04-18

## Context

The CONFIT backend had two auth service implementations:

1. **Sync version** (`backend/services/auth_service.py`)
   - Uses sync SQLAlchemy `Session`
   - Direct ORM queries
   - `UserProfile` Pydantic model
   - `seed_auth_users()` for startup seeding
   - Used by 45+ routers in `backend/routers/`

2. **Async version** (`backend/application/services/auth_service.py`)
   - Uses async SQLAlchemy `AsyncSession`
   - Clean architecture (domain entities, repositories)
   - `UserDTO` Pydantic model
   - Only referenced by `backend/api/auth.py`
   - **NOT included in `main.py`** - dead code

## Decision

Delete the async auth service and keep the sync version as the canonical auth service.

### Rationale

1. **Dead code**: The async auth router (`backend/api/auth.py`) was never imported in `main.py`
2. **Architectural incompatibility**: The two versions use incompatible DB session types (Session vs AsyncSession)
3. **Production dependency**: 45+ routers depend on the sync version via `utils/auth_deps.py`
4. **Startup seeding**: `seed_auth_users()` is called at app startup and only exists in sync version
5. **No migration path**: Converting to async would require rewriting all routers

## Consequences

### Deleted Files
- `backend/api/auth.py` - Dead router (not in main.py)
- `backend/application/services/auth_service.py` - Unused async service

### Modified Files
- `backend/api/deps.py` - Removed `get_auth_service()` function

### Retained
- `backend/services/auth_service.py` - Canonical sync auth service
- `backend/routers/auth.py` - Canonical auth router
- `backend/utils/auth_deps.py` - Auth dependencies for routers

## Future Considerations

If async authentication is needed in the future:
1. Create an async wrapper around the sync service using `run_in_executor()`
2. Or migrate all routers to async (major undertaking)
3. Keep JWT handling sync (it's CPU-bound, not I/O-bound)
