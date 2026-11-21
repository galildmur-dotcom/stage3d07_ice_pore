@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DQ - SAFE PREFLIGHT ONLY
echo P10DQ: PIN, formula, resources, Gmsh 4.15.2 and FIVE GEO parse-only checks.
echo No Gmsh -1/-2/-3, no FEM, no one-shot marker.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DQ STOP: Python 3 missing.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DQ_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DQ_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
:DONE
echo P10DQ PREFLIGHT process exit: %RC%
echo Return P10DQ_EVIDENCE.zip if STOP. No 1D run was performed.
pause
exit /b %RC%
