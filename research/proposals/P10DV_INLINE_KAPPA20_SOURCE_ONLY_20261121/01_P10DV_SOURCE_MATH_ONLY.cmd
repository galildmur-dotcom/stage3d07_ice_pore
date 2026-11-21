@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DV - READ ONLY FIELD MATH SELFTEST
echo P10DV: exact original M1 and P10DN field source pins, direct inline F6 parity.
echo No native Gmsh, no 1D/2D/3D mesh, no FEM, no markers.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DV STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DV_inline_source_unit.py" --selftest
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DV_inline_source_unit.py" --selftest
set "RC=%ERRORLEVEL%"
:DONE
echo P10DV SOURCE-ONLY exit: %RC%
echo This test does not authorize a Gmsh run or physical FEM.
pause
exit /b %RC%
