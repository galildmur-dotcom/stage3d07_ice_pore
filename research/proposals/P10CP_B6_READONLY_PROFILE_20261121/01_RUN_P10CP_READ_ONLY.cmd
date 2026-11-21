@echo off
setlocal EnableExtensions DisableDelayedExpansion
title P10CP - ORIGINAL MESH SIZE PROFILE - READ ONLY - NO FEM
echo ================================================================
echo P10CP R1 - One Click READ-ONLY profile of original pinned meshes
echo NO GMSH, NO REMESH, NO FEM, NO WRITES TO G: OR F:
echo ================================================================
echo.
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo RESULT=P10CP_STOP_POWERSHELL_NOT_FOUND
  pause
  exit /b 2
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0P10CP_launch.ps1"
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
echo Send ONLY the freshly created P10CP_EVIDENCE.zip after a PASS.
echo No source meshes are included in that ZIP.
pause
exit /b %RC%
