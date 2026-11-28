@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DO - ONE M2 GMSH MESH - NO FEM
echo.
echo P10DO R1: at most ONE NEW M2 mesh-only native Gmsh attempt.
echo Requires accepted exact M1 and successful safe source/geometry preflight.
echo C1 kappa[0,1], target local volume reduction 0 to 20 percent.
echo No physical forward, adjoint, FEM, H0 cache or old markers touched.
echo The one-shot is consumed immediately BEFORE native Gmsh launch.
echo.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DO STOP: Python 3 not found.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DO_one_click_m2.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DO_one_click_m2.py"
set "RC=%ERRORLEVEL%"
goto DONE
:DONE
echo.
echo P10DO process exit: %RC%
echo Return P10DO_EVIDENCE.zip only (small).
echo Keep original M1, new M2.msh and all one-shot markers locally.
pause
exit /b %RC%
