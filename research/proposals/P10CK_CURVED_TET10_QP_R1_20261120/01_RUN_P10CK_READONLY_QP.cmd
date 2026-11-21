@echo off
setlocal EnableExtensions DisableDelayedExpansion
title P10CK R1 - curved Tet10 27QP mesh-only (NO FEM)
pushd "%~dp0" || (echo STOP: Cannot open extracted package folder.& pause & exit /b 2)
echo.
echo P10CK R1: READ-ONLY geometry on THREE pinned Gmsh2 meshes.
echo PHYSICAL FEM=0, REMESH=0, GIT MUTATION=0.
echo Source G: meshes are READ ONLY. Results appear next to this CMD.
echo Duration estimate: 3-15 minutes, hard guard 15 minutes after input checks.
echo Memory estimate: under 1.5 GiB, preliminary; stop if PC becomes unstable.
echo ONE ATTEMPT ONLY. Do NOT rerun this package after STOP.
echo.
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if errorlevel 1 goto no_python
python P10CK_curved_qp_audit.py --mesh-root "G:\ildar\Stage3D07\P10M_MESHES" --reference-dir "%CD%\reference" --time-budget-seconds 900
goto done
:use_py
py -3 P10CK_curved_qp_audit.py --mesh-root "G:\ildar\Stage3D07\P10M_MESHES" --reference-dir "%CD%\reference" --time-budget-seconds 900
goto done
:no_python
echo RESULT=P10CK_NO_PYTHON_STOP
echo Install Python3 or report this STOP. Do not switch tools automatically.
goto failed
:done
if errorlevel 1 goto failed
echo.
echo RESULT=P10CK_ONE_SHOT_PASS_OR_REVIEW_DETAILS_IN_EVIDENCE
echo Send ONLY newest P10CK_RUNS/P10CK_*/P10CK_EVIDENCE.zip to ChatGPT.
goto end
:failed
echo.
echo STOP. Send one newest P10CK_RUNS/P10CK_*/P10CK_EVIDENCE.zip if created,
echo or the exact final STOP line. DO NOT rerun this R1 directory.
:end
popd
pause
endlocal
