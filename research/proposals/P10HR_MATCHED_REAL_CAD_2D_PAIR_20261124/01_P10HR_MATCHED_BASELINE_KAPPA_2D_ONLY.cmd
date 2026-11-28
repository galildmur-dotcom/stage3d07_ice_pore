@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HR - matched original Field7 vs direct mechanical kappa.
echo Two bounded 2D surface runs only. NO 3D/M2/FEM.
set "ENV_PY=.p10hr_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check
python -m venv --system-site-packages .p10hr_env > P10HR_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:check
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HR_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HR_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:run
"%ENV_PY%" P10HR_guard.py
echo Send P10HR_GUARD_RESULT.json, P10HR_GMSH_LOG.txt and P10HR_RESULT.json, if present.
goto :done
:failed
echo P10HR STOP before Gmsh - send P10HR_INSTALL_LOG.txt.
:done
pause
