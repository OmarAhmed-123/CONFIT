@echo off
cd /d %~dp0..
python migrations\run_migration.py
pause
