@echo off
setlocal
cd /d "%~dp0"
echo P10EW: corrected C1 StrCat safe native GEO parse ONLY.
echo No native -3, no M2 generation, no FEM, no one-shot marker consumption.
py -3 P10EW_safe_parse_only.py --safe-parse
set "stage3d07_exit=%ERRORLEVEL%"
echo.
echo Exit code: %stage3d07_exit%
echo Send the new P10EW_EVIDENCE.zip from P10EW_R1_PARSE_RUNS to ChatGPT.
echo Do NOT launch any 02 buttons inside P10EV_PINNED_PARENT.
pause
exit /b %stage3d07_exit%
