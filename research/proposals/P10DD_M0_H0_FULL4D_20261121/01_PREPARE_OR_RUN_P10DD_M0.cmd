@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 P10DD_one_click_h0.py
) else (
  python P10DD_one_click_h0.py
)
echo.
echo P10DD complete or STOP. Read P10DD_OUTPUT, do not repeat a physical attempt.
pause
