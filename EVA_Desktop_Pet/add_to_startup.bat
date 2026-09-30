@echo off
set "PETDIR=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LINK=%STARTUP%\EVA Desktop Pet.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%LINK%'); $s.TargetPath = '%PETDIR%run.bat'; $s.WorkingDirectory = '%PETDIR%'; $s.Save()"

echo EVA Desktop Pet wurde dem Windows-Autostart hinzugefuegt.
pause
