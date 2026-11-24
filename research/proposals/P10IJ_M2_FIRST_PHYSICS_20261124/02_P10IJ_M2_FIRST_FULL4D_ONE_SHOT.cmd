@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IJ FIRST M2 FULL4D ONE SHOT" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IJ_M2_FIRST_FULL4D.py --run
) else (
  python -u P10IJ_M2_FIRST_FULL4D.py --run
)
set "RC=%ERRORLEVEL%"
echo P10IJ_PHYSICS_EXIT=%RC%
exit /b %RC%
