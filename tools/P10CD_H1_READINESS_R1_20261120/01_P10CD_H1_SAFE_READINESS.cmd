@echo off
setlocal
echo P10CD - exact H1 mesh and existing EXE SHA readiness. READ-ONLY, NO FEM.
echo Do not modify G:\ildar\Stage3D07 or run any solver.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CD_Check_H1.ps1"
set "P10CD_EXIT=%ERRORLEVEL%"
echo.
echo P10CD exit code: %P10CD_EXIT%
echo Send ONE P10CD_EVIDENCE.zip from the newly created P10CD_RESULTS folder.
echo Press any key to close.
pause >nul
exit /b %P10CD_EXIT%
