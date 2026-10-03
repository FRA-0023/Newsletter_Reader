# Bootstrap script for local Python Virtual Environment (Zero-Docker mode)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Creating Python virtual environment in .venv..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host "Upgrading pip and installing requirements..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Bootstrap completed successfully!" -ForegroundColor Green
Write-Host "To validate configuration, run:" -ForegroundColor Yellow
Write-Host ".\.venv\Scripts\python.exe -m src.cli validate-config"
