@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HK: REAL M0/M1 4D MECHANICAL KAPPA, DIRECT SCALAR-CALL TEST
echo NO GMSH, NO MESH, NO FEM. Requires Python with numpy only.
python p10hk_direct_kappa_callback_benchmark.py > P10HK_RESULT.json 2> P10HK_ERROR.txt
if errorlevel 1 goto :failed
echo PASS. Submit P10HK_RESULT.json.
type P10HK_RESULT.json
goto :done
:failed
echo P10HK STOP. Submit P10HK_ERROR.txt.
type P10HK_ERROR.txt
:done
pause
