@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EK R1 SAFE PREFLIGHT ONLY: verify exact M1, Gmsh, B Alg5 and GEO parse.
echo This button NEVER launches a 3D mesh or FEM. Marker remains unused.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EK_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EK_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EK 01 exit code %RC%. Proceed to 02 only on preflight PASS.
pause
exit /b %RC%
