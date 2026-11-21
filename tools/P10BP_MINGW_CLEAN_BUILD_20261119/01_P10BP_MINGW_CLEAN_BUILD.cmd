@echo off
setlocal
title Stage3D07 P10BP isolated MinGW clean build
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10BP_Mingw_Clean_Build.ps1"
set "P10BP_EXIT=%ERRORLEVEL%"
echo.
echo P10BP exit code: %P10BP_EXIT%
echo Read P10BP_RESULT.txt in the new G:\ildar\P10BP_ATTEST_* folder.
echo Send one P10BP_EVIDENCE.zip file after reviewing its contents.
pause
exit /b %P10BP_EXIT%
