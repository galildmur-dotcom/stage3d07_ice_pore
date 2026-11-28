@echo off
setlocal
set "P10BZ_ROOT=%~dp0"
echo P10BZ R1 - isolated Windows MinGW native tests, NO FEM.
echo This tool never patches or builds in G:\ildar\Stage3D07.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%P10BZ_ROOT%P10BZ_Run_Native.ps1"
set "P10BZ_EXIT=%ERRORLEVEL%"
echo.
echo P10BZ script exit code: %P10BZ_EXIT%
echo Press any key to close. Results folder is shown above.
pause >nul
exit /b %P10BZ_EXIT%
