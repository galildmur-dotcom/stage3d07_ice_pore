@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HL NATIVE GMSH CALLBACK PREFLIGHT
echo ONE SYNTHETIC 1D LINE ONLY. NO ORIGINAL CAD/M1/M2. NO 2D/3D/FEM.
python P10HL_one_line_callback.py > P10HL_LOG.txt 2>&1
if errorlevel 1 goto :failed
echo P10HL RUN FINISHED - return P10HL_RESULT.json and P10HL_LOG.txt
type P10HL_LOG.txt
goto :done
:failed
echo P10HL STOP - return P10HL_ERROR.txt and P10HL_LOG.txt
type P10HL_LOG.txt
:done
pause
