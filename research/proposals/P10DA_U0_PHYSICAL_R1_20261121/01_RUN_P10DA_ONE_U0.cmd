@echo off
setlocal
cd /d "%~dp0"
echo P10DA: one PHYSICAL solve on the existing 2mm uniform U0.
echo Checks pinned U0 mesh and pinned existing EXE. NO Gmsh, no rebuild, no remeshing.
echo Physical solver starts ONLY if you type RUN ONE U0 P10DA after safe checks.
where py.exe >nul 2>nul
if errorlevel 1 goto with_python
py -3 "%~dp0P10DA_run_one_u0.py"
set "P10DA_EXIT=%ERRORLEVEL%"
goto finish
:with_python
python "%~dp0P10DA_run_one_u0.py"
set "P10DA_EXIT=%ERRORLEVEL%"
:finish
echo.
echo P10DA native wrapper exit: %P10DA_EXIT%
echo Send only P10DA_EVIDENCE.zip from P10DA_RESULTS, not the mesh or huge solver output.
pause
exit /b %P10DA_EXIT%
