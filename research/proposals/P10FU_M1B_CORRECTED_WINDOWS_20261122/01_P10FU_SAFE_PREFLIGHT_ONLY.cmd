@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FU M1B PREFLIGHT - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FU_CHECK_RESULT.txt"
> "%LOG%" echo P10FU M1B source and native parse check. NO 3D MESH, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FU_one_click_m1b.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FU_one_click_m1b.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10FU_PREFLIGHT_PASS. Next: 02_P10FU_ONE_M1B_3D_ONLY.cmd
) else (
    echo P10FU_PREFLIGHT_STOP. Send P10FU_CHECK_RESULT.txt; do NOT run 02.
)
echo Window stays open. Close with X. No keyboard entry required.
exit /b %CHECK_EXIT%
