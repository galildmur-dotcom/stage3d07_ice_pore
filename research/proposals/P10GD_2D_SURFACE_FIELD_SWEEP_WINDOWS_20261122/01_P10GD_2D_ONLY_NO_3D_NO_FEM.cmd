@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GD SURFACE DIAGNOSTIC - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GD_SURFACE_RESULT.txt"
> "%LOG%" echo P10GD: native Gmsh 1D and 2D field sweep ONLY. No 3D. No FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GD_surface_sweep.py" --surface-only >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GD_surface_sweep.py" --surface-only >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GD SURFACE DIAGNOSTIC COMPLETE. Send P10GD_SURFACE_SWEEP_EVIDENCE.zip.
) else (
    echo P10GD STOP. Send the ZIP from newest LOCAL_RUNS\P10GD_SURFACE_SWEEP_... if it exists.
    echo If no ZIP exists, send P10GD_SURFACE_RESULT.txt.
)
echo No keyboard input required. This window stays open until you close it with X.
exit /b %CHECK_EXIT%
