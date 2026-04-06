# PentAGI — AI Penetration Testing Platform

## Overview

PentAGI is an AI-powered penetration testing platform integrated with CONFIT Security. It uses DeepSeek AI to perform automated security scans against your application.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONFIT Security Stack                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   PentAGI   │───▶│  pgvector   │    │   External APIs     │  │
│  │   Server    │    │  PostgreSQL │    │  - DeepSeek AI      │  │
│  │  (port 8443)│    │  (internal) │    │  - Shodan           │  │
│  └──────┬──────┘    └─────────────┘    │  - VirusTotal       │  │
│         │                              └─────────────────────┘  │
│         ▼                                                        │
│  ┌─────────────┐                                               │
│  │   PentAGI   │                                               │
│  │   Worker    │                                               │
│  └─────────────┘                                               │
│                                                                 │
│  ┌─────────────┐                                               │
│  │   CONFIT    │◀────── GraphQL/REST API ──────┐               │
│  │    API      │                               │               │
│  └─────────────┘                               │               │
│                                                │               │
└────────────────────────────────────────────────│───────────────┘
                                                 │
                    Docker Network: confit-network
```

## Quick Start

### 1. Configure Environment

Copy the security environment template and configure API keys:

```bash
# The .env file should contain:
DEEPSEEK_API_KEY=your-deepseek-api-key
PENTAGI_API_TOKEN=your-secure-token
PENTAGI_POSTGRES_USER=pentagi
PENTAGI_POSTGRES_PASSWORD=secure_password
PENTAGI_POSTGRES_DB=pentagidb
```

### 2. Start Services

**Windows:**
```batch
cd ai-security\pentagi
start-pentagi.bat
```

**Linux/Mac:**
```bash
cd ai-security/pentagi
chmod +x start-pentagi.sh
./start-pentagi.sh
```

**Or using Docker Compose directly:**
```bash
cd backend
docker compose up -d pentagi-pgvector pentagi pentagi-worker
```

### 3. Access PentAGI UI

Open https://localhost:8443 in your browser.

**Note:** The first startup may take 60-90 seconds for the health check to pass.

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, tokens, database) |
| `deepseek.provider.yml` | DeepSeek AI provider configuration |
| `example.custom.provider.yml` | Template for custom OpenAI-compatible providers |
| `example.ollama.provider.yml` | Template for local Ollama LLM |

## API Endpoints

PentAGI exposes these endpoints for CONFIT integration:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/graphql` | POST | GraphQL API for scan management |

## Scan Types

| Type | Description |
|------|-------------|
| `api` | API security testing (OWASP API Top 10) |
| `web` | Web application security testing (XSS, CSRF, etc.) |
| `auth` | Authentication/authorization testing |
| `full` | Comprehensive penetration test |

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API key |
| `PENTAGI_API_TOKEN` | Secure token for API authentication |

### Optional (Security Intelligence)

| Variable | Description |
|----------|-------------|
| `SHODAN_API_KEY` | Shodan API key for network intelligence |
| `VIRUSTOTAL_API_KEY` | VirusTotal API key for malware analysis |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `PENTAGI_POSTGRES_USER` | `pentagi` | PostgreSQL username |
| `PENTAGI_POSTGRES_PASSWORD` | `pentagi_secure_2026` | PostgreSQL password |
| `PENTAGI_POSTGRES_DB` | `pentagidb` | Database name |

## Troubleshooting

### PentAGI won't start

1. Check logs: `docker compose logs pentagi`
2. Verify pgvector is healthy: `docker compose logs pentagi-pgvector`
3. Ensure DEEPSEEK_API_KEY is set

### Health check fails

```bash
# Manual health check
docker exec confit-pentagi wget --no-check-certificate -qO- https://localhost:8443/api/v1/health
```

### Database connection issues

```bash
# Check database connectivity
docker exec confit-pentagi-pgvector pg_isready -U pentagi -d pentagidb
```

### Reset everything

```bash
docker compose down -v
docker compose up -d pentagi-pgvector pentagi pentagi-worker
```

## Security Notes

1. **API Tokens**: Generate secure tokens for production use
2. **Network Isolation**: pgvector runs on an internal network
3. **Docker Socket**: PentAGI requires Docker socket access for spawning test containers
4. **SSL Verification**: Disabled by default for development; enable in production

## Integration with CONFIT

The CONFIT API router at `/api/security/*` provides:

- `POST /api/security/scan` — Start a scan
- `GET /api/security/status/{scan_id}` — Check scan status
- `GET /api/security/report/{scan_id}` — Get scan report
- `GET /api/security/scans` — List all scans
- `GET /api/security/targets/discover` — Auto-discover targets
- `GET /api/security/health` — PentAGI health check
