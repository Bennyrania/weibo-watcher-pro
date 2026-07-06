@echo off
title Weibo Watcher Install

echo ============================================
echo    Weibo Watcher - Install
echo ============================================
echo.

set "ROOT=%~dp0"
for /f %%i in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set TS=%%i
set "LF=%ROOT%logs\install_%TS%.log"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

echo Log: %LF%
echo ============================================ >> "%LF%" 2>&1
echo Install started %DATE% %TIME% >> "%LF%" 2>&1
echo ============================================ >> "%LF%" 2>&1

:: Step 1: Check Python
echo [1/4] Checking Python...
echo [1/4] Checking Python... >> "%LF%" 2>&1

set "PYTHON_CMD=python"
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
) else (
    python --version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Python not found!
        echo.
        echo Please install Python 3.9 or newer from:
        echo   https://www.python.org/downloads/
        echo.
        echo IMPORTANT: check "Add Python to PATH" during install.
        echo.
        echo Then run install.bat again.
        echo.
        echo [ERROR] Python not found >> "%LF%" 2>&1
        pause
        exit /b 1
    )
)

%PYTHON_CMD% --version >> "%LF%" 2>&1
%PYTHON_CMD% --version
echo Python OK

:: Step 2: Clean old venv + create new one
echo.
echo [2/4] Creating virtual environment...
echo [2/4] Creating virtual environment... >> "%LF%" 2>&1

if exist "%ROOT%.venv\Scripts\python.exe" (
    echo Removing old virtual environment...
    rmdir /s /q "%ROOT%.venv" >> "%LF%" 2>&1
    echo Old environment removed
)

%PYTHON_CMD% -m venv "%ROOT%.venv" >> "%LF%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create virtual environment!
    echo Check log: %LF%
    pause
    exit /b 1
)
echo Virtual environment created

:: Step 3: Upgrade pip first
echo.
echo [3/5] Upgrading pip...
echo [3/5] Upgrading pip... >> "%LF%" 2>&1

"%ROOT%.venv\Scripts\python" -m pip install --upgrade pip --default-timeout=60 >> "%LF%" 2>&1
echo pip upgraded

:: Step 4: Install requirements (with mirror fallback)
echo.
echo [4/5] Installing dependencies...
echo [4/5] Installing dependencies... >> "%LF%" 2>&1

"%ROOT%.venv\Scripts\python" -m pip install -r "%ROOT%requirements.txt" --default-timeout=60 >> "%LF%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] First attempt failed, trying Chinese mirror...
    echo [INFO] Trying mirror... >> "%LF%" 2>&1
    "%ROOT%.venv\Scripts\python" -m pip install -r "%ROOT%requirements.txt" --default-timeout=60 -i https://pypi.tuna.tsinghua.edu.cn/simple >> "%LF%" 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Some dependencies may have warnings
        echo [WARNING] Dependency install had warnings >> "%LF%" 2>&1
    ) else (
        echo Dependencies installed (via mirror)
    )
) else (
    echo Dependencies installed
)

:: Step 5: Verify
echo.
echo [5/5] Verifying installation...
echo [5/5] Verifying installation... >> "%LF%" 2>&1

"%ROOT%.venv\Scripts\python" -c "import flask, requests, yaml; print('OK')" >> "%LF%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Verification failed!
    echo.
    echo Possible reasons:
    echo   1. Network issue - try again later
    echo   2. Antivirus blocking - check log: %LF%
    echo.
    echo If problem persists, send the log file to support.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo    Install complete!
echo.
echo    Now fill in your Cookie:
echo     1. Open data\config.yaml in Notepad
echo     2. Find the line: cookie: ""
echo     3. Paste your Cookie between the quotes
echo     4. Save the file
echo.
echo    Then double-click start.bat to run.
echo ============================================
echo.
echo Log saved to: %LF%
echo.

:: Create desktop shortcut
set "SHORTCUT=%USERPROFILE%\Desktop\WeiboWatcher.lnk"
if not exist "%SHORTCUT%" (
    powershell -Command "$WS=New-Object -ComObject WScript.Shell; $SC=$WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath='%ROOT%start.bat'; $SC.WorkingDirectory='%ROOT%'; $SC.Description='Weibo Watcher'; $SC.Save()" >nul 2>&1
    echo Desktop shortcut created
)

echo Press any key to exit...
pause >nul
