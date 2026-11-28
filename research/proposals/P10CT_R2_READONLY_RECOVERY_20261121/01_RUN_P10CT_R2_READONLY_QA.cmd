@echo off
setlocal
cd /d "%~dp0"
echo P10CT R2: READ-ONLY audit of the EXISTING P10CT R1 U0 mesh.
echo No Gmsh, no FEM, no modifications of the existing .msh.
where py.exe >nul 2>nul
if errorlevel 1 goto with_python
py -3 "%~dp0P10CT_R2_readonly_runner.py"
set "P10CT_EXIT=%ERRORLEVEL%"
goto finished
:with_python
python "%~dp0P10CT_R2_readonly_runner.py"
set "P10CT_EXIT=%ERRORLEVEL%"
:finished
echo.
echo Exit code: %P10CT_EXIT%
pause
exit /b %P10CT_EXIT%
