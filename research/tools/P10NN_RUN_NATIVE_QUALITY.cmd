@echo off
setlocal
cd /d "%~dp0"
echo P10NN read-only diagnostic Gmsh 4.15.2: NO GENERATION, NO FEM, NO MARKERS
py -3 -u P10NN_NATIVE_QUALITY.py
set "RC=%ERRORLEVEL%"
echo P10NN_EXIT=%RC%
exit /b %RC%
