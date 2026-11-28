@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DW - SINGLE INLINE F6 1D ONLY
echo P10DW R1: PREVIOUS 01 PASS REQUIRED, source/CAD M1 SHA rechecked.
echo ONE bounded Gmsh -1 exact flattened F6, 15s/2GiB/20MiB msh.
echo NO -2/-3/M2 Tet10, NO physical forward/adjoint/FEM.
echo A new global and local P10DW marker is consumed immediately before -1.
echo NEVER rerun 02 after PASS/STOP. Keep all old markers and caches.
where py.exe >nul 2>nul
if not errorlevel 1 goto USE_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo P10DW STOP: Python 3 missing.
set "RC=2"
goto DONE
:USE_PY
py -3 "%~dp0P10DW_one_click_1d.py" --one-1d
set "RC=%ERRORLEVEL%"
goto DONE
:USE_PYTHON
python "%~dp0P10DW_one_click_1d.py" --one-1d
set "RC=%ERRORLEVEL%"
:DONE
echo P10DW DIAGNOSTIC exit: %RC%
echo Send ONLY P10DW_EVIDENCE.zip. NEVER rerun button 02.
pause
exit /b %RC%
