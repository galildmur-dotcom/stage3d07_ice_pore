@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FW M1U PREFLIGHT - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FW_CHECK_RESULT.txt"
> "%LOG%" echo P10FW first-M1 uniform 15-20 all-volume PREFLIGHT. NO 3D MESH, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FW_one_click_m1u.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FW_one_click_m1u.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10FW_PREFLIGHT_PASS. Next: 02_P10FW_ONE_M1U_3D_ONLY.cmd
) else (
    echo P10FW_PREFLIGHT_STOP. Send P10FW_CHECK_RESULT.txt; do NOT run 02.
)
echo Window stays open. Close with X. No keyboard entry required.
exit /b %CHECK_EXIT%
