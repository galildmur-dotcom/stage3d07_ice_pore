@echo off
setlocal
cd /d "%~dp0"
echo P10NP HighOrderElastic plus exact boundary restoration; diagnostic IN MEMORY only
echo No mesh output, no FEM, no one-shot marker
py -3 -u P10NP_NATIVE_BOUNDARY_RESTORATION.py > P10NP_GMSH_RESTORE_LOG.txt 2>&1
set "RC=%ERRORLEVEL%"
type P10NP_GMSH_RESTORE_LOG.txt
echo P10NP_EXIT=%RC%
exit /b %RC%
