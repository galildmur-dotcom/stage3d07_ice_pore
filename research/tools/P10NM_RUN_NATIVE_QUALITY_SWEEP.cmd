@echo off
setlocal
cd /d "%~dp0"
echo P10NM diagnostic quality sweep: Gmsh 4.15.2 / NO GMSH GENERATION / NO FEM / NO MARKERS
py -3 -u P10NM_NATIVE_QUALITY_SWEEP.py
set "EXITCODE=%ERRORLEVEL%"
echo P10NM_EXIT=%EXITCODE%
exit /b %EXITCODE%
