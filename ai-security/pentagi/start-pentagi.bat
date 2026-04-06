@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM PentAGI Startup Script for CONFIT Security
REM ═══════════════════════════════════════════════════════════════════════════════
REM This script starts PentAGI services with proper configuration

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo Starting PentAGI AI Penetration Testing Platform
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0..\..\backend"

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found in backend directory
    echo Please copy .env.example to .env and configure the required variables:
    echo   - DEEPSEEK_API_KEY
    echo   - PENTAGI_API_TOKEN
    echo   - SHODAN_API_KEY (optional)
    echo   - VIRUSTOTAL_API_KEY (optional)
    pause
    exit /b 1
)

echo [INFO] Starting PentAGI services...
echo.

REM Start only PentAGI-related services
docker compose up -d pentagi-pgvector pentagi pentagi-worker

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start PentAGI services
    echo Check Docker logs: docker compose logs pentagi
    pause
    exit /b 1
)

echo.
echo [SUCCESS] PentAGI services started
echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo PentAGI is now running at: https://localhost:8443
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
echo To view logs:     docker compose logs -f pentagi
echo To stop services: docker compose down pentagi pentagi-worker pentagi-pgvector
echo.
pause
