@echo off
if /I "%~1"=="--visible" goto RUN
start "P10IQ M3 SOURCE PREFLIGHT NO FEM" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
cd /d "%~dp0"
echo P10IQ_SOURCE_ONLY_NO_COMPILATION_NO_FEM
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u P10IQ_M3_SOURCE_ONLY_PREFLIGHT.py
) else (
  python -u P10IQ_M3_SOURCE_ONLY_PREFLIGHT.py
)
set "RC=%ERRORLEVEL%"
echo P10IQ_PREFLIGHT_EXIT=%RC%
exit /b %RC%
