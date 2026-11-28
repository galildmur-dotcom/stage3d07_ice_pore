@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GO ONE SINGLE MATH FIELD ONLY NATIVE 1D" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GO 02: ONE native 1D A original F3 + ONE B fully inlined south C1.
echo Hard 30s each, RAM 8GiB, nt2; live Gmsh log and heartbeat 2s.
echo NO -2, NO -3, NO FEM. Do not repeat this button after STOP.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GO_1d_probe.py" --run-1d
) else (
    python "%~dp0P10GO_1d_probe.py" --run-1d
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GO_02_EXIT_CODE=%CHECK_EXIT%
if exist "%~dp0P10GO_02_RESULT.txt" type "%~dp0P10GO_02_RESULT.txt"
echo Send ONE P10GO_1D_PROBE_EVIDENCE.zip when present.
echo Otherwise send P10GO_02_RESULT.txt or console text.
echo NEVER REPEAT 02. You may close this window with X.
exit /b %CHECK_EXIT%
