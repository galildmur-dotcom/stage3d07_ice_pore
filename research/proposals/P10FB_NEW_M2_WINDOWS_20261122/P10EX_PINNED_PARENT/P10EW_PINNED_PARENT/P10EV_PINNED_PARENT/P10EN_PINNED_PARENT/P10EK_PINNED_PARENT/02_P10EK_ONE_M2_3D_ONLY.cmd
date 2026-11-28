@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EK R1: ONE new native Gmsh -3 M2 mesh-only, surface Delaunay5, 3D HXT10.
echo This button NEVER launches FEM. Native attempt is consumed even on failure.
echo Do NOT delete new or historical one-shot markers; never rerun after consumption.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EK_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EK_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
:finish
echo P10EK 02 exit code %RC%. KEEP RESULTS AND MARKERS.
pause
exit /b %RC%
