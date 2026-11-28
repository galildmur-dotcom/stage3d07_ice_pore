@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10BM_PROJECT=G:\ildar\Stage3D07"
set "P10BM_SCRIPT=%~dp0P10BM_Publish_History.ps1"
if not exist "%P10BM_SCRIPT%" (
  echo P10BM ERROR: PowerShell script is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BM: explicitly approved 56-commit history, independent GitHub branch.
echo Target: research/p10bi-local-seven-sources-20261119
echo Preflight and remote branch existence checks run first.
echo Only a typed PUSH 56 permits one non-force Git push.
echo No checkout, merge, reset, clean, source edit, tags or FEM.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%P10BM_SCRIPT%" -ProjectRoot "%P10BM_PROJECT%"
set "P10BM_RC=%ERRORLEVEL%"
echo.
echo P10BM exit code: %P10BM_RC%
echo Send only P10BM_PUSH_RESULT.txt to ChatGPT.
echo If a GitHub sign-in window appears, use your normal account; never paste passwords in the report.
pause
exit /b %P10BM_RC%
