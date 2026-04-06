# CONFIT PostgreSQL Database Setup

Production-ready PostgreSQL configuration with Docker, SQLAlchemy, and Alembic migrations.

## Quick Start

### 1. Start PostgreSQL Container

```bash
# From the backend directory
docker-compose -f docker-compose.postgres.yml up -d
```

### 2. Configure Environment

```bash
# Copy the PostgreSQL environment file
cp .env.postgres .env

# Or set environment variables directly
export DATABASE_URL="postgresql://confit:AAIOH2040%%Ff%@localhost:5432/confit"
```

### 3. Run Migrations

```bash
# Initialize database with Alembic
alembic upgrade head
```

### 4. Test Connection

```bash
python test_postgres_connection.py
```

## Files Structure

```
backend/
├── docker-compose.postgres.yml  # PostgreSQL-only Docker setup
├── .env.postgres                # Environment template for PostgreSQL
├── alembic.ini                  # Alembic configuration
├── alembic/
│   ├── env.py                   # Alembic environment
│   ├── script.py.mako           # Migration template
│   └── versions/
│       └── 0001_initial_schema.py
├── database/
│   ├── __init__.py              # Database package exports
│   ├── config.py                # Database URL and settings
│   ├── session.py               # Session management (sync/async)
│   ├── base.py                  # SQLAlchemy Base
│   ├── models.py                # ORM models
│   └── init/
│       └── 01-init.sql          # PostgreSQL initialization
└── test_postgres_connection.py  # Connection test script
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./confit.db` | Database connection URL |
| `POSTGRES_USER` | `confit` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `confit_dev_password_2026!` | PostgreSQL password (development example) |
| `POSTGRES_DB` | `confit` | Database name |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `DB_POOL_SIZE` | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool timeout (seconds) |
| `DB_POOL_RECYCLE` | `3600` | Connection recycle time |

### Connection URL Formats

**Docker (container-to-container):**
```
postgresql://confit:confit_dev_password_2026!@postgres:5432/confit
```

**Local Development (localhost):**
```
postgresql://confit:confit_dev_password_2026!@localhost:5432/confit
```

**Async (SQLAlchemy async):**
```
postgresql+asyncpg://confit:confit_dev_password_2026!@postgres:5432/confit
```

## Docker Commands

```bash
# Start PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# View logs
docker-compose -f docker-compose.postgres.yml logs -f postgres

# Stop PostgreSQL
docker-compose -f docker-compose.postgres.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.postgres.yml down -v

# Start with pgAdmin (optional)
docker-compose -f docker-compose.postgres.yml --profile admin up -d
```

## Alembic Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# View migration history
alembic history

# View current revision
alembic current
```

## Usage in FastAPI

### Sync Session

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db

@app.get("/items/")
def read_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return items
```

### Async Session

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session

@app.get("/items/")
async def read_items(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return items
```

### Context Manager (Background Tasks)

```python
from database import get_db_session

async def background_task():
    async with get_db_session() as db:
        result = await db.execute(select(Item))
        items = result.scalars().all()
        # Auto-commits on exit, rolls back on exception
```

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as templates
2. **Use strong passwords** - Minimum 16 characters with special characters
3. **Limit network exposure** - PostgreSQL port only exposed locally
4. **Use SSL in production** - Configure `sslmode=require` in URL
5. **Rotate credentials** - Change passwords periodically
6. **Use secrets management** - Docker secrets, Kubernetes secrets, or vault
7. **Enable connection pooling** - Prevents connection exhaustion
8. **Monitor connections** - Use pgAdmin or monitoring tools

## Troubleshooting

### Connection Refused

```bash
# Check if container is running
docker ps | grep confit-postgres

# Check container logs
docker logs confit-postgres

# Verify port is not in use
netstat -an | grep 5432
```

### Authentication Failed

```bash
# Verify credentials in .env match docker-compose
# Note: %% in password is URL encoding for %
```

### Database Does Not Exist

```bash
# Connect to PostgreSQL and create database
docker exec -it confit-postgres psql -U confit -c "CREATE DATABASE confit;"
```

### Migration Errors

```bash
# Reset migrations
alembic downgrade base
alembic upgrade head

# Or recreate database
docker-compose -f docker-compose.postgres.yml down -v
docker-compose -f docker-compose.postgres.yml up -d
```

## pgAdmin Access

When started with `--profile admin`:

1. Open http://localhost:5050
2. Login: `admin@confit.local` / `confit_dev_password_2026!`
3. Add server:
   - Host: `postgres`
   - Port: `5432`
   - Username: `confit`
   - Password: `AAIOH2040%%Ff%`
