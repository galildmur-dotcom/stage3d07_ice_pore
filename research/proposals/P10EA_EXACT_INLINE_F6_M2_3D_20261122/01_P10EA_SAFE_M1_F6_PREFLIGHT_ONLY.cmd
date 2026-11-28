@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EA R1: safe exact-original-M1 / inline F6 / Gmsh GEO -parse_and_exit ONLY.
echo No mesh 1D/2D/3D, no FEM, no one-shot marker consumption.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EA_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EA_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EA 01 exit code %RC%.
pause
exit /b %RC%
