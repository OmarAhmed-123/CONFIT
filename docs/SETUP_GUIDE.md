# CONFIT Platform Setup Guide

This guide covers setting up the CONFIT platform with the new Next.js frontend and FastAPI backend.

## Architecture Overview

```
CONFIT/
├── backend/           # FastAPI backend (Python)
│   ├── routers/       # API endpoints
│   ├── services/      # Business logic
│   ├── database/      # SQLAlchemy models
│   └── main.py        # Application entry point
│
├── frontend/          # Next.js frontend (TypeScript/React)
│   ├── src/
│   │   ├── app/       # Next.js App Router pages
│   │   ├── components/# React components
│   │   ├── context/   # React contexts
│   │   ├── services/  # API service layer
│   │   ├── lib/       # Utilities
│   │   └── types/     # TypeScript types
│   └── package.json
│
└── src/               # Legacy React/Vite frontend (deprecated)
```

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+ and pip
- **PostgreSQL** (production) or SQLite (development)
- **Redis** (optional, for caching and queues)

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# Edit .env with your configuration
# Required: JWT_SECRET, DATABASE_URL

# Run database migrations
alembic upgrade head

# Start the server
python main.py
# or
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
copy .env.example .env.local

# Edit .env.local with your configuration
# Required: NEXT_PUBLIC_API_BASE_URL, NEXTAUTH_SECRET

# Start development server
npm run dev
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Configuration

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | Yes |
| `JWT_SECRET` | Secret for JWT tokens | Yes |
| `STRIPE_SECRET_KEY` | Stripe API secret key | For payments |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | For webhooks |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | For OAuth |
| `APPLE_CLIENT_ID` | Apple Sign-In client ID | For OAuth |

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | Yes |
| `NEXTAUTH_SECRET` | NextAuth.js secret | Yes |
| `NEXTAUTH_URL` | App URL for OAuth | Yes |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | For payments |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Google OAuth client ID | For OAuth |

## OAuth Setup

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **APIs & Services** → **Credentials**
4. Create **OAuth 2.0 Client ID**
5. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google`
   - `https://yourdomain.com/api/auth/callback/google`
6. Copy Client ID and Client Secret to environment files

### Apple Sign-In

1. Go to [Apple Developer Portal](https://developer.apple.com/)
2. Create a **Services ID** for Sign In with Apple
3. Configure return URLs:
   - `http://localhost:3000/api/auth/callback/apple`
4. Generate and download the private key
5. Create client secret JWT (see Apple documentation)

## Stripe Setup

### 1. Create Stripe Account

1. Sign up at [Stripe](https://dashboard.stripe.com/)
2. Get API keys from **Developers** → **API Keys**

### 2. Configure Webhooks

1. Go to **Developers** → **Webhooks**
2. Add endpoint: `https://your-api-domain.com/api/payments/webhooks/stripe`
3. Select events to listen:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
4. Copy the signing secret to `STRIPE_WEBHOOK_SECRET`

### 3. Test Mode

Use test mode keys for development:
- Publishable key: `pk_test_...`
- Secret key: `sk_test_...`

Use Stripe CLI for local webhook testing:
```bash
stripe listen --forward-to localhost:8000/api/payments/webhooks/stripe
```

## CONFIT CARE Setup

CONFIT CARE is the donation system that allows donors to create campaigns and help beneficiaries shop for clothing.

### Database Models

The following models are automatically created:
- `donation_campaigns` - Campaign management
- `campaign_beneficiaries` - Beneficiary management
- `care_vouchers` - Voucher generation and tracking
- `voucher_transactions` - Transaction logging
- `donation_transactions` - Donation tracking

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/care/donor/dashboard` | Donor dashboard summary |
| `GET /api/care/donor/campaigns` | List donor's campaigns |
| `POST /api/care/campaigns` | Create new campaign |
| `GET /api/care/campaigns/{id}` | Get campaign details |
| `POST /api/care/campaigns/{id}/beneficiaries` | Add beneficiary |
| `POST /api/care/campaigns/{id}/vouchers` | Create vouchers |
| `POST /api/care/vouchers/validate` | Validate voucher code |
| `POST /api/care/vouchers/redeem` | Redeem voucher |

## Docker Deployment

### Development

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run backend
cd backend && python main.py

# Run frontend
cd frontend && npm run dev
```

### Production

```bash
# Build and start all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

#### "Cannot find module 'next-auth/react'"

Run `npm install` in the frontend directory:
```bash
cd frontend && npm install
```

#### "CORS error in browser"

Ensure `FRONTEND_URL` is set in backend `.env` and matches your frontend URL exactly.

#### "JWT secret not configured"

Generate a secure secret:
```bash
# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Linux/macOS
openssl rand -base64 32
```

#### "Database connection failed"

1. Verify `DATABASE_URL` format:
   - SQLite: `sqlite:///./confit.db`
   - PostgreSQL: `postgresql://user:password@host:port/database`
2. Ensure PostgreSQL is running
3. Run migrations: `alembic upgrade head`

#### "Stripe webhook signature verification failed"

1. Verify `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard
2. Ensure you're using the correct webhook secret (not API key)
3. For local testing, use Stripe CLI to forward webhooks

### Getting Help

1. Check the [API Documentation](http://localhost:8000/docs)
2. Review logs in terminal output
3. Check browser console for frontend errors
4. Open an issue on GitHub

## Next Steps

1. Configure OAuth providers for social login
2. Set up Stripe for payments
3. Create your first CONFIT CARE campaign
4. Customize the design system in `frontend/src/styles/globals.css`
