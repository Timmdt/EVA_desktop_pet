@echo off
cd /d "%~dp0"

echo ==========================================
echo       EVA Desktop Pet - Installation
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python wurde nicht gefunden.
    echo Installiere Python 3.11 oder 3.12 und aktiviere "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Virtuelle Umgebung wird erstellt...
    py -m venv .venv
)

echo [2/3] PySide6 wird installiert...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [3/3] Fertig.
echo.
echo Starte EVA jetzt mit run.bat
pause
