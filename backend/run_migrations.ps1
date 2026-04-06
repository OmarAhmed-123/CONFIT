# Run database migrations without requiring `alembic` on PATH.
# Usage (from backend folder): .\run_migrations.ps1
$ErrorActionPreference = 'Stop'
$BackendRoot = $PSScriptRoot
Set-Location $BackendRoot

function Resolve-Python {
    $candidates = @(
        (Join-Path $BackendRoot '.venv\Scripts\python.exe'),
        (Join-Path $BackendRoot 'venv\Scripts\python.exe')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return 'python'
}

$py = Resolve-Python
Write-Host "Using: $py" -ForegroundColor Cyan
& $py -m pip show alembic *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Alembic not installed. Run: pip install -r requirements.txt (preferably inside .venv)" -ForegroundColor Red
    exit 1
}
& $py -m alembic upgrade head
exit $LASTEXITCODE
