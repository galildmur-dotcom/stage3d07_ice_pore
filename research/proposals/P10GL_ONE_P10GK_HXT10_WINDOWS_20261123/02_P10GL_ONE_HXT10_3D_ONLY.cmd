@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GL ONE APPROVED P10GK HXT10 M1 NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GL_02_RESULT.txt"
> "%LOG%" echo P10GL 02: ONE user-approved new native Gmsh4.15.2 HXT10 -3. HARD 900s/private 8GiB, nt=2. NO FEM.
>nul echo Marker files are created before native Gmsh. NEVER retry after STOP.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GL_one_hxt10.py" --one-hxt10 >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GL_one_hxt10.py" --one-hxt10 >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GL 27QP PRELIMINARY ONLY. SEND ONE P10GL_M1_HXT10_EVIDENCE.zip. NO FEM GO.
) else (
    echo P10GL STOP. DO NOT REPEAT BUTTON 02. SEND EVIDENCE ZIP OR P10GL_02_RESULT.txt.
)
echo Close this window with X. No input required.
exit /b %CHECK_EXIT%
