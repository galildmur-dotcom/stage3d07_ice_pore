@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GV ONE M1 SIGNED 4D" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10GV_run.py --run
) else (
  python -u P10GV_run.py --run
)
set "P10GV_RC=%ERRORLEVEL%"
echo P10GV_PHYSICAL_EXIT=%P10GV_RC%
exit /b %P10GV_RC%
