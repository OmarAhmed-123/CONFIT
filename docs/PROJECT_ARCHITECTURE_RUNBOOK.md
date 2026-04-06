# CONFIT Project Architecture and Runbook

This document defines the cleaned structure for the project:

- Backend code lives under `backend`.
- Frontend code (Next.js) lives under `frontend`.
- Vite-based frontend flow is removed from the active run path.

## 1) High-Level Architecture

### Backend (`backend`)

- Main API app: `backend/main.py`
- Routers: `backend/routers`
- Database models and migrations: `backend/database`, `backend/migrations`
- Services/business logic: `backend/services`
- Environment templates: `backend/.env.oauth.example` and related files

Runtime target:

- Local API server: `http://127.0.0.1:8000`

### Frontend (`frontend`) - Next.js

- Next App Router pages: `frontend/src/app`
- Shared UI and feature components: `frontend/src/components`
- Reusable logic/hooks/stores: `frontend/src/hooks`, `frontend/src/stores`, `frontend/src/lib`
- Static public assets: `frontend/public`
- Next config: `frontend/next.config.ts`

Runtime target:

- Local web app: `http://localhost:3000`

## 2) Cleanup Applied

The following Vite-era files were removed from active project root usage:

- `vitest.config.ts`
- `eslint.config.js` (legacy root React config)
- `run_build.bat` (hardcoded Vite build)
- `build_check.cjs` (hardcoded Vite build check)
- `frontend/src/vite-env.d.ts`
- `frontend/scripts/migrate-react-router.mjs` (one-time migration helper)

Static assets were centralized to Next public directory:

- Added `frontend/public/placeholder.svg`
- Added `frontend/public/robots.txt`
- Removed duplicate root/public copies

Root npm scripts now proxy to `frontend` only to prevent accidental Vite workflow usage.

## 3) Prerequisites

- Node.js 20+ and npm
- Python 3.12 (recommended) for backend
- (Recommended) virtual environment for backend dependencies

## 4) Environment Setup

### Frontend env

From `frontend`, copy:

```powershell
Copy-Item .env.example .env.local -Force
```

Review at minimum:

- `NEXT_PUBLIC_API_BASE_URL` (usually `http://127.0.0.1:8000`)
- Any auth/stripe/supabase public keys used by your flows

### Backend env

From `backend`, create `.env` from your available example file(s), then fill required keys.

If your deployment currently relies on OAuth setup, start from:

- `backend/.env.oauth.example`

## 5) Install and Run

## Frontend (Next.js)

```powershell
cd E:\CONFIT\frontend
npm install
npm run dev
```

Production build:

```powershell
npm run build
npm run start
```

## Backend (FastAPI)

```powershell
cd E:\CONFIT\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

If your default `python` points to 3.14 and pip fails, always run backend with:

```powershell
E:\CONFIT\backend\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

## 6) Recommended Daily Workflow

Use two terminals:

- Terminal 1: backend (`uvicorn`)
- Terminal 2: frontend (`npm run dev` inside `frontend`)

Then open:

- Frontend: `http://localhost:3000`
- Backend docs/health endpoints as configured in `backend/main.py`

## 7) Notes About Remaining Legacy Areas

This repository may still contain old or experimental folders outside `frontend`/`backend` (for example old app/service workspaces). They are not part of the active clean run path defined here.

If you want a strict phase-2 migration, do it as a separate pass:

1. Identify each legacy folder owner/dependency.
2. Move or archive only after import/runtime verification.
3. Run regression tests after each folder migration.

This keeps production behavior stable while finishing structural cleanup safely.
