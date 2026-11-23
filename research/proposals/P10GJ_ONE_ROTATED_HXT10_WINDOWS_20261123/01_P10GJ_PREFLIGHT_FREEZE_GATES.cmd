@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GJ PREFLIGHT M0 GATES - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GJ_01_RESULT.txt"
> "%LOG%" echo P10GJ 01: read-only M0 QA27, frozen D-027 numeric gates, native Gmsh parse only. NO -1/-2/-3/FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GJ_one_click_m1.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GJ_one_click_m1.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GJ PREFLIGHT PASS. One 02 button is authorized for 24 hours.
) else (
    echo P10GJ PREFLIGHT STOP. DO NOT run 02. Send P10GJ_01_RESULT.txt.
)
echo No text or path input required. Close this window using X.
exit /b %CHECK_EXIT%
