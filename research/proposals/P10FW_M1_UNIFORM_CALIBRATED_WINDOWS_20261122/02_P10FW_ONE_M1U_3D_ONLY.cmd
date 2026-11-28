@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FW M1U ONE 3D - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FW_MESH_RESULT.txt"
> "%LOG%" echo P10FW one 3D uniform-target M1U MESH-ONLY. NO FEM/KEYBOARD INPUT.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FW_one_click_m1u.py" --one-mesh >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FW_one_click_m1u.py" --one-mesh >> "%LOG%" 2>&1
)
set "MESH_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo MESH_EXIT_CODE=%MESH_EXIT%
type "%LOG%"
if "%MESH_EXIT%"=="0" (
    echo Candidate saved: G:\ildar\Stage3D07\meshes\M1U_CANDIDATE.msh
    echo Next: independent 729QP on ALL 18 spatial regions. NO PHYSICS YET.
) else (
    echo P10FW_M1U_STOP. Send P10FW_MESH_RESULT.txt and available evidence ZIP.
)
echo The one-shot M1U lock is NEVER removed automatically.
echo Window stays open. Close with X. No keyboard entry required.
exit /b %MESH_EXIT%
