@echo off
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh LATEST --mode tz
) else (
    python "%~dp0P10FN_physics.py" --mesh LATEST --mode tz
)
exit /b %ERRORLEVEL%
