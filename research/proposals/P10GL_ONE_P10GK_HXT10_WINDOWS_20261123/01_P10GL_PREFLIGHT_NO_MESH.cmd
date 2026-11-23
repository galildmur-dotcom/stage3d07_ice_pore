@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GL PREFLIGHT M0 AND P10GK SOURCE NO MESH" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GL_01_RESULT.txt"
> "%LOG%" echo P10GL 01: frozen M0 D-027 + P10GK source pins + native wrapper parse ONLY. NO -1/-2/-3/FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GL_one_hxt10.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GL_one_hxt10.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GL PREFLIGHT PASS. Button 02 may be run exactly ONCE within 24 hours.
) else (
    echo P10GL PREFLIGHT STOP. DO NOT run 02. Send P10GL_01_RESULT.txt.
)
echo Close this window with X. No input required.
exit /b %CHECK_EXIT%
