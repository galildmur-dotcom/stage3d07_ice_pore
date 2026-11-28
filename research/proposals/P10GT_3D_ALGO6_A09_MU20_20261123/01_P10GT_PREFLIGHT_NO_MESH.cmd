@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GT HXT10 PREFLIGHT NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GT 01: source SHA, frozen D027, real Gmsh parse-only. No -1/-2/-3/FEM.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 P10GT_hxt10.py --preflight
) else (
  python P10GT_hxt10.py --preflight
)
set "RC=%ERRORLEVEL%"
echo P10GT_PREFLIGHT_EXIT=%RC%
exit /b %RC%
