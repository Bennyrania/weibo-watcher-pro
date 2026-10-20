@echo off
setlocal enabledelayedexpansion
title Weibo Watcher

echo ============================================
echo    Weibo Watcher - Starting...
echo ============================================
echo.

:: -- 0. Lock working directory (so shortcuts / other cwd still find the app package)
set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PORT=5000"

:: Timestamp via PowerShell (Chinese Windows %DATE% format breaks substring tricks)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set "TS=%%i"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
set "LF=%ROOT%logs\start_%TS%.log"

:: -- 1. Check virtual environment
set "PYTHON_CMD="
if exist "%ROOT%.venv\Scripts\pythonw.exe" set "PYTHON_CMD=%ROOT%.venv\Scripts\pythonw.exe"
if not defined PYTHON_CMD if exist "%ROOT%.venv\Scripts\python.exe" set "PYTHON_CMD=%ROOT%.venv\Scripts\python.exe"
if not defined PYTHON_CMD (
    echo [ERROR] Virtual environment not found.
    echo         Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: -- 2. Check config
if not exist "%ROOT%data\config.yaml" (
    echo [WARN] data\config.yaml not found.
    echo        Dashboard will open in "not configured" state.
    echo        Fill in uid + cookie there, then restart the service.
    echo.
)

:: -- 3. Free the port if an old instance is still holding it
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo [INFO] Port %PORT% busy, stopping old instance PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

:: -- 4. Launch in background (pythonw has no console, keeps running after this window closes)
echo Starting service on port %PORT% ...
start "" /b "%PYTHON_CMD%" -m app.main

:: -- 5. Health check: wait up to 20s for the port to actually listen
set "OK="
for /l %%i in (1,1,20) do (
    if not defined OK (
        ping -n 2 127.0.0.1 >nul
        for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do set "OK=%%p"
    )
)

if defined OK (
    echo.
    echo ============================================
    echo    Service started!   PID !OK!
    echo    http://127.0.0.1:%PORT%
    echo.
    echo    To stop: double-click stop.bat
    echo ============================================
    start http://127.0.0.1:%PORT%
    timeout /t 3 /nobreak >nul
    exit /b 0
)

:: -- 6. Startup failed: print something actionable
echo.
echo ============================================
echo    [ERROR] Service did NOT start within 20s.
echo.
echo    Log: %ROOT%logs\server.log
echo.
echo    Common causes:
echo      - dependencies missing       --^> run install.bat
echo      - port %PORT% held by another app --^> run stop.bat
echo      - broken data\config.yaml    --^> check the Cookie line format
echo ============================================
echo.
if exist "%ROOT%logs\server.log" powershell -NoProfile -Command "Get-Content -Tail 15 -Encoding UTF8 '%ROOT%logs\server.log'" 2>nul
echo.
pause
exit /b 1
