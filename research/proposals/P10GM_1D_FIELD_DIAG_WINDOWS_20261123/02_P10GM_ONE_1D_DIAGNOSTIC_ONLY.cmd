@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GM ONE BOUNDED 1D DIAGNOSTIC NO 3D" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GM 02: visible progress. Up to three separate Gmsh -1 tests, 30s EACH.
echo No -2/-3, no FEM. DO NOT repeat 02, even after STOP.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GM_1d_probe.py" --run-1d
) else (
    python "%~dp0P10GM_1d_probe.py" --run-1d
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GM_02_EXIT_CODE=%CHECK_EXIT%
if exist "%~dp0P10GM_02_RESULT.txt" type "%~dp0P10GM_02_RESULT.txt"
echo If evidence was produced, send ONE P10GM_1D_PROBE_EVIDENCE.zip.
echo Otherwise send the console text or P10GM_GMSH_1D.log.
echo DO NOT repeat 02. You may close this window with X.
exit /b %CHECK_EXIT%
