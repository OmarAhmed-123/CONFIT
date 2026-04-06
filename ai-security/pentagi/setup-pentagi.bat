@echo off
echo ============================================================
echo PentAGI Official Setup
echo ============================================================
echo.

cd /d e:\CONFIT\ai-security\pentagi

echo [1] Downloading PentAGI installer...
powershell -Command "Invoke-WebRequest -Uri 'https://pentagi.com/downloads/windows/amd64/installer-latest.zip' -OutFile 'installer.zip' -UseBasicParsing"

echo [2] Extracting...
powershell -Command "Expand-Archive -Path 'installer.zip' -DestinationPath '.' -Force"

echo [3] Running installer...
echo Please run installer.exe manually to configure PentAGI properly.
echo.
echo The installer will:
echo   - Configure LLM providers
echo   - Set up SSL certificates
echo   - Start PentAGI services
echo.
start installer.exe

echo.
pause
