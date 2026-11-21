@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DT - ONE 3-WAY 1D DIAGNOSTIC
echo P10DT: one new sequence of 3 distinct Gmsh -1 tests, up to 15s EACH.
echo Maximum 45s native 1D wall; NEVER starts -2/-3 or physical FEM.
echo A/B/C each runs once; STOP does not authorize any retry.
echo ONLY new P10DT markers; leave P10DO/P10DQ/P10DR and M1 untouched.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DT STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DT_one_click_1d.py"
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DT_one_click_1d.py"
set "RC=%ERRORLEVEL%"
:DONE
echo P10DT DIAGNOSTIC exit: %RC%
echo Send ONLY new P10DT_EVIDENCE.zip. NEVER rerun button 02.
pause
exit /b %RC%
