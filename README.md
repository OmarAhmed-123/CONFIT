# CONFIT

CONFIT is split into:
- `frontend` (Next.js App Router)
- `backend` (FastAPI)

## Core Documentation

- Architecture + runbook: `docs/PROJECT_ARCHITECTURE_RUNBOOK.md`
- Roles, permissions, test users, E2E guide: `docs/ACCESS_CONTROL_AND_E2E.md`

## Quick Start

Frontend:
```powershell
cd E:\CONFIT\frontend
npm install
npm run dev
```

Backend:
```powershell
cd E:\CONFIT\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

If your default Python is not 3.12, run backend explicitly with:
```powershell
E:\CONFIT\backend\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

## Local E2E Audit

Run the API feature audit:
```powershell
cd E:\CONFIT\backend
E:\CONFIT\backend\.venv\Scripts\python.exe .\scripts\e2e_feature_audit.py
```

Expected output:
- `TOTAL=... PASS=... FAIL=0`
- Report file: `backend/e2e_feature_audit_report.json`
