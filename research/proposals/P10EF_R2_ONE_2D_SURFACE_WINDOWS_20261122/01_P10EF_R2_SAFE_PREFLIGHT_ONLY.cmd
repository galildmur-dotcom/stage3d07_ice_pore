@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EF R2 safe preflight ONLY: exact M1/M2, SHA, native GEO -parse_and_exit.
echo NO 2D/3D meshing, NO FEM, NO one-shot marker consumption.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EF_R2_one_2d_surface.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EF_R2_one_2d_surface.py" --preflight-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EF R2 preflight exit code %RC%.
pause
exit /b %RC%
