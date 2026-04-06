<#
.SYNOPSIS
    Smoke-test CONFIT payment-related HTTP endpoints (FastAPI legacy backend).

.DESCRIPTION
    Calls:
      GET  /api/payments/config
      POST /api/payments/bnpl/plan
      POST /api/payments/intent (expects 404/400 without a real order — optional check)

    Requires the Python backend running (default: http://127.0.0.1:8001 per vite proxy).

.PARAMETER BaseUrl
    Root URL of the FastAPI app (no trailing slash).

.EXAMPLE
    .\scripts\test-payment-smoke.ps1
    .\scripts\test-payment-smoke.ps1 -BaseUrl "http://127.0.0.1:8000"
#>

param(
    [string] $BaseUrl = "http://127.0.0.1:8001"
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

function Test-Endpoint {
    param([string] $Name, [scriptblock] $Call)
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    try {
        $result = & $Call
        Write-Host ($result | ConvertTo-Json -Depth 6 -Compress)
        return $true
    } catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
        return $false
    }
}

Write-Host "CONFIT payment smoke test against $BaseUrl" -ForegroundColor Green

$ok = $true

$ok = (Test-Endpoint "GET /api/payments/config" {
    Invoke-RestMethod -Uri "$BaseUrl/api/payments/config" -Method Get -TimeoutSec 15
}) -and $ok

$ok = (Test-Endpoint "POST /api/payments/bnpl/plan" {
    $body = @{
        total_amount = 99.99
        installments = 4
        annual_interest_rate = 0
        currency = "USD"
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "$BaseUrl/api/payments/bnpl/plan" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
}) -and $ok

# Intent without order should fail with 4xx — proves route is mounted
Write-Host "`n=== POST /api/payments/intent (expect error without order) ===" -ForegroundColor Cyan
try {
    $body = '{"order_id":"00000000-0000-0000-0000-000000000000"}'
    Invoke-WebRequest -Uri "$BaseUrl/api/payments/intent" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "Unexpected: server returned success for fake order id" -ForegroundColor Red
    $ok = $false
} catch {
    $r = $_.Exception.Response
    if ($r -and [int]$r.StatusCode -ge 400) {
        Write-Host "Expected failure: HTTP $([int]$r.StatusCode)" -ForegroundColor Yellow
    } else {
        Write-Host "Expected failure: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if ($ok) {
    Write-Host "`nSmoke test finished: OK (config + BNPL; intent returns error without real order)." -ForegroundColor Green
    exit 0
}

Write-Host "`nSmoke test finished: some checks failed. Is the backend running? e.g.:" -ForegroundColor Yellow
Write-Host "  cd E:\CONFIT\backend; .\.venv\Scripts\Activate.ps1; `$env:PORT=8001; python -m uvicorn main:app --host 127.0.0.1 --port 8001"
exit 1
