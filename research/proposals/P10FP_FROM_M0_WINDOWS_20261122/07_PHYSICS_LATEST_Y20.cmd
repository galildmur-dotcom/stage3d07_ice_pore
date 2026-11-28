@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP PHYSICS y20 - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh LATEST --mode y20
) else (
    python "%~dp0P10FN_physics.py" --mesh LATEST --mode y20
)
set "RESULT=%ERRORLEVEL%"
echo P10FP physics y20 exit code: %RESULT%
echo This window stays open; close with X. No keyboard input required.
exit /b %RESULT%
