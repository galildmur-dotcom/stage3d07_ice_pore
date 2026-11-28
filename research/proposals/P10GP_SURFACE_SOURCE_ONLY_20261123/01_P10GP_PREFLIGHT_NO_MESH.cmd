@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GP PRELIGHT NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GP 01: source SHA, M0 SHA, Gmsh SHA, 2 parse-only checks. NO mesh.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 P10GP_windows_2d.py --preflight
) else (
    python P10GP_windows_2d.py --preflight
)
set "P10GP_EXIT=%ERRORLEVEL%"
echo P10GP_PREFLIGHT_EXIT=%P10GP_EXIT%
echo Only after PASS, ask for separate approval before native 02.
exit /b %P10GP_EXIT%
