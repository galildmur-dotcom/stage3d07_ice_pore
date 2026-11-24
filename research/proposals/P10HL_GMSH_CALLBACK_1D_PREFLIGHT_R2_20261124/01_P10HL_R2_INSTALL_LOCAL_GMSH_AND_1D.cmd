@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HL R2: local Python environment + pinned Gmsh 4.15.2 API
echo One synthetic 1D line ONLY. No original M1/M2, 2D/3D or FEM.
set "ENV_PY=.p10hl_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check_api
echo Creating isolated local Python environment, reusing installed NumPy...
python -m venv --system-site-packages .p10hl_env > P10HL_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :installation_failed
:check_api
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HL_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run_test
echo Installing pinned Gmsh API 4.15.2 into this folder only (Internet needed)...
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HL_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :installation_failed
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HL_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :installation_failed
:run_test
echo Running exact one-line Gmsh test...
"%ENV_PY%" P10HL_one_line_callback.py > P10HL_LOG.txt 2>&1
if errorlevel 1 goto :run_failed
echo P10HL R2 finished. Return P10HL_RESULT.json, P10HL_LOG.txt.
type P10HL_LOG.txt
goto :done
:installation_failed
echo P10HL R2 STOP before mesh; return P10HL_INSTALL_LOG.txt.
type P10HL_INSTALL_LOG.txt
goto :done
:run_failed
echo P10HL R2 STOP; return P10HL_ERROR.txt and P10HL_LOG.txt.
type P10HL_LOG.txt
:done
pause
