@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IR M3 PREFLIGHT NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IR_M3_FIRST_FULL4D.py
) else (
  python -u P10IR_M3_FIRST_FULL4D.py
)
set "RC=%ERRORLEVEL%"
echo P10IR_PREFLIGHT_EXIT=%RC%
exit /b %RC%
