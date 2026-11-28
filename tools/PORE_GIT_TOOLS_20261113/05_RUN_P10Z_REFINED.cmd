@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Run-P10Z-Refinement.ps1"
echo.
echo Press any key to close this window...
pause >nul
