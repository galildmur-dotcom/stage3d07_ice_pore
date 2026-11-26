@echo off
setlocal
cd /d "%~dp0"
echo P10NO Gmsh 4.15.2 native optimizer diagnostic; mesh mutation IN MEMORY ONLY
echo No Gmsh generation, no optimized MSH output, no FEM, no one-shot marker
py -3 -u P10NO_RUN_NATIVE_OPTIMIZERS.py
set "EXITCODE=%ERRORLEVEL%"
echo P10NO_EXIT=%EXITCODE%
exit /b %EXITCODE%
