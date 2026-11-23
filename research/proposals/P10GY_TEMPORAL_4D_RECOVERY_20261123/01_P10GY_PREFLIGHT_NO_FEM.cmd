@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GY FIXED 4D PREFLIGHT" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10GY_temporal_series.py
) else (
  python -u P10GY_temporal_series.py
)
set "RC=%ERRORLEVEL%"
echo P10GY_PREFLIGHT_EXIT=%RC%
exit /b %RC%
