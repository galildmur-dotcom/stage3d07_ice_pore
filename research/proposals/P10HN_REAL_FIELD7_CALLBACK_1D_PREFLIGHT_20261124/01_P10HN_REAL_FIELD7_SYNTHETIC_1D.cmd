@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HN - pinned P10GT Field[7] native callback diagnostic.
echo One synthetic 1D line only; NO original CAD, M1, M2, 2D/3D or FEM.
set "ENV_PY=.p10hn_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check_api
python -m venv --system-site-packages .p10hn_env > P10HN_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:check_api
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HN_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HN_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :install_failed
:run
"%ENV_PY%" P10HN_real_field7_callback.py > P10HN_LOG.txt 2>&1
if errorlevel 1 goto :test_failed
echo P10HN completed. Return P10HN_RESULT.json and P10HN_LOG.txt.
type P10HN_LOG.txt
goto :done
:install_failed
echo P10HN STOP BEFORE MESH - submit P10HN_INSTALL_LOG.txt
goto :done
:test_failed
echo P10HN STOP - submit P10HN_ERROR.txt and P10HN_LOG.txt
type P10HN_LOG.txt
:done
pause
