@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EN R1: ONE new Gmsh -3 M2, alpha=0.17, Delaunay5/Tet10.
echo NO physical FEM. New one-shot markers are permanent even after failure.
echo Do not restart old P10EK/P10EA; do not remove any markers.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EN_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EN_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
:finish
echo P10EN 02 exit code %RC%. Preserve all results and markers.
pause
exit /b %RC%
