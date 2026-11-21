@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DR - SAFE PREFLIGHT ONLY
echo P10DR: PIN, F3/F4/kappa samples, RAM/disk, native Gmsh 4.15.2 and 7 GEO parses.
echo ONLY parse-and-exit: NO Gmsh -1/-2/-3, no FEM, no one-shot marker.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DR STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DR_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DR_one_click_1d.py" --preflight-only
set "RC=%ERRORLEVEL%"
:DONE
echo P10DR PREFLIGHT exit: %RC%
echo If STOP, send ONLY P10DR_EVIDENCE.zip. Do not run button 02.
pause
exit /b %RC%
