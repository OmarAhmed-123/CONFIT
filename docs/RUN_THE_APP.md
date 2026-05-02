# CONFIT — How to Run the Application

> **Last updated:** 2026-04-26  
> **Stack:** Next.js 15 (frontend) + FastAPI (backend) + PostgreSQL/SQLite + Redis + Elasticsearch + Celery  
> **Python:** 3.12+  
> **Node.js:** 18+ (LTS)

---

## 1. Prerequisites

### Required

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ (LTS) | Frontend runtime |
| PostgreSQL | 15+ | Primary database (asyncpg) |
| SQLite | 3.40+ | Secondary / test database |
| Redis | 7+ | Caching, sessions, rate-limiting |
| Elasticsearch | 8+ | Search index (optional — graceful fallback) |

### Optional

| Tool | Purpose |
|------|---------|
| Docker + Docker Compose | Run all infra in containers |
| `poetry` or `venv` | Python dependency isolation |

---

## 2. Quick Start (Docker Compose — Recommended)

If you have Docker installed, you can spin up the entire stack with one command:

```bash
# From repo root
docker compose up --build
```

This will start:
- PostgreSQL on `5432`
- Redis on `6379`
- Elasticsearch on `9200`
- Backend Uvicorn on `8001`
- Frontend Next.js dev server on `3000`

---

## 3. Manual Setup (Local Development)

### 3.1 Clone & enter the repo

```bash
git clone https://github.com/OmarAhmed-123/CONFIT.git
cd CONFIT
```

### 3.2 Backend Setup

```bash
# Create virtual environment
cd backend
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# OR (Windows CMD)
venv\Scripts\activate.bat
# OR (macOS / Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
# Edit .env with your DB credentials, JWT secret, payment keys, etc.
```

#### Database migrations

```bash
# Create / upgrade DB schema (Alembic)
alembic upgrade head
```

#### Seed initial data (optional)

```bash
python scripts/seed_data.py
```

#### Run the backend dev server

```bash
# Option A — Uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Option B — FastAPI CLI (if installed)
fastapi dev main.py --port 8001
```

Backend will be available at `http://localhost:8001`  
Auto-generated docs: `http://localhost:8001/docs`

### 3.3 Frontend Setup

```bash
# From repo root
cd frontend

# Install dependencies
npm install

# Set environment variables
copy .env.example .env.local      # Windows
cp .env.example .env.local        # macOS / Linux
```

