@echo off
setlocal
cd /d "%~dp0"
echo P10EX: ONE newly authorized M2 native 3D mesh ONLY.
echo The one-shot local and Windows profile markers will be permanent.
echo DO NOT RUN THIS TWICE OR REMOVE MARKERS EVEN AFTER FAILURE.
echo FEM / forward / adjoint / H0 / old meshes untouched.
py -3 P10EX_one_click_m2.py --one-m2
set "stage3d07_exit=%ERRORLEVEL%"
echo.
echo P10EX ONE M2 3D exit: %stage3d07_exit%
echo Send ONLY P10EX_EVIDENCE.zip; M2 raw included when <= 32 MiB.
echo Never launch this 02 again.
pause
exit /b %stage3d07_exit%
