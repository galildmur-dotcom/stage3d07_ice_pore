@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP PHYSICS - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10FN: latest approved mesh, fresh forward and same-mesh adjoint, R mode.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh LATEST --mode R
) else (
    python "%~dp0P10FN_physics.py" --mesh LATEST --mode R
)
set "RESULT=%ERRORLEVEL%"
echo P10FN physics exit code: %RESULT%
echo Evidence is saved to G:\ildar\Stage3D07\LOCAL_RUNS.
echo This window stays open; close with X. No keyboard input required.
exit /b %RESULT%
