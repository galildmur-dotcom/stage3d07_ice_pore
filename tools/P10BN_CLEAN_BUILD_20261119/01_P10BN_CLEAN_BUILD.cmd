@echo off
setlocal
title Stage3D07 P10BN isolated Windows build
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10BN_Clean_Build.ps1"
set "P10BN_EXIT=%ERRORLEVEL%"
echo.
echo P10BN exit code: %P10BN_EXIT%
echo Read P10BN_RESULT.txt in the new G:\ildar\P10BN_ATTEST_* folder.
echo Send one P10BN_EVIDENCE.zip file after reviewing its contents.
pause
exit /b %P10BN_EXIT%
