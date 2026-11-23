@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GH PREFLIGHT - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GH_01_RESULT.txt"
> "%LOG%" echo P10GH 01: source SHA, M0, Gmsh version, GEO parse ONLY. No 2D/3D/FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GH_surface_compare.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GH_surface_compare.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GH PREFLIGHT PASS. You may click the new 02 button ONE TIME.
) else (
    echo P10GH PREFLIGHT STOP. Do NOT run 02. Send P10GH_01_RESULT.txt.
)
echo No text input required. This window stays open until you close it with X.
exit /b %CHECK_EXIT%
