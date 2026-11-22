@echo off
setlocal
cd /d "%~dp0"
py -3 P10FB_one_click_m2.py --one-m2
echo.
echo NEVER run button 02 again after any outcome.
pause
exit /b %ERRORLEVEL%
