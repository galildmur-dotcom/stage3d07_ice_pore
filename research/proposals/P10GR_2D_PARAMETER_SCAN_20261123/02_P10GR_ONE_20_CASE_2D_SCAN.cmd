@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GR ONE SHOT 20 CASE SURFACE ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GR 02: EXACTLY 20 Gmsh -2 cases, each max 90s/2GiB/2threads.
echo NEVER -3/FEM. Run only after explicit approval. One-shot markers are permanent.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 P10GR_scan.py --one-scan
) else (
    python P10GR_scan.py --one-scan
)
set "CHECK_EXIT=%ERRORLEVEL%"
echo P10GR_SCAN_EXIT=%CHECK_EXIT%
if exist P10GR_02_RESULT.txt type P10GR_02_RESULT.txt
echo Submit ONE P10GR_SCAN_EVIDENCE.zip or STOP text. DO NOT REPEAT 02.
exit /b %CHECK_EXIT%
