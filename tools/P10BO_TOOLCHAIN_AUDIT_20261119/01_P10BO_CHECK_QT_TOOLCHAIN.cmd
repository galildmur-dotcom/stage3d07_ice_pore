@echo off
setlocal
title Stage3D07 P10BO read-only Qt Creator toolchain audit
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10BO_Check_Qt_Toolchain.ps1"
set "P10BO_EXIT=%ERRORLEVEL%"
echo.
echo P10BO exit code: %P10BO_EXIT%
echo Send one P10BO_TOOLCHAIN_REPORT.txt to ChatGPT.
pause
exit /b %P10BO_EXIT%
