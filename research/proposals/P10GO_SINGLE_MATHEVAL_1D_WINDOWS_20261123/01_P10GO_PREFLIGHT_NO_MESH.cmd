@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GO 01 SOURCE MATH AND GMSH CHECK NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GO 01: SHA/pins, 10201-point exact single-field math and C1 QA.
echo Check Gmsh4.15.2 SHA/version. NO mesh, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GO_1d_probe.py" --preflight
) else (
    python "%~dp0P10GO_1d_probe.py" --preflight
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GO_01_EXIT_CODE=%CHECK_EXIT%
if "%CHECK_EXIT%"=="0" (
    echo PREFLIGHT PASS. 02 can be run ONCE within 24 hours.
) else (
    echo PREFLIGHT STOP. Do not run 02. Send console text.
)
echo You may close this window with X.
exit /b %CHECK_EXIT%
