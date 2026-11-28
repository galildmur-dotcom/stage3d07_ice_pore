@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FX M1V ONE 3D - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FX_MESH_RESULT.txt"
> "%LOG%" echo P10FX R3 one 3D uniform-target M1V MESH-ONLY. NO FEM/KEYBOARD INPUT.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FX_one_click_m1v.py" --one-mesh >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FX_one_click_m1v.py" --one-mesh >> "%LOG%" 2>&1
)
set "MESH_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo MESH_EXIT_CODE=%MESH_EXIT%
type "%LOG%"
if "%MESH_EXIT%"=="0" (
    echo Candidate saved: G:\ildar\Stage3D07\meshes\M1V_CANDIDATE.msh
    echo Next: independent 729QP on ALL 18 spatial regions. NO PHYSICS YET.
) else (
    echo P10FX_M1V_STOP. Send P10FX_MESH_RESULT.txt and available evidence ZIP.
)
echo The one-shot M1V lock is NEVER removed automatically.
echo Window stays open. Close with X. No keyboard entry required.
exit /b %MESH_EXIT%
