# EVA Desktop Pet

EVA erscheint als transparente Idle-Animation auf dem Desktop.

## Starten

Unter Windows einfach `start_pet.bat` doppelt anklicken. Beim ersten Start wird automatisch eine virtuelle Python-Umgebung angelegt und die benoetigten Pakete werden installiert.

Alternativ in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe evaPet.py
```

## Bedienung

- Mit der linken Maustaste ziehen: EVA verschieben
- Mausrad: Groesse aendern
- Rechtsklick: Groesse, Vordergrund-Modus und Beenden

Groesse und Position werden in `petState.json` gespeichert. Die 32 Animationsbilder werden beim ersten Start automatisch aus `assets/models/idle.png` erzeugt. Jeder Sprite wird dabei in einer gleich grossen transparenten Box zentriert, damit EVA zwischen den Frames nicht verspringt.
