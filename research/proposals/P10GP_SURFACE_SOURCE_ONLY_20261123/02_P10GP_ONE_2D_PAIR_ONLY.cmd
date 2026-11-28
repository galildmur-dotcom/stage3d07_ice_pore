@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GP ONE PAIR 2D ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GP 02: TWO native Gmsh -2 max 120s/2GiB each; NO -3/FEM.
echo RUN ONLY AFTER EXPLICIT APPROVAL. Do not repeat after STOP.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 P10GP_windows_2d.py --one-2d-pair
) else (
    python P10GP_windows_2d.py --one-2d-pair
)
set "P10GP_EXIT=%ERRORLEVEL%"
echo P10GP_2D_EXIT=%P10GP_EXIT%
if exist P10GP_02_RESULT.txt type P10GP_02_RESULT.txt
echo Send ONE P10GP_2D_EVIDENCE.zip. Never repeat 02.
exit /b %P10GP_EXIT%
