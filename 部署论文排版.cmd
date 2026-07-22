@echo off
cd /d "%~dp0"
title Deploy Paper Typesetting...

echo [1/3] Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo ERROR: Git push failed!
    timeout /t 5 >nul
    exit /b 1
)

echo [2/3] Updating server...
ssh -o StrictHostKeyChecking=no root@8.134.164.52 "bash /opt/paper-typesetting/update.sh"
if %errorlevel% neq 0 (
    echo ERROR: Server update failed!
    timeout /t 5 >nul
    exit /b 1
)

echo [3/3] Checking service...
ssh -o StrictHostKeyChecking=no root@8.134.164.52 "systemctl is-active paper-typesetting"

echo.
echo Done! http://casemaker.help/paper
timeout /t 3 >nul
