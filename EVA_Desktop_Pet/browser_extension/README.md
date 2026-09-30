# EVA Media Detector

Diese lokale Chrome-/Edge-Erweiterung meldet EVA ausschließlich, ob auf einer
HTTPS-Webseite gerade ein Video abgespielt wird. URLs, Titel und Verlauf werden
nicht an EVA übertragen.

## Installation in Chrome

1. `chrome://extensions` öffnen.
2. Oben rechts den **Entwicklermodus** aktivieren.
3. **Entpackte Erweiterung laden** auswählen.
4. Diesen Ordner `browser_extension` auswählen.

## Installation in Edge

1. `edge://extensions` öffnen.
2. **Entwicklermodus** aktivieren.
3. **Entpackt laden** auswählen.
4. Diesen Ordner `browser_extension` auswählen.

EVA muss laufen, damit die Erweiterung den Status an
`http://127.0.0.1:8765/media-state` senden kann.

Solange noch keine Popcorn-Sprites vorhanden sind, verwendet EVA bei laufenden
Videos die vorhandene `display`-Animation.
