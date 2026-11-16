@echo off
setlocal EnableExtensions
set "REPO=G:\ildar\Stage3D07"
set "SCRIPT=%~dp0lit08c_b6_mask_identity.py"
set "OUT=%REPO%\LOCAL_RUNS\LIT08C_B6_MASK_IDENTITY_20261116"
echo Stage3D07 LIT08C: pointwise B6 mask identity, GEOMETRY ONLY (NO FEM)
echo Meshes: H4W4B2.msh and H4W4B20_P10AB.msh
echo Output: %OUT%\LIT08C_B6_MASK_IDENTITY.csv
echo.
if not exist "%SCRIPT%" (
  echo LIT08C_STOP missing Python script
  pause
  exit /b 2
)
py -3 "%SCRIPT%" --repo "%REPO%" --out "%OUT%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo LIT08C_STOP code=%RC%. Do not change or delete any meshes.
) else (
  echo LIT08C_MASK_IDENTITY_OK
  echo Please send ONLY: %OUT%\LIT08C_B6_MASK_IDENTITY.csv
)
pause
exit /b %RC%
