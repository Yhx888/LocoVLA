# Upkie 课程一键启动
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Upkie Motion Control Course" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[X] .venv not found at .venv" -ForegroundColor Red
    Write-Host "    Run: python -m venv .venv"
    Write-Host "    Then: .venv\Scripts\pip install -r requirements.lock"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[+] Server: http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "[+] Close this window to stop" -ForegroundColor Gray
Write-Host ""
Start-Process "http://127.0.0.1:8765"
& $venvPython scripts\run_course_web.py
pause
