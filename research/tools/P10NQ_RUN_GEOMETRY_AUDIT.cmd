@echo off
setlocal
cd /d "%~dp0"
echo P10NQ geometric correspondence of original and in-memory Gmsh HighOrderElastic
echo NO mesh output, generation, FEM or markers
py -3 -u P10NQ_GEOMETRY_CORRESPONDENCE.py > P10NQ_GMSH_GEOMETRY_LOG.txt 2>&1
set "RC=%ERRORLEVEL%"
type P10NQ_GMSH_GEOMETRY_LOG.txt
echo P10NQ_EXIT=%RC%
exit /b %RC%
