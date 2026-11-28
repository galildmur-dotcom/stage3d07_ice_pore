@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EF R2: ONE new 2D Gmsh -2 pore surface mesh ONLY, no -3, no FEM.
echo Requires separate explicit authorization, successful button01 and exact typed phrase.
echo NEVER rerun button02 after permanent one-shot markers exist.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EF_R2_one_2d_surface.py" --one-2d
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EF_R2_one_2d_surface.py" --one-2d
set "RC=%ERRORLEVEL%"
:finish
echo P10EF R2 02 exit code %RC%. NEVER RETRY AFTER ONE-SHOT CONSUMPTION.
pause
exit /b %RC%
