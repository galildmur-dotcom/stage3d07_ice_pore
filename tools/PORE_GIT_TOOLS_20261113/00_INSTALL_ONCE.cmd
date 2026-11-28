@echo off
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install.ps1"
echo.
echo Press any key to close this window...
pause >nul
