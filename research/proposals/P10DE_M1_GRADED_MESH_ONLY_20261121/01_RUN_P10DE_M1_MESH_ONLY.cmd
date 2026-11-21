@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DE - ONE M1 GRADED MESH ONLY - NO FEM
echo.
echo P10DE: M0=H0, one Gmsh M1 graded mesh, 20 percent target volume.
echo NO FEM. No file in G:\ildar\Stage3D07 will be modified.
echo Gmsh 4.15.2, H0 exact SHA, full curved 27QP QA, one-shot.
echo.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DE STOP: Python 3 was not found.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DE_one_click_m1.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DE_one_click_m1.py"
set "RC=%ERRORLEVEL%"
goto DONE
:DONE
echo.
echo P10DE process exit: %RC%
echo Send only P10DE_EVIDENCE.zip from the newly created P10DE_RUNS folder.
echo Do not send the large M1.msh and do not launch the physical solver.
pause
exit /b %RC%
