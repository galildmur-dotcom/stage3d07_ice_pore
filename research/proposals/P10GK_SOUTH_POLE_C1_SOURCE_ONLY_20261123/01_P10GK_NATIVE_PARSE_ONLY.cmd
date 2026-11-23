@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GK SOURCE + GMSH PARSE ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
set "LOG=%~dp0P10GK_01_RESULT.txt"
> "%LOG%" echo P10GK R1: source-only C1 field QA + native Gmsh parse_and_exit. NO MESH. NO FEM.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10GK_source_qa.py" --preflight >> "%LOG%" 2>&1
) else (
    python "%~dp0P10GK_source_qa.py" --preflight >> "%LOG%" 2>&1
)
set "CHECK_EXIT=%ERRORLEVEL%"
>> "%LOG%" echo CHECK_EXIT_CODE=%CHECK_EXIT%
type "%LOG%"
if "%CHECK_EXIT%"=="0" (
    echo P10GK SOURCE + NATIVE PARSE ONLY PASS. NO NEW MESH, NO FEM.
) else (
    echo P10GK SOURCE PARSE STOP. Send P10GK_01_RESULT.txt. DO NOT MESH.
)
echo Do not attempt native Gmsh -3 without separate research authorization.
echo Close this window with X. No user input needed.
exit /b %CHECK_EXIT%
