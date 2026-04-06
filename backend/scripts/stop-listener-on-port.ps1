# Stops the process listening on the given TCP port (default 8000).
# Usage:  .\scripts\stop-listener-on-port.ps1
#         .\scripts\stop-listener-on-port.ps1 -Port 8001
param(
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host "No listener on port $Port."
    exit 0
}
$pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $pids) {
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $name = if ($p) { $p.ProcessName } else { "?" }
    Write-Host "Stopping PID $procId ($name) on port $Port"
    Stop-Process -Id $procId -Force
}
Write-Host "Done."
