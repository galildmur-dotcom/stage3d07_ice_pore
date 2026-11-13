@echo off
setlocal
chcp 65001 >nul
echo === P10AA: curved pore surface comparison (no FEM) ===
py -3 "%~dp0p10aa_surface_identity.py" --selftest
if errorlevel 1 (
  echo P10AA STOP: selftest error.
  pause
  exit /b 1
)
py -3 "%~dp0p10aa_surface_identity.py" --gui
if errorlevel 1 (
  echo P10AA STOP: review error output above.
  pause
  exit /b 1
)
echo P10AA completed. Upload the short zip from PORE_CHATGPT_EXPORTS.
pause
