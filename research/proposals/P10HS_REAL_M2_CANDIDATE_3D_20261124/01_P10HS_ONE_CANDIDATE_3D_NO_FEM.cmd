@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo P10HS: ONE original CAD 3D Tet10 M2 candidate only.
echo NO FEM, NO automatic acceptance, NO repeat. External guard 600s.
set "ENV_PY=.p10hs_env\Scripts\python.exe"
if exist "%ENV_PY%" goto :check
python -m venv --system-site-packages .p10hs_env > P10HS_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:check
"%ENV_PY%" -c "import gmsh; assert gmsh.__version__=='4.15.2'; import numpy" >> P10HS_INSTALL_LOG.txt 2>&1
if not errorlevel 1 goto :run
"%ENV_PY%" -m pip install --disable-pip-version-check --only-binary=:all: --no-deps gmsh==4.15.2 >> P10HS_INSTALL_LOG.txt 2>&1
if errorlevel 1 goto :failed
:run
"%ENV_PY%" P10HS_guard.py
echo If finished, send P10HS_M2_UNVERIFIED_CANDIDATE_EVIDENCE.zip.
echo If stopped, send P10HS_GUARD_RESULT.json, P10HS_GMSH_LOG.txt, P10HS_WORKER_ERROR.txt.
goto :done
:failed
echo P10HS STOP before Gmsh. Send P10HS_INSTALL_LOG.txt.
:done
pause
