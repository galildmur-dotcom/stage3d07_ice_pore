@echo off
setlocal
cd /d "%~dp0"
echo P10NL READONLY native Gmsh 4.15.2 diagnostic quality comparison
echo NO MESH GENERATION - NO FEM - NO MARKER - NOT M13 R3
py -3 P10NL_NATIVE_GMSH_QUALITY.py
set "CODE=%ERRORLEVEL%"
echo P10NL_EXIT=%CODE%
pause
exit /b %CODE%
