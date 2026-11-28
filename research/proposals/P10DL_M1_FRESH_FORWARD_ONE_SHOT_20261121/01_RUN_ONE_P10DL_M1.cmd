@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 P10DL_one_click_m1.py
) else (
  python P10DL_one_click_m1.py
)
set "P10DL_EXIT=%ERRORLEVEL%"
echo.
echo P10DL finished with exit %P10DL_EXIT%.
echo If one-shot was consumed, NEVER repeat. Return P10DL_EVIDENCE.zip or STOP log.
pause
exit /b %P10DL_EXIT%
