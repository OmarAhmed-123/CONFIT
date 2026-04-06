@echo off
echo ============================================================
echo PentAGI Standalone Setup
echo ============================================================
echo.

cd /d e:\CONFIT\pentagi-standalone

echo [1] Stopping old containers...
docker stop pentagi-server pentagi-worker pentagi-pgvector 2>nul
docker rm pentagi-server pentagi-worker pentagi-pgvector 2>nul

echo [2] Starting PentAGI...
docker compose up -d

echo [3] Waiting 30 seconds for startup...
timeout /t 30 /nobreak >nul

echo [4] Container status:
docker ps --filter "name=pentagi"

echo.
echo [5] PentAGI logs:
docker logs pentagi-server --tail 20

echo.
echo [6] Testing connection...
curl -k https://localhost:8443/api/v1/health 2>&1 || echo Connection test done

echo.
echo ============================================================
echo PentAGI URL: https://localhost:8443
echo.
echo IMPORTANT: When you open in browser, you will see SSL warning.
echo Click "Advanced" then "Proceed to localhost (unsafe)"
echo ============================================================
pause
