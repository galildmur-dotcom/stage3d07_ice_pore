@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EN R1 SAFE PREFLIGHT: alpha=0.17, original M1 SHA, Gmsh and C1 MathEval source.
echo No 3D mesh and no FEM. One-shot markers are not created by this button.
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0P10EN_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto finish
:python_fallback
python "%~dp0P10EN_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EN 01 exit code %RC%. Only PASS allows one 02 within 24 hours.
pause
exit /b %RC%
