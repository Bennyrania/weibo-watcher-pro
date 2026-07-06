@echo off
title Weibo Watcher - Stop

echo Stopping Weibo Watcher...
echo.

:: Find process on port 5000 and kill it
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo Found PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    echo Stopped.
)

:: Also kill any orphan python.exe in our project folder
for /f %%a in ('wmic process where "name='python.exe' and commandline like '%%weibo-watcher%%'" get processid 2^>nul ^| findstr "[0-9]"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ============================================
echo    Service stopped.
echo    You can safely restart with start.bat
echo ============================================
echo.
pause
