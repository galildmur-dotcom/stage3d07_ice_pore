@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DT - SAFE PREFLIGHT ONLY
echo P10DT: verify 8 source pins, original geometry, Gmsh 4.15.2 and 3 GEO parses.
echo NO Gmsh -1/-2/-3, NO physical FEM, NO one-shot markers consumed.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DT STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DT_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DT_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
:DONE
echo P10DT PREFLIGHT exit: %RC%
echo If STOP, send only P10DT_EVIDENCE.zip; DO NOT start button 02.
pause
exit /b %RC%
