@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GB M1W PREFLIGHT - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GB_CHECK_RESULT.txt"
> "%LOG%" echo P10GB R1: native 1D MathEx plus 2D pore-surface preflight. NO 3D, NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GB_one_click_m1w.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GB_one_click_m1w.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GB_PREFLIGHT_PASS. Next: 02_P10GB_ONE_M1W_3D_ONLY.cmd
) else (
    echo P10GB_PREFLIGHT_STOP. Send P10GB_PREFLIGHT_STOP_EVIDENCE.zip from newest LOCAL_RUNS\P10GB_PREFLIGHT_... if it exists.
    echo If no ZIP exists, send P10GB_CHECK_RESULT.txt. Do NOT run 02.
)
echo Window stays open. Close with X. No keyboard entry required.
exit /b %CHECK_EXIT%
