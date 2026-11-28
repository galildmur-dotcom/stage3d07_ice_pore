@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10BJ_PROJECT=G:\ildar\Stage3D07"
set "P10BJ_SCRIPT=%~dp0P10BJ_Finish_Local_Commit.ps1"
if not exist "%P10BJ_SCRIPT%" (
  echo P10BJ ERROR: PowerShell script is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BJ: controlled recovery after P10BI branch switch.
echo Expected: P10BI research branch, original HEAD, 5 modified + 2 untracked files.
echo All seven SHA-256 values will be rechecked. Independent backups are created.
echo A commit requires explicit COMMIT 7. No push, pull, branch creation or FEM.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%P10BJ_SCRIPT%" -ProjectRoot "%P10BJ_PROJECT%"
set "P10BJ_RC=%ERRORLEVEL%"
echo.
echo P10BJ exit code: %P10BJ_RC%
echo Send only P10BJ_RESULT.txt to ChatGPT; do not rerun on an error.
pause
exit /b %P10BJ_RC%
