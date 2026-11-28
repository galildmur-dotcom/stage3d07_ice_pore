@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10BI_PROJECT=G:\ildar\Stage3D07"
set "P10BI_SCRIPT=%~dp0P10BI_Check_Commit.ps1"
if not exist "%P10BI_SCRIPT%" (
  echo P10BI ERROR: PowerShell script is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BI: seven-source local Git snapshot with independent backup.
echo Target: %P10BI_PROJECT%
echo Preflight and backup run first. A commit requires typing COMMIT 7.
echo No push, pull, reset, clean, patch or FEM will be run.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%P10BI_SCRIPT%" -ProjectRoot "%P10BI_PROJECT%"
set "P10BI_RC=%ERRORLEVEL%"
echo.
echo P10BI exit code: %P10BI_RC%
echo Please send only the generated P10BI_RESULT.txt to ChatGPT.
pause
exit /b %P10BI_RC%
