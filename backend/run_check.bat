@echo off
cd /d e:\CONFIT\backend
python check_db2.py
type db_status.txt
pause
