# Changelog

All notable changes to the CONFIT project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Phase 1 - Cleanup (2026-04-18)

#### Deleted
- `backend/routers/profile_fixed.py` - Duplicate of `profile.py` with no references
- `backend/api/auth.py` - Dead code (not included in `main.py`)
- `backend/application/services/auth_service.py` - Unused async auth service

#### Modified
- `backend/api/deps.py` - Removed unused `get_auth_service()` function

#### Added
- `docs/ADRs/001-auth-consolidation.md` - Architecture Decision Record documenting auth consolidation

#### Summary
- Removed 2 duplicate files and 1 dead auth implementation
- Verified `backend/services/auth_service.py` as canonical auth service (sync, used by 45+ routers)
- Verified `backend/routers/auth.py` as canonical auth router (included in `main.py`)
- All imports verified working after cleanup
