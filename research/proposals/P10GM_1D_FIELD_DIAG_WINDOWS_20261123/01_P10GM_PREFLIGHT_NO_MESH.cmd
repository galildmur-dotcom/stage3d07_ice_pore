@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GM 01 PREFLIGHT NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
echo P10GM 01: source/QA, M0 SHA, Gmsh version/SHA. NO mesh. NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GM_1d_probe.py" --preflight
) else (
    python "%~dp0P10GM_1d_probe.py" --preflight
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GM_01_EXIT_CODE=%CHECK_EXIT%
if "%CHECK_EXIT%"=="0" (
    echo PREFLIGHT PASS. Run 02 once within 24 hours.
) else (
    echo PREFLIGHT STOP. Do not run 02. Send screenshot or console text.
)
echo You may close this window with X.
exit /b %CHECK_EXIT%
