@echo off
setlocal
cd /d "%~dp0"
echo P10CT R1: ONE U0 MESH-ONLY attempt, no FEM, no source tree writes.
echo Check README_RU.md before running. Outputs remain in this extracted folder.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CT_run.ps1"
set "P10CT_EXIT=%ERRORLEVEL%"
echo.
echo P10CT launcher exit code: %P10CT_EXIT%
pause
exit /b %P10CT_EXIT%
