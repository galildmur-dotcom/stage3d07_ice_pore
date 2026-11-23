@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GX TEMPORAL PREFLIGHT" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10GX_temporal_series.py
) else (
  python -u P10GX_temporal_series.py
)
set "RC=%ERRORLEVEL%"
echo P10GX_PREFLIGHT_EXIT=%RC%
exit /b %RC%
