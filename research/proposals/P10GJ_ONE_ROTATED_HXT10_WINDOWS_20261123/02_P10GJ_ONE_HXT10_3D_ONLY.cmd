@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GJ ONE HXT10 - result" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GJ_02_RESULT.txt"
> "%LOG%" echo P10GJ 02: ONE protected Gmsh 4.15.2 HXT10 -3 M1 candidate, no FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GJ_one_click_m1.py" --one-hxt10 >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GJ_one_click_m1.py" --one-hxt10 >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GJ one mesh preliminary QA PASS. Send ONE P10GJ_M1_HXT10_EVIDENCE.zip.
) else (
    echo P10GJ STOP. NEVER rerun 02 or remove markers.
    echo Send newest P10GJ_M1_HXT10_EVIDENCE.zip if present.
    echo Otherwise send P10GJ_02_RESULT.txt.
)
echo No text or path input required. Close this window using X.
exit /b %CHECK_EXIT%
