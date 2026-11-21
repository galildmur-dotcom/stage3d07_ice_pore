@echo off
setlocal
cd /d "%~dp0"
echo P10CX R1 -- ONE 2D surface-only U1_geo Gmsh 4.15.2 attempt.
echo No 3D Tet10, no FEM, no writes to source repository.
echo All output remains under this extracted directory.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CX_run.ps1"
set "P10CX_RC=%ERRORLEVEL%"
echo.
echo P10CX exit code: %P10CX_RC%
pause
exit /b %P10CX_RC%
