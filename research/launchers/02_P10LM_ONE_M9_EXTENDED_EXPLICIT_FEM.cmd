@echo off
if /I "%~1"=="--visible" goto RUN
start "P10LM M9 ONE FULL4D FEM 36x25" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
echo P10LM_ONE_M9_FEM_START one-shot, do not run twice
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10LM_WORK\P10LM_M9_TWO_TERM.py --run
) else (
  python -u P10LM_WORK\P10LM_M9_TWO_TERM.py --run
)
set "P10LM_RC=%ERRORLEVEL%"
echo P10LM_ONE_SHOT_EXIT=%P10LM_RC%
exit /b %P10LM_RC%
