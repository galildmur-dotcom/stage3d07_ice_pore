@echo off
if /I "%~1"=="--visible" goto RUN
start "P10FP CHECK - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10FP_CHECK_RESULT.txt"
> "%LOG%" echo P10FP CHECK: source, approvals, and adaptation recipe; NO FEM OR GMSH.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_check.py" >> "%LOG%" 2>&1
) else (
    python "%~dp0P10FN_check.py" >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10FP_CHECK_PASS. You can now run 01_GENERATE_NEXT_MESH.cmd.
) else (
    echo P10FP_CHECK_FAILED. Send P10FP_CHECK_RESULT.txt for diagnosis.
)
echo The window stays open. Close with the X button; no keyboard input needed.
exit /b %CHECK_EXIT%
