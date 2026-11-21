@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1

if exist "C:\Program Files\Python313\python.exe" (
    "C:\Program Files\Python313\python.exe" "%~dp0p10bf_collect_provenance.py"
    goto done
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0p10bf_collect_provenance.py"
    goto done
)

echo P10BF_STOP: Python 3 was not found.
pause
exit /b 2

:done
set "P10BF_RC=%errorlevel%"
if not "%P10BF_RC%"=="0" (
    echo P10BF_STOP: see the error message above.
) else (
    echo P10BF_EXPORT_COMPLETED. Upload the P10BF_EVIDENCE_EXPORT_*.zip file.
)
pause
exit /b %P10BF_RC%
