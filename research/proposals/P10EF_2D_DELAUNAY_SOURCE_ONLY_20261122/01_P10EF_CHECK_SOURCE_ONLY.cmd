@echo off
setlocal
cd /d "%~dp0"
echo P10EF SOURCE-ONLY SHA AND SINGLE-LINE DIFF CHECK, NO GMSH, NO FEM
py -3 "%~dp0P10EF_SOURCE_CHECK.py" --check
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo P10EF_SOURCE_STOP RC=%RC%
if "%RC%"=="0" echo P10EF_SOURCE_CHECK_PASS_NO_GMSH_NO_FEM
pause
exit /b %RC%
