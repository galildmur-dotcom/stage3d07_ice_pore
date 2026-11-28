@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GG ONE 2D PAIR - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GG_02_RESULT.txt"
> "%LOG%" echo P10GG 02: ONE protected original plus rotated Gmsh -2 pair. No 3D/FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GG_surface_compare.py" --one-2d-pair >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GG_surface_compare.py" --one-2d-pair >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GG TWO SURFACE MESHES COMPLETE. Send ONE P10GG_CAD_POLE_2D_EVIDENCE.zip.
) else (
    echo P10GG STOP. Do not rerun 02 or delete markers.
    echo Send newest P10GG_CAD_POLE_2D_EVIDENCE.zip if present.
    echo Otherwise send P10GG_02_RESULT.txt.
)
echo No text input required. This window stays open until you close it with X.
exit /b %CHECK_EXIT%
