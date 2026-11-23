@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GR PREFLIGHT 20 SOURCE AND PARSE ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GR 01: verify 20 GEO variants, SHA and parse-only; no mesh/FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 P10GR_scan.py --preflight
) else (
    python P10GR_scan.py --preflight
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GR_PREFLIGHT_EXIT=%CHECK_EXIT%
echo Do not run 02 without separate explicit research approval.
exit /b %CHECK_EXIT%
