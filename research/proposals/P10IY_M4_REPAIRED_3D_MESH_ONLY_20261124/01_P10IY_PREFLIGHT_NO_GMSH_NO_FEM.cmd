@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IY R1 PREFLIGHT NO GMSH NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IY_guard.py
) else (
  python -u P10IY_guard.py
)
set "RC=%ERRORLEVEL%"
echo P10IY_R1_PREFLIGHT_EXIT=%RC%
exit /b %RC%
