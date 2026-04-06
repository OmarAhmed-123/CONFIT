<#
.SYNOPSIS
    Reinstall npm dependencies for CONFIT after ENOSPC, kill EPERM corruption, or broken hoists.

.DESCRIPTION
    - Sets TEMP/TMP and npm_config_cache under the repo (avoids full system drive during extract).
    - Uses a SINGLE `npm install` at the workspace root so hoisted packages (next, tsx, react) resolve
      the same way production/CI does. Per-package installs can leave apps/web or services/api with
      empty local node_modules while deps live only at root — that is valid for npm workspaces.
    - Optional -Clean removes node_modules under root, apps/web, services/api, and packages/* before install.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\repair-node-modules.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\repair-node-modules.ps1 -Clean

.EXAMPLE
    # If folders stay locked, stop all Node processes first (closes dev servers everywhere):
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\repair-node-modules.ps1 -Clean -StopNode
#>

param(
    [switch] $Clean,
    # Stops every node.exe on this machine so locked node_modules can be removed. Use only if retries/rename fail.
    [switch] $StopNode
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $root)) { throw "Cannot find repo root." }

$tmp = Join-Path $root ".tmp"
$npmCache = Join-Path $root ".npm-cache"
New-Item -ItemType Directory -Path $tmp, $npmCache -Force | Out-Null

$env:TEMP = $tmp
$env:TMP = $tmp
$env:npm_config_cache = $npmCache

Write-Host "TEMP=$tmp"
Write-Host "npm cache=$npmCache"
Set-Location -LiteralPath $root

function Remove-NodeModulesTree {
    param([string] $LiteralPath)
    if (-not (Test-Path -LiteralPath $LiteralPath)) { return }

    Write-Host "Removing $LiteralPath" -ForegroundColor Yellow
    $maxAttempts = 8
    for ($a = 0; $a -lt $maxAttempts; $a++) {
        try {
            Remove-Item -LiteralPath $LiteralPath -Recurse -Force -ErrorAction Stop
            return
        } catch {
            if ($a -lt $maxAttempts - 1) {
                Write-Host "  (locked) retry $($a + 2)/$maxAttempts in 2s..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds 2
            }
        }
    }

    $parent = Split-Path -LiteralPath $LiteralPath -Parent
    $leaf = Split-Path -LiteralPath $LiteralPath -Leaf
    $stamp = [Guid]::NewGuid().ToString("n").Substring(0, 8)
    $newName = "${leaf}.__pending_delete__.$stamp"
    $staged = Join-Path $parent $newName
    try {
        Rename-Item -LiteralPath $LiteralPath -NewName $newName -ErrorAction Stop
        Write-Warning "Could not delete locked folder; renamed for fresh install. Remove manually later when idle: $staged"
    } catch {
        throw @"
Cannot remove or rename: $LiteralPath
- Close every terminal running: npm run dev, Next.js, services/api, Playwright, etc.
- Temporarily pause real-time antivirus scan on this repo folder, then re-run.
- Or run this script with -StopNode (stops ALL node.exe on this PC).
"@
    }
}

if ($Clean) {
    if ($StopNode) {
        Write-Host "`n=== -StopNode: stopping all node.exe processes ===" -ForegroundColor Yellow
        Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  Stop PID $($_.Id)" -ForegroundColor DarkYellow
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "`n=== Clean: removing workspace node_modules trees ===" -ForegroundColor Cyan
    Remove-NodeModulesTree -LiteralPath (Join-Path $root "node_modules")
    Remove-NodeModulesTree -LiteralPath (Join-Path $root "apps\web\node_modules")
    Remove-NodeModulesTree -LiteralPath (Join-Path $root "services\api\node_modules")
    $packages = Join-Path $root "packages"
    if (Test-Path -LiteralPath $packages) {
        Get-ChildItem -LiteralPath $packages -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-NodeModulesTree -LiteralPath (Join-Path $_.FullName "node_modules")
        }
    }
}

Write-Host "`n=== npm install (workspace root) ===" -ForegroundColor Cyan
& npm install
if ($LASTEXITCODE -ne 0) { throw "npm install failed at repo root." }

Write-Host "`n=== build @confit/contracts (TypeScript -> dist/) ===" -ForegroundColor Cyan
Push-Location -LiteralPath $root
try {
    & npm run build:contracts
    if ($LASTEXITCODE -ne 0) { throw "build:contracts failed." }
} finally {
    Pop-Location
}

$contractsIndex = Join-Path $root "packages\contracts\dist\index.js"
if (-not (Test-Path -LiteralPath $contractsIndex)) {
    throw "Expected $contractsIndex after build:contracts."
}

Write-Host "`nSanity checks:" -ForegroundColor Cyan
$nextBin = Join-Path $root "node_modules\next\dist\bin\next"
$tsxCli = Join-Path $root "node_modules\tsx\dist\cli.mjs"
if (-not (Test-Path -LiteralPath $nextBin)) {
    Write-Warning "next CLI not found at $nextBin — if web dev fails, run again with -Clean."
} else { Write-Host "  OK next" -ForegroundColor Green }
if (-not (Test-Path -LiteralPath $tsxCli)) {
    Write-Warning "tsx CLI not found at $tsxCli — if API dev fails, run again with -Clean."
} else { Write-Host "  OK tsx" -ForegroundColor Green }
Write-Host "  OK @confit/contracts dist" -ForegroundColor Green

Write-Host "`nDone. Start: npm run dev:api && npm run dev:web (and Vite: npm run dev)." -ForegroundColor Green
Write-Host "If Vite fails with @swc native binding: npm run fix:swc" -ForegroundColor DarkGray
