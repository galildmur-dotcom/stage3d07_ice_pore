@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Apply-Patch.ps1"
) else (
  powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Apply-Patch.ps1" -PatchPath "%~1"
)
echo.
echo Press any key to close this window...
pause >nul
