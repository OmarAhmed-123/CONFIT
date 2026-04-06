@echo off
REM Use from CMD.exe before npm (PowerShell uses $env:... instead).
REM Usage:  call scripts\use-npm-cache-on-repo-drive.cmd

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

set "TEMP=%REPO_ROOT%\.tmp"
set "TMP=%REPO_ROOT%\.tmp"
set "npm_config_cache=%REPO_ROOT%\.npm-cache"

if not exist "%TEMP%" mkdir "%TEMP%" 2>nul
if not exist "%npm_config_cache%" mkdir "%npm_config_cache%" 2>nul

echo TEMP=%TEMP%
echo npm_config_cache=%npm_config_cache%
