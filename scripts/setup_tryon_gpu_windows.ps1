Param(
  [string]$ProjectRoot = "E:\CONFIT"
)

$backend = Join-Path $ProjectRoot "backend"
Set-Location $backend

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Run this next for CUDA verification:"
Write-Host 'python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''NO GPU'')"'

