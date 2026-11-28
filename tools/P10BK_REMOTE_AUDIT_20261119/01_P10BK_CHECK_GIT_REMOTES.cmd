@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10BK_PROJECT=G:\ildar\Stage3D07"
set "P10BK_SCRIPT=%~dp0P10BK_Check_Git_Remotes.ps1"
if not exist "%P10BK_SCRIPT%" (
  echo P10BK ERROR: PowerShell script is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BK: read-only local Git topology and remote URL audit.
echo Expected local commit: 90fd2559c0224ac0a7d2dbe2fe081a6a319080e4.
echo No Git fetch, pull, push, branch switch, commit or FEM.
echo Remote credentials and URL query strings will be hidden in the report.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%P10BK_SCRIPT%" -ProjectRoot "%P10BK_PROJECT%"
set "P10BK_RC=%ERRORLEVEL%"
echo.
echo P10BK exit code: %P10BK_RC%
echo Please send only P10BK_REMOTE_REPORT.txt to ChatGPT.
pause
exit /b %P10BK_RC%
