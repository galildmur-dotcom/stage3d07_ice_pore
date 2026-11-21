@echo off
setlocal
set "P10CA_TOOL=%~dp0"
echo P10CA R1 - ONE authorized physical H0, no H1/H2, no Git changes.
echo Source/worktree G:\ildar\Stage3D07 is READ ONLY.
echo TWO confirmations: PREPARE P10CA, then RUN ONE H0 P10CA.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%P10CA_TOOL%P10CA_Run_One_H0.ps1"
set "P10CA_EXIT=%ERRORLEVEL%"
echo.
echo P10CA script exit code: %P10CA_EXIT%
echo Press any key to close. Send P10CA_EVIDENCE.zip from the result folder.
pause >nul
exit /b %P10CA_EXIT%
