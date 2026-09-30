# EVA Desktop Pet

Ein kleiner Desktop-Pet-Prototyp für Windows — noch komplett ohne EVA-Agent.

## Enthalten

- transparente Pixel-Sprite-Animation
- Always-on-top
- per Maus verschiebbar
- Mausrad verändert die Größe
- Klick auf EVA -> kurz fröhlich
- Rechtsklick -> Emotionen / Display-Modus / Optionen
- automatische kleine Idle-Aktionen
- Position und Größe werden gespeichert
- System-Tray-Icon
- externe Mini-Schnittstelle für den späteren Desktop-Agent

## Installation

1. Ordner entpacken.
2. `install.bat` doppelklicken.
3. Danach `run.bat` starten.

Python 3.11 oder 3.12 ist ideal.

## Bedienung

### Verschieben
Linke Maustaste halten und EVA ziehen.

### Größe
Maus über EVA und Mausrad drehen.

### Emotionen
Rechtsklick auf EVA:

- Idle
- Fröhlich
- Neugierig
- Traurig
- Zum Display schauen

### Auto-Emotionen
Im Rechtsklick-Menü aktivieren/deaktivieren.

### Klick
Ein normaler Linksklick macht EVA für kurze Zeit fröhlich.

### Beenden
Rechtsklick -> `EVA Pet beenden`.

Wenn du EVA versteckst, bleibt sie im System-Tray.

## Aus der Konsole steuern

Während das Pet läuft:

```powershell
python control_pet.py happy 3
python control_pet.py curious 5
python control_pet.py display 8
python control_pet.py sad
python control_pet.py idle
```

Die Zahl ist die Dauer in Sekunden. Ohne Dauer bleibt der Zustand aktiv.

Genau diese Schnittstelle kann später dein Desktop-Agent benutzen.

## Windows-Autostart

`add_to_startup.bat` starten.

Entfernen:

`remove_from_startup.bat`

## Assets

`assets/`

- idle.png
- happy.png
- curious.png
- sad.png
- display.png

Alle Sprite-Sheets bestehen aus vier Frames nebeneinander.

## Späterer EVA-Agent

Später kann EVA z.B. automatisch:

```text
denkt          -> curious
spricht        -> happy / speaking
arbeitet       -> display
Fehler         -> sad/confused
wartet         -> idle
```

setzen.

Dafür muss der Agent zunächst nur dieselbe `pet_command.json`-Schnittstelle bedienen.
