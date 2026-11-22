@echo off
setlocal
cd /d "%~dp0"
echo P10EX: exact C1 StrCat M2 safe preflight only, NO M2 and NO FEM.
py -3 P10EX_one_click_m2.py --preflight-only
set "stage3d07_exit=%ERRORLEVEL%"
echo.
echo P10EX SAFE PREFLIGHT exit: %stage3d07_exit%
echo If PASS, separately use 02_P10EX_ONE_M2_3D_ONLY.cmd within 24 hours.
echo Keep original M1 and P10EW/P10EV prior evidence unchanged.
pause
exit /b %stage3d07_exit%
