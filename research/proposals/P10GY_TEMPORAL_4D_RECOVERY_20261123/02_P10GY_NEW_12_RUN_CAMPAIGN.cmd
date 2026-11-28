@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GY FIXED 12 FULL4D TEMPORAL RUNS" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10GY_temporal_series.py --run
) else (
  python -u P10GY_temporal_series.py --run
)
set "RC=%ERRORLEVEL%"
echo P10GY_CAMPAIGN_EXIT=%RC%
exit /b %RC%
