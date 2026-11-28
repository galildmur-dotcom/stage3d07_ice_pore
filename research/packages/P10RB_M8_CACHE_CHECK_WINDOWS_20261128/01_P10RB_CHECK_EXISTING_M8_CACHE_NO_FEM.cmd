@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "P10RB_SCRIPT=%~dp0p10rb_m8_forward_cache_inventory.py"
set "P10RB_OUT=%~dp0P10RB_M8_CACHE_INVENTORY.json"
set "P10RB_RUNS=G:\ildar\Stage3D07\LOCAL_RUNS"

echo P10RB_START: checking existing M8 history only.
echo P10RB_NO_GMSH_NO_FEM_NO_ADJOINT_NO_HISTORY_COPY
echo P10RB_RUNS_ROOT: %P10RB_RUNS%
if not exist "%P10RB_SCRIPT%" (
    echo P10RB_STOP: Python file not found next to this CMD.
    exit /b 2
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%P10RB_SCRIPT%" --runs-root "%P10RB_RUNS%" --output "%P10RB_OUT%"
) else (
    python "%P10RB_SCRIPT%" --runs-root "%P10RB_RUNS%" --output "%P10RB_OUT%"
)
set "P10RB_EXIT=%ERRORLEVEL%"
if not "%P10RB_EXIT%"=="0" (
    echo P10RB_STOP: inventory failed with exit code %P10RB_EXIT%.
    exit /b %P10RB_EXIT%
)
if not exist "%P10RB_OUT%" (
    echo P10RB_STOP: expected JSON output missing.
    exit /b 3
)
echo P10RB_PASS: source-only read-only cache inventory finished.
echo P10RB_SEND_FILE: %P10RB_OUT%
exit /b 0
