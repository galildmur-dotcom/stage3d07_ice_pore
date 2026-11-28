@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo P10EV NEW M2 one-shot: source SHA / original M1 / Gmsh 4.15.2 / native GEO parse.
echo Button 01 ONLY: NO M2 -3, NO FEM, NO marker consumption.
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3 "%~dp0P10EV_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto finish
:fallback
python "%~dp0P10EV_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
:finish
echo P10EV 01 exit code %RC%. Button 02 allowed only after PASS within 24h.
pause
exit /b %RC%
