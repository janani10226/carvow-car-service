@echo off
title Carvow Admin Portal Launcher
echo ===================================================
echo        CARVOW LIVE ADMIN PORTAL LAUNCHER
echo ===================================================
echo.

:: Check if server is running on port 5001
powershell -Command "if (Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if %errorlevel% neq 0 (
    echo [INFO] Carvow Web Server is not running. Starting server...
    pushd "%~dp0\.."
    start "" /b python app.py
    popd
    timeout /t 2 /nobreak >nul
)

echo [OK] Opening Live Admin Portal in default browser...
start http://127.0.0.1:5001/admin/login

echo.
echo ===================================================
echo   Admin Portal URL: http://127.0.0.1:5001/admin/login
echo ===================================================
echo Window will close automatically in 3 seconds.
timeout /t 3 >nul