#### Required environment variables (`.env.local`)

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_PAYMOB_IFRAME_URL=https://accept.paymob.com/api/acceptance/iframes/...
```

> **Note:** In **development**, the frontend uses Next.js rewrite proxy. Any path starting with `/api/*` is forwarded to the backend automatically (see `frontend/next.config.ts`). Paths without `/api/` prefix (e.g., `/sustainability/*`, `/planner/*`, `/analytics/notifications/*`) are sent directly to `NEXT_PUBLIC_API_BASE_URL`. Make sure the backend URL is set correctly.

#### Run the frontend dev server

```bash
# From repo root
npm run dev

# OR directly inside frontend/
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## 4. Environment Variable Reference

### Backend (`.env`)

| Variable | Example | Required |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost/confit` | Yes |
| `DATABASE_URL_SYNC` | `postgresql://user:pass@localhost/confit` | Yes (for Alembic) |
| `REDIS_URL` | `redis://localhost:6379/0` | Yes |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | No (graceful fallback) |
| `JWT_SECRET` | `super-secret-change-me` | Yes |
| `JWT_ALGORITHM` | `HS256` | Yes |
| `JWT_EXPIRATION_MINUTES` | `60` | Yes |
| `ENVIRONMENT` | `development` | Yes (`development` / `staging` / `production`) |
| `PAYMOB_API_KEY` | `...` | Yes (Egypt payments) |
| `PAYMOB_HMAC_SECRET` | `...` | Yes (webhook verification) |
| `PAYMOB_INTEGRATION_ID_CARD` | `...` | Yes |
| `PAYMOB_INTEGRATION_ID_MEEZA` | `...` | Yes |
| `PAYMOB_INTEGRATION_ID_INSTAPAY` | `...` | Yes |
| `PAYMOB_INTEGRATION_ID_VALU` | `...` | Yes |
| `STRIPE_SECRET_KEY` | `sk_test_...` | Yes (Stripe) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Yes |
| `FAWRY_MERCHANT_CODE` | `...` | Yes (Fawry) |
| `FAWRY_SECURITY_KEY` | `...` | Yes |
| `VALU_API_KEY` | `...` | Yes (Valu BNPL) |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` | `...` | No (email fallback to console) |

### Frontend (`.env.local`)

| Variable | Example | Required |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8001` | Yes |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_test_...` | Yes |
| `NEXT_PUBLIC_PAYMOB_IFRAME_URL` | `https://accept.paymob.com/api/acceptance/iframes/...` | Yes (Egypt) |
| `NEXT_PUBLIC_APP_NAME` | `CONFIT` | No |

---

## 5. Running Both Servers (Development)

### Option A — Two terminals

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

### Option B — Root package.json scripts

```bash
# From repo root
npm run dev        # Starts frontend only (uses next.config.ts proxy for /api/*)
```

> ⚠️ The root `package.json` does **not** start the backend automatically. You must run the backend separately or use Docker Compose.

---

## 6. Production Build

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

### Frontend

```bash
cd frontend
npm install
npm run build
npm start
```

---

## 7. Common Issues & Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `404` on `/api/auth/login` | Backend not running | Start backend (`uvicorn main:app --port 8001`) |
| `404` on `/sustainability/products/123` | `NEXT_PUBLIC_API_BASE_URL` missing in `.env.local` | Add it and restart frontend |
| `CORS` errors | Backend `allow_origins` mismatch | Ensure backend allows `http://localhost:3000` |
| Database errors after schema change | Migrations not run | `cd backend && alembic upgrade head` |
| Payment iframe not loading | Missing `NEXT_PUBLIC_PAYMOB_IFRAME_URL` | Add it to `.env.local` |
| `Module not found` in frontend | Dependencies missing | `cd frontend && npm install` |
| `Module not found` in backend | Virtual env not activated | `source venv/bin/activate` or `.\venv\Scripts\Activate.ps1` |

---

## 8. Testing

### Backend (pytest)

```bash
cd backend
pytest -xvs tests/
```

### Frontend (Playwright / unit)

```bash
cd frontend
npx playwright test   # E2E
npm run lint          # ESLint
npm run type-check    # TypeScript
```

---

## 9. Project Structure

```
CONFIT/
├── backend/
│   ├── main.py                 # FastAPI entry point (69 routers)
│   ├── routers/                # Active API routers (mounted in main.py)
│   ├── api/                    # Additional API modules (some legacy)
│   ├── schemas/                # Pydantic models
│   ├── models/                 # SQLAlchemy ORM models
│   ├── services/               # Business logic layer
│   ├── alembic/                # DB migrations
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── lib/api/            # API client, endpoints, helpers
│   │   ├── services/           # Service layer (maps to backend routers)
│   │   ├── hooks/              # TanStack Query hooks
│   │   ├── components/         # React components
│   │   └── pages/ / app/       # Next.js routes
│   ├── next.config.ts          # Next.js config (includes /api/* proxy)
│   └── package.json            # Node dependencies
├── docs/
│   ├── INTEGRATION_AUDIT.md    # Full integration audit
│   └── RUN_THE_APP.md          # This file
└── package.json               # Root workspace scripts
```

---

## 10. Next Steps After First Run

1. Open `http://localhost:3000` → sign up a test user.
2. Open `http://localhost:8001/docs` → verify all endpoints are documented.
3. Run a smoke test: Add product to cart → Checkout → select Paymob/Fawry/Valu → verify flow.
4. Check the integration audit (`docs/INTEGRATION_AUDIT.md`) for any remaining gaps.
