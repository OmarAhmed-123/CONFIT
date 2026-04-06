# CONFIT Frontend Start Script
# Kills any processes on ports 3000/3001/3002, cleans cache, and starts Next.js

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CONFIT Frontend - Clean Start Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Kill processes on frontend ports
$ports = @(3000, 3001, 3002)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $pids) {
            Write-Host "Killing process $pid on port $port..." -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

# Kill any remaining node processes
Write-Host "Stopping any remaining Node processes..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Clean build artifacts
Write-Host "Cleaning build artifacts..." -ForegroundColor Yellow
$frontendPath = "E:\CONFIT\frontend"
Remove-Item -Path "$frontendPath\.next" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$frontendPath\node_modules\.cache" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$frontendPath\tsconfig.tsbuildinfo" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Starting Next.js Development Server" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Set environment variables to prevent hanging
$env:NEXT_TELEMETRY_DISABLED = "1"
$env:NEXT_NO_TURBOPACK = "1"

# Start Next.js
Set-Location $frontendPath
& npm run dev
