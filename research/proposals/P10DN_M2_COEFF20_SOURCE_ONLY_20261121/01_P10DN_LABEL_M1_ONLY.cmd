@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 P10DN_m2_coefficient.py --label-m1
) else (
  python P10DN_m2_coefficient.py --label-m1
)
set "P10DN_EXIT=%ERRORLEVEL%"
echo.
echo P10DN label-only finished with exit %P10DN_EXIT%.
echo No Gmsh or physical FEM was started. No M1 or old marker was modified.
pause
exit /b %P10DN_EXIT%
