@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HP: original immutable CAD + direct mechanical kappa, only 1D.
echo External child 120s guard, 300000 callback cap. NO 2D/3D/M2/FEM.
set "ENV_PY=.p10hp_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check_api
python -m venv --system-site-packages .p10hp_env > P10HP_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:check_api
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HP_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HP_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:run
"%ENV_PY%" P10HP_guard.py
echo Return P10HP_GUARD_RESULT.json and P10HP_GMSH_LOG.txt.
echo If present, also P10HP_RESULT.json or P10HP_WORKER_ERROR.txt.
goto :done
:install_failed
echo P10HP INSTALL STOP before Gmsh: return P10HP_INSTALL_LOG.txt
:done
pause
