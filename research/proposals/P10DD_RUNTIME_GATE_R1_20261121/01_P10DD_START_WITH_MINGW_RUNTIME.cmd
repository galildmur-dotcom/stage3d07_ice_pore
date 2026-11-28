@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 P10DD_runtime_gate.py
) else (
  python P10DD_runtime_gate.py
)
set "P10DD_EXIT=%ERRORLEVEL%"
echo.
echo P10DD_RUNTIME_GATE finished with exit %P10DD_EXIT%.
echo If a physical attempt started, never repeat it blindly. Send P10DD_EVIDENCE.zip or STOP.
pause
exit /b %P10DD_EXIT%
