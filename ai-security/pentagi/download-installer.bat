@echo off
echo Downloading PentAGI installer...
powershell -Command "Invoke-WebRequest -Uri 'https://pentagi.com/downloads/windows/amd64/installer-latest.zip' -OutFile 'e:\CONFIT\ai-security\pentagi\installer.zip'"
echo Extracting...
powershell -Command "Expand-Archive -Path 'e:\CONFIT\ai-security\pentagi\installer.zip' -DestinationPath 'e:\CONFIT\ai-security\pentagi' -Force"
echo.
echo Installer downloaded to: e:\CONFIT\ai-security\pentagi
echo Run the installer.exe to configure PentAGI properly.
pause
