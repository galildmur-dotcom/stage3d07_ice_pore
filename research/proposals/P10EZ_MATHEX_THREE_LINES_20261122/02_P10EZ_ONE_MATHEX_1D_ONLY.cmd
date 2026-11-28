@echo off
setlocal
cd /d "%~dp0"
py -3 P10EZ_one_click_1d.py --mode one-1d
echo.
echo NEVER run button 02 twice, even after a STOP.
pause
exit /b %ERRORLEVEL%
