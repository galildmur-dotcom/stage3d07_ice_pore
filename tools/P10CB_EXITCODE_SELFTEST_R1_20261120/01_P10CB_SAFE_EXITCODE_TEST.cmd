@echo off
setlocal
echo P10CB - safe native exit-code diagnosis on existing P10CA EXE.
echo NO FEM, NO MESH, NO PREFLIGHT, NO BUILD, NO GIT CHANGES.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CB_Test_ExitCode.ps1"
set "P10CB_EXIT=%ERRORLEVEL%"
echo.
echo P10CB script exit: %P10CB_EXIT%
echo Send exactly one P10CB_EVIDENCE.zip from new result folder.
pause
exit /b %P10CB_EXIT%
