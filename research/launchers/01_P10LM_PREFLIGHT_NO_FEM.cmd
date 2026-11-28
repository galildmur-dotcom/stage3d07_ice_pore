@echo off
if /I "%~1"=="--visible" goto RUN
start "P10LM M9 PREFLIGHT + WINDOWS HEARTBEAT TEST NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
echo P10LM_PREPARE_START source SHA101, M9 geometry, 65-second native watchdog test
echo P10LM_PREPARE_DOES_NOT_COMPILE_OR_RUN_FEM_OR_CONSUME_MARKER
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10LM_WORK\P10LM_M9_TWO_TERM.py --watchdog-selftest
) else (
  python -u P10LM_WORK\P10LM_M9_TWO_TERM.py --watchdog-selftest
)
set "P10LM_RC=%ERRORLEVEL%"
echo P10LM_PREFLIGHT_AND_WATCHDOG_EXIT=%P10LM_RC%
exit /b %P10LM_RC%
