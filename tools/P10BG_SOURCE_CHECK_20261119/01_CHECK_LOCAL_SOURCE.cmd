@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "STAGE3D07_PROJECT=G:\ildar\Stage3D07"
set "STAGE3D07_CHECK=%~dp0P10BG_Source_Check.ps1"
if not exist "%STAGE3D07_CHECK%" (
  echo ERROR: P10BG_Source_Check.ps1 is missing beside this CMD.
  pause
  exit /b 2
)
echo P10BG read-only source preflight: %STAGE3D07_PROJECT%
echo No project files or Git refs will be changed.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STAGE3D07_CHECK%" -ProjectRoot "%STAGE3D07_PROJECT%"
set "STAGE3D07_RC=%ERRORLEVEL%"
echo.
echo P10BG check exit code: %STAGE3D07_RC%
echo Please send P10BG_LOCAL_SOURCE_REPORT.txt and P10BG_SHA256.csv to ChatGPT.
pause
exit /b %STAGE3D07_RC%
