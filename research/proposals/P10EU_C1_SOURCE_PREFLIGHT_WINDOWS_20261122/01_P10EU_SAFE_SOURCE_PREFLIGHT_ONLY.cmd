@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EU source-only SHA and Gmsh GEO contract preflight.
echo No Gmsh, no M2 mesh, no FEM, no one-shot marker.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EU_safe_preflight.py" --source-only
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EU_safe_preflight.py" --source-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EU source preflight exit code %RC%.
pause
exit /b %RC%
