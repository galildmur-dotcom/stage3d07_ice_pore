@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EV ONE newly authorized native M2 Gmsh -3; no physical FEM.
echo First complete 01. Do not run 02 more than once even after error.
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3 "%~dp0P10EV_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
goto finish
:fallback
python "%~dp0P10EV_one_click_m2.py" --one-m2
set "RC=%ERRORLEVEL%"
:finish
echo P10EV 02 exit code %RC%. Send the newest P10EV_EVIDENCE.zip.
pause
exit /b %RC%
