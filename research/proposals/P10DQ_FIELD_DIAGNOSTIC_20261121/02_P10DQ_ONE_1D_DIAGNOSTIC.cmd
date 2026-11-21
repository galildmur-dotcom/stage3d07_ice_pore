@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DQ - ONE BOUNDED 1D DIAGNOSTIC
echo P10DQ: up to FIVE Gmsh -1 sequential variants, at most 25s EACH.
echo No Gmsh -2/-3, no FEM, no original M1/M2/old marker modification.
echo New P10DQ one-shot markers consumed just before native Gmsh -1.
echo On any STOP do NOT rerun or delete markers.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DQ STOP: Python 3 missing.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DQ_one_click_1d.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DQ_one_click_1d.py"
set "RC=%ERRORLEVEL%"
:DONE
echo P10DQ DIAGNOSTIC process exit: %RC%
echo Return ONLY P10DQ_EVIDENCE.zip. Keep all originals/markers.
pause
exit /b %RC%
