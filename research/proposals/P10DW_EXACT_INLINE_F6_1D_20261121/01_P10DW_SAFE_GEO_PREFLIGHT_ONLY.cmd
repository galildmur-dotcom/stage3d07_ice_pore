@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DW - SOURCE GEO PREFLIGHT ONLY
echo P10DW R1: exact original P10DG M1 SHA, source/math, CAD, Gmsh4.15.2.
echo Two bounded Gmsh -parse_and_exit ONLY; NO -1/-2/-3, NO physical FEM.
echo No one-shot is consumed; old markers, caches and original M1 are read-only.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DW STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DW_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DW_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
:DONE
echo P10DW PREFLIGHT exit: %RC%
echo If STOP, send new P10DW_EVIDENCE.zip; do not start button 02.
pause
exit /b %RC%
