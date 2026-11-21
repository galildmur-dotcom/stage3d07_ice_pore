@echo off
setlocal
title P10BS - read-only export of existing P10BD/P10BE CSV (NO FEM)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10BS_Export_Existing_Csv.ps1"
set "P10BS_EXIT=%ERRORLEVEL%"
echo.
echo P10BS exit code: %P10BS_EXIT%
echo Inspect P10BS_RESULT.txt and send ONLY P10BS_EVIDENCE.zip from the new P10BS_EXPORT_* folder.
echo No build, no FEM, no Git actions were requested.
pause
exit /b %P10BS_EXIT%
