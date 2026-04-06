@echo off
echo ═══════════════════════════════════════════════════════════════════════════════
echo PentAGI Diagnostic and Startup
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

cd /d "e:\CONFIT\backend"

echo [1] Checking Docker...
docker version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running or not installed
    pause
    exit /b 1
)
echo [OK] Docker is running

echo.
echo [2] Checking PentAGI image...
docker images vxcontrol/pentagi:latest --format "found" 2>nul | findstr "found" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Pulling PentAGI image...
    docker pull vxcontrol/pentagi:latest
)
echo [OK] Image ready

echo.
echo [3] Removing old containers...
docker rm -f confit-pentagi confit-pentagi-worker confit-pentagi-pgvector 2>nul
echo [OK] Old containers removed

echo.
echo [4] Starting fresh PentAGI services...
docker compose up -d pentagi-pgvector

echo [INFO] Waiting for database to be ready (30 seconds)...
timeout /t 30 /nobreak >nul

echo [INFO] Starting PentAGI server...
docker compose up -d pentagi

echo [INFO] Waiting for PentAGI to start (60 seconds)...
timeout /t 60 /nobreak >nul

echo [INFO] Starting PentAGI worker...
docker compose up -d pentagi-worker

echo.
echo [5] Checking container status...
docker ps -a --filter "name=pentagi" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo PentAGI should be running at: https://localhost:8443
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
echo To view logs: docker logs confit-pentagi
echo.
pause
