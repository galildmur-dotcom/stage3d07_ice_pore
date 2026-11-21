@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stage3D07 P10DO - READ ONLY M1 LABEL + GMSH PARSE
echo.
echo P10DO R1: READ-ONLY accepted M1 and native Gmsh GEO parse only.
echo Verify exact M1 SHA, label all 9736 Tet10, test 27QP QA.
echo NO 3D M2 mesh. NO FEM. No P10DO one-shot marker consumed.
echo.
where py.exe >nul 2>nul
if not errorlevel 1 goto USING_PY
where python.exe >nul 2>nul
if not errorlevel 1 goto USING_PYTHON
echo P10DO STOP: Python 3 not found.
set "RC=2"
goto DONE
:USING_PY
py -3 "%~dp0P10DO_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:USING_PYTHON
python "%~dp0P10DO_one_click_m2.py" --preflight-only
set "RC=%ERRORLEVEL%"
goto DONE
:DONE
echo.
echo P10DO preflight exit: %RC%
echo Send small P10DO_EVIDENCE.zip if STOP occurs.
echo Do not run second button if this preflight fails.
pause
exit /b %RC%
