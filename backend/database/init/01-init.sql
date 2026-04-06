-- CONFIT Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Ensure the database exists (already created by POSTGRES_DB env var)
-- This is for reference and additional setup

-- Create extensions (if needed)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Create schemas for organization
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON SCHEMA app TO confit;
GRANT ALL PRIVILEGES ON SCHEMA audit TO confit;
GRANT ALL PRIVILEGES ON DATABASE confit TO confit;

-- Set default schema for the user
ALTER USER confit SET search_path TO app, public;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'CONFIT database initialized successfully';
END
$$;
