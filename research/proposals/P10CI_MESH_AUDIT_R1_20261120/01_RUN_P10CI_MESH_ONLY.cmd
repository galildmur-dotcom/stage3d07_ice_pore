@echo off
setlocal EnableExtensions DisableDelayedExpansion
title P10CI - READ ONLY MESH GEOMETRY AUDIT - NO FEM

echo =========================================================
echo P10CI R1 - mesh-only read-only, WITHOUT FEM OR REMESHING
echo =========================================================
echo Reading only three pinned files in G:\ildar\Stage3D07\P10M_MESHES
echo Outputs will be NEW local folders beside this CMD.
echo No file in G: is written or changed.
echo.

if not exist "G:\ildar\Stage3D07\P10M_MESHES" (
  echo STOP: original P10M_MESHES directory is not found.
  echo Do not copy or rename meshes for this test. Contact the assistant.
  pause
  exit /b 2
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -V >nul 2>&1
  if not errorlevel 1 (
    py -3 "%~dp0P10CI_mesh_audit.py" --mesh-root "G:\ildar\Stage3D07\P10M_MESHES" --indicator "%~dp0P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
    if errorlevel 1 (set "RC=2") else (set "RC=0")
    goto :DONE
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  python -V >nul 2>&1
  if not errorlevel 1 (
    python "%~dp0P10CI_mesh_audit.py" --mesh-root "G:\ildar\Stage3D07\P10M_MESHES" --indicator "%~dp0P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
    if errorlevel 1 (set "RC=2") else (set "RC=0")
    goto :DONE
  )
)

echo STOP: Python 3 launcher was not found, or Python cannot start.
echo No FEM or mesh operations were attempted.
set "RC=2"

:DONE
echo.
echo P10CI command exit code: %RC%
echo If an EVIDENCE path is shown, send ONLY that small ZIP.
echo Keep all original meshes and old run directories untouched.
pause
exit /b %RC%
