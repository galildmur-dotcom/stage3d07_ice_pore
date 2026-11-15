@echo off
setlocal
set "REPO=G:\ildar\Stage3D07"
set "OUT=%REPO%\LOCAL_RUNS\P10AM0_SURFACE_W2_W4_W5_20261115"
if exist "%OUT%" (
  echo P10AM0_STOP: output already exists: %OUT%
  echo Do NOT overwrite evidence. Change OUT to a NEW folder for rerun.
  pause
  exit /b 2
)
py -3 "%~dp0p10am0_surface_geometry.py" ^
 --mesh "W2=%REPO%\P10M_MESHES\H4W2.msh" ^
 --mesh "W4=%REPO%\P10M_MESHES\H4W4B2.msh" ^
 --mesh "W5=%REPO%\P10M_MESHES\H4W5B2_P10AC.msh" ^
 --out "%OUT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
 echo P10AM0_RUN_OK
) else (
 echo P10AM0_RUN_STOPPED code=%RC%
)
pause
exit /b %RC%
