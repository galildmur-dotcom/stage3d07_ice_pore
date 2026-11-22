@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP PHYSICS tz - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh LATEST --mode tz
) else (
    python "%~dp0P10FN_physics.py" --mesh LATEST --mode tz
)
set "RESULT=%ERRORLEVEL%"
echo P10FP physics tz exit code: %RESULT%
echo This window stays open; close with X. No keyboard input required.
exit /b %RESULT%
