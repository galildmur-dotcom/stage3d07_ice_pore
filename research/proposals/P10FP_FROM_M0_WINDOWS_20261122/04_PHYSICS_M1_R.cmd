@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP PHYSICS M1 - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh M1 --mode R
) else (
    python "%~dp0P10FN_physics.py" --mesh M1 --mode R
)
set "RESULT=%ERRORLEVEL%"
echo P10FP physics M1 exit code: %RESULT%
echo This window stays open; close with X. No keyboard input required.
exit /b %RESULT%
