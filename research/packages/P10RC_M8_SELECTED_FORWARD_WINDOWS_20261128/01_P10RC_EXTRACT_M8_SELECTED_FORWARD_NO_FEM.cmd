@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "P10RC_CACHE=G:\ildar\Stage3D07\LOCAL_RUNS\P10KV_M8_R_DT25_20261125_053635_154561\P10FN_M8_DT25_R\forward_history.bin"
set "P10RC_OUT=%~dp0P10RC_OUTPUT"
echo P10RC: M8 read-only selective forward history export, NO FEM / NO ADJOINT.
echo Original cache: "%P10RC_CACHE%"
if not exist "%P10RC_CACHE%" (
  echo P10RC_STOP: Original forward_history.bin not found in observed P10RB location.
  exit /b 2
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0p10rc_m8_selected_forward_export.py" --cache "%P10RC_CACHE%" --mesh "%~dp0M8.msh" --selection "%~dp0P10RA_M8_REAL_PHYSICAL_ALGOIM_PILOT_SELECTION_QA.json" --out-dir "%P10RC_OUT%"
  if errorlevel 1 exit /b 2
  exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0p10rc_m8_selected_forward_export.py" --cache "%P10RC_CACHE%" --mesh "%~dp0M8.msh" --selection "%~dp0P10RA_M8_REAL_PHYSICAL_ALGOIM_PILOT_SELECTION_QA.json" --out-dir "%P10RC_OUT%"
  if errorlevel 1 exit /b 2
  exit /b 0
)
echo P10RC_STOP: Python 3 not found. No calculation has started.
exit /b 2
