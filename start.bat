@echo off
cls
echo ============================================
echo   Upkie Course - Starting...
echo ============================================
echo.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [X] .venv not found at: %CD%\.venv
    echo.
    echo Run these commands first:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b
)

if not exist "dashboard\web\dist\index.html" (
    echo [!] Building frontend...
    if not exist "dashboard\web\node_modules" (
        cd dashboard\web
        call npm install
        cd ..\..
    )
    cd dashboard\web
    call npm run build
    cd ..\..
)

echo [+] Server: http://127.0.0.1:8765
echo [+] Close this window to stop
echo.
".venv\Scripts\python.exe" scripts\run_course_web.py

pause
