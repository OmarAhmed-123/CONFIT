@echo off
cd /d E:\CONFIT\backend
echo Current directory: %CD%
python -m pytest tests\test_security_hardening.py -v --tb=short 2>&1
echo Exit code: %ERRORLEVEL%
pause
