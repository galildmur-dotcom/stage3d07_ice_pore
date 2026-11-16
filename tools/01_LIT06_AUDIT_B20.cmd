@echo off
setlocal EnableExtensions
set "REPO=G:\ildar\Stage3D07"
set "PYTHON=py"
set "SCRIPT=%~dp0lit06_b20_geometry_audit.py"
set "OUT=%REPO%\LOCAL_RUNS\LIT06_B20_Q3_GEOMETRY"
echo STAGE3D07 LIT06 B20 geometry-only audit (NO FEM)
echo repo: %REPO%
echo output: %OUT%\LIT06_B20_Q3_GEOMETRY.csv
echo.
if not exist "%SCRIPT%" (
 echo LIT06_STOP: Python script missing: %SCRIPT%
 pause
 exit /b 2
)
%PYTHON% -3 "%SCRIPT%" --repo "%REPO%" --labels H4W2B20 H4W4B20 H4W5B20 --out "%OUT%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
 echo LIT06_STOP code=%RC%
 echo Check Python/NumPy, existing MSH2 files, and output directory.
) else (
 echo LIT06_B20_AUDIT_OK
 echo Send only: %OUT%\LIT06_B20_Q3_GEOMETRY.csv
)
echo.
pause
exit /b %RC%
