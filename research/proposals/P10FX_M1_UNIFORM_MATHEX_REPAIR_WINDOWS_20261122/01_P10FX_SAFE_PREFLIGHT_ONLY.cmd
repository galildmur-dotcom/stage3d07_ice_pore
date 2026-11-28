@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FX M1V PREFLIGHT - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FX_CHECK_RESULT.txt"
> "%LOG%" echo P10FX first-M1 uniform 15-20 all-volume PREFLIGHT. NO 3D MESH, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FX_one_click_m1v.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FX_one_click_m1v.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10FX_PREFLIGHT_PASS. Next: 02_P10FX_ONE_M1V_3D_ONLY.cmd
) else (
    echo P10FX_PREFLIGHT_STOP. Send P10FX_CHECK_RESULT.txt; do NOT run 02.
)
echo Window stays open. Close with X. No keyboard entry required.
exit /b %CHECK_EXIT%
