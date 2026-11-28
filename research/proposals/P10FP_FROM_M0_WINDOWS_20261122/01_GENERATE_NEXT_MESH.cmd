@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP MESH - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10FP: fresh M0 or next reviewed adaptive Gmsh 3D mesh, NO PHYSICS.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_adapt.py" --auto
) else (
    python "%~dp0P10FN_adapt.py" --auto
)
set "RESULT=%ERRORLEVEL%"
echo P10FN mesh exit code: %RESULT%
echo Evidence is saved to G:\ildar\Stage3D07\LOCAL_RUNS.
echo This window stays open; close with X. No keyboard input required.
exit /b %RESULT%
