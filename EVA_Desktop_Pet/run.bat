@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo EVA Pet ist noch nicht eingerichtet.
    echo Fuehre zuerst install.bat aus.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" eva_pet.py
