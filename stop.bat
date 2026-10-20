@echo off
setlocal enabledelayedexpansion
title Weibo Watcher - Stop

echo Stopping Weibo Watcher...
echo.

set "PORT=5000"
set "FOUND="

:: -- 1. Anything listening on the port (this covers python / pythonw alike)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo [INFO] Found listener on port %PORT%, PID %%a
    taskkill /F /PID %%a >nul 2>&1
    set "FOUND=1"
)

:: -- 2. Orphan python processes whose command line points at this folder
::    (wmic is removed on recent Windows 11 builds -- use CIM via PowerShell)
for /f %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*app.main*' } ^| Select-Object -ExpandProperty ProcessId" 2^>nul') do (
    echo [INFO] Stopping python process PID %%a
    taskkill /F /PID %%a >nul 2>&1
    set "FOUND=1"
)

echo.
if defined FOUND (
    echo ============================================
    echo    Service stopped.
    echo    You can safely restart with start.bat
    echo ============================================
) else (
    echo ============================================
    echo    Nothing was running on port %PORT%.
    echo ============================================
)
echo.
timeout /t 5 /nobreak >nul
