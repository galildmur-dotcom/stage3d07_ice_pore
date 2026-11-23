@echo off
if /I "%~1"=="--visible" goto RUN
start "P10GT ONE HXT10 3D ONLY" cmd.exe /K call "%~f0" --visible
exit /b %ERRORLEVEL%
:RUN
setlocal
cd /d "%~dp0"
echo P10GT 02: one native Gmsh HXT10 -3; 900s, RAM 8GiB, -nt 2.
echo Native FEM forbidden; permanent one-shot markers before Gmsh.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 P10GT_hxt10.py --one-3d
) else (
  python P10GT_hxt10.py --one-3d
)
set "RC=%ERRORLEVEL%"
echo P10GT_3D_EXIT=%RC%
if exist P10GT_02_RESULT.txt type P10GT_02_RESULT.txt
echo SEND ONE P10GT_HXT10_EVIDENCE.zip. NEVER REPEAT 02, EVEN ON STOP.
exit /b %RC%
