@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GN 01 CHECK ONLY NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GN 01: check source SHA, frozen M0, Gmsh4.15.2; NO mesh, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GN_1d_probe.py" --preflight
) else (
    python "%~dp0P10GN_1d_probe.py" --preflight
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GN_01_EXIT_CODE=%CHECK_EXIT%
if "%CHECK_EXIT%"=="0" (
    echo PREFLIGHT PASS. Proceed to 02 ONCE within 24 hours.
) else (
    echo PREFLIGHT STOP. Do not run 02. Report console text.
)
echo You may close this window with X.
exit /b %CHECK_EXIT%
