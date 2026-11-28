@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GN ONE 1D REFERENCE TESTS NO 3D" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GN 02: up to 3 bounded native Gmsh -1 cases; hard 30s per case.
echo D=F3 reference, E=F3*0.94, F=F6+size floor only if D/E both PASS.
echo Live Gmsh log and heartbeat every 2s. NO -2, NO -3, NO FEM.
echo ONE SHOT: do not repeat this button or delete P10GN marker after STOP.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GN_1d_probe.py" --run-1d
) else (
    python "%~dp0P10GN_1d_probe.py" --run-1d
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GN_02_EXIT_CODE=%CHECK_EXIT%
if exist "%~dp0P10GN_02_RESULT.txt" type "%~dp0P10GN_02_RESULT.txt"
echo Send ONE P10GN_1D_PROBE_EVIDENCE.zip if it exists.
echo Otherwise send P10GN_02_RESULT.txt or the console text.
echo NEVER REPEAT 02. You may close this window with X.
exit /b %CHECK_EXIT%
