@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 (
  echo P10IB_SETUP_STOP: cannot enter folder.
  pause
  exit /b 2
)
set "P10IB_SETUP_LOG=%CD%\P10IB_PYTHON_GMSH_SETUP_LOG.txt"
echo P10IB Python Gmsh 4.15.2 setup started > "%P10IB_SETUP_LOG%"
echo Only Python dependency installation, NO mesh, NO FEM.
python --version >> "%P10IB_SETUP_LOG%" 2>&1
if errorlevel 1 goto P10IB_SETUP_STOP
python -m pip --version >> "%P10IB_SETUP_LOG%" 2>&1
if errorlevel 1 goto P10IB_SETUP_STOP
echo Installing Gmsh 4.15.2 in current user's Python packages. Please wait.
python -m pip install --user --disable-pip-version-check gmsh==4.15.2 >> "%P10IB_SETUP_LOG%" 2>&1
if errorlevel 1 goto P10IB_SETUP_STOP
python -c "import gmsh; assert gmsh.__version__ == '4.15.2', gmsh.__version__; print('P10IB_PYTHON_GMSH_4_15_2_OK')" >> "%P10IB_SETUP_LOG%" 2>&1
if errorlevel 1 goto P10IB_SETUP_STOP
echo P10IB_SETUP_OK: Python gmsh 4.15.2 installed. Launch 01_P10IB_ONE_ORIGINAL_CAD_2D_NO_FEM.cmd separately.
goto P10IB_SETUP_END
:P10IB_SETUP_STOP
echo P10IB_SETUP_STOP: see P10IB_PYTHON_GMSH_SETUP_LOG.txt; do not launch the mesh yet.
:P10IB_SETUP_END
echo.
type "%P10IB_SETUP_LOG%"
echo.
echo Window remains open until a key is pressed.
pause
endlocal
