@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 P10DK_source_preflight.py
) else (
  python P10DK_source_preflight.py
)
set "RC=%ERRORLEVEL%"
echo.
echo P10DK source-only gate exit=%RC%. NO M1 FEM, NO Gmsh.
echo This command does not authorize a physical run.
pause
exit /b %RC%
