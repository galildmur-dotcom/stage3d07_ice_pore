@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EA R1: one NEW native 3D M2 Gmsh mesh-only. NOT A FEM SOLVER.
echo WARNING: button 02 requires SEPARATE user authorization after safe button 01!
echo If you have not authorized this new -3 attempt, close this window now.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EA_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EA_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
:finish
echo P10EA 02 exit code %RC%. NEVER RERUN after one-shot consumption.
pause
exit /b %RC%
