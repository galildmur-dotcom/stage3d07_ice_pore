@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HQ: one real CAD 2D surface test, direct 4D mechanical kappa.
echo External timeout 180s; callback cap 1000000; NO 3D/M2/FEM.
set "ENV_PY=.p10hq_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check_api
python -m venv --system-site-packages .p10hq_env > P10HQ_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:check_api
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HQ_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HQ_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:run
"%ENV_PY%" P10HQ_guard.py
echo Return P10HQ_GUARD_RESULT.json, P10HQ_GMSH_LOG.txt and P10HQ_RESULT.json if generated.
goto :done
:install_failed
echo P10HQ STOP BEFORE MESH - return P10HQ_INSTALL_LOG.txt.
:done
pause
