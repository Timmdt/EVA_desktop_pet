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

Pro Zustand werden zwei Sheets zu acht Originalbildern verbunden. Für Tanzen
wird stattdessen das neue `assets/dancing_v2.png` mit einem 4×2-Raster verwendet;
die acht Posen werden auf dieselbe Größe und Grundlinie ausgerichtet. Beim Start
werden mit OpenCV drei bewegungsbasierte Zwischenbilder je Übergang erzeugt,
auch vom letzten Bild zurück zum ersten (32 Frames pro Zustand). Die Pixel
werden verschoben statt zwei Posen zu überblenden; Farben und Transparenz
bleiben erhalten. Bei stark unterschiedlichen Posen können sich Details am
Wechsel zwischen den beiden Ausgangsbildern noch sichtbar ändern.

In `eva_pet.py` steuert `INTERMEDIATE_FRAMES` die Zahl der Zwischenbilder und
`ANIMATION_SPEED` das Tempo. Der Standardwert `0.65` verlangsamt Sprite-Animation
und Schweben um 35 Prozent. Mehr Zwischenbilder erhöhen die Bildrate, nicht das
Bewegungstempo. Die Berechnung aller Zustände kann beim Start einige Sekunden
dauern. Nach einem Update installiert `install.bat` die benötigten Pakete.

Idle und Verstecken behandeln ihre kurzen Blinzelposen getrennt von der
Körperbewegung: Die Zwischenbilder behalten offene Augen, das geschlossene
Originalbild erscheint nur für einen Bildschritt (standardmäßig etwa 77 ms).
Nur die Augenbereiche werden ersetzt; Körpertempo, Mund und Schweben behalten
ihren langsamen Ablauf. Die Tanzposen haben durchgehend offene Augen und
zusammenpassende Armbewegungen, damit beim Interpolieren keine unterschiedlichen
Gesichtsausdrücke ineinander verzogen werden.

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
