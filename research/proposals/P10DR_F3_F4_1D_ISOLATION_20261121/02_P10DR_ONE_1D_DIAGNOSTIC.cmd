@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DR - ONE BOUNDED 1D DIAGNOSTIC SEQUENCE
echo P10DR: one-shot series of 7 independent native Gmsh -1 tests, max 15s EACH.
echo Full series max 105s Gmsh wall. Does NOT create M2, launch 2D/3D or FEM.
echo Creates ONLY NEW P10DR one-shot markers immediately before first Gmsh -1.
echo DO NOT rerun after PASS/STOP or remove ANY old/new marker.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DR STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DR_one_click_1d.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DR_one_click_1d.py"
set "RC=%ERRORLEVEL%"
:DONE
echo P10DR DIAGNOSTIC exit: %RC%
echo Send ONLY the new P10DR_EVIDENCE.zip. Old M1/M2/cache remain unchanged.
pause
exit /b %RC%
