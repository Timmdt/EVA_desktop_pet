@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Richte EVA beim ersten Start ein...
    py -m venv .venv
    if errorlevel 1 goto :error
)

if not exist ".venv\.eva_ready" (
    echo Installiere die benoetigten Pakete...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
    type nul > ".venv\.eva_ready"
)

start "EVA Desktop Pet" ".venv\Scripts\pythonw.exe" evaPet.py
exit /b 0

:error
echo.
echo EVA konnte nicht eingerichtet werden.
pause
exit /b 1
