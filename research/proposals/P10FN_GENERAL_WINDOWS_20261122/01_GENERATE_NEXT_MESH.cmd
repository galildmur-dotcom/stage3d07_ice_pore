@echo off
setlocal
echo P10FN: adaptive Gmsh 3D mesh generation, NO PHYSICS.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_adapt.py" --recipe "%~dp0recipes\ACTIVE.json"
) else (
    python "%~dp0P10FN_adapt.py" --recipe "%~dp0recipes\ACTIVE.json"
)
set "RESULT=%ERRORLEVEL%"
echo P10FN mesh exit code: %RESULT%
echo Evidence is saved to G:\ildar\Stage3D07\LOCAL_RUNS.
exit /b %RESULT%
