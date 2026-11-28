@echo off
setlocal
echo P10FN: verifying source, approvals, and adaptation recipe; no FEM or Gmsh.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0P10FN_check.py"
) else (
    python "%~dp0P10FN_check.py"
)
exit /b %ERRORLEVEL%
