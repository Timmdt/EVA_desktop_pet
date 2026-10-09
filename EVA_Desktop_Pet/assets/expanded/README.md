# Erweiterte EVA-Animationen

Die neuen 4x4-Sprite-Sheets werden getrennt von den Originalen in diesem
Verzeichnis abgelegt. Dies ist ein bewusst optionales Upgrade: Fehlen neue
Bilddateien, verwendet EVA automatisch die bisherigen Originalbilder.

## Installieren

1. Das Archiv `EVA_Chat_Animationen_GitHub.zip` aus dem Chat herunterladen.
2. Das Archiv im Repository-Hauptverzeichnis entpacken. Die Dateien gehören
   nach `EVA_Desktop_Pet/assets/expanded/` und nicht direkt in `assets/`.
3. Die entpackten PNG-Dateien und die `manifest.json` committen.
4. Die geänderte `eva_pet.py` und `expanded_sprites.py` verwenden.

Die Quelldateien wurden nach SHA-256 dedupliziert. Die bereits im Repo
vorhandenen originalen `idle_*.png`, `display_*.png` und `dancing_*.png`
bleiben unverändert. Insgesamt sind 22 eindeutige neu generierte 4x4-Sheets
im Archiv, daneben eine vom Nutzer zur Verfügung gestellte Bett-Referenz.

## Verhalten

- Alle neuen Raster werden einheitlich in 16 Posen (4 Spalten, 4 Reihen)
  ausgeschnitten; alte Sheets nutzen weiterhin ihre jeweilige Loader-Logik.
- EVA interpoliert weiterhin mit OpenCV zwischen den echten Posen.
- Die Schleifendauer bleibt gleich; die 16 Schlüsselbilder werden mit der
  doppelten Originalbild-Kadenz abgespielt.
- Die alten speziellen Blink-Patches werden nur für ursprüngliche Assets
  angewendet, nicht auf die neuen 4x4-Sheets.
- Die neuen Sheets werden nicht anhand ihrer wechselnden äußeren Alpha-
  Silhouetten zentriert. Dies vermeidet ein häufiges Bild-Shifting.
- Einige KI-Sheets wurden aus schwarzem Hintergrund freigestellt; die
  dunklen Gesichtspartien sollten vor dem produktiven Einsatz geprüft werden.

Hinweis: Nicht jedes KI-generierte 4x4-Sheet hat perfekte pose-to-pose-Kohärenz.
Insbesondere die Übergänge 16 -> 1 benötigen bei Bedarf manuelle Korrektur.
