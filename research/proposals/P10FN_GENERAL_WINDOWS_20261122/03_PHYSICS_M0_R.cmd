@echo off
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_physics.py" --mesh M0 --mode R
) else (
    python "%~dp0P10FN_physics.py" --mesh M0 --mode R
)
exit /b %ERRORLEVEL%
