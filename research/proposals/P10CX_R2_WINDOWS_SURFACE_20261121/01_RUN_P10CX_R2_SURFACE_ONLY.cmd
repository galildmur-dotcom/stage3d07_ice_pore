@echo off
setlocal
cd /d "%~dp0"
echo P10CX R2: ONE 2D surface-only Gmsh 4.15.2 attempt.
echo This repairs the R1 version-probe STOP; never rerun R1.
echo No source repo writes, no 3D Tet10, no FEM.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CX_R2_run.ps1"
set "P10CX_R2_EXIT=%ERRORLEVEL%"
echo.
echo P10CX R2 launcher exit code: %P10CX_R2_EXIT%
pause
exit /b %P10CX_R2_EXIT%
