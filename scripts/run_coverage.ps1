# Coverage gate 80% para SteelConnectionJm.
param([switch]$Open, [switch]$IncludeSlow)

$ErrorActionPreference = "Stop"

if ($IncludeSlow) {
    $markFilter = ""
} else {
    $markFilter = "not slow and not fastsap and not dxf"
}

if ($markFilter -eq "") {
    python -m pytest --cov --cov-report=term-missing --cov-report=html --cov-report=xml -q
} else {
    python -m pytest --cov --cov-report=term-missing --cov-report=html --cov-report=xml -q -m "$markFilter"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Coverage gate (80%) o tests fallaron" -ForegroundColor Red
    exit 1
}
Write-Host "Coverage OK (>=80%)" -ForegroundColor Green
if ($Open) { Start-Process "htmlcov/index.html" }
