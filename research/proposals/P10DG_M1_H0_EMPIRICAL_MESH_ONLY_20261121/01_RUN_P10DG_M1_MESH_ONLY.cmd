@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DG - ONE M1 MESH ONLY - NO FEM
echo.
echo P10DG R1: one new M1 mesh-only run, empirical H0-based graded size.
echo H0=M0 exact SHA, Gmsh 4.15.2, all Tet10 27QP, global/radial QA.
echo NO FEM. H0, original G: project, old P10DE marker remain untouched.
echo.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DG STOP: Python 3 was not found.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DG_one_click_m1.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DG_one_click_m1.py"
set "RC=%ERRORLEVEL%"
goto DONE
:DONE
echo.
echo P10DG process exit: %RC%
echo Send only P10DG_EVIDENCE.zip from P10DG_RUNS folder.
echo Do NOT send M1.msh, do NOT run FEM, do NOT delete P10DG marker.
pause
exit /b %RC%
