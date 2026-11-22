@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FU M1B ONE 3D - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FU_MESH_RESULT.txt"
> "%LOG%" echo P10FU M1B one-shot mesh-only. NO FEM, NO KEYBOARD INPUT.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FU_one_click_m1b.py" --one-mesh >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FU_one_click_m1b.py" --one-mesh >> "%LOG%" 2>&1
)
set "MESH_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo MESH_EXIT_CODE=%MESH_EXIT%
type "%LOG%"
if "%MESH_EXIT%"=="0" (
    echo Mesh generated: G:\ildar\Stage3D07\meshes\M1B_CANDIDATE.msh
    echo Independent local polar 343/729QP review is still REQUIRED.
) else (
    echo P10FU_M1B_STOP. Send P10FU_MESH_RESULT.txt and available evidence ZIP.
)
echo The one-shot M1B lock is NEVER removed automatically.
echo Window stays open. Close with X. No keyboard entry required.
exit /b %MESH_EXIT%
