@echo off
setlocal
cd /d "%~dp0"
py -3 P10FB_one_click_m2.py --preflight-only
echo.
echo Only after PASS may the one-shot button 02 be considered.
pause
exit /b %ERRORLEVEL%
