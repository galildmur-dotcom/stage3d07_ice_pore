@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "P10IB_HERE=%~dp0"
set "P10IB_DIAG=%P10IB_HERE%P10IB_LAUNCH_DIAGNOSTICS.txt"
cd /d "%P10IB_HERE%"
if errorlevel 1 (
  echo P10IB_STOP: cannot enter package directory.
  pause
  exit /b 2
)
echo P10IB: guarded original CAD 2D only; NO 3D and NO FEM.
echo P10IB R2 STARTED > "%P10IB_DIAG%"
echo Directory: %CD% >> "%P10IB_DIAG%"
if exist "P10IB_ONE_2D_ATTEMPT_CONSUMED.marker" (
  echo P10IB_STOP: one-shot marker exists. DO NOT rerun the native attempt.
  echo P10IB_STOP: marker already exists; no Python executed. >> "%P10IB_DIAG%"
  goto P10IB_FINISH_STOP
)
where python >> "%P10IB_DIAG%" 2>&1
if errorlevel 1 (
  echo P10IB_STOP: Python not on PATH.
  echo P10IB_STOP: Python not on PATH. >> "%P10IB_DIAG%"
  goto P10IB_FINISH_STOP
)
python --version >> "%P10IB_DIAG%" 2>&1
if errorlevel 1 (
  echo P10IB_STOP: Python executable did not start.
  goto P10IB_FINISH_STOP
)
python -c "import gmsh; print('Gmsh Python version:', gmsh.__version__)" >> "%P10IB_DIAG%" 2>&1
if errorlevel 1 (
  echo P10IB_STOP: Gmsh Python import failed. See diagnostics.
  goto P10IB_FINISH_STOP
)
python P10IB_2D_guard.py >> "%P10IB_DIAG%" 2>&1
set "P10IB_EXIT=%ERRORLEVEL%"
if not "%P10IB_EXIT%"=="0" (
  echo P10IB_STOP: guarded run failed or was blocked. See diagnostics.
  goto P10IB_FINISH_STOP
)
echo P10IB COMPLETE: send P10IB_2D_ONLY_EVIDENCE.zip.
echo P10IB COMPLETE >> "%P10IB_DIAG%"
goto P10IB_FINISH
:P10IB_FINISH_STOP
echo P10IB STOP: send P10IB_LAUNCH_DIAGNOSTICS.txt and existing guard/log/error files.
:P10IB_FINISH
echo.
echo ---------------- DIAGNOSTICS ----------------
type "%P10IB_DIAG%"
echo ---------------------------------------------
echo This window stays open until you press a key.
pause
endlocal
