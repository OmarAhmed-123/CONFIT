@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════════════════════════════════
echo PentAGI Startup Script
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

cd /d "e:\CONFIT\backend"

echo [Step 1] Stopping and removing old containers...
docker stop confit-pentagi confit-pentagi-worker confit-pentagi-pgvector 2>nul
docker rm confit-pentagi confit-pentagi-worker confit-pentagi-pgvector 2>nul
echo Done.

echo.
echo [Step 2] Starting pgvector database...
docker compose up -d pentagi-pgvector
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start pgvector
    pause
    exit /b 1
)

echo Waiting 20 seconds for database...
timeout /t 20 /nobreak >nul

echo.
echo [Step 3] Starting PentAGI server...
docker compose up -d pentagi
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start PentAGI
    pause
    exit /b 1
)

echo Waiting 10 seconds...
timeout /t 10 /nobreak >nul

echo.
echo [Step 4] Starting PentAGI worker...
docker compose up -d pentagi-worker

echo.
echo [Step 5] Container status:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=pentagi"

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo PentAGI URL: https://localhost:8443
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
pause
