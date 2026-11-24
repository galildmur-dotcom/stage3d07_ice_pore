@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IO M3 ONE SHOT MESH ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IO_guard.py --run
) else (
  python -u P10IO_guard.py --run
)
set "RC=%ERRORLEVEL%"
echo P10IO_MESH_ONLY_EXIT=%RC%
exit /b %RC%
