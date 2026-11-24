@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HV - three independent 3D candidates alpha 0.15, 0.20, 0.25.
echo NO FEM, NO accepted M2, NO physics. 600s / 6M callbacks total.
set "ENV_PY=.p10hv_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check
python -m venv --system-site-packages .p10hv_env > P10HV_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:check
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HV_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HV_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:run
"%ENV_PY%" P10HV_guard.py
echo On PASS submit P10HV_THREE_ALPHA_3D_EVIDENCE.zip.
echo On STOP submit guard, Gmsh log and worker error if present.
goto :done
:failed
echo P10HV installation STOP before Gmsh; send P10HV_INSTALL_LOG.txt.
:done
pause
