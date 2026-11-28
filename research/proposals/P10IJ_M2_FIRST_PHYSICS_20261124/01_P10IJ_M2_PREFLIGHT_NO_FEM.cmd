@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IJ M2 PREFLIGHT NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IJ_M2_FIRST_FULL4D.py
) else (
  python -u P10IJ_M2_FIRST_FULL4D.py
)
set "RC=%ERRORLEVEL%"
echo P10IJ_PREFLIGHT_EXIT=%RC%
exit /b %RC%
