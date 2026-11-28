@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HT R2: one original CAD 3D candidate, Gmsh pore-probe radial extension.
echo Physical ice C2 unchanged. NO FEM. 600 s external guard.
set "ENV_PY=.p10ht_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check
python -m venv --system-site-packages .p10ht_env > P10HT_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:check
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HT_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HT_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:run
"%ENV_PY%" P10HT_guard.py
echo If finished, return P10HT_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip.
echo If stopped, return P10HT_GUARD_RESULT.json, P10HT_GMSH_LOG.txt and P10HT_WORKER_ERROR.txt.
goto :done
:failed
echo P10HT STOP before Gmsh - send P10HT_INSTALL_LOG.txt.
:done
pause
