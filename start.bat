@echo off
title Weibo Watcher

echo ============================================
echo    Weibo Watcher - Starting...
echo ============================================

set "ROOT=%~dp0"
set "LF=%ROOT%logs\start_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log"
set "LF=%LF: =0%"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

:: Check virtual environment
if not exist "%ROOT%.venv\Scripts\pythonw.exe" (
    if not exist "%ROOT%.venv\Scripts\python.exe" (
        echo [ERROR] Virtual environment not found.
        echo Please run install.bat first.
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=%ROOT%.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=%ROOT%.venv\Scripts\pythonw.exe"
)

:: Kill any existing instance first
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Launch service in background
echo Starting service...
echo.
%PYTHON_CMD% -m app.main > "%ROOT%logs\server_output.log" 2>&1

:: Wait a moment, then open browser
ping -n 3 127.0.0.1 >nul
start http://127.0.0.1:5000

echo ============================================
echo    Service started!
echo    Open browser to: http://127.0.0.1:5000
echo.
echo    To stop: double-click stop.bat
echo ============================================
echo.

:: Close this window automatically after 3 seconds
timeout /t 3 /nobreak >nul
