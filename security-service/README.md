# Security Service (CONFIT)

This repository implements the **internal security orchestration layer** under:

- `backend/services/security/` (PentAGI client + discovery + persistence)
- `backend/routers/security.py` (FastAPI routes under `/api/security/*`)
- `src/pages/SecurityDashboard.tsx` (React UI at `/security`)

The `security-service/` folder is intentionally a **documentation anchor** to avoid duplicating code in a second service tree.
