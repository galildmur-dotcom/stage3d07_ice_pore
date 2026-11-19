@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10BL_PROJECT=G:\ildar\Stage3D07"
set "P10BL_SCRIPT=%~dp0P10BL_History_Scope.ps1"
if not exist "%P10BL_SCRIPT%" (
  echo P10BL ERROR: PowerShell script is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BL: inspect historical Git data before any GitHub push.
echo This is a READ-ONLY audit of the local branch and its reachable objects.
echo NO push, fetch, pull, checkout, branch edit, commit, or FEM.
echo Output is one compact text report, not a Git bundle.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%P10BL_SCRIPT%" -ProjectRoot "%P10BL_PROJECT%"
set "P10BL_RC=%ERRORLEVEL%"
echo.
echo P10BL exit code: %P10BL_RC%
echo Send only P10BL_HISTORY_SCOPE.txt to ChatGPT.
pause
exit /b %P10BL_RC%
