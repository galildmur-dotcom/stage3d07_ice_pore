@echo off
setlocal
cd /d "%~dp0"
py -3 P10EZ_one_click_1d.py --mode preflight
echo.
echo Please keep this window and the evidence archive.
pause
exit /b %ERRORLEVEL%
