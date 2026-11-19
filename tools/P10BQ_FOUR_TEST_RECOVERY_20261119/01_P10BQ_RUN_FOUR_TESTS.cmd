@echo off
setlocal
title Stage3D07 P10BQ four existing tests only
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10BQ_Run_Four_Tests.ps1"
set "P10BQ_EXIT=%ERRORLEVEL%"
echo.
echo P10BQ exit code: %P10BQ_EXIT%
echo Find P10BQ_RESULT.txt in the new G:\ildar\P10BQ_TESTS_* folder.
echo Send only its P10BQ_EVIDENCE.zip file after inspecting its contents.
pause
exit /b %P10BQ_EXIT%
