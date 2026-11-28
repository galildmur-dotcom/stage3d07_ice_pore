@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IR M3 FIRST REAL FULL4D ONE SHOT" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
echo P10IR_M3_ONE_SHOT_REAL_FEM_APPROVED
echo P10IR_NOTICE: heartbeat every 30 seconds; do not start twice
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IR_M3_FIRST_FULL4D.py --run
) else (
  python -u P10IR_M3_FIRST_FULL4D.py --run
)
set "RC=%ERRORLEVEL%"
echo P10IR_EXIT=%RC%
exit /b %RC%
