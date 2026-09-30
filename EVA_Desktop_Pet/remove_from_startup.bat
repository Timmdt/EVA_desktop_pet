@echo off
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\EVA Desktop Pet.lnk"

if exist "%LINK%" (
    del "%LINK%"
    echo EVA Desktop Pet wurde aus dem Autostart entfernt.
) else (
    echo Kein Autostart-Eintrag gefunden.
)

pause
